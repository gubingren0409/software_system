#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly SPEC_DIR="/home/gubingren/benchmarks/SPECjvm2008"
readonly RESULT_ID="SPECjvm2008.007"
readonly RAW_FILE="${SPEC_DIR}/results/${RESULT_ID}/${RESULT_ID}.raw"
readonly LOG_FILE="${PROJECT_DIR}/logs/reporter_regeneration.log"

export JAVA_HOME="/home/gubingren/java/java-se-8u41-ri"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

cd "${SPEC_DIR}"
{
  echo "PURPOSE=Generate reports from the completed Java 7 Base raw result; no benchmark is rerun"
  echo "START_TIME=$(date --iso-8601=seconds)"
  echo "COMMAND=java -jar SPECjvm2008.jar --reporter ${RAW_FILE}"
  java -version 2>&1
  java -jar SPECjvm2008.jar --reporter "${RAW_FILE}"
  status=$?
  echo "END_TIME=$(date --iso-8601=seconds)"
  echo "EXIT_STATUS=${status}"
  exit "${status}"
} 2>&1 | tee "${LOG_FILE}"

mkdir -p "${PROJECT_DIR}/specjvm2008/results"
cp -a "${SPEC_DIR}/results/." "${PROJECT_DIR}/specjvm2008/results/"
