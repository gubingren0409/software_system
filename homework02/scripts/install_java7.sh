#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/mnt/e/software_system/A2/homework02"
readonly ARCHIVE="${PROJECT_DIR}/downloads/openjdk-7u75-b13-linux-x64-18_dec_2014.tar.gz"
readonly JAVA_PARENT="${HOME}/java"
readonly JAVA_DIR="${JAVA_PARENT}/java-se-7u75-ri"

mkdir -p "${JAVA_PARENT}"
if [[ ! -x "${JAVA_DIR}/bin/java" ]]; then
  tar -xzf "${ARCHIVE}" -C "${JAVA_PARENT}"
fi

export JAVA_HOME="${JAVA_DIR}"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

echo "JAVA_HOME=${JAVA_HOME}"
command -v java
java -version
command -v javac
javac -version
sha256sum "${ARCHIVE}"
