#!/bin/bash
# 独立测试第一轮派发脚本
REPO="/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow"
cd "$REPO"

echo "=== Tester 1: PNH (deepseek) ==="
omp -p "@packets/2026-09-20-test-round-1/tester-prompt-pnh.md" \
  --provider cms-router --model deepseek-flash --thinking max --no-session \
  2>&1 | tail -3

echo "=== Tester 2: AD (gemini) ==="
omp -p "@packets/2026-09-20-test-round-1/tester-prompt-ad.md" \
  --provider google-antigravity --model gemini-3.8-flash --thinking high --no-session \
  2>&1 | tail -3

echo "=== TEST_ROUND_1_DONE ==="
