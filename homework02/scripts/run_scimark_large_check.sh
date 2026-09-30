#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly SPEC_DIR="${HOME}/benchmarks/SPECjvm2008"
readonly LOG_FILE="${PROJECT_DIR}/logs/scimark_large_16t_check.log"

export JAVA_HOME="${HOME}/java/java-se-7u75-ri"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

cd "${SPEC_DIR}"
{
  echo "PURPOSE=Non-compliant short diagnostic only; not reported as a Base result"
  echo "START_TIME=$(date --iso-8601=seconds)"
  echo "COMMAND=java -jar SPECjvm2008.jar -bt 16 -wt 5s -it 5s scimark.fft.large"
  java -version 2>&1
  java -jar SPECjvm2008.jar -bt 16 -wt 5s -it 5s scimark.fft.large
  status=$?
  echo "END_TIME=$(date --iso-8601=seconds)"
  echo "EXIT_STATUS=${status}"
  exit "${status}"
} 2>&1 | tee "${LOG_FILE}"
