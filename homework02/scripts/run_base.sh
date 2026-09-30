#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly SPEC_DIR="${HOME}/benchmarks/SPECjvm2008"
readonly LOG_FILE="${PROJECT_DIR}/logs/base_run.log"

export JAVA_HOME="${HOME}/java/java-se-7u75-ri"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

cd "${SPEC_DIR}"
set +e
{
  echo "START_TIME=$(date --iso-8601=seconds)"
  echo "WORKING_DIRECTORY=$(pwd)"
  echo "COMMAND=java -jar SPECjvm2008.jar --base -bt 16"
  echo "JAVA_HOME=${JAVA_HOME}"
  echo "CLASSPATH=${CLASSPATH}"
  java -version 2>&1
  java -jar SPECjvm2008.jar --base -bt 16
  status=$?
  echo "END_TIME=$(date --iso-8601=seconds)"
  echo "EXIT_STATUS=${status}"
  exit "${status}"
} 2>&1 | tee "${LOG_FILE}"
benchmark_status=${PIPESTATUS[0]}
set -e

mkdir -p "${PROJECT_DIR}/specjvm2008/results"
cp -a "${SPEC_DIR}/results/." "${PROJECT_DIR}/specjvm2008/results/"
exit "${benchmark_status}"
