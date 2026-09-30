#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly SPEC_DIR="/home/gubingren/benchmarks/SPECjvm2008"
readonly JAVA7_DIR="/home/gubingren/java/java-se-7u75-ri"
readonly JAVA8_DIR="/home/gubingren/java/java-se-8u41-ri"
readonly CSV_FILE="${PROJECT_DIR}/analysis/repeat_test_results.csv"

export JAVA_HOME="${JAVA7_DIR}"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

cd "${SPEC_DIR}"
printf 'run,benchmark,score_ops_per_min,start_time,end_time,result_id,valid,command\n' > "${CSV_FILE}"

for run_number in 1 2 3; do
  log_file="${PROJECT_DIR}/logs/repeat_compress_run${run_number}.log"
  set +e
  {
    echo "PURPOSE=Single-workload repeat; not a complete publishable Base suite"
    echo "START_TIME=$(date --iso-8601=seconds)"
    echo "COMMAND=java -jar SPECjvm2008.jar --base -bt 16 compress"
    echo "JAVA_HOME=${JAVA_HOME}"
    echo "CLASSPATH=${CLASSPATH}"
    java -version 2>&1
    java -jar SPECjvm2008.jar --base -bt 16 compress
    status=$?
    echo "END_TIME=$(date --iso-8601=seconds)"
    echo "EXIT_STATUS=${status}"
    exit "${status}"
  } 2>&1 | tee "${log_file}"
  run_status=${PIPESTATUS[0]}
  set -e

  if [[ "${run_status}" -ne 0 ]]; then
    echo "Repeat ${run_number} failed with exit status ${run_status}; see ${log_file}" >&2
    exit "${run_status}"
  fi

  raw_file=$(sed -n '/^Results are stored in:/{n;p;q;}' "${log_file}")
  score=$(sed -n 's/^Score on compress: \([0-9.]*\) ops\/m$/\1/p' "${log_file}" | tail -n 1)
  start_time=$(sed -n 's/^START_TIME=//p' "${log_file}" | tail -n 1)
  end_time=$(sed -n 's/^END_TIME=//p' "${log_file}" | tail -n 1)
  if [[ ! -f "${raw_file}" || -z "${score}" ]]; then
    echo "Repeat ${run_number} is missing a raw file or score; see ${log_file}" >&2
    exit 1
  fi
  if ! grep -q '^Valid run!$' "${log_file}"; then
    echo "Repeat ${run_number} did not print a valid-run marker; see ${log_file}" >&2
    exit 1
  fi
  result_id=$(basename "$(dirname "${raw_file}")")
  printf 'Run%s,compress,%s,%s,%s,%s,true,"java -jar SPECjvm2008.jar --base -bt 16 compress"\n' \
    "${run_number}" "${score}" "${start_time}" "${end_time}" "${result_id}" >> "${CSV_FILE}"
  echo "RECORDED_RUN=${run_number} RESULT_ID=${result_id} SCORE_OPS_PER_MIN=${score}"
done

{
  echo "PURPOSE=Generate reports from three already completed raw results; no benchmarks are rerun"
  echo "START_TIME=$(date --iso-8601=seconds)"
  for result_id in $(awk -F, 'NR > 1 {print $6}' "${CSV_FILE}"); do
    raw_file="${SPEC_DIR}/results/${result_id}/${result_id}.raw"
    echo "COMMAND=${JAVA8_DIR}/bin/java -jar SPECjvm2008.jar --reporter ${raw_file}"
    "${JAVA8_DIR}/bin/java" -jar SPECjvm2008.jar --reporter "${raw_file}"
  done
  echo "END_TIME=$(date --iso-8601=seconds)"
} 2>&1 | tee "${PROJECT_DIR}/logs/repeat_reporter.log"

cp -a "${SPEC_DIR}/results/." "${PROJECT_DIR}/specjvm2008/results/"
