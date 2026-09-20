#!/bin/bash
REPO="/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow"
cd "$REPO"

echo "=== Tester 1: IgAN (grok build/grok-4.6 high) ==="
omp -p "@packets/2026-09-20-test-round-2/tester-v2-igan.md" \
  --provider cursor --model cursor-grok-4.6 --thinking high --no-session \
  2>&1 | tail -6

echo "=== Tester 2: UC (cursor/default auto) ==="
omp -p "@packets/2026-09-20-test-round-2/tester-v2-uc.md" \
  --provider cursor --model default --no-session \
  2>&1 | tail -6

echo "=== ROUND2_V2_DONE ==="
