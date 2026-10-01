#!/usr/bin/env bash
set -euo pipefail

readonly JAVA7='/home/gubingren/java/java-se-7u75-ri'
readonly SPEC_JAR='/home/gubingren/benchmarks/SPECjvm2008/SPECjvm2008.jar'
export JAVA_HOME="$JAVA7"
export PATH="${JAVA_HOME}/bin:${PATH}"
export CLASSPATH=''

echo '# Optional experiment environment collection'
echo "COLLECTED_AT=$(date --iso-8601=seconds)"
echo
echo '# uname -a'
uname -a
echo
echo '# /etc/os-release'
cat /etc/os-release
echo
echo '# CPU summary'
lscpu | grep -E '^(Architecture|CPU\(s\)|On-line CPU|Model name|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|L1d cache|L1i cache|L2 cache|L3 cache):'
echo
echo '# Memory before/after the sequential experiment (collection-time snapshot)'
free -h
echo
echo '# Java and javac'
java -version 2>&1
javac -version 2>&1
echo
echo '# Environment variables'
echo "JAVA_HOME=$JAVA_HOME"
echo "PATH=$PATH"
echo "CLASSPATH=$CLASSPATH"
echo
echo '# JVM selected collector/heap flags (no benchmark)'
java -XX:+PrintFlagsFinal -version 2>&1 | grep -E 'UseParallelGC|UseParallelOldGC|UseAdaptiveSizePolicy|InitialHeapSize|MaxHeapSize'
echo
echo '# SPEC kit SHA-256'
sha256sum "$SPEC_JAR"
