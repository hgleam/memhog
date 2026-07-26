#!/usr/bin/env python3
"""【雛形】文書間の「散文の再掲」を検出する（同じ説明を2箇所に書かせない）。

コピー後に直すのは MIN_LEN / SKIP_DOCS / ALLOW の3つだけ。

文意の類似判定には踏み込まず、十分に長い同一行の丸写しだけを見る。
誤検知で無効化されるより、確実な丸写しを確実に止める方が機能する。

「0 件なら PASS」型なので、導入時とフィルタ変更時は1回壊して FAIL を見ること:

    L=$(grep -m1 -E '.{40,}' README.md | sed 's/^ *//')
    printf '\n%s\n' "$L" >> docs/README.md
    python3 tests/test_doc_dedup.py     # -> FAIL
    git checkout -- docs/README.md

標準ライブラリのみ。実行: python3 tests/test_doc_dedup.py -> 末尾に ALL_PASS
"""
import glob
import os
import re
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MIN_LEN = 40  # これ未満は偶然一致しうるので見ない
SKIP_DOCS = {"docs/devlog.md"}

# 意図的に複数文書へ置く文（理由を必ず書く。無条件に通す抜け穴にしない）。
ALLOW: dict[str, str] = {}


def target_docs() -> list[str]:
    out = []
    for pattern in ("README.md", "docs/**/*.md"):
        for path in glob.glob(os.path.join(REPO, pattern), recursive=True):
            rel = os.path.relpath(path, REPO)
            if rel not in SKIP_DOCS:
                out.append(rel)
    return sorted(set(out))


def prose_lines(rel: str) -> set[str]:
    """コードブロックを除いた本文から比較対象の行を集める。

    コマンド例・ツリーは同一で構わない（別テストが担当）ので落とす。
    見出し・表の区切り・リンクだけの行も比較しない。
    """
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        body = fh.read()
    body = re.sub(r"```[^\n]*\n.*?\n```", "", body, flags=re.S)
    out = set()
    for raw in body.splitlines():
        line = raw.strip()
        if len(line) < MIN_LEN or line.startswith("#"):
            continue
        if set(line) <= set("|-: "):
            continue
        if re.fullmatch(r"[-*>|\s]*\[[^\]]+\]\([^)]+\)[.,、。\s]*", line):
            continue
        # 出典・参考リンクの行は複数の文書から同じ資料を引くのが正当なので比較しない
        if "http" in line:
            continue
        out.add(line)
    return out


docs = {rel: prose_lines(rel) for rel in target_docs()}

owners: dict[str, list[str]] = defaultdict(list)
for rel, lines in docs.items():
    for line in lines:
        owners[line].append(rel)

dupes = {line: sorted(where) for line, where in owners.items()
         if len(where) > 1 and line not in ALLOW}

report = [f"{'  /  '.join(where)}: {line[:50]}…"
          for line, where in sorted(dupes.items())]

checks = [
    ("比較対象の文書を発見できている", len(docs) >= 1),
    (f"文書間に同一文の再掲が無い（{len(dupes)} 件）", not dupes),
]


def failures() -> list[str]:
    """満たされていない検査項目のラベル。"""
    return [label for label, res in checks if not res]


def test_doc_dedup() -> None:
    """pytest から収集されたときも同じ検査を行う。

    トップレベルで raise SystemExit すると pytest が INTERNALERROR になり
    既存のテスト実行ごと壊れる（実測）。レポート出力は __main__ 側に置く。
    """
    assert not failures(), "\n".join(failures())


if __name__ == "__main__":
    if report:
        print("再掲の疑い:")
        for line in report:
            print("  " + line)
        print()
    ok = True
    for label, res in checks:
        print(("PASS " if res else "FAIL ") + label)
        ok = ok and bool(res)
    print()
    print("ALL_PASS" if ok else "HAS_FAILURE")
    raise SystemExit(0 if ok else 1)
