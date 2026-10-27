"""Inspect preserved Release machine code; no program or profiler is executed."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, default=ROOT / "results/stage-b")
parser.add_argument("--destination", type=Path, required=True)
args = parser.parse_args()
OUT, DEST = args.out.resolve(), args.destination.resolve()


def functions(label):
    raw = (OUT / f"final/disassembly-{label}/stdout.txt").read_text()
    result = {}
    current = None
    for line in raw.splitlines():
        header = re.match(r"^[0-9a-f]+ <([^>]+)>:", line)
        if header:
            current = header[1]
            result[current] = []
        instruction = re.match(r"^\s+[0-9a-f]+:\s+(.+)$", line)
        if current and instruction:
            value = instruction[1].split("#")[0].strip()
            value = re.sub(r"\b[0-9a-f]+\s+<([^>]+)>", r"<\1>", value)
            value = re.sub(r"-?0x[0-9a-f]+\(%rip\)", "RIPREL(%rip)", value)
            result[current].append(value)
    return result


normal, alternative = functions("release"), functions("i-no-inline-keyword")
i_symbols = sorted(name for name in normal if re.fullmatch(r"(?:sort|recursive|merge|copy|alloc|free)_i(?:[.$].*)?", name))
assert i_symbols
identical = all(normal[name] == alternative.get(name) for name in i_symbols)
normal_nm = (OUT / "final/nm-release/stdout.txt").read_text()
alternative_nm = (OUT / "final/nm-i-no-inline-keyword/stdout.txt").read_text()


def sizes(text):
    return {name: int(size) for size, name in re.findall(r"^\d+\s+(\d+)\s+[Tt]\s+(\S+)$", text, re.M)}


size_map, other_sizes = sizes(normal_nm), sizes(alternative_nm)
volume = {v: {name: size for name, size in size_map.items()
                 if re.fullmatch(rf"(?:sort|recursive|merge|copy|alloc|free|insertion)_{v}(?:[.$].*)?", name)} for v in "aipcmf"}
remarks = (OUT / "final/build-release/stderr.txt").read_text()
result = {"recursive_inline_keyword_changes_code": not identical,
          "i_function_names": i_symbols, "i_bytes_with_keyword": sum(size_map[n] for n in i_symbols),
          "i_bytes_without_keyword": sum(other_sizes[n] for n in i_symbols),
          "normalization": "drop instruction addresses, symbolic-target absolute addresses and RIP displacements; retain mnemonics/registers/immediates and target names",
          "private_text_bytes": {v: sum(group.values()) for v, group in volume.items()}, "symbols": volume,
          "recursive_i_rejected_by_compiler": "'recursive_i' not inlined into 'recursive_i'" in remarks,
          "a_merge_already_inlined": "'merge_a' inlined into 'sort_a'" in remarks,
          "i_merge_inlined": "'merge_i' inlined into 'recursive_i'" in remarks,
          "i_copy_inlined": "'copy_i' inlined into 'merge_i'" in remarks,
          "i_alloc_inlined": "'alloc_i' inlined into 'merge_i'" in remarks,
          "i_recursive_call_instructions": [line for n in i_symbols for line in normal[n] if re.match(r"call", line) and "<recursive_i>" in line]}
DEST.mkdir(parents=True, exist_ok=False)
(DEST / "inline-analysis.json").write_text(json.dumps(result, indent=2) + "\n")
(DEST / "i-normalized-assembly.txt").write_text("\n".join(name+"\n"+"\n".join(normal[name]) for name in i_symbols)+"\n")
(DEST / "i-no-keyword-normalized-assembly.txt").write_text("\n".join(name+"\n"+"\n".join(alternative[name]) for name in i_symbols)+"\n")
print(json.dumps(result, indent=2))
