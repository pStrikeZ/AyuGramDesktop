#!/bin/bash
set -e

cd Telegram
eval "$(python3 build/build_target.py linux-environment "$@")"
./configure.sh "$@"
cmake --build "../out/$BUILD_KEY" --config "${CONFIG:-Release}"
