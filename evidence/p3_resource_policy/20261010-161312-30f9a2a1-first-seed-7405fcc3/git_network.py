"""Normal GitHub fetch/push and verification; no remote or TLS settings changed."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import capture

phase = sys.argv[1]
assert phase in ("fetch", "push", "verify")
directory = HERE if phase == "fetch" else ROOT / "build" / (HERE.name + "-push")
helper = "credential.helper=/mnt/c/Program" + chr(92) + " Files/Git/mingw64/bin/git-credential-manager.exe"
prefix = ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--", "env",
          "GIT_DIR=/mnt/e/software_system/course_repo/.git/worktrees/project01",
          "GIT_WORK_TREE=/mnt/e/software_system/project01", "timeout", "90", "git", "-c", helper]
options = {"fetch": ["fetch", "github"],
           "push": ["push", "https://github.com/gubingren0409/software_system.git", "project01:project01"],
           "verify": ["ls-remote", "https://github.com/gubingren0409/software_system.git", "refs/heads/project01"]}
result = capture(prefix + options[phase], directory, "github_" + phase, HERE.name, timeout=110)
print(json.dumps({"phase": phase, "returncode": result["returncode"], "qpc_seconds": result["qpc_seconds"],
                  "stdout": (directory / result["stdout_path"]).read_text(encoding="utf-8", errors="replace"),
                  "stderr": (directory / result["stderr_path"]).read_text(encoding="utf-8", errors="replace")}))
raise SystemExit(result["returncode"] if type(result["returncode"]) is int else 1)
