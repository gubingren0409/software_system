#!/usr/bin/env bash
# Re-run one formerly invalid cell without writing the original experiment tree.
set -uo pipefail

if [[ $# -ne 4 ]]; then
  echo 'Usage: run_oom_reverification_one.sh PROJECT_DIR WORKLOAD HEAP_CONFIG REPETITION' >&2
  exit 2
fi

project_dir="$1"
workload="$2"
heap_config="$3"
repetition="$4"
spec_dir='/home/gubingren/benchmarks/SPECjvm2008'
java7='/home/gubingren/java/java-se-7u75-ri/bin/java'
java8='/home/gubingren/java/java-se-8u41-ri/bin/java'
local_log_dir="${spec_dir}/oom_reverification_logs"
repo_root="${project_dir}/logs/jvm_parameter/oom_reverification"
repo_gc_dir="${repo_root}/gc"
result_repo="${project_dir}/specjvm2008/verification_results"
watchdog_seconds=900

case "$workload" in
  derby|scimark.fft.large) ;;
  *) echo "Unsupported verification workload: $workload" >&2; exit 2 ;;
esac
case "$heap_config" in
  xmx512m) heap_arg='-Xmx512m' ;;
  xmx1024m) heap_arg='-Xmx1024m' ;;
  *) echo "Unsupported verification heap: $heap_config" >&2; exit 2 ;;
esac
case "$repetition" in 1|2|3) ;; *) echo 'Repetition must be 1, 2, or 3' >&2; exit 2 ;; esac
if [[ "$workload" == derby && "$heap_config" != xmx512m ]]; then
  echo 'Only the original invalid Derby/512 MiB cell may be reverified' >&2
  exit 2
fi

slug="${workload//./_}"
source_key="${slug}__${heap_config}__r${repetition}"
key="oomverify__${source_key}"
repo_meta="${repo_root}/${key}.meta"
repo_run_log="${repo_root}/${key}.log"
repo_reporter_log="${repo_root}/${key}.reporter.log"
repo_gc_log="${repo_gc_dir}/${key}.gc.log"
local_run_log="${local_log_dir}/${key}.log"
local_reporter_log="${local_log_dir}/${key}.reporter.log"
local_gc_log="${local_log_dir}/${key}.gc.log"

for item in "$repo_meta" "$repo_run_log" "$repo_reporter_log" "$repo_gc_log" \
            "$local_run_log" "$local_reporter_log" "$local_gc_log"; do
  if [[ -e "$item" ]]; then
    echo "Refusing to overwrite verification artifact: $item" >&2
    exit 3
  fi
done
if [[ ! -f "${spec_dir}/SPECjvm2008.jar" || ! -x "$java7" || ! -x "$java8" ]]; then
  echo 'SPEC kit or Java RI binaries are missing' >&2
  exit 3
fi

mkdir -p "$local_log_dir" "$repo_root" "$repo_gc_dir" "$result_repo"
export JAVA_HOME='/home/gubingren/java/java-se-7u75-ri'
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=''
cd "$spec_dir" || exit 3

