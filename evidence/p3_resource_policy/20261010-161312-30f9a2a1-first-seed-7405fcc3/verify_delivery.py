"""Check this evidence/doc-only delivery without running targets or probes."""
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import atomic_write_json, load
from autotuner.core import sha256_file

plan = load(HERE / "execution_plan.json")
recovery = Path(plan["recovery_directory"])
review = load(HERE / "independent_recover.json")
summary = load(HERE / "delivery_summary.json")
assert summary["new_campaign_checkpoint_byte_unchanged"] and summary["historical_protection"]["pass"]
assert summary["recovery_entry_returncode"] == 2 and summary["independent_audit_returncode"] == 1
assert summary["resource"]["rejection_reasons"] == ["host_memory"]
assert summary["new_clock_intervals"] == 0 and summary["formal_campaign_invoked"] is False
assert not Path(plan["resume_directory"]).exists()
assert not any(recovery.glob("window_*.operation.json"))
assert review["clock_recovery_reevaluation"]["recovery_eligible"] is False
assert all(value is False for value in summary["acceptance"].values())
assert sha256_file(ROOT / "code/original/matrix_multiplication.c") == "188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15"
raw_identity_count = 0
for relative, identity in summary["recovery_raw_file_identities"].items():
    data = (ROOT / relative).read_bytes()
    assert hashlib.sha256(data).hexdigest() == identity["sha256"]
    assert hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == identity["lf_sha256"]
    raw_identity_count += 1
json_count = 0
for folder in (HERE, recovery):
    for path in folder.glob("*.json"):
        load(path)
        json_count += 1
for name in ("execute.py", "finalize.py", "finalize_initial.py", "verify_delivery.py"):
    ast.parse((HERE / name).read_text(encoding="utf-8"), filename=name)
documents = ["README.md", "report.md", "docs/P3_FIRST_SEED_STATUS.md", "docs/P3_FIRST_SEED_7405FCC3.md",
             "docs/P3_RESOURCE_POLICY.md", "docs/WORK_LOG.md", "docs/AUDIT_HANDOFF.md"]
links = 0
for relative in documents:
    path = ROOT / relative
    for target in re.findall(r"\]\(([^\s)]+)\)", path.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        assert (path.parent / target.split("#", 1)[0]).exists(), (relative, target)
        links += 1
runtime_diff = subprocess.check_output(["git", "diff", plan["runtime_content_commit"], "--",
                                       "autotuner", "code", "configs", "scripts", "tests"], cwd=ROOT)
assert runtime_diff == b""
result = {"status": "PASS", "scope": "Delivery consistency only, not a new recovery or successful formal comparison",
          "runtime_diff_empty": True, "original_c_byte_sha_pass": True,
          "raw_recovery_files_checked": raw_identity_count, "json_files_checked": json_count,
          "batch_python_ast_count": 4, "relative_links_checked": links,
          "executed_verifier_sha256": sha256_file(Path(__file__)), "acceptance_unchanged": summary["acceptance"]}
atomic_write_json(HERE / "delivery_checks.json", result)
print(json.dumps(result))
