"""Read-only final accounting for the resource-rejected recovery batch."""
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, utc_now
from autotuner.resources import judge, load_policy
from scripts.p3_clock_contract import atomic_write_json, load, snapshot_campaign, check_operation
from execute import PLAN, RECOVERY, RESUME, TAG, operation, protection

assert not RESUME.exists(), "A rejected recovery must not launch resume"
manifest = load(RECOVERY / "manifest.json")
resource = load(RECOVERY / "resources.stdout.txt")
policy_path = ROOT / "configs/resource_policy.json"
recomputed = judge(resource, load_policy(policy_path), "Recovery", sha256_file(policy_path))
assert recomputed == resource and resource["decision"] == "REJECT"
assert resource["rejection_reasons"] == ["host_memory"]
for name in ("resources", "frozen_files"):
    check_operation(load(RECOVERY / (name + ".operation.json")), RECOVERY, manifest, name)

windows_code = r"""$ErrorActionPreference='Stop'
$osInfo=Get-CimInstance Win32_OperatingSystem
$topMemory=Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 ProcessName,Id,WorkingSet64,PrivateMemorySize64
[pscustomobject]@{captured_at=(Get-Date -Format o);snapshot_use='Read-only explanation after gate REJECT; not a new admission gate';available_memory_bytes=([int64]$osInfo.FreePhysicalMemory*1024);total_memory_bytes=([int64]$osInfo.TotalVisibleMemorySize*1024);top_processes=$topMemory} | ConvertTo-Json -Depth 5
"""
operation("host_memory_explanation_corrected", ["C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
          "-NoProfile", "-Command", windows_code], timeout=40)
linux_code = r"""import fcntl,json,pathlib,sys,platform
found=[]
for directory in pathlib.Path('/proc').iterdir():
    if directory.name.isdigit():
        try:
            args=[s.decode(errors='replace') for s in (directory/'cmdline').read_bytes().split(bytes([0])) if s]
            if 'autotuner.campaign' in args or any(a.startswith('/var/tmp/matrix-autotuner-p3-10245102457/cache/') for a in args):
                found.append({'pid':int(directory.name),'command':args,'stat':(directory/'stat').read_text()})
        except (OSError,ProcessLookupError):
            pass
lock=pathlib.Path('/var/tmp/matrix-autotuner-p3-10245102457.runner.lock')
available='unknown'
if lock.exists():
    with lock.open('r') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            available=True
            fcntl.flock(handle,fcntl.LOCK_UN)
        except BlockingIOError:
            available=False
print(json.dumps({'python':sys.version,'kernel':platform.release(),'formal_processes':found,'runner_lock_available':available}))
"""
operation("formal_process_state_corrected", ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--",
          "timeout", "30", "python3", "-c", linux_code], timeout=40)
operation("git_runtime_diff_after_corrected", ["git", "diff", PLAN["content_commit"], "--", "autotuner", "code", "configs", "scripts", "tests"])
assert (HERE / "git_runtime_diff_after_corrected.stdout.txt").read_bytes() == b""
after = snapshot_campaign(PLAN["campaign_directory"])
before = load(HERE / "campaign_before.json")
assert after["checkpoint_sha256"] == before["checkpoint_sha256"] and after["trajectories"] == before["trajectories"]
atomic_write_json(HERE / "campaign_after.json", after)
legacy = snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb")
old = load(HERE / "legacy_campaign_before.json")
assert legacy["checkpoint_sha256"] == old["checkpoint_sha256"] and legacy["trajectories"] == old["trajectories"]
atomic_write_json(HERE / "legacy_campaign_after.json", legacy)
sealed = protection()
assert sealed == load(HERE / "protection_before.json")
atomic_write_json(HERE / "protection_after.json", sealed)

acceptance = load(HERE / "independent_recover.json")
operations = []
for folder in (HERE, RECOVERY):
    for path in sorted(folder.glob("*.operation.json")):
        record = load(path)
        for stream in ("stdout", "stderr"):
            assert sha256_file(folder / record[stream + "_path"]) == record[stream + "_sha256"]
        operations.append({"path": str(path.relative_to(ROOT)), "returncode": record["returncode"],
                           "qpc_seconds": record["qpc_seconds"], "start_utc_ns": record["start_utc_ns"],
                           "end_utc_ns": record["end_utc_ns"], "qpc_start": record["qpc_start"],
                           "qpc_end": record["qpc_end"], "qpc_frequency": record["qpc_frequency"]})
intervals = sorted((op["qpc_start"]/op["qpc_frequency"], op["qpc_end"]/op["qpc_frequency"]) for op in operations)
merged = []
for start, end in intervals:
    if not merged or start > merged[-1][1]:
        merged.append([start, end])
    else:
        merged[-1][1] = max(merged[-1][1], end)
