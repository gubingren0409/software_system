"""Batch-local orchestration only; does not change the frozen runtime."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, sha256_json, utc_now
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, capture, load, snapshot_campaign

HERE = Path(__file__).resolve().parent
TAG = HERE.name.removesuffix("-first-seed-7405fcc3")
PLAN_PATH = ROOT / "evidence/p3_resource_policy/20261010-143415/corrected_session_plan.json"
PLAN = load(PLAN_PATH)
RECOVERY = HERE.parent / (TAG + "-recovery-7405fcc3")
RESUME = HERE.parent / (TAG + "-resume-7405fcc3")
CONTENT = "7405fcc37074ab815294ba401d5cf5e8280f3d5f"
SESSION = "3768a29ade69408da4c5d0c4404ba44e"
assert PLAN["content_commit"] == CONTENT and PLAN["session_id"] == SESSION


def operation(name, command, timeout=120):
    result = capture(command, HERE, name, TAG, timeout=timeout)
    print(json.dumps({"operation": name, "returncode": result["returncode"],
                      "qpc_seconds": result["qpc_seconds"]}), flush=True)
    return result


def protection():
    prefixes = ["code/original", "evidence/p2", "evidence/p3", "evidence/p3_clock_contract",
                "evidence/p3_clock_repair", "evidence/p3_resource_policy/20261010-143415"]
    paths = subprocess.check_output(["git", "ls-files", "--", *prefixes], cwd=ROOT).decode().splitlines()
    # The new session is expected to change only after resume; seal everything else.
    excluded = "evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3/"
    hashes = {p: sha256_file(ROOT / p) for p in paths if not p.startswith(excluded)}
    return {"baseline_git_commit": "b19e6cde1004c00d641f4459d1530c89ed56a383",
            "tracked_file_count": len(hashes), "raw_byte_sha256_map_digest": sha256_json(hashes),
            "excluded_mutable_new_campaign": excluded,
            "focused_raw_files": {p: value for p, value in hashes.items()
                                  if p.endswith(("checkpoint.json", "samples.jsonl", "PAUSE_REQUEST"))}}


def args(mode):
    result = [sys.executable, "-X", "utf8", "scripts/start_p3_first_seed.py", "--mode", mode]
    for flag, key in [("--content-sha", "content_commit"), ("--auxiliary-sha", "content_commit"),
                      ("--archive-directory", "archive_directory"), ("--campaign-directory", "campaign_directory"),
                      ("--git-identity", "git_identity"), ("--session-id", "session_id")]:
        result.extend([flag, PLAN[key]])
    result.extend(["--output", str(RECOVERY if mode == "recover" else RESUME)])
    if mode == "resume":
        result.extend(["--recovery-directory", str(RECOVERY)])
    return result


def preflight():
    operation("git_status_before", ["git", "status", "--short"])
    operation("git_head_before", ["git", "rev-parse", "HEAD"])
    operation("git_branch_before", ["git", "branch", "--show-current"])
    assert operation("baseline_ancestor", ["git", "merge-base", "--is-ancestor",
                     "b19e6cde1004c00d641f4459d1530c89ed56a383", "HEAD"])["returncode"] == 0
    result = operation("runtime_diff", ["git", "diff", CONTENT, "--", "autotuner", "code", "configs", "scripts", "tests"])
    assert result["returncode"] == 0 and result["stdout_byte_count"] == 0
    cp = snapshot_campaign(PLAN["campaign_directory"])
    assert cp["checkpoint"]["session_id"] == SESSION and cp["checkpoint"]["status"] == "initialized"
    assert not cp["trajectories"] and not cp["checkpoint"]["completed_trajectories"]
    atomic_write_json(HERE / "campaign_before.json", cp)
    atomic_write_json(HERE / "legacy_campaign_before.json", snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb"))
    identity = load(Path(PLAN["git_identity"]))
    actual = source_identity(ROOT, identity["files"])
    tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)", CONTENT,
                                    "--", *identity["files"]], cwd=ROOT, text=True)
    assert {p: b for b, p in (line.split("\t", 1) for line in tree.splitlines())} == identity["files"]
    atomic_write_json(HERE / "worktree_source_identity.json", actual)
    expected = {PLAN["archive_directory"] + "/" + p: item["executed_sha256"]
                for p, item in cp["checkpoint"]["preflight_identity"]["files"].items()}
    checked = operation("archive_source_hashes", ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--",
                         "timeout", "60", "sha256sum", *expected], timeout=90)
    assert checked["returncode"] == 0
    actual_archive = {p: h for h, p in (line.split(None, 1) for line in
                      (HERE / "archive_source_hashes.stdout.txt").read_text().splitlines())}
    assert actual_archive == expected
    atomic_write_json(HERE / "protection_before.json", protection())
    atomic_write_json(HERE / "execution_plan.json", {
        "declared_at": utc_now(), "batch_id": TAG, "runtime_content_commit": CONTENT,
        "delivery_baseline": "b19e6cde1004c00d641f4459d1530c89ed56a383", "session_id": SESSION,
        "plan_sha256": sha256_file(PLAN_PATH), "orchestration_sha256": sha256_file(Path(__file__)),
        "source_file_count": len(actual), "archive_sha256_pass": True,
        "recovery_directory": str(RECOVERY), "resume_directory": str(RESUME),
        "recovery_attempt_limit": 1, "recovery_command": args("recover"), "conditional_resume_command": args("resume"),
        "formal_scope": "seed 20261008; random/greedy 12 each, deduplicated 4/8/12 prefix retests; no Grid rerun",
        "recovery_eligibility_requires": ["evidence_integrity_pass", "timing_checks_pass", "recovery_eligible"],
        "all_raw_intervals_required": 20, "clock_tolerances_unchanged": True})
    print(json.dumps({"preflight_pass": True, "runtime_files": len(actual), "session_id": SESSION}), flush=True)


def audit(mode):
    output = HERE / ("independent_" + mode + ".json")
    command = [sys.executable, "-X", "utf8", "scripts/audit_p3_first_seed.py", "--batch",
               str(RECOVERY if mode == "recover" else RESUME), "--output", str(output), "--require-two"]
    if mode == "resume":
        command.extend(["--clock-recovery", str(RECOVERY)])
    return operation("audit_" + mode, command, timeout=240)


if __name__ == "__main__":
    phase = argparse.ArgumentParser()
    phase.add_argument("phase", choices=["preflight", "recover", "resume", "audit-recover", "audit-resume", "protect-after"])
    phase = phase.parse_args().phase
    if phase == "preflight":
        preflight()
    elif phase == "recover":
        assert load(HERE / "execution_plan.json")["recovery_attempt_limit"] == 1
        result = operation("recovery_entry", args("recover"), timeout=480)
        raise SystemExit(result["returncode"] if type(result["returncode"]) is int else 1)
    elif phase == "resume":
        reviewed = load(HERE / "independent_recover.json")
        assert reviewed["evidence_integrity_pass"] is True and reviewed["timing_checks_pass"] is True
        assert reviewed["clock_recovery_reevaluation"]["recovery_eligible"] is True
        assert load(RECOVERY / "summary.json")["recovery_eligible"] is True
        result = operation("resume_entry", args("resume"), timeout=None)
        raise SystemExit(result["returncode"] if type(result["returncode"]) is int else 1)
    elif phase.startswith("audit-"):
        result = audit(phase.removeprefix("audit-"))
        raise SystemExit(result["returncode"] if type(result["returncode"]) is int else 1)
    else:
        after = protection()
        atomic_write_json(HERE / "protection_after.json", after)
        assert after == load(HERE / "protection_before.json"), "Sealed history changed"
        print(json.dumps({"historical_protection_pass": True, "files": after["tracked_file_count"]}))
