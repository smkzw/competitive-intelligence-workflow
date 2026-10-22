#!/usr/bin/env bash
# 复制 ECharts（不入库）。优先从旧仓库同版本文件复制，否则从 npm CDN 下载固定版本。
set -euo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/src/ciw2/render/static/echarts.min.js"
OLD="$(cd "$(dirname "$0")/../.." && pwd)/src/ci_workflow/renderers/portal/assets/echarts.min.js"
if [[ -f "$OLD" ]]; then cp "$OLD" "$DEST"; echo "copied from v1: $OLD";
else curl -fsSL "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js" -o "$DEST"; echo "downloaded echarts 5.5.1"; fi
