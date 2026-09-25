#!/usr/bin/env bash
set -euo pipefail
# Local build wrapper: reads unified.json via env filters
# Usage: APP_NAME=youtube SOURCE=morphe ARCH=arm64-v8a MODE=apk ./build.sh
mkdir -p build temp build_records
python -m src
