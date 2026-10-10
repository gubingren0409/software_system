"""Windows entry point: bounded recovery, then the unchanged first-seed campaign."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, sha256_json, utc_now
from autotuner.session import valid_formal_gate, source_identity
from autotuner.resources import valid_gate
from scripts.p3_clock_contract import (ARCHIVE, CRITERIA_SHA, FORMAL_CONTENT, POWERSHELL,
    PROBE_SHA, SESSION, acceptance, atomic_write_json, campaign_command, capture, check_clock_intervals, load,
    probe_command, snapshot_campaign, verify_clock_evidence, verify_recovery, wsl_path)

CAMPAIGN = ROOT / "evidence/p3/campaign-e308bfb"
AUXILIARY_FILES = ["scripts/p3_clock_contract.py", "scripts/start_p3_first_seed.py",
    "scripts/resume_p3_first_seed.ps1", "scripts/audit_p3_first_seed.py",
    "scripts/record_p3_first_seed_checks.py", "tests/test_first_seed_audit.py", "tests/test_p3_clock_contract.py"]


def complete(snapshot):
    names = ("00_random_20261008", "01_greedy_20261008")
    return snapshot["checkpoint"]["status"] == "batch_complete" and all(
        name in snapshot["trajectories"] and snapshot["trajectories"][name]["checkpoint"]["status"] == "complete" and
        len(snapshot["trajectories"][name]["checkpoint"]["observations"]) == 12 for name in names)


def first_failure(state, reason):
    if state["failure_reason"] is None:
        state["failure_reason"] = reason
    else:
        state["additional_failures"].append(reason)


def auxiliary_identity(commit):
    if len(commit) != 40:
        raise ValueError("Require exact auxiliary content SHA")
    tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)",
                                   commit, "--", *AUXILIARY_FILES], cwd=ROOT, text=True)
    blobs = {path: blob for blob, path in (line.split("\t", 1) for line in tree.splitlines())}
    if set(blobs) != set(AUXILIARY_FILES):
        raise ValueError("Required auxiliary files missing from content commit")
    return source_identity(ROOT, blobs)


def frozen_source_expectations(previous, repo_root=ROOT):
    """The later diagnostic criteria belong to the auxiliary tree, not e308bfb."""
    expected = dict(previous)
    expected[ARCHIVE + "/scripts/check_p2_clocks.py"] = PROBE_SHA
    expected[wsl_path(Path(repo_root) / "configs/timing_audit_protocol.json")] = CRITERIA_SHA
    return expected


def recovery_outcome(integrity, timing, resource):
    if not timing:
        return "P3_CLOCK_BLOCKED", "The declared twenty-interval clock review failed"
    if not integrity:
        return "P3_IDENTITY_BLOCKED", "Frozen file or evidence identity check failed"
    if not resource:
        return "P3_RESOURCE_BLOCKED", "Formal resource gate rejected"
    return "P3_RECOVERY_ELIGIBLE", None


def make_manifest(output, mode, commit, args=None):
    if args is not None and args.content_sha:
        return make_new_manifest(output, mode, commit, args)
    before = snapshot_campaign(CAMPAIGN)
    if before["checkpoint"]["session_id"] != SESSION or before["checkpoint"]["fingerprint"]["content_commit"] != FORMAL_CONTENT:
        raise ValueError("Original formal identity differs")
    atomic_write_json(output / "campaign_before.json", before)
    manifest = {"schema": "p3-clock-batch-v2", "auxiliary_controller_version": "2.1",
        "batch_id": uuid.uuid4().hex, "purpose": mode,
        "declared_at": utc_now(), "formal_content_commit": FORMAL_CONTENT, "session_id": SESSION,
        "repo_root_at_run": str(ROOT), "evidence_directory_at_run": str(output.resolve()),
        "auxiliary_content_commit": commit, "auxiliary_files": auxiliary_identity(commit),
        "criteria_sha256": CRITERIA_SHA, "probe_script_sha256": PROBE_SHA,
        "checker_sha256": sha256_file(ROOT / "scripts/p3_clock_contract.py"),
        "campaign_before_sha256": sha256_file(output / "campaign_before.json"), "operations": {}}
    names, count = (("window_A", "window_B"), 10) if mode == "recover" else (("clock_before", "clock_after"), 3)
    for name in names:
        manifest["operations"][name] = {"command": probe_command(output / (name + ".wsl.json"), count),
            "intervals": count, "seconds": 3, "output_file": name + ".wsl.json", "timeout_seconds": 120}
    manifest["operations"]["resources"] = {"command": [POWERSHELL, "-NoProfile", "-File",
        str(ROOT / "scripts/check_p2_resources.ps1"), "-Mode", "Formal"], "timeout_seconds": 90}
    manifest["operations"]["campaign"] = {"command": campaign_command(), "timeout_seconds": None}
    old = json.loads(subprocess.check_output(["git", "show",
        "fdeed77c43dcbbf74de46968055677f97fed8faf:evidence/p3/first-seed-review-20261009-1658/cache_and_archive_identity.json"], cwd=ROOT))
    expected = frozen_source_expectations(old["actual_sha256"])
    manifest["frozen_files_expected"] = expected
    manifest["operations"]["frozen_files"] = {"command": ["wsl.exe", "-d", "Ubuntu-24.04", "--", "sha256sum", *expected],
                                                   "timeout_seconds": 90}
    return manifest


def make_new_manifest(output, mode, commit, args):
    """New resource policy always binds a new real content/session, never e308bfb."""
    from scripts.p3_clock_contract import batch_identity
    identity = load(args.git_identity)
    if identity["content_sha"] != args.content_sha or commit != args.content_sha:
        raise ValueError("New auxiliary/archive/Git content identities differ")
    tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)",
                                   commit, "--", *identity["files"]], cwd=ROOT, text=True)
    actual_blobs = {path: blob for blob, path in (line.split("\t", 1) for line in tree.splitlines())}
    if actual_blobs != identity["files"]:
        raise ValueError("Git identity is not the specified content tree")
    before = snapshot_campaign(args.campaign_directory)
    preflight = before["checkpoint"]["preflight_identity"]
    if before["checkpoint"]["session_id"] != args.session_id or preflight["content_commit"] != args.content_sha or \
            {key: item["git_blob_sha1"] for key, item in preflight["files"].items()} != identity["files"]:
        raise ValueError("New session/archive source identity differs")
    atomic_write_json(output / "campaign_before.json", before)
    protocol = load(ROOT / "configs/measurement_protocol.json")
    if preflight["measurement_protocol_hash"] != sha256_json(protocol):
        raise ValueError("Initialized campaign uses a different protocol")
    atomic_write_json(output / "measurement_protocol.json", protocol)
    manifest = {"schema": "p3-clock-batch-v3", "auxiliary_controller_version": "3.0",
        "batch_id": uuid.uuid4().hex, "purpose": mode, "declared_at": utc_now(),
        "formal_content_commit": args.content_sha, "auxiliary_content_commit": commit,
        "session_id": args.session_id, "archive_directory": args.archive_directory,
        "git_identity_path": str(args.git_identity.resolve()), "git_identity_sha256": sha256_file(args.git_identity),
        "campaign_directory": str(args.campaign_directory.resolve()), "repo_root_at_run": str(ROOT),
        "evidence_directory_at_run": str(output.resolve()),
        "auxiliary_files": source_identity(ROOT, identity["files"]),
        "criteria_sha256": CRITERIA_SHA, "probe_script_sha256": PROBE_SHA,
        "checker_sha256": sha256_file(ROOT / "scripts/p3_clock_contract.py"),
        "measurement_protocol_hash": preflight["measurement_protocol_hash"],
        "resource_policy_hash": protocol["resource_gate"]["policy_hash"],
        "resource_gate_purpose": "Recovery" if mode == "recover" else "Formal",
        "campaign_before_sha256": sha256_file(output / "campaign_before.json"), "operations": {}}
    batch_identity(manifest)
    for name in (("window_A", "window_B") if mode == "recover" else ("clock_before", "clock_after")):
        count = 10 if mode == "recover" else 3
        manifest["operations"][name] = {"command": probe_command(output / (name + ".wsl.json"), count, archive=args.archive_directory),
            "intervals": count, "seconds": 3, "output_file": name + ".wsl.json", "timeout_seconds": 120}
    manifest["operations"]["resources"] = {"command": [POWERSHELL, "-NoProfile", "-File",
        str(ROOT / "scripts/check_p2_resources.ps1"), "-Mode", manifest["resource_gate_purpose"],
        "-RuntimeRoot", args.archive_directory], "timeout_seconds": 90}
    manifest["operations"]["campaign"] = {"command": campaign_command(ROOT, archive=args.archive_directory,
        content_sha=args.content_sha, git_identity=args.git_identity, campaign=args.campaign_directory,
        session_id=args.session_id), "timeout_seconds": None}
    expected = {args.archive_directory + "/" + relative: item["executed_sha256"] for relative, item in preflight["files"].items()}
    manifest["frozen_files_expected"] = expected
    manifest["operations"]["frozen_files"] = {"command": ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--",
        "timeout", "60", "sha256sum", *expected], "timeout_seconds": 90}
    return manifest


def run_probe(output, manifest, name):
    spec = manifest["operations"][name]
    capture(spec["command"], output, name, manifest["batch_id"], sha256_file(output / "manifest.json"), timeout=spec["timeout_seconds"])
    check = verify_clock_evidence(output, name, check_saved=False)
    atomic_write_json(output / (name + ".check.json"), check)
    return check


def verify_frozen_files(output, manifest):
    spec = manifest["operations"]["frozen_files"]
    operation = capture(spec["command"], output, "frozen_files", manifest["batch_id"],
                        sha256_file(output / "manifest.json"), timeout=spec["timeout_seconds"])
    try:
        actual = {line.split(maxsplit=1)[1].strip(): line.split()[0]
                  for line in (output / "frozen_files.stdout.txt").read_text().splitlines()}
    except (ValueError, IndexError):
        actual = {}
    passed = operation["returncode"] == 0 and not operation["timed_out"] and actual == manifest["frozen_files_expected"]
    atomic_write_json(output / "frozen_files.json", {"pass": passed, "expected": manifest["frozen_files_expected"], "actual": actual})
    return passed


def resources(output, manifest):
    spec = manifest["operations"]["resources"]
    operation = capture(spec["command"], output, "resources", manifest["batch_id"],
                        sha256_file(output / "manifest.json"), timeout=spec["timeout_seconds"])
    try:
        parsed = load(output / "resources.stdout.txt")
        protocol = load(output / "measurement_protocol.json") if manifest["schema"] == "p3-clock-batch-v3" else load(CAMPAIGN / "protocol.json")
        purpose = manifest.get("resource_gate_purpose", "Formal")
        valid = valid_gate(parsed, protocol, purpose) if manifest["schema"] == "p3-clock-batch-v3" else valid_formal_gate(parsed, protocol)
        passed = operation["returncode"] == 0 and not operation["timed_out"] and valid
        result = {"parsed": parsed, "pass": passed, "returncode": operation["returncode"]}
    except (ValueError, OSError) as error:
        result = {"pass": False, "error": str(error), "returncode": operation["returncode"]}
    atomic_write_json(output / "resource_gate.json", result)
    return result["pass"]


def metadata(output, manifest):
    capture(["C:/Windows/System32/w32tm.exe", "/query", "/status", "/verbose"],
            output, "windows_ntp_status", manifest["batch_id"], timeout=30)
    command = "$o=Get-CimInstance Win32_OperatingSystem; $events=@(); $eventError=$null; " \
        "try {$events=@(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddHours(-24);" \
        "ProviderName=@('Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter'," \
        "'Microsoft-Windows-Kernel-General','Microsoft-Windows-Time-Service')} -MaxEvents 30 -ErrorAction Stop | " \
        "Select-Object TimeCreated,Id,ProviderName)} catch {$eventError=$_.Exception.Message}; " \
        "[pscustomobject]@{version=$o.Version;build=$o.BuildNumber;boot=$o.LastBootUpTime.ToString('o');" \
        "events=$events;event_query_error=$eventError;event_scope='last 24h, at most 30 records; not proof of absence';" \
        "physical_clock_accuracy='unknown';clock_anomaly_root_cause='unknown'} | ConvertTo-Json -Depth 6"
    capture([POWERSHELL, "-NoProfile", "-Command", command], output, "windows_metadata", manifest["batch_id"], timeout=40)
    code = "import json,subprocess; cmds=[['uname','-a'],['cat','/etc/os-release'],['uptime','-s']," \
        "['cat','/sys/devices/system/clocksource/clocksource0/current_clocksource']," \
        "['timedatectl','show','-p','NTPSynchronized','-p','CanNTP','-p','NTP']]; out=[]\n" \
        "for c in cmds:\n p=subprocess.run(c,text=True,capture_output=True,timeout=5); " \
        "out.append({'command':c,'stdout':p.stdout,'stderr':p.stderr,'returncode':p.returncode})\n" \
        "print(json.dumps(out))"
    capture(["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--", "python3", "-c", code],
            output, "wsl_metadata", manifest["batch_id"], timeout=40)


def recovery(args):
    output = args.output
    manifest = make_manifest(output, "recover", args.auxiliary_sha, args)
    is_new = manifest["schema"] == "p3-clock-batch-v3"
    campaign = args.campaign_directory if is_new else CAMPAIGN
    policy = {"schema": "p3-clock-recovery-policy-v3" if is_new else "p3-clock-recovery-policy-v2", "declared_at": utc_now(), "batch_id": manifest["batch_id"],
        "windows": 2, "intervals_per_window": 10, "seconds_per_interval": 3, "total_interval_count": 20,
        "total_sleep_budget_seconds": 60, "probe_timeout_seconds": 120, "inner_probe_timeout_seconds": 90,
        "criteria_sha256": CRITERIA_SHA, "rule": "abs(MONO-RAW)<=0.005+0.01*RAW; REALTIME allowance unchanged",
        "all_twenty_required": True, "stop_after_failure": True, "no_extra_recovery_attempts": True,
        "conditional_resume_boundary_probes": "Only after recovery passes: one pre and one post, each 3x3s, per batch",
        "system_settings_modified": False, "calibration_applied": False,
        "resource_policy_hash": manifest.get("resource_policy_hash"), "ntp_sync_required": False}
    atomic_write_json(output / "policy.json", policy)
    manifest["policy_sha256"] = sha256_file(output / "policy.json")
    atomic_write_json(output / "manifest.json", manifest)
    identity_pass = verify_frozen_files(output, manifest)
    metadata(output, manifest)
    resource_pass = resources(output, manifest)
    checks = {name: run_probe(output, manifest, name) for name in ("window_A", "window_B")} if identity_pass and resource_pass else {}
    after = snapshot_campaign(campaign)
    atomic_write_json(output / "campaign_after.json", after)
    recomputed = verify_recovery(output, after)
    integrity, timing = recomputed["evidence_integrity_pass"], recomputed["timing_checks_pass"]
    status, reason = recovery_outcome(integrity, timing, resource_pass)
    if not checks:
        status, reason = ("P3_IDENTITY_BLOCKED", "Source identity rejected; clock probes not run") if not identity_pass else \
                         ("P3_RESOURCE_BLOCKED", "Recovery memory/disk/data gate rejected; clock probes not run")
    result = {**acceptance(integrity, complete(after), timing), "schema": "p3-recovery-summary-v3" if is_new else "p3-recovery-summary-v2",
        "auxiliary_controller_version": "3.0" if is_new else "2.1", "pre_clock_pass": None, "post_clock_pass": None,
        "campaign_invoked": False, "campaign_returncode": "unknown", "failure_reason": reason,
        "boundary_scope": "No actual campaign batch invoked; pre/post boundary checks not performed",
        "recovery_eligible": recomputed["recovery_eligible"],
        "formal_resource_gate_pass": None if is_new else resource_pass,
        "recovery_resource_gate_pass": resource_pass if is_new else None, "frozen_identity_pass": identity_pass,
        "clock_check_status": "performed" if checks else "not_performed",
        "windows": checks, "status": status,
        "auxiliary_content_commit": args.auxiliary_sha, "formal_content_commit": manifest["formal_content_commit"], "session_id": manifest["session_id"],
        "campaign_after_sha256": sha256_file(output / "campaign_after.json"),
        "integrity_errors": recomputed["errors"],
        "policy_sha256": sha256_file(output / "policy.json"), "manifest_sha256": sha256_file(output / "manifest.json")}
    # A recovery-only check is a prerequisite, not a certificate for a formal batch.
    result["comparison_ready"] = result["comparison_ready"] and result["campaign_invoked"]
    atomic_write_json(output / "summary.json", result)
    print(json.dumps({k: result[k] for k in ("status", "recovery_eligible", "timing_checks_pass", "evidence_integrity_pass")}))
    return 0 if result["recovery_eligible"] else 2


def resume(args):
    output, recovery_path = args.output, args.recovery_directory
    if recovery_path is None:
        raise ValueError("A successful, current 20-interval recovery is required")
    campaign = args.campaign_directory if args.content_sha else CAMPAIGN
    recomputed = verify_recovery(recovery_path, snapshot_campaign(campaign))
    if not recomputed["recovery_eligible"]:
        raise ValueError("Recovery not eligible or evidence changed")
    manifest = make_manifest(output, "resume", args.auxiliary_sha, args)
    if load(output / "campaign_before.json")["checkpoint_sha256"] != load(recovery_path / "campaign_after.json")["checkpoint_sha256"]:
        raise ValueError("Recovery is stale for this campaign checkpoint")
    manifest.update(recovery_directory=str(recovery_path.resolve()), recovery_manifest_sha256=sha256_file(recovery_path / "manifest.json"))
    atomic_write_json(output / "manifest.json", manifest)
    state = {"schema": "p3-first-seed-controller-v2", "batch_id": manifest["batch_id"],
        "pre_clock_pass": None, "campaign_invoked": False, "campaign_returncode": "unknown", "post_clock_pass": None,
        "failure_reason": None, "additional_failures": [], "status": "created"}
    last_progress = time.perf_counter()
    def progress():
        nonlocal last_progress
        if time.perf_counter() - last_progress < 60:
            return
        last_progress = time.perf_counter()
        current = snapshot_campaign(campaign)
        rows, observations = [], []
        for name, value in current["trajectories"].items():
            trajectory = value["checkpoint"]
            observations.extend(trajectory["observations"])
            active = trajectory["active"]
            sample_count = active.get("sample_count", 0) if active else None
            if active:
                path = campaign / "trajectories" / name / "configurations" / (active["purpose"] + "_" + active["attempt_id"] + ".json")
                if path.exists():
                    sample_count = len(load(path)["samples"])
            rows.append({"name": name, "complete_configs": len(trajectory["observations"]), "active": active,
                         "current_group_saved_executions": sample_count,
                         "next_execution": "warmup" if sample_count == 0 else
                            (f"measurement {sample_count}/5" if sample_count is not None and sample_count < 6 else "unknown"),
                         "last_saved": trajectory["updated_at"]})
        payload = {"progress_at": utc_now(), "campaign_status": current["checkpoint"]["status"], "trajectories": rows, "process_state": "campaign child still running",
            "rough_remaining_search_seconds": (24 - len(observations)) * sum(g["evaluation_wall_seconds"] for g in observations) / len(observations)
                                              if observations else None,
            "estimate_scope": "Observed terminal throughput only; composition-biased; excludes gates/retests; not experiment data"}
        atomic_write_json(output / "progress" / (uuid.uuid4().hex + ".json"), payload)
        print(json.dumps(payload), flush=True)
    try:
        if not verify_frozen_files(output, manifest):
            raise ValueError("Frozen file identity check failed")
        if not resources(output, manifest):
            raise ValueError("Fresh formal resource gate rejected")
        state["pre_clock_pass"] = run_probe(output, manifest, "clock_before")["pass"]
        if not state["pre_clock_pass"]:
            raise ValueError("Pre-batch clock check rejected; campaign not invoked")
        state["campaign_invoked"], state["status"] = True, "running"
        atomic_write_json(output / "controller.json", state)
        spec = manifest["operations"]["campaign"]
        operation = capture(spec["command"], output, "campaign", manifest["batch_id"],
                            sha256_file(output / "manifest.json"), timeout=None, progress=progress)
        state["campaign_returncode"] = operation["returncode"]
        if operation["returncode"] != 0:
            first_failure(state, "Campaign paused/failed or exit unknown")
    except (ValueError, OSError, KeyError) as error:
        first_failure(state, str(error))
    finally:
        if state["pre_clock_pass"] is not None:
            try:
                state["post_clock_pass"] = run_probe(output, manifest, "clock_after")["pass"]
                if not state["post_clock_pass"]:
                    first_failure(state, "Post-batch clock check rejected")
            except (ValueError, OSError) as error:
                first_failure(state, "Post-batch clock error: " + str(error))
        atomic_write_json(output / "campaign_after.json", snapshot_campaign(campaign))
        state["campaign_after_sha256"] = sha256_file(output / "campaign_after.json")
        state["status"] = "returned" if state["failure_reason"] is None else "blocked_or_partial"
        atomic_write_json(output / "controller.json", state)
    command = [sys.executable, "scripts/audit_p3_first_seed.py", "--batch", str(output), "--clock-recovery",
               str(recovery_path), "--output", str(output / "summary.json"), "--require-two"]
    operation = capture(command, output, "acceptance", manifest["batch_id"], timeout=180)
    return operation["returncode"] if type(operation["returncode"]) is int else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("recover", "resume", "check"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--auxiliary-sha", default="")
    parser.add_argument("--content-sha", default="")
    parser.add_argument("--archive-directory")
    parser.add_argument("--campaign-directory", type=Path)
    parser.add_argument("--git-identity", type=Path)
    parser.add_argument("--session-id")
    parser.add_argument("--recovery-directory", type=Path)
    parser.add_argument("--probe-file", type=Path)
    parser.add_argument("--intervals", type=int, default=10)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if os.name != "nt":
        parser.error("Use the Windows entry point")
    if args.mode != "check" and not all((args.content_sha, args.archive_directory, args.campaign_directory, args.git_identity, args.session_id)):
        parser.error("New runs require explicit --content-sha, --archive-directory, --campaign-directory, --git-identity and --session-id; legacy batches are read-only")
    if args.content_sha and not args.auxiliary_sha:
        args.auxiliary_sha = args.content_sha
    if not args.child:
        if args.output.exists():
            raise ValueError("Use a unique, new output directory")
        args.output.mkdir(parents=True)
        command = [POWERSHELL, "-NoProfile", "-File", str(ROOT / "scripts/resume_p3_first_seed.ps1"),
            "-EvidenceDirectory", str(args.output), "-PythonExecutable", sys.executable, "-Mode", args.mode,
            "-Intervals", str(args.intervals)]
        for option, value in (("-RecoveryDirectory", args.recovery_directory), ("-AuxiliarySha", args.auxiliary_sha), ("-ProbeFile", args.probe_file)):
            if value:
                command.extend((option, str(value)))
        for option, value in (("-ContentSha", args.content_sha), ("-ArchiveDirectory", args.archive_directory),
                              ("-CampaignDirectory", args.campaign_directory), ("-GitIdentity", args.git_identity), ("-SessionId", args.session_id)):
            if value:
                command.extend((option, str(value)))
        record = capture(command, args.output, "windows_entry", uuid.uuid4().hex, timeout=None if args.mode == "resume" else 360)
        print(json.dumps({"output": str(args.output), "pid": record["pid"], "returncode": record["returncode"]}))
        return record["returncode"] if type(record["returncode"]) is int else 1
    if args.mode == "check":
        try:
            result = check_clock_intervals(load(args.probe_file), load(ROOT / "configs/timing_audit_protocol.json")["diagnostic_criteria"], args.intervals)
        except (ValueError, OSError) as error:
            result = {"pass": False, "errors": [str(error)]}
        atomic_write_json(args.output / "check_only.json", result)
        return 0 if result["pass"] else 2
    from scripts.p3_clock_contract import batch_identity
    batch_identity({"schema": "p3-clock-batch-v3", "formal_content_commit": args.content_sha,
                    "session_id": args.session_id, "archive_directory": args.archive_directory})
    if args.mode == "recover" and not (args.campaign_directory / "checkpoint.json").exists():
        command = campaign_command(ROOT, archive=args.archive_directory, content_sha=args.content_sha,
            git_identity=args.git_identity, campaign=args.campaign_directory,
            session_id=args.session_id, initialize_only=True)
        initialized = capture(command, args.output, "initialize_new_campaign", uuid.uuid4().hex, timeout=90)
        if initialized["returncode"] != 0:
            raise ValueError("New campaign initialization failed; no clock probes run")
    return recovery(args) if args.mode == "recover" else resume(args)


if __name__ == "__main__":
    raise SystemExit(main())
