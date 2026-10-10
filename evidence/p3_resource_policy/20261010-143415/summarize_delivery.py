"""Read-only batch conclusion, protection and nested costs; never runs a target/probe."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file
from scripts.p3_clock_contract import atomic_write_json, load, snapshot_campaign, verify_recovery

BATCH = Path(__file__).resolve().parent
BASE = "aae4147f1e246c5fb115060ef484df625b611e3d"


def main():
    fixed = load(BATCH / "corrected_session_plan.json")
    clean = load(BATCH / ("clean-" + fixed["content_commit"][:8]) / "summary.json")
    actual = load(BATCH / "independent_resume_e0353bf.json")
    before = load(BATCH / "legacy_campaign_before.json")
    old = snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb")
    assert before["checkpoint"] == old["checkpoint"] and before["trajectories"] == old["trajectories"]
    inventory = load(ROOT / "evidence/p3_clock_repair/20261010-121004/protected_files_before.json")["files"]
    selected = {p: v for p, v in inventory.items() if p.startswith(("evidence/", "code/"))}
    changed = [p for p, v in selected.items() if not (ROOT / p).is_file() or sha256_file(ROOT / p) != v["runtime_sha256"]]
    assert not changed, changed
    protected = ["evidence/p3_clock_repair/20261010-121004", "evidence/p3_clock_repair/20261010-135557",
                 "evidence/p3_clock_repair/admin-20261010-135245"]
    tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)", BASE, "--", *protected], cwd=ROOT)
    items = [line.decode().split("\t", 1) for line in tree.splitlines()]
    blobs = subprocess.check_output(["git", "cat-file", "--batch"], cwd=ROOT,
        input=b"".join((blob + "\n").encode() for blob, _ in items))
    offset = 0
    for blob, relative in items:
        end = blobs.index(b"\n", offset); size = int(blobs[offset:end].split()[2])
        assert (ROOT / relative).read_bytes() == blobs[end + 1:end + 1 + size], relative
        offset = end + 2 + size
    subprocess.run(["git", "diff", "--exit-code", BASE, "--", "evidence/p2", "evidence/p3", "evidence/p3_clock_contract",
        "evidence/p3_audit_0023ceed", "evidence/p3_clock_repair", "code", "autotuner/core.py", "autotuner/measurement.py",
        "autotuner/search.py", "configs/target.json", "configs/config_space.json", "configs/search_protocol.json",
        "configs/timing_audit_protocol.json", "scripts/check_p2_clocks.py"], cwd=ROOT, check=True)
    attempted = snapshot_campaign(BATCH / "campaign-e0353bfd")
    corrected = snapshot_campaign(Path(fixed["campaign_directory"]))
    assert not corrected["trajectories"] and corrected["checkpoint"]["status"] == "initialized"
    assert corrected["checkpoint"]["session_id"] == fixed["session_id"]
    assert corrected["checkpoint"]["preflight_identity"]["content_commit"] == fixed["content_commit"]
    assert not attempted["trajectories"] and clean["pass"]
    reviewed = verify_recovery(BATCH / "recovery")
    assert reviewed["recovery_eligible"]  # Certifies e0353bf only, never the corrected session.
    windows = reviewed["windows"]
    checks = [{"window": name, **row} for name, value in windows.items() for row in value["checks"]]
    assert len(checks) == 20
    recovery_gate = load(BATCH / "recovery/resources.stdout.txt")
    formal_gate = load(BATCH / "resume/resources.stdout.txt")
    collector_failure = load(BATCH / "diagnosis/exact_gate_launch_bytes.stdout.txt")
    assert collector_failure["returncode"] == 1
    assert actual["controller"]["campaign_returncode"] == 1
    ops, intervals = [], []
    for path in sorted(BATCH.rglob("*.operation.json")):
        if path.name.startswith("delivery_analysis"):
            continue  # This analysis cannot include its own unfinished capture.
        record = load(path)
        assert type(record["returncode"]) is int, str(path)
        for stream in ("stdout", "stderr"):
            assert sha256_file(path.parent / record[stream + "_path"]) == record[stream + "_sha256"], str(path)
        assert record["qpc_seconds"] == (record["qpc_end"] - record["qpc_start"]) / record["qpc_frequency"]
        intervals.append((record["qpc_start"] / record["qpc_frequency"], record["qpc_end"] / record["qpc_frequency"]))
        ops.append({"path": path.relative_to(BATCH).as_posix(), "sha256": sha256_file(path),
                    "returncode": record["returncode"], "seconds": record["qpc_seconds"]})
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], end)
        else: merged.append([start, end])
    process = load(BATCH / "final_checks/process_state_corrected.stdout.txt")
    assert not process["formal_processes"] and process["runner_lock_available"]
    frozen = load(ROOT / "evidence/p3_clock_repair/20261010-135557/frozen_expectations.json")["expected"]
    actual_frozen = {line.split(maxsplit=1)[1].strip(): line.split()[0]
        for line in (BATCH / "final_checks/legacy_frozen_files.stdout.txt").read_text().splitlines()}
    assert actual_frozen == frozen
    result = {"schema": "p3-resource-policy-delivery-v1", "status": "P3_PARTIAL",
        "blocker": "Runner fixed after the sole recovery; corrected content/session needs a newly authorized bound recovery, not reused old proof.",
        "policy_version": recovery_gate["policy_version"], "policy_hash": recovery_gate["policy_hash"],
        "actual_executed_batch_acceptance": {k: actual[k] for k in ("evidence_integrity_pass", "execution_complete", "timing_checks_pass", "comparison_ready")},
        "corrected_current_session_acceptance": {"evidence_integrity_pass": True, "execution_complete": False,
            "timing_checks_pass": False, "comparison_ready": False, "timing_status": "not_performed", "formal_gate_status": "not_performed"},
        "actual_content_commit": attempted["checkpoint"]["preflight_identity"]["content_commit"],
        "attempted_session_id": attempted["checkpoint"]["session_id"], "corrected_session": fixed,
        "clock": {"interval_count": len(checks), "monotonic_raw_failures": sum(not r["monotonic_raw_pass"] for r in checks),
            "realtime_raw_failures": sum(not r["realtime_raw_pass"] for r in checks),
            "monotonic_raw_difference_range_seconds": [min(r["monotonic_raw_difference_seconds"] for r in checks), max(r["monotonic_raw_difference_seconds"] for r in checks)],
            "windows_host_checks": {name: value["host_check"] for name, value in windows.items()},
            "actual_resume_boundary_checks": {name: {"pass": value["pass"], "interval_count": len(value["checks"]), "host_check": value["host_check"]}
                for name, value in actual["boundary_clock_checks"].items()}, "all_recovery_rows": checks},
        "actual_resource_gates": {"Recovery": recovery_gate, "Formal": formal_gate},
        "progress": {"legacy_complete_configs": sum(len(v["checkpoint"]["observations"]) for v in old["trajectories"].values()),
            "legacy_raw_executions": sum(v["sample_count"] for v in old["trajectories"].values()), "legacy_partial_abandoned": 3,
            "legacy_partial_pending_restart": 2, "new_complete_configs": 0, "new_raw_executions": 0,
            "new_complete_trajectories": 0, "new_retests": 0, "remaining_first_seed_configurations": 24},
        "history_protection": {"inventory_evidence_and_code_raw_hash_count": len(selected), "later_exact_git_byte_count": len(items),
            "legacy_frozen_identity_count": len(frozen), "checkpoint_jsonl_run_ids_observations_pause_marker_unchanged": True,
            "teacher_sha256": sha256_file(ROOT / "code/original/matrix_multiplication.c")},
        "costs": {"new_formal_target_execution_seconds": 0, "new_retest_seconds": 0, "new_abandoned_target_seconds": 0,
            "failed_campaign_checkpoint_active_seconds": attempted["checkpoint"]["active_total_seconds"],
            "failed_campaign_checkpoint_gate_wait_seconds": attempted["checkpoint"]["wait_seconds"],
            "failed_campaign_full_host_call_seconds": load(BATCH / "resume/campaign.operation.json")["qpc_seconds"],
            "checkpoint_scope": "Uncaught failure tail was not accumulated. Zero saved wait is not zero actual collection cost. Host full call includes startup, not the same interval as WSL checkpoint active.",
            "recovery_full_host_entry_seconds": load(BATCH / "execution/recovery_entry.operation.json")["qpc_seconds"],
            "resume_full_host_entry_seconds": load(BATCH / "execution/resume_entry.operation.json")["qpc_seconds"],
            "actual_recovery_gate_host_seconds": load(BATCH / "recovery/resources.operation.json")["qpc_seconds"],
            "actual_formal_gate_host_seconds": load(BATCH / "resume/resources.operation.json")["qpc_seconds"],
            "recorded_auxiliary_qpc_union_seconds": sum(end - start for start, end in merged),
            "scope": "All capture intervals merged, not summed across nested wrappers; diagnostic C, initialization, gates and clock captures included. Excludes this analysis, later verification, editing/model/offline/git push and unrecorded preparation. End-to-end prefix cost unknown.",
            "legacy_campaign_active_seconds_unchanged": old["checkpoint"]["active_total_seconds"],
            "legacy_campaign_gate_wait_seconds_unchanged": old["checkpoint"]["wait_seconds"]},
        "captured_operations": ops, "process_state": process, "analysis_source_sha256": sha256_file(Path(__file__))}
    atomic_write_json(BATCH / "delivery_analysis.json", result)
    print(json.dumps({"status": result["status"], "clock_intervals": len(checks), "history_files": len(selected) + len(items),
                      "current_session": fixed["session_id"], "formal_targets": 0}))


if __name__ == "__main__":
    main()
