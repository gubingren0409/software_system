"""One batch's bounded clean validation; no formal search or real clock probes."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, capture, load, wsl_path


def main():
    content = sys.argv[1]
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != content:
        raise ValueError("Validate the actual frozen HEAD before collecting new evidence")
    batch = Path(__file__).resolve().parents[1]
    output = batch / ("clean-" + content[:8])
    output.mkdir()
    archive = "/var/tmp/matrix-autotuner-p3-policy-content-" + content
    windows = ROOT / "build/p3-resource-policy-clean" / content
    windows.mkdir(parents=True)
    tar = windows.parent / (content + ".tar")
    selected = ["autotuner", "code", "configs", "scripts", "tests",
        "evidence/p3/campaign-e308bfb/protocol.json", "evidence/p3/campaign-e308bfb/campaign_protocol.json"]
    commands = []

    def run(name, command, timeout=120):
        result = capture(command, output, name, "clean-" + content, timeout=timeout)
        commands.append({"name": name, "returncode": result["returncode"], "timed_out": result["timed_out"]})
        if result["returncode"] != 0 or result["timed_out"]:
            raise RuntimeError("Clean validation failed: " + name)
        return result

    run("export", ["git", "archive", "--format=tar", "--output=" + str(tar), content, *selected])
    with tarfile.open(tar) as saved:
        saved.extractall(windows, filter="data")
    run("extract_wsl", ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--", "python3", "-c",
        "from pathlib import Path; import tarfile; p=Path(" + repr(archive) + "); p.mkdir(); "
        "t=tarfile.open(" + repr(wsl_path(tar)) + "); t.extractall(p,filter='data'); t.close()"])
    tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)",
                                   content, "--", "autotuner", "code/working", "code/original/matrix_multiplication.c",
                                   "configs", "scripts"], cwd=ROOT, text=True)
    blobs = {path: blob for blob, path in (line.split("\t", 1) for line in tree.splitlines())}
    identity = {"content_sha": content, "files": blobs}
    atomic_write_json(output / "git_identity.json", identity)
    win_identity = source_identity(windows, blobs)
    atomic_write_json(output / "windows_source_identity.json", win_identity)
    atomic_write_json(output / "working_source_identity.json", source_identity(ROOT, blobs))
    prefix = ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", archive, "--", "env", "-u", "PYTHONPATH",
              "PYTHONDONTWRITEBYTECODE=1", "python3"]
    run("wsl_source_identity", [*prefix, "-c",
        "from pathlib import Path; import json; from autotuner.session import source_identity; "
        "v=json.load(open(" + repr(wsl_path(output / "git_identity.json")) + ")); "
        "print(json.dumps(source_identity(Path.cwd(),v['files']),sort_keys=True))"])
    run("clean_conditions", [*prefix, "-c",
        "from pathlib import Path; import os; p=Path.cwd(); assert not (p/'.git').exists(); "
        "assert not list(p.rglob('__pycache__')); assert 'PYTHONPATH' not in os.environ; "
        "import autotuner.resources, autotuner.core; print('clean import PASS')"])
    run("versions_wsl", [*prefix, "-c",
        "import platform, subprocess, sys; print(sys.version); print(platform.platform()); "
        "[subprocess.run(c,check=True) for c in [['gcc','--version'],['uname','-a'],['git','--version']]]"])
    run("cli_help", [*prefix, "-m", "autotuner", "--help"])
    run("list_configs", [*prefix, "-m", "autotuner", "list-configs"])
    configs = load(output / "list_configs.stdout.txt")
    assert len(configs) == 20 and len({(c["optimization"], c["block_size"]) for c in configs}) == 20
    for name, pattern in (("resource_tests_wsl", "test_resource_policy.py"),
                          ("binding_tests_wsl", "test_new_session_binding.py"),
                          ("clock_tests_wsl", "test_p3_clock_contract.py"),
                          ("campaign_tests_wsl", "test_campaign*.py"),
                          ("first_seed_tests_wsl", "test_first_seed_audit.py")):
        run(name, [*prefix, "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"], 150)
    for name, pattern in (("resource_tests_windows", "test_resource_policy.py"),
                          ("binding_tests_windows", "test_new_session_binding.py"),
                          ("clock_tests_windows", "test_p3_clock_contract.py")):
        code = "import os,sys,unittest; os.chdir(" + repr(str(windows)) + "); sys.path.insert(0,os.getcwd()); " \
            "s=unittest.defaultTestLoader.discover('tests',pattern=" + repr(pattern) + "); " \
            "r=unittest.TextTestRunner(verbosity=2).run(s); raise SystemExit(not r.wasSuccessful())"
        run(name, [sys.executable, "-I", "-B", "-X", "utf8", "-c", code], 160)
    target = load(windows / "configs/target.json")
    cache = archive + "-diagnostic-cache"
    target.update(candidate_source=archive + "/code/working/matrix_multiplication.c",
        reference_source=archive + "/code/working/reference_generator.c",
        shared_sources=[archive + "/code/working/matrix_input.h"], cache_root=cache)
    atomic_write_json(output / "diagnostic_target.json", target)
    run("empty_cache_before", [*prefix, "-c", "from pathlib import Path; p=Path(" + repr(cache) + "); "
        "assert not p.exists(); print('empty isolated cache before evaluation')"])
    run("evaluate_n17", [*prefix, "-m", "autotuner", "--target", wsl_path(output / "diagnostic_target.json"),
        "--evidence-root", wsl_path(output / "n17"), "evaluate", "--size", "17", "--optimization", "O2",
        "--block-size", "8", "--seed", "20261008", "--input", "random", "--timeout", "30", "--label", "clean-policy-n17"])
    evaluated = load(output / "evaluate_n17.stdout.txt")
    assert evaluated["classification"] == "success" and evaluated["source"] == "fresh_measurement"
    assert evaluated["target_result"]["checked_entries"] == 17**2
    diagnostic_session = uuid.uuid4().hex
    run("initialize_actual_cli", [*prefix, "-m", "autotuner", "campaign", "--content-sha", content,
        "--git-identity", wsl_path(output / "git_identity.json"), "--campaign-directory", wsl_path(output / "initialized_campaign"),
        "--session-id", diagnostic_session, "--initialize-only", "--trajectory-limit", "2"])
    checkpoint = load(output / "initialized_campaign/checkpoint.json")
    assert checkpoint["session_id"] == diagnostic_session and checkpoint["completed_trajectories"] == []
    assert checkpoint["status"] == "initialized" and "fingerprint" not in checkpoint
    # Exercise the exact WSL -> Windows UNC launch path without running targets
    # or taking another real admission/clock sample. This is explicitly a replay.
    source = load(output / "wsl_source_identity.stdout.txt")["scripts/check_p2_resources.ps1"]
    replay = {"schema": "p3-resource-snapshot-v1", "collector_sha256": source["executed_sha256"],
        "collector_lf_sha256": source["git_content_sha256"], "host_total_visible_bytes": 16 * 2**30,
        "host_samples": [{"timestamp": f"2026-10-10T14:00:0{i}+08:00", "cpu_percent": cpu,
                          "available_memory_bytes": 3 * 2**30} for i, cpu in enumerate((13,9,16,18,15))],
        "wsl_total_bytes": 8 * 2**30, "wsl_available_bytes": 4 * 2**30,
        "wsl_swap_total_bytes": 2**30, "wsl_swap_free_bytes": 2**30, "wsl_root_free_bytes": 5 * 2**30}
    atomic_write_json(output / "controlled_replay_input.json", replay)
    code = "from pathlib import Path; import json,subprocess; from autotuner.resources import wait_formal; " \
        "root=Path.cwd(); script=subprocess.run(['wslpath','-w',str(root/'scripts/check_p2_resources.ps1')],capture_output=True,text=True,check=True).stdout.strip(); " \
        "command=['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-Mode','Formal','-RuntimeRoot',str(root),'-InputSnapshot'," + repr(str(output / "controlled_replay_input.json")) + "]; " \
        "rows=[]; passed,elapsed=wait_formal(command,json.load(open('configs/measurement_protocol.json')),rows.append); " \
        "print(json.dumps({'synthetic':True,'is_real_gate':False,'pass':passed,'elapsed_seconds':elapsed,'records':rows})); assert passed and len(rows)==1"
    run("controlled_unc_resource_replay", [*prefix, "-c", code], 150)
    run("invariants", ["git", "diff", "--exit-code", "aae4147f1e246c5fb115060ef484df625b611e3d", content, "--",
        "code", "autotuner/core.py", "autotuner/measurement.py", "autotuner/search.py", "configs/config_space.json",
        "configs/search_protocol.json", "configs/target.json", "configs/timing_audit_protocol.json", "scripts/check_p2_clocks.py"])
    atomic_write_json(output / "summary.json", {"content_commit": content, "archive_directory": archive,
        "windows_archive_directory": str(windows), "commands": commands, "pass": True,
        "source_file_count": len(blobs), "unique_configuration_count": len(configs),
        "orchestrator_sha256": sha256_file(Path(__file__)), "python_windows": sys.version,
        "teacher_byte_sha256": sha256_file(windows / "code/original/matrix_multiplication.c"),
        "diagnostic_execution": {"n": 17, "optimization": "O2", "block_size": 8,
            "source": evaluated["source"], "classification": evaluated["classification"]},
        "initialized_diagnostic_session": diagnostic_session,
        "real_recovery_probe_count": 0, "formal_execution_count": 0})
    print(json.dumps({"content_commit": content, "pass": True, "output": str(output), "commands": len(commands)}))


if __name__ == "__main__":
    main()
