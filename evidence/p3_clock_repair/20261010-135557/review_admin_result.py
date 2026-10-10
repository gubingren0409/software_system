"""One-off read-only postprocessing of this admin review; never runs a probe/campaign."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import (
    acceptance, acceptance_exit, atomic_write_json, load, sha256_file, snapshot_campaign,
)
from scripts.start_p3_first_seed import auxiliary_identity
from autotuner.session import valid_formal_gate

BATCH = Path(__file__).resolve().parent
BASE = "e4f93333bf48b0d4c82cd8568110a7101240f15c"
AUX = "fa597017c2317772a0f7f34faa75194ffecec8f2"
ADMIN = ROOT / "evidence/p3_clock_repair/admin-20261010-135245/admin-session.txt"


def main():
    output = BATCH / "independent_acceptance.json"
    if output.exists():
        raise ValueError("Refusing to replace this batch's independent acceptance")
    errors = []
    start = load(BATCH / "start.json")
    admin_bytes = ADMIN.read_bytes()
    admin = admin_bytes.decode("utf-8-sig").replace("\x00", "")
    if hashlib.sha256(admin_bytes).hexdigest() != start["admin_raw_sha256"]:
        errors.append("Original administrator transcript changed")
    if (BATCH / "admin-session.readable.txt").read_bytes() != admin.encode("utf-8"):
        errors.append("NUL-removal derivative does not match original")
    operations = {}
    for path in sorted((BATCH / "operations").glob("*.operation.json")):
        operation = load(path)
        if operation["schema"] != "p3-captured-operation-v2" or operation["batch_id"] != BATCH.name:
            errors.append("Operation batch/schema mismatch: " + path.name)
        for stream in ("stdout", "stderr"):
            if sha256_file(path.parent / operation[stream + "_path"]) != operation[stream + "_sha256"]:
                errors.append("Raw stream changed: " + path.name + " " + stream)
        elapsed = (operation["qpc_end"] - operation["qpc_start"]) / operation["qpc_frequency"]
        if elapsed <= 0 or elapsed != operation["qpc_seconds"]:
            errors.append("QPC delta mismatch: " + path.name)
        operations[operation["operation_kind"]] = operation
    required = {"git_fetch_github", "windows_time_status", "formal_resources", "partial_campaign_audit", "frozen_files", "formal_process_state_tokens"}
    if not required.issubset(operations):
        errors.append("Missing required review operation")

    status = (BATCH / "operations/windows_time_status.stdout.txt").read_bytes().decode("gb18030")
    atomic_write_json(BATCH / "windows_time_status.readable.json", {"encoding": "gb18030", "stdout": status})
    gate = load(BATCH / "operations/formal_resources.stdout.txt")
    gate_op = operations["formal_resources"]
    protocol = load(ROOT / "configs/measurement_protocol.json")
    gate_pass = gate_op["returncode"] == 0 and not gate_op["timed_out"] and valid_formal_gate(gate, protocol)
    gate_limits = protocol["resource_gate"]
    gate_checks = {
        "host_memory": gate["host_minimum_available_bytes"] >= gate_limits["formal_host_minimum_available_bytes"],
        "wsl_memory": gate["wsl_available_bytes"] >= gate_limits["formal_wsl_minimum_available_bytes"],
        "root_disk": gate["wsl_root_free_bytes"] >= gate_limits["formal_wsl_root_minimum_free_bytes"],
        "host_cpu_average": gate["host_cpu_average_percent"] <= gate_limits["formal_host_cpu_average_maximum_percent"],
        "host_cpu_single_sample": gate["host_cpu_maximum_percent"] <= gate_limits["formal_host_cpu_single_sample_maximum_percent"],
    }
    if gate_pass != load(BATCH / "resource_gate_review.json")["formal_gate_pass"]:
        errors.append("Saved gate decision contradicts raw gate")
    expected = load(BATCH / "frozen_expectations.json")["expected"]
    actual = {line.split(maxsplit=1)[1].strip(): line.split()[0]
              for line in (BATCH / "operations/frozen_files.stdout.txt").read_text(encoding="utf-8").splitlines()}
    frozen_pass = operations["frozen_files"]["returncode"] == 0 and actual == expected
    if not frozen_pass:
        errors.append("Frozen identities differ")
    aux = auxiliary_identity(AUX)
    if aux != load(BATCH / "auxiliary_identity.json"):
        errors.append("Auxiliary source changed during review")

    # Reuse the earlier byte-hash inventory, not a new duplicated multi-MB ledger.
    prior = ROOT / "evidence/p3_clock_repair/20261010-121004"
    inventory_path = prior / "protected_files_before.json"
    inventory = load(inventory_path)["files"]
    changed = [relative for relative, item in inventory.items()
               if not (ROOT / relative).is_file() or sha256_file(ROOT / relative) != item["runtime_sha256"]]
    # The immediately preceding batch explicitly disabled EOL conversion. Compare
    # all its Git blobs to execution bytes, including its inventory and manifests.
    tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)",
                                    BASE, "--", str(prior.relative_to(ROOT)).replace("\\", "/")], cwd=ROOT)
    objects = [line.decode("utf-8").split("\t", 1) for line in tree.splitlines()]
    blobs = subprocess.check_output(["git", "cat-file", "--batch"],
                                   input=b"".join((blob + "\n").encode() for blob, _ in objects), cwd=ROOT)
    offset = 0
    for blob, relative in objects:
        end = blobs.index(b"\n", offset)
        header = blobs[offset:end].decode("ascii").split()
        length = int(header[2])
        original = blobs[end + 1:end + 1 + length]
        offset = end + 2 + length
        if not (ROOT / relative).is_file() or (ROOT / relative).read_bytes() != original:
            changed.append(relative)
    if changed:
        errors.append("Protected history changed")
    before, after = load(BATCH / "campaign_before.json"), snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb")
    atomic_write_json(BATCH / "campaign_after_review.json", after)
    same = all(before[key] == after[key] for key in ("checkpoint", "checkpoint_sha256", "checkpoint_lf_sha256", "trajectories"))
    if not same:
        errors.append("Campaign checkpoint/observations/JSONL changed")
    audit = load(BATCH / "partial_campaign_audit/audit.json")
    if operations["partial_campaign_audit"]["returncode"] != 0 or audit["status"] != "PASS":
        errors.append("Existing partial campaign auditor rejected")
    assert re.search(r"Leap\s+指示符:\s+3", status)
    assert "resync_exit_code=0" in admin and "没有可用的时间数据" in admin

    process_state = load(BATCH / "operations/formal_process_state_tokens.stdout.txt")
    if operations["formal_process_state_tokens"]["returncode"] != 0 or process_state["formal_processes"] or process_state["runner_lock_state"] != "available":
        errors.append("Formal process/lock state not verified idle")
    partial = []
    complete_sample_count = retest_count = 0
    for name, trajectory in after["trajectories"].items():
        checkpoint = trajectory["checkpoint"]
        complete_sample_count += sum(len(group["samples"]) for group in checkpoint["observations"])
        retest_count += len(checkpoint["independent_retests"])
        records = [json.loads(line) for line in (ROOT / "evidence/p3/campaign-e308bfb/trajectories" / name / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line]
        scored = {group["attempt_id"] for group in checkpoint["observations"]}
        for group in checkpoint["abandoned_attempts"] + ([checkpoint["active"]] if checkpoint["active"] else []):
            selected = [record for record in records if record["attempt_id"] == group["attempt_id"]]
            if len(selected) != group["sample_count"] or group["attempt_id"] in scored:
                errors.append("Partial attempt count/score mismatch")
            partial.append({"attempt_id": group["attempt_id"], "sample_count": len(selected),
                "state": "pending_restart" if group is checkpoint["active"] else "abandoned",
                "process_wall_seconds": sum(record["process_wall_seconds"] for record in selected)})
    execution_complete = audit["completed_trajectory_count"] >= 2 and len(audit["prefix_rows"]) >= 6
    flags = acceptance(not errors, execution_complete, False)
    intervals = sorted((op["qpc_start"] / op["qpc_frequency"], op["qpc_end"] / op["qpc_frequency"])
                       for op in operations.values())
    union = 0.0
    low, high = intervals[0]
    for begin, end in intervals[1:]:
        if begin > high:
            union += high - low
            low, high = begin, end
        else:
            high = max(high, end)
    union += high - low
    result = {
        **flags, "schema": "p3-admin-result-independent-review-v1", "batch": BATCH.name,
        "acceptance_scope": "Supplied admin log, current gate/status, source identity and preserved history only; NOT a recovery certificate",
        "audit_baseline": BASE, "auxiliary_content_commit": AUX, "postprocessor_sha256": sha256_file(Path(__file__)),
        "postprocessing_corrections": "Initial one-off postprocessor passed str to a Path-only hash function; initial substring process check matched its own timeout parent. Initial source/streams/exit are retained; final process classification uses argv tokens. Reviewed fa59701 helpers and clock probes were not changed or rerun.",
        "initial_postprocessor_sha256": sha256_file(BATCH / "review_admin_result_initial.py"),
        "errors": errors, "admin_log_sha256": sha256_file(ADMIN),
        "admin_review": {"service": "Running", "configuration_source_peers_output_present": True,
            "configuration_source_peers_native_returncodes": "unknown (not recorded)",
            "existing_source": "time.windows.com,0x9", "server_change_evidence": False,
            "resync_attempt_observed": True, "resync_exact_flags": "unknown (command not echoed)",
            "recorded_resync_exit_code": 0, "resync_native_exit_code_reliability": "unknown (no invocation script/native operation record)",
            "resync_message": "没有可用的时间数据", "post_leap": 3, "post_stratum": 0,
            "post_last_sync_error": 1, "updated_last_success_field_is_not_sync_proof": True,
            "treatment_result": "failed_or_ambiguous; current status remains unsynchronized",
            "administrator_operation_elapsed_seconds": "unknown (no QPC; wall clock moved backwards)"},
        "current_status_query_returncode": operations["windows_time_status"]["returncode"],
        "formal_gate": gate, "formal_gate_returncode": gate_op["returncode"],
        "formal_resource_gate_pass": gate_pass, "resource_limit_checks": gate_checks,
        "frozen_identity_pass": frozen_pass, "frozen_identity_count": len(expected),
        "auxiliary_sources_unchanged": True, "protected_inventory_reference": str(inventory_path.relative_to(ROOT)),
        "protected_inventory_sha256": sha256_file(inventory_path),
        "protected_inventory_file_count": len(inventory), "prior_batch_exact_git_byte_count": len(objects),
        "changed_protected_files": changed, "checkpoint_run_ids_observations_unchanged": same,
        "campaign_content_commit": after["checkpoint"]["fingerprint"]["content_commit"],
        "session_id": after["checkpoint"]["session_id"],
        "raw_execution_count": audit["raw_execution_count"], "complete_configuration_count": len(audit["configuration_rows"]),
        "complete_trajectory_count": audit["completed_trajectory_count"], "budget_result_rows": len(audit["prefix_rows"]),
        "complete_group_sample_count": complete_sample_count, "independent_retest_groups": retest_count,
        "partial_groups": partial, "partial_groups_not_scored": not any("Partial" in error for error in errors),
        "formal_process_state": process_state,
        "original_teacher_c_sha256": sha256_file(ROOT / "code/original/matrix_multiplication.c"),
        "new_recovery_status": "not_performed_prerequisites_rejected", "new_clock_intervals": 0,
        "new_resume_status": "not_performed", "new_formal_executions": 0,
        "recovery_eligible": False, "blockers": ["Administrator resync failed/unclear and current Leap=3", "Formal CPU average 14.2% exceeds 10%"],
        "historical_cost_seconds": audit["cost_seconds"],
        "this_batch_campaign_cost_delta_seconds": 0, "this_batch_retest_cost_seconds": 0,
        "this_batch_abandoned_cost_delta_seconds": 0, "this_batch_new_formal_wait_seconds": 0,
        "recorded_auxiliary_qpc_union_seconds_before_postprocessing": union,
        "cost_scope": "Recorded capture intervals only; excludes this postprocessor, editing/model/offline/commit/push. Formal gate is nested in auxiliary union, not added to it. Historical costs retain uncalibrated MONOTONIC scope.",
        "require_two_exit_code": acceptance_exit(flags, require_two=True),
    }
    atomic_write_json(output, result)
    print(json.dumps({key: result[key] for key in (*flags, "require_two_exit_code", "blockers", "changed_protected_files")}, ensure_ascii=True))
    return acceptance_exit(flags, require_two=True)


if __name__ == "__main__":
    raise SystemExit(main())
