#!/usr/bin/env bash
set -euo pipefail

export JAVA_HOME="${HOME}/java/java-se-7u75-ri"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=""

echo "# Collection time"
date --iso-8601=seconds
echo
echo "# uname -a"
uname -a
echo
echo "# lsb_release -a"
lsb_release -a 2>&1
echo
echo "# /etc/os-release"
cat /etc/os-release
echo
echo "# CPU"
lscpu
echo
echo "# Memory"
free -h
echo
echo "# Java"
java -version 2>&1
javac -version 2>&1
echo "Selected Java 7 because SPEC's official FAQ and Known Issues state that the compiler workloads do not run on Java SE 8 or later."
echo
echo "# Environment variables used for the benchmark"
printf 'JAVA_HOME=%s\n' "${JAVA_HOME}"
printf 'PATH=%s\n' "${PATH}"
printf 'CLASSPATH=%s\n' "${CLASSPATH}"
echo
echo "# Java executable resolution"
command -v java
readlink -f "$(command -v java)"
command -v javac
readlink -f "$(command -v javac)"
echo
echo "# Storage"
df -hT "${HOME}" /mnt/e/software_system/A2/homework02
echo
echo "# Repository state"
if git -C /mnt/e/software_system rev-parse --show-toplevel 2>&1; then
  git -C /mnt/e/software_system status --short --branch
  git -C /mnt/e/software_system branch --all --no-color
else
  echo "No Git repository found at /mnt/e/software_system or its parents."
  echo "Therefore branch homework02 cannot be verified in the current workspace."
fi
