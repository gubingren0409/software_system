"""Initialize the corrected empty session and collect read-only protection checks."""
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, capture, load, wsl_path

batch = Path(__file__).resolve().parents[1]
clean = load(batch / "clean-7405fcc3/summary.json")
assert clean["pass"]
content = clean["content_commit"]
identity = batch / "clean-7405fcc3/git_identity.json"
source_identity(ROOT, load(identity)["files"])
session = uuid.uuid4().hex
campaign = batch / "campaign-7405fcc3"
args = ["--content-sha", content, "--auxiliary-sha", content,
        "--archive-directory", clean["archive_directory"], "--campaign-directory", str(campaign),
        "--git-identity", str(identity), "--session-id", session]
recovery = batch / "recovery-corrected-next-round"
resume = batch / "resume-corrected-next-round"
atomic_write_json(batch / "corrected_session_plan.json", {"content_commit": content, "session_id": session,
    "archive_directory": clean["archive_directory"], "campaign_directory": str(campaign),
    "git_identity": str(identity), "git_identity_sha256": sha256_file(identity),
    "requires_new_recovery_authorization": True, "current_clock_status": "not_performed",
    "prior_recovery_not_imported": True,
    "next_recovery_command": ["python", "scripts/start_p3_first_seed.py", "--mode", "recover", *args, "--output", str(recovery)],
    "next_resume_command_only_after_all_checks": ["python", "scripts/start_p3_first_seed.py", "--mode", "resume", *args,
        "--recovery-directory", str(recovery), "--output", str(resume)]})
operation = capture(["wsl.exe", "-d", "Ubuntu-24.04", "--cd", clean["archive_directory"], "--", "env", "-u", "PYTHONPATH",
    "PYTHONDONTWRITEBYTECODE=1", "python3", "-m", "autotuner", "campaign", "--content-sha", content,
    "--git-identity", wsl_path(identity), "--campaign-directory", wsl_path(campaign),
    "--session-id", session, "--initialize-only", "--trajectory-limit", "2"],
    batch / "final_checks", "initialize_corrected_session", "policy-final", timeout=90)
assert operation["returncode"] == 0
expected = load(ROOT / "evidence/p3_clock_repair/20261010-135557/frozen_expectations.json")["expected"]
operation = capture(["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--", "timeout", "60", "sha256sum", *expected],
    batch / "final_checks", "legacy_frozen_files", "policy-final", timeout=90)
assert operation["returncode"] == 0
code = """
from pathlib import Path
import fcntl, json
found=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        args=[v.decode(errors='backslashreplace') for v in path.read_bytes().split(b'\0') if v]
        if args and (('campaign' in args and 'autotuner' in args) or
            (Path(args[0]).name in ('candidate','reference_generator') and args[0].startswith('/var/tmp/matrix-autotuner-'))):
            found.append({'pid':int(path.parent.name),'command':args})
    except (OSError, ValueError): pass
lock=Path('/var/tmp/matrix-autotuner-p3-10245102457.runner.lock')
available=False
with lock.open('r') as stream:
    try:
        fcntl.flock(stream, fcntl.LOCK_EX|fcntl.LOCK_NB); available=True
        fcntl.flock(stream, fcntl.LOCK_UN)
    except BlockingIOError: pass
print(json.dumps({'formal_processes':found,'runner_lock_available':available}))
"""
operation = capture(["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--", "python3", "-c", code],
    batch / "final_checks", "process_state", "policy-final", timeout=30)
assert operation["returncode"] == 0
print({"content_commit": content, "new_empty_session": session, "recovery_repeated": False})
