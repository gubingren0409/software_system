#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly SPEC_DIR="/home/gubingren/benchmarks/SPECjvm2008"
readonly JAVA7_DIR="/home/gubingren/java/java-se-7u75-ri"
readonly JAVA8_DIR="/home/gubingren/java/java-se-8u41-ri"
readonly CSV_FILE="${PROJECT_DIR}/analysis/jvm_parameter_base_results.csv"

export JAVA_HOME="${JAVA7_DIR}"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

cd "${SPEC_DIR}"
printf 'variant,xmx,score_ops_per_min,start_time,end_time,result_id,valid,command\n' > "${CSV_FILE}"

for variant in baseline modified; do
  if [[ "${variant}" == baseline ]]; then
    log_file="${PROJECT_DIR}/logs/parameter_base_baseline.log"
    xmx_value="default"
    command_text="java -jar SPECjvm2008.jar --base -bt 16 compress"
    jvm_args=()
  else
    log_file="${PROJECT_DIR}/logs/parameter_base_xmx2560m.log"
    xmx_value="2560m"
    command_text="java -Xmx2560m -jar SPECjvm2008.jar --base -bt 16 compress"
    jvm_args=(-Xmx2560m)
  fi

  set +e
  {
    echo "PURPOSE=Base-mode single-workload comparison; not a compliant full-suite Base result"
    echo "START_TIME=$(date --iso-8601=seconds)"
    echo "COMMAND=${command_text}"
    echo "JAVA_HOME=${JAVA_HOME}"
    echo "CLASSPATH=${CLASSPATH}"
    java -version 2>&1
    echo "MAX_HEAP_FLAG_BEFORE_RUN:"
    java "${jvm_args[@]}" -XX:+PrintFlagsFinal -version 2>&1 | grep 'MaxHeapSize'
    java "${jvm_args[@]}" -jar SPECjvm2008.jar --base -bt 16 compress
    status=$?
    echo "END_TIME=$(date --iso-8601=seconds)"
    echo "EXIT_STATUS=${status}"
    exit "${status}"
  } 2>&1 | tee "${log_file}"
  run_status=${PIPESTATUS[0]}
  set -e

  if [[ "${run_status}" -ne 0 ]]; then
    echo "${variant} failed with exit status ${run_status}; see ${log_file}" >&2
    exit "${run_status}"
  fi

  raw_file=$(sed -n '/^Results are stored in:/{n;p;q;}' "${log_file}")
  score=$(sed -n 's/^Score on compress: \([0-9.]*\) ops\/m$/\1/p' "${log_file}" | tail -n 1)
  start_time=$(sed -n 's/^START_TIME=//p' "${log_file}" | tail -n 1)
  end_time=$(sed -n 's/^END_TIME=//p' "${log_file}" | tail -n 1)
  if [[ ! -f "${raw_file}" || -z "${score}" ]]; then
    echo "${variant} is missing a raw file or score; see ${log_file}" >&2
    exit 1
  fi
  if ! grep -q '^Valid run!$' "${log_file}"; then
    echo "${variant} did not print a valid-run marker; see ${log_file}" >&2
    exit 1
  fi
  result_id=$(basename "$(dirname "${raw_file}")")
  printf '%s,%s,%s,%s,%s,%s,true,"%s"\n' \
    "${variant}" "${xmx_value}" "${score}" "${start_time}" "${end_time}" "${result_id}" "${command_text}" >> "${CSV_FILE}"
  echo "RECORDED_VARIANT=${variant} RESULT_ID=${result_id} SCORE_OPS_PER_MIN=${score}"
done

{
  echo "PURPOSE=Generate reports from already completed Base-mode single-item raw results"
  echo "START_TIME=$(date --iso-8601=seconds)"
  for result_id in $(awk -F, 'NR > 1 {print $6}' "${CSV_FILE}"); do
    raw_file="${SPEC_DIR}/results/${result_id}/${result_id}.raw"
    echo "COMMAND=${JAVA8_DIR}/bin/java -jar SPECjvm2008.jar --reporter ${raw_file}"
    "${JAVA8_DIR}/bin/java" -jar SPECjvm2008.jar --reporter "${raw_file}"
  done
  echo "END_TIME=$(date --iso-8601=seconds)"
} 2>&1 | tee "${PROJECT_DIR}/logs/parameter_base_reporter.log"

cp -a "${SPEC_DIR}/results/." "${PROJECT_DIR}/specjvm2008/results/"
