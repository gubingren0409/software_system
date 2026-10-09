"""Strict auxiliary clock/evidence contract. Never changes the formal timer."""
from __future__ import annotations

import ctypes
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, utc_now

FORMAL_CONTENT = "e308bfb873e6811c50ad685a979af345302fda8d"
SESSION = "dc1c292900654d44b36a72548b95a610"
ARCHIVE = "/var/tmp/matrix-autotuner-p2-content-" + FORMAL_CONTENT
CRITERIA_SHA = "720c91efdf26f6e435629d2638781cca1d79ebc49f49d203a7dcdaa398311b9f"
PROBE_SHA = "1cf4217497f674520ce22f015c61067287051d5644af66f4b27d2df2720706aa"
POWERSHELL = "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
MODULE_PATH = "C:/Windows/System32/WindowsPowerShell/v1.0/Modules"
CLOCKS = ("monotonic", "raw", "realtime", "boottime")
TOLERANCES = {"monotonic_raw_absolute_allowance_seconds": 0.005,
              "monotonic_raw_relative_tolerance": 0.01,
              "realtime_raw_absolute_allowance_seconds": 0.25,
              "realtime_raw_relative_tolerance": 0.01}


def atomic_write_json(path, value):
    """New auxiliary JSON is explicitly LF on Windows; old files stay intact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_bytes((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + token)))


def positive_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def check_clock_intervals(probe, criteria, expected_count):
    """Recompute integer ns endpoints before division; never trust saved deltas."""
    result = {"evidence_integrity_pass": False, "timing_checks_pass": False,
              "pass": False, "expected_interval_count": expected_count, "checks": [], "errors": []}
    try:
        if type(expected_count) is not int or expected_count < 1:
            raise ValueError("Invalid expected interval count")
        if not isinstance(criteria, dict) or any(criteria.get(k) != v for k, v in TOLERANCES.items()):
            raise ValueError("Frozen tolerances differ")
        if not isinstance(probe, dict) or probe.get("schema") != "p2-clock-probe-v1":
            raise ValueError("Probe schema differs")
        if probe.get("script_sha256") != PROBE_SHA or probe.get("system_settings_modified") is not False:
            raise ValueError("Probe source identity/settings differ")
        for field in ("captured_at", "command", "commands", "clock_info"):
            if field not in probe:
                raise ValueError("Missing probe field: " + field)
        if not isinstance(probe["captured_at"], str):
            raise ValueError("Invalid capture timestamp type")
        datetime.fromisoformat(probe["captured_at"])
        if not isinstance(probe["command"], list) or len(probe["command"]) < 2 or \
                any(not isinstance(value, str) for value in probe["command"]):
            raise ValueError("Invalid probe command type")
        if not isinstance(probe["commands"], list) or not probe["commands"] or \
                any(not isinstance(item, dict) or type(item.get("returncode")) is not int or
                    not isinstance(item.get("command"), list) or not isinstance(item.get("stdout"), str) or
                    not isinstance(item.get("stderr"), str) for item in probe["commands"]):
            raise ValueError("Invalid metadata operation type")
        if not isinstance(probe["clock_info"], dict) or any(
                not isinstance(probe["clock_info"].get(name), str) for name in ("time", "monotonic")):
            raise ValueError("Invalid clock_info type")
        intervals = probe.get("wsl_intervals")
        if not isinstance(intervals, list) or len(intervals) != expected_count:
            raise ValueError("Probe interval count differs")
        for index, sample in enumerate(intervals):
            row = {"interval_index": index, "monotonic_raw_pass": False, "realtime_raw_pass": False}
            try:
                delta = {}
                for clock in CLOCKS:
                    key = clock + "_ns"
                    before, after = sample["before"][key], sample["after"][key]
                    if type(before) is not int or type(after) is not int or before <= 0 or after <= before:
                        raise ValueError(f"Invalid integer endpoints: interval {index} {clock}")
                    seconds = (after - before) / 1_000_000_000
                    saved = sample["delta"][clock + "_seconds"]
                    if not positive_number(saved) or saved != seconds:
                        raise ValueError(f"Saved delta differs from integer endpoints: interval {index} {clock}")
                    delta[clock + "_seconds"] = seconds
                raw = delta["raw_seconds"]
                row["delta"] = delta
                for clock in ("monotonic", "realtime"):
                    difference = abs(delta[clock + "_seconds"] - raw)
                    limit = TOLERANCES[clock + "_raw_absolute_allowance_seconds"] + \
                            TOLERANCES[clock + "_raw_relative_tolerance"] * raw
                    row[clock + "_raw_difference_seconds"] = difference
                    row[clock + "_raw_limit_seconds"] = limit
                    row[clock + "_raw_pass"] = difference <= limit
            except (ValueError, KeyError, TypeError, OverflowError) as error:
                row["error"] = str(error)
                result["errors"].append(str(error))
            result["checks"].append(row)
        result["evidence_integrity_pass"] = not result["errors"]
        result["timing_checks_pass"] = result["evidence_integrity_pass"] and all(
            r["monotonic_raw_pass"] and r["realtime_raw_pass"] for r in result["checks"])
        result["pass"] = result["timing_checks_pass"]
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        result["errors"].append(str(error))
    return result


def wsl_path(path):
    path = str(path).replace("\\", "/")
    if len(path) > 2 and path[1] == ":":
        return "/mnt/" + path[0].lower() + path[2:]
    return str(Path(path).resolve())


def probe_command(output, count, seconds=3):
    return ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", ARCHIVE, "--", "env", "-u", "PYTHONPATH",
            "PYTHONDONTWRITEBYTECODE=1", "timeout", "90", "python3", "scripts/check_p2_clocks.py",
            "--intervals", str(count), "--seconds", str(seconds), "--skip-host", "--output", wsl_path(output)]


def campaign_command(repo_root=ROOT):
    repo_root = str(repo_root).replace("\\", "/").rstrip("/")
    return ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", ARCHIVE, "--", "env", "-u", "PYTHONPATH",
            "PYTHONDONTWRITEBYTECODE=1", "python3", "-m", "autotuner", "campaign", "--content-sha", FORMAL_CONTENT,
            "--git-identity", wsl_path(repo_root + "/evidence/p3/content-e308bfb/git_identity.json"),
            "--campaign-directory", wsl_path(repo_root + "/evidence/p3/campaign-e308bfb"), "--trajectory-limit", "2", "--resume"]


def qpc():
    if os.name == "nt":
        value, frequency = ctypes.c_longlong(), ctypes.c_longlong()
        if not ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(value)) or not \
                ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency)):
            raise OSError("QPC unavailable")
        return value.value, frequency.value
    return time.perf_counter_ns(), 1_000_000_000  # Only used in controlled POSIX unit tests.


def capture(command, directory, name, batch_id, manifest_sha=None, timeout=120, progress=None):
    """Capture owned child PID/exit/stdout/stderr; module override only in child env."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stdout, stderr = directory / (name + ".stdout.txt"), directory / (name + ".stderr.txt")
    if stdout.exists() or stderr.exists():
        raise ValueError("Refusing to overwrite operation evidence: " + name)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if os.name == "nt":
        env["PSModulePath"] = MODULE_PATH
    start_utc_ns = time.time_ns()
    start_qpc, frequency = qpc()
    record = {"schema": "p3-captured-operation-v2", "batch_id": batch_id, "operation_kind": name,
              "operation_id": uuid.uuid4().hex, "command": list(command), "cwd": str(ROOT),
              "manifest_sha256": manifest_sha, "start_utc_ns": start_utc_ns,
              "qpc_start": start_qpc, "qpc_frequency": frequency, "timeout_seconds": timeout,
              "returncode": "unknown", "pid": "unknown", "timed_out": False}
    started = time.perf_counter()
    with stdout.open("wb") as out, stderr.open("wb") as err:
        try:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=out, stderr=err,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            record["pid"] = child.pid
            atomic_write_json(directory / (name + ".operation.json"), record)
            while True:
                try:
                    record["returncode"] = child.wait(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    if progress:
                        progress()
                    if timeout is not None and time.perf_counter() - started > timeout:
                        record["timed_out"] = True
                        child.terminate()  # Only our own child; WSL probe also has timeout(1).
                        record["returncode"] = child.wait(timeout=15)
                        break
        except (OSError, subprocess.TimeoutExpired) as error:
            record["launch_error"] = str(error)
    record.update(end_utc_ns=time.time_ns(), qpc_end=qpc()[0], ended_at=utc_now(),
                  stdout_path=stdout.name, stderr_path=stderr.name,
                  stdout_sha256=sha256_file(stdout), stderr_sha256=sha256_file(stderr))
    for stream, path in (("stdout", stdout), ("stderr", stderr)):
        data = path.read_bytes()
        record[stream + "_lf_sha256"] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
        record[stream + "_byte_count"] = len(data)
        record[stream + "_crlf_count"] = data.count(b"\r\n")
    record["utc_seconds"] = (record["end_utc_ns"] - start_utc_ns) / 1e9
    record["qpc_seconds"] = (record["qpc_end"] - start_qpc) / frequency
    atomic_write_json(directory / (name + ".operation.json"), record)
    return record


def check_operation(operation, directory, manifest, name):
    expected = manifest["operations"][name]
    if operation.get("schema") != "p3-captured-operation-v2" or \
            operation.get("batch_id") != manifest["batch_id"] or operation.get("operation_kind") != name or \
            operation.get("manifest_sha256") != sha256_file(Path(directory) / "manifest.json") or \
            operation.get("command") != expected["command"] or not operation.get("operation_id") or \
            operation.get("timeout_seconds") != expected["timeout_seconds"]:
        raise ValueError("Operation identity/manifest/command differs (possibly stale batch)")
    if type(operation.get("pid")) is not int or operation["pid"] <= 0:
        raise ValueError("Operation PID unknown")
    if (type(operation.get("returncode")) is not int and operation.get("returncode") != "unknown") or \
            type(operation.get("timed_out")) is not bool:
        raise ValueError("Invalid operation exit/timeout type")
    for stream in ("stdout", "stderr"):
        if operation.get(stream + "_path") != name + "." + stream + ".txt":
            raise ValueError("Operation stream identity differs")
        data = (Path(directory) / operation[stream + "_path"]).read_bytes()
        raw_match = hashlib.sha256(data).hexdigest() == operation.get(stream + "_sha256")
        lf_match = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == operation.get(stream + "_lf_sha256")
        if not raw_match and not lf_match:
            raise ValueError("Operation stream identity differs")
    for key in ("qpc_start", "qpc_end", "qpc_frequency", "start_utc_ns", "end_utc_ns"):
        if type(operation.get(key)) is not int or operation[key] <= 0:
            raise ValueError("Invalid operation integer timing: " + key)
    utc = (operation["end_utc_ns"] - operation["start_utc_ns"]) / 1e9
    elapsed = (operation["qpc_end"] - operation["qpc_start"]) / operation["qpc_frequency"]
    if not all(positive_number(v) for v in (utc, elapsed)) or \
            operation.get("utc_seconds") != utc or operation.get("qpc_seconds") != elapsed:
        raise ValueError("Operation saved elapsed differs from endpoints")
    return {"utc_seconds": utc, "qpc_seconds": elapsed,
            "pass": abs(utc - elapsed) <= 0.25 + 0.01 * elapsed,
            "scope": "Windows UTC and QPC surround the same entire child invocation, not WSL sleep totals"}


def verify_clock_evidence(directory, name, check_saved=True):
    directory = Path(directory)
    answer = {"evidence_integrity_pass": False, "timing_checks_pass": False, "pass": False, "errors": []}
    try:
        manifest = load(directory / "manifest.json")
        if manifest.get("schema") != "p3-clock-batch-v2" or manifest.get("formal_content_commit") != FORMAL_CONTENT or \
                manifest.get("session_id") != SESSION:
            raise ValueError("Batch schema/formal identity differs")
        if manifest.get("criteria_sha256") != CRITERIA_SHA or \
                sha256_file(ROOT / "configs/timing_audit_protocol.json") != CRITERIA_SHA or \
                manifest.get("probe_script_sha256") != PROBE_SHA or \
                manifest.get("checker_sha256") != sha256_file(Path(__file__)):
            raise ValueError("Criteria/probe/checker source identity differs")
        expected = manifest["operations"][name]
        operation_path = directory / (name + ".operation.json")
        operation = load(operation_path)
        host = check_operation(operation, directory, manifest, name)
        if operation.get("returncode") != 0 or type(operation.get("returncode")) is not int or \
                operation.get("timed_out") is not False:
            raise ValueError("Clock probe failed/timed out/exit unknown")
        probe_path = directory / expected["output_file"]
        original_output = manifest["evidence_directory_at_run"].replace("\\", "/").rstrip("/") + "/" + name + ".wsl.json"
        if expected["output_file"] != name + ".wsl.json" or expected["command"] != \
                probe_command(original_output, expected["intervals"], expected["seconds"]):
            raise ValueError("Probe command/output/count binding differs")
        probe = load(probe_path)
        if probe != load(directory / operation["stdout_path"]):
            raise ValueError("Probe stdout differs from saved raw evidence")
        if probe["command"][1:] != ["scripts/check_p2_clocks.py", "--intervals", str(expected["intervals"]),
                "--seconds", str(expected["seconds"]), "--skip-host", "--output", wsl_path(original_output)]:
            raise ValueError("Raw probe invocation differs")
        answer = check_clock_intervals(probe, load(ROOT / "configs/timing_audit_protocol.json")["diagnostic_criteria"],
                                       expected["intervals"])
        answer.update(host_check=host, operation_sha256=sha256_file(operation_path),
                      probe_sha256=sha256_file(probe_path), manifest_sha256=sha256_file(directory / "manifest.json"),
                      checker_sha256=sha256_file(Path(__file__)))
        answer["timing_checks_pass"] = answer["timing_checks_pass"] and host["pass"]
        answer["pass"] = answer["evidence_integrity_pass"] and answer["timing_checks_pass"]
        if check_saved and (directory / (name + ".check.json")).exists() and \
                json.dumps(load(directory / (name + ".check.json")), sort_keys=True, allow_nan=False) != \
                json.dumps(answer, sort_keys=True, allow_nan=False):
            raise ValueError("Saved check contradicts raw recomputation or input hashes")
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
        answer.update(evidence_integrity_pass=False, timing_checks_pass=False, **{"pass": False})
        answer["errors"].append(str(error))
    return answer


def snapshot_campaign(campaign):
    campaign = Path(campaign)
    checkpoint = load(campaign / "checkpoint.json")
    trajectories = {}
    for path in sorted(campaign.glob("trajectories/*/checkpoint.json")):
        directory = path.parent
        samples = directory / "samples.jsonl"
        data = samples.read_bytes() if samples.exists() else b""
        records = [json.loads(line) for line in data.splitlines() if line]
        trajectories[directory.name] = {"checkpoint": load(path), "checkpoint_sha256": sha256_file(path),
            "checkpoint_lf_sha256": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "sample_count": len(records), "run_ids": [r["run_id"] for r in records],
            "sample_bytes": len(data), "samples_sha256": hashlib.sha256(data).hexdigest(),
            "samples_lf_sha256": hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest(),
            "sample_line_sha256": [hashlib.sha256(line.replace(b"\r\n", b"\n")).hexdigest()
                                   for line in data.splitlines(keepends=True)],
            "lf_count": data.count(b"\n"), "crlf_count": data.count(b"\r\n")}
    return {"schema": "p3-campaign-snapshot-v2", "captured_at": utc_now(), "captured_qpc": qpc()[0],
            "checkpoint": checkpoint, "checkpoint_sha256": sha256_file(campaign / "checkpoint.json"),
            "checkpoint_lf_sha256": hashlib.sha256((campaign / "checkpoint.json").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "trajectories": trajectories}


def acceptance(evidence_integrity_pass, execution_complete, timing_checks_pass):
    fields = {"evidence_integrity_pass": evidence_integrity_pass,
              "execution_complete": execution_complete, "timing_checks_pass": timing_checks_pass}
    if any(type(value) is not bool for value in fields.values()):
        raise ValueError("Acceptance flags must be booleans")
    return {**fields, "comparison_ready": all(fields.values())}


def acceptance_exit(status, require_two=False):
    if not status["evidence_integrity_pass"]:
        return 1
    return 2 if require_two and not status["comparison_ready"] else 0


def verify_setup_evidence(directory, manifest):
    directory = Path(directory)
    for name in ("resources", "frozen_files"):
        check_operation(load(directory / (name + ".operation.json")), directory, manifest, name)
    source_op = load(directory / "frozen_files.operation.json")
    actual = {line.split(maxsplit=1)[1].strip(): line.split()[0]
              for line in (directory / "frozen_files.stdout.txt").read_text().splitlines()}
    identity = source_op["returncode"] == 0 and source_op["timed_out"] is False and actual == manifest["frozen_files_expected"]
    from autotuner.session import valid_formal_gate
    resource_op = load(directory / "resources.operation.json")
    gate = resource_op["returncode"] == 0 and resource_op["timed_out"] is False and valid_formal_gate(
        load(directory / "resources.stdout.txt"), load(ROOT / "configs/measurement_protocol.json"))
    return {"frozen_identity_pass": identity, "formal_resource_gate_pass": gate}


def verify_recovery(directory, current_snapshot=None):
    directory = Path(directory)
    result = {"evidence_integrity_pass": False, "timing_checks_pass": False,
              "recovery_eligible": False, "errors": []}
    try:
        manifest, policy = load(directory / "manifest.json"), load(directory / "policy.json")
        if manifest.get("purpose") != "recover" or policy.get("schema") != "p3-clock-recovery-policy-v2" or \
                policy.get("batch_id") != manifest["batch_id"] or manifest.get("policy_sha256") != sha256_file(directory / "policy.json"):
            raise ValueError("Recovery policy/manifest binding differs")
        for key, expected in (("windows", 2), ("intervals_per_window", 10), ("seconds_per_interval", 3),
                              ("total_interval_count", 20), ("total_sleep_budget_seconds", 60)):
            if type(policy.get(key)) is not int or policy[key] != expected:
                raise ValueError("Recovery policy count/budget differs")
        for name in ("window_A", "window_B"):
            spec = manifest["operations"][name]
            if type(spec.get("intervals")) is not int or spec["intervals"] != 10 or \
                    type(spec.get("seconds")) is not int or spec["seconds"] != 3:
                raise ValueError("Recovery manifest must request exactly 10x3 seconds per window")
        if policy.get("criteria_sha256") != CRITERIA_SHA or policy.get("all_twenty_required") is not True or \
                policy.get("no_extra_recovery_attempts") is not True:
            raise ValueError("Recovery criteria/rules differ")
        checks = {name: verify_clock_evidence(directory, name) for name in ("window_A", "window_B")}
        before, after = load(directory / "campaign_before.json"), load(directory / "campaign_after.json")
        if any(snapshot["checkpoint"]["session_id"] != SESSION or
               snapshot["checkpoint"]["fingerprint"]["content_commit"] != FORMAL_CONTENT for snapshot in (before, after)):
            raise ValueError("Recovery snapshot formal identity differs")
        if manifest["campaign_before_sha256"] != sha256_file(directory / "campaign_before.json") or \
                before["checkpoint"] != after["checkpoint"] or before["trajectories"] != after["trajectories"]:
            raise ValueError("Campaign changed during recovery")
        if current_snapshot is not None and (after["checkpoint_lf_sha256"] != current_snapshot["checkpoint_lf_sha256"] or
                {k: (v["checkpoint_lf_sha256"], v["samples_lf_sha256"]) for k, v in after["trajectories"].items()} !=
                {k: (v["checkpoint_lf_sha256"], v["samples_lf_sha256"]) for k, v in current_snapshot["trajectories"].items()}):
            raise ValueError("Recovery is stale for current campaign")
        setup = verify_setup_evidence(directory, manifest)
        identity, gate = setup["frozen_identity_pass"], setup["formal_resource_gate_pass"]
        integrity = identity and all(item["evidence_integrity_pass"] for item in checks.values())
        timing = all(item["pass"] for item in checks.values())
        result.update(evidence_integrity_pass=integrity, timing_checks_pass=timing,
                      recovery_eligible=integrity and timing and gate, formal_resource_gate_pass=gate,
                      frozen_identity_pass=identity, windows=checks,
                      policy_sha256=sha256_file(directory / "policy.json"),
                      manifest_sha256=sha256_file(directory / "manifest.json"))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        result["errors"].append(str(error))
    return result


def verify_batch_binding(directory, current_snapshot):
    """Bind new records/checkpoints and both clocks to this exact campaign call."""
    directory = Path(directory)
    manifest = load(directory / "manifest.json")
    controller = load(directory / "controller.json")
    before, after = load(directory / "campaign_before.json"), load(directory / "campaign_after.json")
    if manifest["campaign_before_sha256"] != sha256_file(directory / "campaign_before.json") or \
            controller["campaign_after_sha256"] != sha256_file(directory / "campaign_after.json") or \
            controller["batch_id"] != manifest["batch_id"]:
        raise ValueError("Batch checkpoint/controller binding differs")
    for snapshot in (before, after, current_snapshot):
        checkpoint = snapshot["checkpoint"]
        if checkpoint["session_id"] != SESSION or checkpoint["fingerprint"]["content_commit"] != FORMAL_CONTENT or \
                checkpoint["fingerprint"] != before["checkpoint"]["fingerprint"]:
            raise ValueError("Batch frozen campaign identity differs")
    for name, previous in before["trajectories"].items():
        later = after["trajectories"][name]
        count = previous["sample_count"]
        if later["run_ids"][:count] != previous["run_ids"] or \
                later["sample_line_sha256"][:count] != previous["sample_line_sha256"] or \
                later["checkpoint"]["observations"][:len(previous["checkpoint"]["observations"])] != \
                previous["checkpoint"]["observations"]:
            raise ValueError("Existing batch observations/IDs changed")
    # A historical passing batch cannot certify a newer, different checkpoint or new runs.
    if after["checkpoint_lf_sha256"] != current_snapshot["checkpoint_lf_sha256"] or \
            {k: (v["checkpoint_lf_sha256"], v["samples_lf_sha256"], v["run_ids"])
             for k, v in after["trajectories"].items()} != \
            {k: (v["checkpoint_lf_sha256"], v["samples_lf_sha256"], v["run_ids"])
             for k, v in current_snapshot["trajectories"].items()}:
        raise ValueError("Stale batch does not cover current checkpoint/records")
    invoked = controller["campaign_invoked"]
    if type(invoked) is not bool:
        raise ValueError("Invalid campaign_invoked type")
    if invoked:
        if manifest["operations"]["campaign"]["command"] != campaign_command(manifest["repo_root_at_run"]):
            raise ValueError("Formal campaign command differs")
        for phase in ("clock_before", "clock_after"):
            spec = manifest["operations"][phase]
            if spec["intervals"] != 3 or spec["seconds"] != 3:
                raise ValueError("Batch boundary clock count/duration differs")
        operation = load(directory / "campaign.operation.json")
        check_operation(operation, directory, manifest, "campaign")
        if operation["returncode"] != controller["campaign_returncode"]:
            raise ValueError("Campaign returncode differs")
        if controller["pre_clock_pass"] is not True:
            raise ValueError("Campaign invoked despite pre-clock refusal")
        pre, post = (load(directory / (phase + ".operation.json"))
                     for phase in ("clock_before", "clock_after"))
        if not pre["qpc_end"] <= operation["qpc_start"] < operation["qpc_end"] <= post["qpc_start"]:
            raise ValueError("Clock/campaign operation order differs")
    elif before["checkpoint_lf_sha256"] != after["checkpoint_lf_sha256"] or \
            any(v["run_ids"] != after["trajectories"][k]["run_ids"] for k, v in before["trajectories"].items()):
        raise ValueError("Campaign changed despite no invocation")
    return {"evidence_integrity_pass": True, "campaign_invoked": invoked,
            "new_run_ids": [run_id for k, v in after["trajectories"].items() for run_id in v["run_ids"]
                            if run_id not in before["trajectories"].get(k, {}).get("run_ids", [])],
            "manifest_sha256": sha256_file(directory / "manifest.json"),
            "campaign_operation_sha256": sha256_file(directory / "campaign.operation.json") if invoked else None}
