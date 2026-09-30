#!/usr/bin/env bash
# Research-only profiles. Never run this against or write to SPECjvm2008.007.
set -euo pipefail

readonly project_dir=/mnt/e/software_system/course_repo/homework02
readonly spec_dir=/home/gubingren/benchmarks/SPECjvm2008
readonly log_dir="${project_dir}/logs/diagnostics"
readonly export_dir="${project_dir}/specjvm2008/results"
export JAVA_HOME=/home/gubingren/java/java-se-7u75-ri
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=

mkdir -p "${log_dir}"
cd "${spec_dir}"
for item in 'compress:015' 'sunflow:016'; do
  workload=${item%:*}
  suffix=${item#*:}
  result_id="SPECjvm2008.${suffix}"
  log_file="${log_dir}/profile_${workload}_${suffix}.log"
  if [[ -e "${spec_dir}/results/${result_id}" || -e "${export_dir}/${result_id}" || -e "${log_file}" ]]; then
    echo "Refusing to overwrite an existing diagnostic artifact: ${result_id}" >&2
    exit 2
  fi
  {
    echo 'PURPOSE=diagnostic only; not a compliant Base result and not a replacement for .007'
    echo "EXPECTED_RESULT_ID=${result_id}"
    echo "START_TIME=$(date --iso-8601=seconds)"
    echo "COMMAND=perf stat ... /usr/bin/time -v java -jar SPECjvm2008.jar --base -bt 16 ${workload}"
    java -version
    set +e
    perf stat -e cycles:u,instructions:u,cache-misses:u,context-switches,page-faults -- \
      /usr/bin/time -v java -jar SPECjvm2008.jar --base -bt 16 "${workload}"
    status=$?
    set -e
    echo "END_TIME=$(date --iso-8601=seconds)"
    echo "EXIT_STATUS=${status}"
    exit "${status}"
  } 2>&1 | tee "${log_file}"
  if [[ ! -f "${spec_dir}/results/${result_id}/${result_id}.raw" ]]; then
    echo "Missing expected raw result: ${result_id}" >&2
    exit 3
  fi
  cp -a "${spec_dir}/results/${result_id}" "${export_dir}/"
done
