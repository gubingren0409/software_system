#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <homework02-directory>" >&2
  exit 2
fi

repo_root="$(cd "$1" && pwd)"
java7="/home/gubingren/java/java-se-7u75-ri/bin/java"
output_dir="$repo_root/logs/jvm_parameter/flags"
mkdir -p "$output_dir"

if [[ ! -x "$java7" ]]; then
  echo "Java 7 RI not found: $java7" >&2
  exit 3
fi

configs=(default xmx512m xmx1024m xmx2560m)
args=("" -Xmx512m -Xmx1024m -Xmx2560m)

for index in "${!configs[@]}"; do
  config="${configs[$index]}"
  heap_arg="${args[$index]}"
  output="$output_dir/${config}.flags.log"
  {
    echo "collected_at=$(date --iso-8601=seconds)"
    echo "heap_config=$config"
    echo "java_path=$java7"
    echo "xmx_argument=$heap_arg"
    echo "command=$java7 ${heap_arg:+$heap_arg }-XX:+PrintFlagsFinal -version"
    if [[ -n "$heap_arg" ]]; then
      "$java7" "$heap_arg" -XX:+PrintFlagsFinal -version
    else
      "$java7" -XX:+PrintFlagsFinal -version
    fi
  } >"$output" 2>&1
done

echo "PASS: four Java 7 JVM flag snapshots captured"
