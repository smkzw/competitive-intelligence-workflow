#!/usr/bin/env bash
# ECharts Apache-2.0；固定已验字节，不混用不同本机/下载版本。
set -euo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/src/ciw2/render/static/echarts.min.js"
OLD="$(cd "$(dirname "$0")/../.." && pwd)/src/ci_workflow/renderers/portal/assets/echarts.min.js"
EXPECTED="b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0"
matches() { [[ "$(shasum -a 256 "$1" | cut -d ' ' -f 1)" == "$EXPECTED" ]]; }
if [[ -f "$DEST" ]]; then
  matches "$DEST" || { echo "Existing ECharts differs from pinned 6.1.0; preserved for inspection." >&2; exit 1; }
  echo "verified ECharts 6.1.0 $EXPECTED"
  exit 0
fi
TEMP_ASSET="$(mktemp "${DEST}.XXXXXX")"
trap 'rm -f "$TEMP_ASSET"' EXIT
if [[ -f "$OLD" ]] && matches "$OLD"; then
  cp "$OLD" "$TEMP_ASSET"
else
  curl --connect-timeout 15 --max-time 60 -fsSL "https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js" -o "$TEMP_ASSET"
fi
matches "$TEMP_ASSET" || { echo "ECharts checksum mismatch; not installed." >&2; exit 1; }
mv "$TEMP_ASSET" "$DEST"
echo "installed ECharts 6.1.0 $EXPECTED"
