#!/bin/sh
# Way of Vanilla: refuse to start a model server unless every GPU has its power cap set.
# Two cards on one splitter cable must not draw the stock 151 W each.
# Usage: gpu-power-check.sh [expected_gpu_count] [max_watts]
EXPECT=${1:-1}
MAXW=${2:-100}
OUT=$(/usr/bin/nvidia-smi --query-gpu=index,power.limit --format=csv,noheader,nounits 2>/dev/null) || {
  echo "gpu-power-check: nvidia-smi failed" >&2; exit 1; }
N=$(printf '%s\n' "$OUT" | grep -c .)
if [ "$N" -lt "$EXPECT" ]; then
  echo "gpu-power-check: found $N GPU(s), expected $EXPECT" >&2; exit 1
fi
BAD=$(printf '%s\n' "$OUT" | awk -F', *' -v m="$MAXW" '$2+0 > m {print "GPU " $1 " limit " $2 " W"}')
if [ -n "$BAD" ]; then
  echo "gpu-power-check: power cap not set ($BAD > $MAXW W). Run: sudo systemctl start wov-gpu-power" >&2
  exit 1
fi
echo "gpu-power-check: $N GPU(s) capped at <= $MAXW W"
