#!/usr/bin/env bash
# One fail-closed quality entry point.  It reports the exact checked scope and
# never turns a non-zero child command into a green verdict.
set -u -o pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRE_CLEAN=0
SOURCE_SET=""

usage() {
  cat <<'EOF'
用法：tools/gate.sh [--require-clean] [--source-set PATH]

默认检查（HTML-only v1 分层）：
  ruff                       src tests tools
  mypy                       src tools（strict；仅允许代码行上的精确豁免）
  v1-fast-tests              tests/unit tests/contract 活跃层
  retained-compat-smoke      tests/unit+tests/contract 内保留轨文件的兼容性 smoke；
                             不是全量保留轨（18 个声明文件大多位于 tests/pdf、
                             tests/html_ppt 等产品轨），不算 v1 release gate；
                             全量口径见分层合同 RETAINED_FILES
  v1-layer-audit             分层合同
  legacy                     tools/check_no_legacy_refs.py

--require-clean 另外要求 Git 工作树无 staged/unstaged/untracked 改动；不代表可发布。
--source-set    另外比对一个历史脏树基线 JSON；仅用于诊断漂移。
EOF
}

while (($# > 0)); do
  case "$1" in
    --require-clean)
      REQUIRE_CLEAN=1
      shift
      ;;
    --source-set)
      if (($# < 2)); then
        echo "GATE_USAGE_ERROR --source-set 需要路径" >&2
        exit 2
      fi
      SOURCE_SET="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "GATE_USAGE_ERROR 未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ((REQUIRE_CLEAN)) && [[ -n "$SOURCE_SET" ]]; then
  echo "GATE_USAGE_ERROR 历史脏树基线不能与 --require-clean 组合为发布证明" >&2
  exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "GATE_ENV_ERROR 缺少 uv；无法执行锁定开发环境检查" >&2
  exit 2
fi

failures=0
steps=0
run_step() {
  local name="$1"
  shift
  steps=$((steps + 1))
  printf 'GATE_STEP name=%s command=' "$name"
  printf '%q ' "$@"
  printf '\n'
  "$@"
  local code=$?
  if ((code != 0)); then
    printf 'GATE_STEP_FAIL name=%s exit=%d\n' "$name" "$code" >&2
    failures=$((failures + 1))
  else
    printf 'GATE_STEP_OK name=%s\n' "$name"
  fi
}

cd "$ROOT" || {
  echo "GATE_ENV_ERROR 无法进入仓库根目录：$ROOT" >&2
  exit 2
}

printf 'GATE_SCOPE root=%s ruff=src,tests,tools mypy=src,tools,strict,no-global-ignore v1_active_tests=tests/unit,tests/contract,-m+"not+retained_legacy_format" retained_compat_smoke=tests/unit,tests/contract,-m+"retained_legacy_format" retained_compat_smoke_semantics=bounded-compat-subset,full-retained-track-not-run-here v1_layer_audit=test_v1_test_layering legacy=check_no_legacy_refs release_semantics=retained-steps-are-not-v1-release-gate' "$ROOT"
if ((REQUIRE_CLEAN)); then
  printf ' clean=required'
else
  printf ' clean=not-required'
fi
if [[ -n "$SOURCE_SET" ]]; then
  printf ' source_set=%s' "$SOURCE_SET"
fi
printf '\n'

run_step ruff uv run ruff check src tests tools
run_step mypy uv run python -m mypy --no-incremental --strict src tools --show-error-codes
run_step v1-fast-tests uv run python -m pytest tests/unit tests/contract -q -m "not retained_legacy_format"
run_step retained-compat-smoke uv run python -m pytest tests/unit tests/contract -q -m "retained_legacy_format"
run_step v1-layer-audit uv run python -m pytest tests/contract/test_v1_test_layering.py -q
run_step legacy-references uv run python tools/check_no_legacy_refs.py

if ((REQUIRE_CLEAN)); then
  run_step clean-tree uv run python tools/check_clean_tree.py --root "$ROOT"
fi
if [[ -n "$SOURCE_SET" ]]; then
  source_args=(uv run python tools/verify_rebaseline_source_set.py "$SOURCE_SET" --root "$ROOT")
  run_step source-set "${source_args[@]}"
fi

if ((failures)); then
  printf 'GATE_FAIL steps=%d failures=%d clean_required=%d\n' "$steps" "$failures" "$REQUIRE_CLEAN" >&2
  exit 1
fi
if ((REQUIRE_CLEAN)); then
  echo "GATE_OK status=clean-quality-only steps=$steps"
else
  echo "GATE_OK status=quality-only steps=$steps"
fi
exit 0
