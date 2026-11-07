#!/usr/bin/env sh
# sh examples/download.sh [JSON_URL] [OUTPUT_PATH]
set -eu
url="${1:-https://baditaflorin.github.io/arad-complaints-data/data/records.json}"
output="${2:-records.json}"
curl --fail --location --retry 2 --connect-timeout 10 --max-time 90 \
  --header 'Accept: application/json' --output "$output" "$url"
printf 'Saved JSON to %s\n' "$output"
