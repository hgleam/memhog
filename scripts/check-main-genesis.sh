#!/usr/bin/env bash
# main genesis 監査（CI/ローカル用・自己完結）:
# 履歴のルートが「1個・scaffold（README ＋任意で .gitignore）のみ」かを検証する。
# 太い初回コミット（ソース混入）や unrelated histories（複数ルート）を検出し、
# 非準拠なら exit 1。
#
# .gitignore / LICENSE を許容する理由: 多くのリポジトリの初回コミットは「README +
# .gitignore」や「README + LICENSE」（gh repo create --license 等）で、いずれも無害な
# scaffold（＝「太い初回コミット」ではない）。README のみに絞ると一般的な genesis を弾いて
# CI を即赤にする（main の履歴書き換えは禁止のため直せない）。
# 監査の本来の目的＝ソースコード混入・複数ルートの検出はそのまま維持する。
#
# 使い方: check-main-genesis.sh [ref]   # 既定 ref=HEAD
# CI では PR ブランチ HEAD を検査（全ブランチは scaffold-only genesis に連なるべき）。
set -uo pipefail

# ⚠ **自己完結を保つ**（各リポジトリへコピーして使うため、外部ライブラリを source しない）。
# ヘルプ整形を持つリポジトリへ入れるときは、コピー側でその作法に合わせる
# （例: tube-funnel は scripts/lib/help.sh の help_render に載せ替えている）。
case "${1:-}" in
  -h | --help)
    cat << 'USAGE'
check-main-genesis.sh — 履歴のルートが scaffold 1個かを検査する

使い方:
  bash scripts/check-main-genesis.sh [ref]      # 既定 ref=HEAD

引数:
  ref    検査する ref（既定 HEAD）

終了コード:
  0  準拠（scaffold のみの単一ルート）
  1  違反（ルートが複数／ルートが太い＝ソース混入）
  2  ルートを取得できない（checkout が浅い等）

備考:
  - CI から呼ぶときは checkout に fetch-depth: 0 が要る（浅いとルートまで辿れない）
  - main に載せてよいのは初回 scaffold だけ・中身は PR 経由、を履歴の形から見る
  - 落ちても直し方はコードの修正ではない。ルートの付け替え（git replace --graft →
    git filter-repo）が要り、全 SHA が変わる
USAGE
    exit 0
    ;;
esac

REF="${1:-HEAD}"
roots=$(git rev-list --max-parents=0 "$REF" 2>/dev/null || true)
[ -z "$roots" ] && { echo "ERROR: ルートの commit が取得できません（fetch-depth: 0 か確認）" >&2; exit 2; }

count=$(printf '%s\n' "$roots" | grep -c .)
fail=0

if [ "$count" -ne 1 ]; then
  echo "❌ ルートが ${count} 個あります（1個であるべき＝unrelated histories 混入）:"
  printf '%s\n' "$roots" | while read -r r; do [ -n "$r" ] && echo "   - $(git log -1 --oneline "$r")"; done
  fail=1
fi

for r in $roots; do
  [ -z "$r" ] && continue
  nonscaffold=$(git show --name-only --pretty=format: "$r" | grep -v '^$' | grep -viE '^(readme(\.md)?|\.gitignore|license(\.md|\.txt)?)$' || true)
  if [ -n "$nonscaffold" ]; then
    echo "❌ ルート $(git rev-parse --short "$r") が scaffold（README/.gitignore/LICENSE）以外を含む（＝太い初回コミット）:"
    printf '%s\n' "$nonscaffold" | sed 's/^/     /'
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "✅ genesis OK: scaffold-only（README[+.gitignore/LICENSE]）の単一ルート（$(git rev-parse --short "$(printf '%s' "$roots" | head -1)")）"
  exit 0
fi
echo "=> 違反あり: main は初回 scaffold（README[+.gitignore/LICENSE]）のみ・内容はPR経由（git ルール）。PRベースで是正してください。"
exit 1
