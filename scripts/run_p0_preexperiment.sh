#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
umask 077
ulimit -c 0

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

mkdir -p build/p0 evidence/p0/preexperiment
raw_dir="evidence/p0/preexperiment"
summary="$raw_dir/summary.csv"

printf 'compiler,optimization,matrix_n,block_size,exit_code,wall_seconds,reported_seconds,checksum,max_abs_error,max_rel_error,failed_entries,verification\n' > "$summary"

{
    printf 'collected_at_local=%s\n' "$(TZ=Asia/Shanghai date --iso-8601=seconds)"
    printf 'collected_at_utc=%s\n' "$(date --utc --iso-8601=seconds)"
    printf 'distro=%s\n' "${WSL_DISTRO_NAME:-unknown}"
    printf 'kernel=%s\n' "$(uname -srmo)"
    printf 'source_sha256='
    sha256sum code/original/matrix_multiplication.c | awk '{print $1}'
    printf 'gcc_path=%s\n' "$(command -v gcc)"
    gcc --version | head -n 1
} > "$raw_dir/session.txt"

sha256sum --check code/original/SHA256SUMS > "$raw_dir/source_hash_check.txt" 2>&1

for opt in O0 O1 O2 O3; do
    original_binary="build/p0/original_${opt}"
    original_log="$raw_dir/compile_original_${opt}.txt"
    {
        printf 'command=gcc -std=c11 -Wall -Wextra -Wpedantic -%s code/original/matrix_multiplication.c -o %s\n' "$opt" "$original_binary"
        gcc -std=c11 -Wall -Wextra -Wpedantic "-$opt" \
            code/original/matrix_multiplication.c -o "$original_binary"
        printf 'exit_code=0\n'
    } > "$original_log" 2>&1
done

for opt in O0 O3; do
    probe_binary="build/p0/probe_${opt}_n65"
    probe_log="$raw_dir/compile_probe_${opt}.txt"
    {
        printf 'command=gcc -std=c11 -Wall -Wextra -Wpedantic -Wconversion -DMATRIX_N=65 -%s experiments/p0/matrix_multiplication_probe.c -lm -o %s\n' "$opt" "$probe_binary"
        gcc -std=c11 -Wall -Wextra -Wpedantic -Wconversion -DMATRIX_N=65 \
            "-$opt" experiments/p0/matrix_multiplication_probe.c -lm -o "$probe_binary"
        printf 'exit_code=0\n'
    } > "$probe_log" 2>&1

    for block in 8 24 64 128; do
        case_id="${opt}_n65_s${block}"
        stdout_file="$raw_dir/${case_id}.stdout.txt"
        stderr_file="$raw_dir/${case_id}.stderr.txt"
        command_file="$raw_dir/${case_id}.command.txt"
        printf 'command=%s %s\n' "$probe_binary" "$block" > "$command_file"

        start_ns="$(date +%s%N)"
        set +e
        "$probe_binary" "$block" > "$stdout_file" 2> "$stderr_file"
        exit_code=$?
        set -e
        end_ns="$(date +%s%N)"
        wall_seconds="$(awk -v start="$start_ns" -v end="$end_ns" 'BEGIN { printf "%.9f", (end-start)/1000000000 }')"
        printf 'exit_code=%d\nwall_seconds=%s\n' "$exit_code" "$wall_seconds" >> "$command_file"

        reported="$(awk -F= '$1=="elapsed_seconds" {print $2}' "$stdout_file")"
        checksum="$(awk -F= '$1=="checksum" {print $2}' "$stdout_file")"
        max_error="$(awk -F= '$1=="max_abs_error" {print $2}' "$stdout_file")"
        max_rel_error="$(awk -F= '$1=="max_rel_error" {print $2}' "$stdout_file")"
        failed_entries="$(awk -F= '$1=="failed_entries" {print $2}' "$stdout_file")"
        verification="$(awk -F= '$1=="verification" {print $2}' "$stdout_file")"
        printf 'gcc,%s,65,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
            "$opt" "$block" "$exit_code" "$wall_seconds" "${reported:-}" \
            "${checksum:-}" "${max_error:-}" "${max_rel_error:-}" \
            "${failed_entries:-}" "${verification:-EXPECTED_REJECTION}" >> "$summary"
    done
done

valgrind_binary="build/p0/probe_valgrind_n65"
{
    printf 'command=gcc -std=c11 -Wall -Wextra -Wpedantic -Wconversion -DMATRIX_N=65 -O1 -g experiments/p0/matrix_multiplication_probe.c -lm -o %s\n' "$valgrind_binary"
    gcc -std=c11 -Wall -Wextra -Wpedantic -Wconversion -DMATRIX_N=65 -O1 -g \
        experiments/p0/matrix_multiplication_probe.c -lm -o "$valgrind_binary"
    printf 'exit_code=0\n'
} > "$raw_dir/compile_probe_valgrind.txt" 2>&1

printf 'command=valgrind --leak-check=full --track-origins=yes --error-exitcode=99 %s 24\n' \
    "$valgrind_binary" > "$raw_dir/valgrind_n65_s24.command.txt"
set +e
valgrind --leak-check=full --track-origins=yes --error-exitcode=99 \
    "$valgrind_binary" 24 \
    > "$raw_dir/valgrind_n65_s24.stdout.txt" \
    2> "$raw_dir/valgrind_n65_s24.stderr.txt"
valgrind_exit=$?
set -e
printf 'exit_code=%d\n' "$valgrind_exit" >> "$raw_dir/valgrind_n65_s24.command.txt"
test "$valgrind_exit" -eq 0
grep -q 'ERROR SUMMARY: 0 errors' "$raw_dir/valgrind_n65_s24.stderr.txt"

{
    printf 'command=objdump -d build/p0/original_O3 | grep multiplication instructions\n'
    objdump -d build/p0/original_O3 | grep -E 'mulsd|mulpd|vmul|vfmadd' | head -n 20
    printf 'pipeline_exit_codes=%s\n' "${PIPESTATUS[*]}"
} > "$raw_dir/original_o3_multiply_instructions.txt" 2>&1

python3 - "$summary" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))

valid = [row for row in rows if int(row["block_size"]) <= int(row["matrix_n"])]
rejected = [row for row in rows if int(row["block_size"]) > int(row["matrix_n"])]
assert len(valid) == 6
assert all(row["exit_code"] == "0" for row in valid)
assert all(row["verification"] == "PASS" for row in valid)
assert all(float(row["max_abs_error"]) <= 1e-12 for row in valid)
assert all(row["failed_entries"] == "0" for row in valid)
assert len({row["checksum"] for row in valid}) == 1
assert len(rejected) == 2
assert all(row["exit_code"] != "0" for row in rejected)
print("preexperiment_verification=PASS")
print(f"valid_cases={len(valid)}")
print(f"expected_rejections={len(rejected)}")
PY
