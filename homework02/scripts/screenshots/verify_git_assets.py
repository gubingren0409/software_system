#!/usr/bin/env python3
"""Verify portable report images and evidence from the Git index or HEAD."""

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
PREFIX = "homework02/"
SESSION = PREFIX + "evidence/terminal_screenshots/2026-10-08-set2/"
VIEWS = ("historicalenvironment", "currentenvironment", "base", "repeats",
         "heapmatrix", "derbygc", "oomsummary", "oomraw")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPOSITORY)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", choices=("INDEX", "HEAD"), default="INDEX")
    args = parser.parse_args()
    listing = git("ls-files", "-z") if args.ref == "INDEX" else git("ls-tree", "-r", "--name-only", "-z", args.ref)
    files = set(listing.decode("utf-8").split("\0")) - {""}

    def blob(path):
        require(path in files, f"Missing or case-mismatched Git file: {path}")
        return git("show", f":{path}" if args.ref == "INDEX" else f"{args.ref}:{path}")

    image_count = 0
    main_count = 0
    for path in sorted(files):
        if not path.startswith(PREFIX) or not path.endswith(".md"):
            continue
        body = blob(path).decode("utf-8-sig")
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body):
            require(not re.match(r"^(?:[a-zA-Z]+:|/)", target) and "\\" not in target,
                    f"Nonportable image reference in {path}: {target}")
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            require(resolved.startswith(PREFIX), f"Image escapes submission directory: {resolved}")
            data = blob(resolved)
            require(data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")), f"Not PNG/JPEG bytes: {resolved}")
            image_count += 1
            if path == PREFIX + "README.md":
                main_count += 1
    require(main_count > 0, "Main README has no embedded images")

    source_paths = set()
    for view in VIEWS:
        record = json.loads(blob(SESSION + view + ".json").decode("utf-8-sig"))
        require(hashlib.sha256(blob(PREFIX + record["screenshot"])).hexdigest() == record["screenshot_sha256"],
                f"Screenshot differs in Git: {view}")
        blob(PREFIX + record["transcript"])
        require(hashlib.sha256(blob(PREFIX + "scripts/screenshots/show_terminal_evidence.ps1")).hexdigest()
                == record["display_script_sha256"], f"Capture script differs in Git: {view}")
        for source in record["sources"]:
            path = PREFIX + source["path"]
            require(path in files, f"Screenshot source not in Git: {path}")
            source_paths.add(path)
    print(f"PASS [{args.ref}]: {main_count} README images; {image_count} Markdown image references; "
          "relative POSIX paths, exact case, PNG/JPEG bytes in Git")
    print(f"PASS [{args.ref}]: 8 native screenshots, transcripts, method hash and "
          f"{len(source_paths)} distinct source files included")


if __name__ == "__main__":
    main()