raw_files = {str(path.relative_to(ROOT)): {"sha256": sha256_file(path), "bytes": path.stat().st_size,
             "lf_sha256": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
             for path in RECOVERY.iterdir() if path.is_file()}
state = load(HERE / "formal_process_state_corrected.stdout.txt")
assert not state["formal_processes"] and state["runner_lock_available"] is True
result = {
    "schema": "p3-first-seed-resource-blocked-delivery-v1", "recorded_at": utc_now(),
    "runtime_content_commit": PLAN["content_commit"], "session_id": PLAN["session_id"],
    "campaign_status": after["checkpoint"]["status"], "recovery_directory": str(RECOVERY),
    "recovery_entry_returncode": load(HERE / "recovery_entry.operation.json")["returncode"],
    "independent_audit_returncode": load(HERE / "audit_recover.operation.json")["returncode"],
    "acceptance": {key: acceptance[key] for key in ("evidence_integrity_pass", "execution_complete", "timing_checks_pass", "comparison_ready")},
    "acceptance_note": "Existing auditor requires both raw clock windows for evidence_integrity_pass. They were deliberately not run after resource REJECT; false is not a source-hash corruption finding.",
    "recorded_operation_hashes_pass": True, "frozen_source_files_pass": 50,
    "new_clock_intervals": 0, "clock_status": "not_performed", "host_same_call_clock_status": "not_performed",
    "formal_gate_status": "not_performed", "formal_campaign_invoked": False,
    "complete_configurations": 0, "complete_trajectories": 0, "raw_target_executions": 0,
    "partial_target_groups": 0, "abandoned_target_groups": 0, "independent_retests": 0, "budget_rows": 0,
    "remaining_scope": "random/greedy each 12 unique configurations and deduplicated prefix retests; seed 20261008 only",
    "resource": {"recomputed_exactly": True, "purpose": resource["purpose"], "decision": resource["decision"],
                 "policy_version": resource["policy_version"], "policy_hash": resource["policy_hash"],
                 "cpu_samples_percent": [s["cpu_percent"] for s in resource["host_samples"]],
                 "cpu_average_percent": resource["host_cpu_average_percent"], "cpu_maximum_percent": resource["host_cpu_maximum_percent"],
                 "host_minimum_available_bytes": resource["host_minimum_available_bytes"],
                 "wsl_available_bytes": resource["wsl_available_bytes"], "root_free_bytes": resource["wsl_root_free_bytes"],
                 "checks": resource["checks"], "warnings": resource["warnings"], "rejection_reasons": resource["rejection_reasons"]},
    "historical_protection": {"pass": True, **sealed}, "new_campaign_checkpoint_byte_unchanged": True,
    "new_campaign_costs": {"active_total_seconds": after["checkpoint"]["active_total_seconds"],
                           "wait_seconds": after["checkpoint"]["wait_seconds"], "active_delta_seconds": 0, "wait_delta_seconds": 0,
                           "terminal_configuration_evaluation_seconds": 0, "retest_seconds": 0, "abandoned_attempt_seconds": 0},
    "auxiliary_costs": {"recorded_operation_qpc_interval_union_seconds": sum(end-start for start,end in merged),
                        "recovery_entry_seconds": load(HERE / "recovery_entry.operation.json")["qpc_seconds"],
                        "nested_recovery_gate_seconds": load(RECOVERY / "resources.operation.json")["qpc_seconds"],
                        "independent_audit_seconds": load(HERE / "audit_recover.operation.json")["qpc_seconds"],
                        "scope": "Captured operations through final process/runtime checks only; nested intervals counted once; excludes hashing/postprocessing/editing/model time/push and no inferred total wall time"},
    "formal_processes": state["formal_processes"], "runner_lock_available": state["runner_lock_available"],
    "executed_finalizer_sha256": sha256_file(Path(__file__)),
    "auxiliary_failure": {"initial_source_sha256": sha256_file(HERE / "finalize_initial.py"),
                          "reason": "Accidental leading plus in two batch-local command strings; both child processes exited 1. Finalizer then failed parsing empty stdout. Raw failures retained; corrected queries are read-only, not a new admission or recovery.",
                          "initial_finalizer_exit_code": 1, "initial_finalizer_duration": "unknown"},
    "operations": operations, "recovery_raw_file_identities": raw_files,
    "next_step": "After host memory recovers >=2 GiB, a new explicitly authorized unique recovery is required; do not reuse this rejected batch or repeat automatically. Same frozen content/session can be retained if identities remain unchanged."
}
atomic_write_json(HERE / "delivery_summary.json", result)
print(json.dumps({"status": "P3_RESOURCE_BLOCKED", "acceptance": result["acceptance"], "protected_files": sealed["tracked_file_count"], "costs": result["auxiliary_costs"]}))
