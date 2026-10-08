"""One-off, own-file-only advisory release; never deletes or changes reference data."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, resource_snapshot, sha256_file, utc_now


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkpoint = json.loads((args.campaign / "checkpoint.json").read_text())
    protocol = json.loads((args.campaign / "protocol.json").read_text())
    target = json.loads((args.campaign / "effective_target.json").read_text())
    expected_root = Path("/var/tmp/matrix-autotuner-p3-10245102457/cache").resolve(strict=True)
    if Path(target["cache_root"]).resolve(strict=True) != expected_root:
        raise ValueError("not this stage's own formal cache")
    key = checkpoint["fingerprint"]["reference_key"]
    if not re.fullmatch("[0-9a-f]{64}", key):
        raise ValueError("invalid reference cache key")
    path = (expected_root / "reference" / key / "reference.bin").resolve(strict=True)
    if not path.is_relative_to(expected_root / "reference") or path.stat().st_uid != os.getuid():
        raise ValueError("reference is outside the project-owned cache or not owned by this user")
    if path.stat().st_size != 8 * protocol["target_matrix_n"] ** 2 or \
            sha256_file(path) != checkpoint["fingerprint"]["reference_sha256"]:
        raise ValueError("reference identity mismatch")
    before = resource_snapshot()
    started = time.monotonic()
    with path.open("rb") as stream:
        os.posix_fadvise(stream.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    elapsed = time.monotonic() - started
    record = {"captured_at": utc_now(), "operation": "POSIX_FADV_DONTNEED on one owned reference file",
              "script_sha256": sha256_file(Path(__file__)), "path": str(path),
              "reference_sha256_before": checkpoint["fingerprint"]["reference_sha256"],
              "advised_bytes": path.stat().st_size, "data_deleted_or_modified": False,
              "syscall_returned_successfully": True, "syscall_wall_seconds": elapsed,
              "resource_before": before, "resource_after": resource_snapshot(),
              "scope": "Advisory file-page eviction only; Windows/WSL physical reclamation is not guaranteed."}
    atomic_write_json(args.output, record)
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
