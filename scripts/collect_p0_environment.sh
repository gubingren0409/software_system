#!/usr/bin/env bash
set -u
export LC_ALL=C

run() {
    printf '\n$ %s\n' "$*"
    "$@" 2>&1
    printf '[exit_code=%d]\n' "$?"
}

printf 'collected_at_local=%s\n' "$(TZ=Asia/Shanghai date --iso-8601=seconds)"
printf 'collected_at_utc=%s\n' "$(date --utc --iso-8601=seconds)"
printf 'WSL_DISTRO_NAME=%s\n' "${WSL_DISTRO_NAME:-unknown}"
printf 'container_marker=%s\n' "$(test -f /.dockerenv && echo present || echo absent)"

run uname -a
run cat /etc/os-release
run lscpu
run sh -c 'grep -E "^(Cpus_allowed|Mems_allowed)" /proc/self/status'
run taskset -pc $$
run nproc
run free -h
run df -h / /mnt/e
run uptime
run sh -c 'ps -e --no-headers | wc -l'
run sh -c 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown'
run sh -c 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>/dev/null || echo unknown'
run sh -c 'grep -m1 "cpu MHz" /proc/cpuinfo || true'

for tool in gcc clang make cmake python3 git perf valgrind; do
    printf '\n## %s\n' "$tool"
    command -v "$tool" 2>&1
    case "$tool" in
        gcc|clang|make|cmake|git|perf|valgrind) "$tool" --version 2>&1 | head -n 2 ;;
        python3) "$tool" --version 2>&1 ;;
    esac
    printf '[exit_code=%d]\n' "${PIPESTATUS[0]}"
done

printf '\n$ perf stat true\n'
perf stat true 2>&1
printf '[exit_code=%d]\n' "$?"
