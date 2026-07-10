#!/usr/bin/env bash
set -euo pipefail

# === 監視対象パターン（/init が自動生成。手動追加も可） ===
WATCH_PATTERNS=(
  "src/memhog/*"
  "scripts/*.sh"
  ".github/workflows/*"
)

STAGED=$(git diff --cached --name-only --diff-filter=ACMR)

HAS_SRC=false
HAS_SPEC=false

while IFS= read -r file; do
  [ -z "$file" ] && continue
  for pattern in "${WATCH_PATTERNS[@]}"; do
    # shellcheck disable=SC2254
    case "$file" in
      $pattern) HAS_SRC=true ;;
    esac
  done
  case "$file" in
    docs/specification/*) HAS_SPEC=true ;;
  esac
done <<< "$STAGED"

if [ "$HAS_SRC" = true ] && [ "$HAS_SPEC" = false ]; then
  if [ ! -f "docs/specification/client/README.md" ] || [ ! -f "docs/specification/develop/README.md" ]; then
    echo ""
    echo "⚠  docs/specification/ が存在しません（client/README.md・develop/README.md）。"
    echo "   仕様書を作成してからコミットしてください（specification スキル参照）。"
    echo ""
    exit 1
  fi

  echo ""
  echo "⚠  コードに変更がありますが docs/specification/ が更新されていません。"
  echo "   仕様変更でなければ --no-verify でスキップ可能です。"
  echo ""
  exit 1
fi
