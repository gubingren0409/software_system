"""Capture targeted test commands and genuine return codes, never target measurements."""
import subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; sys.path.insert(0,str(ROOT))
from scripts.p3_clock_contract import capture
label=sys.argv[1]
command=[sys.executable,'-B','-X','utf8','scripts/verify_raw_grid_code.py']
op=capture(command,HERE,label,HERE.name,timeout=240)
print(op['returncode']); raise SystemExit(op['returncode'] if type(op['returncode']) is int else 1)