before_ids="$(find results -mindepth 1 -maxdepth 1 -type d -name 'SPECjvm2008.*' -printf '%f\n' | sort)"
start_time="$(date --iso-8601=seconds)"
command_text="timeout --signal=TERM --kill-after=30s ${watchdog_seconds}s ${java7} -XX:+PrintGCDetails -XX:+PrintGCTimeStamps -Xloggc:${local_gc_log} ${heap_arg} -jar SPECjvm2008.jar --base -bt 16 ${workload}"
{
  echo 'PURPOSE=Independent reproduction of an original OOM/invalid attempt; not part of the 48-cell matrix'
  echo "SOURCE_RUN_KEY=$source_key"
  echo "VERIFICATION_RUN_KEY=$key"
  echo "START_TIME=$start_time"
  echo "COMMAND=$command_text"
  echo 'COMMAND_EQUIVALENCE=Same Java, SPEC mode, benchmark threads, workload, heap flag and GC flags; only log destination/result namespace differ'
  echo 'WATCHDOG_NOTE=900 s verification safety boundary; original Derby Run1 used manual termination at 956 s'
  echo "JAVA_HOME=$JAVA_HOME"
  echo "CLASSPATH=$CLASSPATH"
  echo "UNAME=$(uname -a)"
  echo 'MEMORY_BEFORE:'
  free -h
  echo 'JAVA_VERSION:'
  "$java7" -version 2>&1
  echo 'MAX_HEAP_FLAG_BEFORE_RUN:'
  "$java7" "$heap_arg" -XX:+PrintFlagsFinal -version 2>&1 | grep 'MaxHeapSize'
  timeout --signal=TERM --kill-after=30s "$watchdog_seconds" \
    "$java7" -XX:+PrintGCDetails -XX:+PrintGCTimeStamps \
    "-Xloggc:${local_gc_log}" "$heap_arg" \
    -jar SPECjvm2008.jar --base -bt 16 "$workload"
  java_exit=$?
  echo "JAVA_EXIT_STATUS=$java_exit"
  echo "END_TIME=$(date --iso-8601=seconds)"
} > "$local_run_log" 2>&1

after_ids="$(find results -mindepth 1 -maxdepth 1 -type d -name 'SPECjvm2008.*' -printf '%f\n' | sort)"
new_ids="$(comm -13 <(printf '%s\n' "$before_ids") <(printf '%s\n' "$after_ids"))"
result_id=''
if [[ "$new_ids" =~ ^SPECjvm2008\.[0-9][0-9][0-9]$ ]]; then
  result_id="$new_ids"
else
  printf 'RESULT_DISCOVERY_ERROR=Expected one new SPEC result directory; found: %s\n' "$new_ids" >> "$local_run_log"
fi

reporter_exit='not_run'
if [[ -n "$result_id" && -f "results/${result_id}/${result_id}.raw" ]]; then
  {
    echo "COMMAND=${java8} -jar SPECjvm2008.jar --reporter results/${result_id}/${result_id}.raw"
    "$java8" -jar SPECjvm2008.jar --reporter "results/${result_id}/${result_id}.raw"
    reporter_exit=$?
    echo "REPORTER_EXIT_STATUS=$reporter_exit"
  } > "$local_reporter_log" 2>&1
fi

if [[ -n "$result_id" ]]; then
  if [[ -e "${result_repo}/${result_id}" ]]; then
    echo "Refusing to overwrite verification result: ${result_repo}/${result_id}" >&2
    exit 4
  fi
  cp -a "results/${result_id}" "$result_repo/" || exit 4
fi
cp -a "$local_run_log" "$repo_run_log" || exit 4
if [[ -f "$local_reporter_log" ]]; then cp -a "$local_reporter_log" "$repo_reporter_log" || exit 4; fi
if [[ -f "$local_gc_log" ]]; then cp -a "$local_gc_log" "$repo_gc_log" || exit 4; fi

end_time="$(date --iso-8601=seconds)"
{
  echo "verification_run_key=$key"
  echo "source_run_key=$source_key"
  echo "workload=$workload"
  echo "heap_config=$heap_config"
  echo "repetition=$repetition"
  echo "start_time=$start_time"
  echo "end_time=$end_time"
  echo "java_exit_status=$java_exit"
  echo "reporter_exit_status=$reporter_exit"
  echo "result_id=$result_id"
  echo "command=$command_text"
  echo "watchdog_seconds=$watchdog_seconds"
  echo "run_log=$(basename "$repo_run_log")"
  echo "gc_log=$(basename "$repo_gc_log")"
  echo "reporter_log=$(basename "$repo_reporter_log")"
} > "$repo_meta"

echo "COMPLETED_REVERIFICATION=$key JAVA_EXIT=$java_exit REPORTER_EXIT=$reporter_exit RESULT_ID=$result_id"
exit 0
