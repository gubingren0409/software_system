#!/usr/bin/env bash
# One independent, single-workload SPECjvm2008 process. Invoked by run_optional.ps1.
set -uo pipefail

if [[ $# -ne 4 ]]; then
  echo 'Usage: run_one.sh PROJECT_DIR WORKLOAD HEAP_CONFIG REPETITION' >&2
  exit 2
fi

project_dir="$1"
workload="$2"
heap_config="$3"
repetition="$4"
spec_dir='/home/gubingren/benchmarks/SPECjvm2008'
java7='/home/gubingren/java/java-se-7u75-ri/bin/java'
java8='/home/gubingren/java/java-se-8u41-ri/bin/java'
local_log_dir="${spec_dir}/optional_run_logs"
result_repo="${project_dir}/specjvm2008/results"

case "$workload" in
  compress|derby|sunflow|scimark.fft.large) ;;
  *) echo "Unsupported workload: $workload" >&2; exit 2 ;;
esac
case "$heap_config" in
  default) heap_args=() ;;
  xmx512m) heap_args=(-Xmx512m) ;;
  xmx1024m) heap_args=(-Xmx1024m) ;;
  xmx2560m) heap_args=(-Xmx2560m) ;;
  *) echo "Unsupported heap config: $heap_config" >&2; exit 2 ;;
esac
case "$repetition" in 1|2|3) ;; *) echo 'Repetition must be 1, 2, or 3' >&2; exit 2 ;; esac

slug="${workload//./_}"
key="${slug}__${heap_config}__r${repetition}"
repo_log_dir="${project_dir}/logs/jvm_parameter/${heap_config}"
repo_gc_dir="${project_dir}/logs/jvm_parameter/gc"
repo_meta="${repo_log_dir}/${key}.meta"
repo_run_log="${repo_log_dir}/${key}.log"
repo_reporter_log="${repo_log_dir}/${key}.reporter.log"
repo_gc_log="${repo_gc_dir}/${key}.gc.log"
local_run_log="${local_log_dir}/${key}.log"
local_reporter_log="${local_log_dir}/${key}.reporter.log"
local_gc_log="${local_log_dir}/${key}.gc.log"
watchdog_seconds=900

for item in "$repo_meta" "$repo_run_log" "$repo_reporter_log" "$repo_gc_log" \
            "$local_run_log" "$local_reporter_log" "$local_gc_log"; do
  if [[ -e "$item" ]]; then
    echo "Refusing to overwrite existing attempt artifact: $item" >&2
    exit 3
  fi
done
if [[ ! -f "${spec_dir}/SPECjvm2008.jar" || ! -x "$java7" || ! -x "$java8" ]]; then
  echo 'SPEC kit or Java RI binaries are missing' >&2
  exit 3
fi

mkdir -p "$local_log_dir" "$repo_log_dir" "$repo_gc_dir"
export JAVA_HOME='/home/gubingren/java/java-se-7u75-ri'
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=''
cd "$spec_dir" || exit 3

before_ids="$(find results -mindepth 1 -maxdepth 1 -type d -name 'SPECjvm2008.*' -printf '%f\n' | sort)"
start_time="$(date --iso-8601=seconds)"
command_text="timeout --signal=TERM --kill-after=30s ${watchdog_seconds}s ${java7} -XX:+PrintGCDetails -XX:+PrintGCTimeStamps -Xloggc:${local_gc_log} ${heap_args[*]:-} -jar SPECjvm2008.jar --base -bt 16 ${workload}"
{
  echo 'PURPOSE=Independent optional -Xmx single-workload attempt; not a compliant full Base result'
  echo "RUN_KEY=$key"
  echo "START_TIME=$start_time"
  echo "COMMAND=$command_text"
  echo "JAVA_HOME=$JAVA_HOME"
  echo "CLASSPATH=$CLASSPATH"
  echo "UNAME=$(uname -a)"
  echo 'MEMORY_BEFORE:'
  free -h
  echo 'JAVA_VERSION:'
  "$java7" -version 2>&1
  echo 'MAX_HEAP_FLAG_BEFORE_RUN:'
  "$java7" "${heap_args[@]}" -XX:+PrintFlagsFinal -version 2>&1 | grep 'MaxHeapSize'
  timeout --signal=TERM --kill-after=30s "${watchdog_seconds}s" \
    "$java7" -XX:+PrintGCDetails -XX:+PrintGCTimeStamps \
    "-Xloggc:${local_gc_log}" "${heap_args[@]}" \
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
  printf 'RESULT_DISCOVERY_ERROR=Expected exactly one new SPEC result directory; found: %s\n' "$new_ids" >> "$local_run_log"
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

# Copy only this attempt's new result. Existing results, especially .007, are immutable.
if [[ -n "$result_id" ]]; then
  if [[ -e "${result_repo}/${result_id}" ]]; then
    echo "Refusing to overwrite existing repository result: ${result_repo}/${result_id}" >&2
    exit 4
  fi
  cp -a "results/${result_id}" "$result_repo/" || exit 4
fi
cp -a "$local_run_log" "$repo_run_log" || exit 4
if [[ -f "$local_reporter_log" ]]; then cp -a "$local_reporter_log" "$repo_reporter_log" || exit 4; fi
if [[ -f "$local_gc_log" ]]; then cp -a "$local_gc_log" "$repo_gc_log" || exit 4; fi

end_time="$(date --iso-8601=seconds)"
{
  echo "run_key=$key"
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
  echo "gc_log=$(basename "$repo_gc_log")"
} > "$repo_meta"

echo "COMPLETED_ATTEMPT=$key JAVA_EXIT=$java_exit REPORTER_EXIT=$reporter_exit RESULT_ID=$result_id"
exit 0
