#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly SPEC_DIR="${HOME}/benchmarks/SPECjvm2008"

export JAVA_HOME="${HOME}/java/java-se-7u75-ri"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

cd "${SPEC_DIR}"
set +e
{
  echo "START_TIME=$(date --iso-8601=seconds)"
  echo "COMMAND=java -jar SPECjvm2008.jar startup.compiler.sunflow"
  java -version 2>&1
  java -jar SPECjvm2008.jar startup.compiler.sunflow
  status=$?
  echo "END_TIME=$(date --iso-8601=seconds)"
  echo "EXIT_STATUS=${status}"
  exit "${status}"
} 2>&1 | tee "${PROJECT_DIR}/logs/java7_compiler_check.log"
check_status=${PIPESTATUS[0]}
set -e

exit "${check_status}"
