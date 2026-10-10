"""Final local delivery check for this batch; no matrix/clock invocation."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import atomic_write_json, load, snapshot_campaign

OUT = Path(__file__).resolve().parent
if (OUT / "final_state.json").exists():
    raise ValueError("Refusing to overwrite final protection evidence")
before = load(OUT / "protected_files_before.json")["files"]
changed = []
for relative, expected in before.items():
    data = (ROOT / relative).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected["runtime_sha256"]:
        changed.append(relative)
assert not changed
start = load(OUT / "campaign_before.json")
now = snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb")
assert start["checkpoint_sha256"] == now["checkpoint_sha256"]
assert start["trajectories"] == now["trajectories"]
pause = ROOT / "evidence/p3/campaign-e308bfb/PAUSE_REQUEST"
assert pause.exists()
original = ROOT / "code/original/matrix_multiplication.c"
original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
assert original_hash == "188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15"
analysis = load(OUT / "diagnosis_analysis.json")
process = load(OUT / "final_operations/wsl_final_processes.stdout.txt")
assert process["formal_processes"] == [] and process["runner_lock_state"] == "available"
audit = load(OUT / "partial_campaign_audit/audit.json")
assert audit["unique_configuration_count"] == 3 and audit["raw_execution_count"] == 23
assert audit["completed_trajectory_count"] == 0 and audit["prefix_rows"] == []

partial_groups = []
for name, trajectory in now["trajectories"].items():
    state = trajectory["checkpoint"]
    scored_ids = {sample["run_id"] for group in state["observations"] for sample in group["samples"]}
    for active in [*state["abandoned_attempts"], *([state["active"]] if state["active"] else [])]:
        path = ROOT / "evidence/p3/campaign-e308bfb/trajectories" / name / "configurations" / (active["purpose"] + "_" + active["attempt_id"] + ".json")
        group = load(path)
        assert not scored_ids.intersection(sample["run_id"] for sample in group["samples"])
        partial_groups.append({"attempt_id": active["attempt_id"], "sample_count": len(group["samples"]),
                               "state": "abandoned" if active in state["abandoned_attempts"] else "pending_restart",
                               "process_wall_seconds": sum(s["process_wall_seconds"] for s in group["samples"])})
assert sorted(g["sample_count"] for g in partial_groups) == [2, 3]

documents = [ROOT / "README.md", ROOT / "report.md", *(ROOT / "docs" / name for name in (
    "P3_CLOCK_REPAIR.md", "P3_FIRST_SEED_STATUS.md", "P3_CLOCK_CONTRACT.md", "P3_AUDIT_HANDOFF.md", "AUDIT_HANDOFF.md", "WORK_LOG.md"))]
link_errors, link_count = [], 0
for path in documents:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
        target = target.strip("<>").split("#", 1)[0]
        if not target or "://" in target:
            continue
        link_count += 1
        if not (path.parent / target).exists():
            link_errors.append({"document": str(path.relative_to(ROOT)), "target": target})
assert not link_errors

sources = {}
for path in sorted(OUT.glob("*.py")):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    sources[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
sources["read_adjtimex.c"] = hashlib.sha256((OUT / "read_adjtimex.c").read_bytes()).hexdigest()
secret = re.compile(rb"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|Authorization: Bearer [A-Za-z0-9._-]{15,}")
findings = [str(path.relative_to(ROOT)) for path in OUT.rglob("*") if path.is_file() and secret.search(path.read_bytes())]
assert not findings
result = {"evidence_integrity_pass": analysis["evidence_integrity_pass"],
          "execution_complete": False, "timing_checks_pass": False, "comparison_ready": False,
          "new_timing_check_status": "not_performed_no_effective_treatment",
          "protected_file_count": len(before), "changed_protected_files": changed,
          "checkpoint_and_run_ids_unchanged": True, "pause_marker_preserved": True,
          "original_teacher_c_runtime_sha256": original_hash,
          "formal_process_state": process, "partial_groups": partial_groups,
          "partial_groups_not_scored": True, "diagnostic_source_sha256": sources,
          "relative_file_links_checked": link_count, "missing_relative_files": link_errors,
          "sensitive_pattern_findings": findings,
          "source_identity_note": "Runtime SHA above; this batch's local -text attributes preserve raw bytes. Old evidence Git/LF identities remain separately recorded."}
atomic_write_json(OUT / "final_state.json", result)
print(json.dumps(result, ensure_ascii=True))
