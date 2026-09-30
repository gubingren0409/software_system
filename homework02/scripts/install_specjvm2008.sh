#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly DOWNLOAD_DIR="${PROJECT_DIR}/downloads"
readonly JAVA_PARENT="${HOME}/java"
readonly JAVA_DIR="${JAVA_PARENT}/java-se-8u41-ri"
readonly SPEC_PARENT="${HOME}/benchmarks"
readonly SPEC_DIR="${SPEC_PARENT}/SPECjvm2008"

mkdir -p "${JAVA_PARENT}" "${SPEC_PARENT}"

if [[ ! -x "${JAVA_DIR}/bin/java" ]]; then
  tar -xzf "${DOWNLOAD_DIR}/openjdk-8u41-b04-linux-x64-14_jan_2020.tar.gz" \
    -C "${JAVA_PARENT}"
fi

export JAVA_HOME="${JAVA_DIR}"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

echo "JAVA_HOME=${JAVA_HOME}"
command -v java
java -version
command -v javac
javac -version

if [[ ! -f "${SPEC_DIR}/SPECjvm2008.jar" ]]; then
  java -jar "${DOWNLOAD_DIR}/SPECjvm2008_1_01_setup.jar" -i console
fi

test -f "${SPEC_DIR}/SPECjvm2008.jar"
echo "SPEC_DIR=${SPEC_DIR}"
sha256sum "${DOWNLOAD_DIR}/openjdk-8u41-b04-linux-x64-14_jan_2020.tar.gz"
sha256sum "${DOWNLOAD_DIR}/SPECjvm2008_1_01_setup.jar"
