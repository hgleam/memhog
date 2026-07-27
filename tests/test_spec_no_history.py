#!/usr/bin/env python3
"""仕様書に「変更履歴」が混ざっていないか検証する（標準ライブラリのみ）。

仕様書（`docs/specification/**`）は**いま何がどうなっているか**だけを書く。
「2026-07-26 変更: 旧→新」「（2026-07-13 追加）」「旧実装は…だった」といった**過程**は
`docs/devlog.md` の担当で、仕様書に置くと次の3つが起きる:

  1. 読み手が「今どっちなのか」を判断するために履歴を読まされる（見出しにまで混ざると特に読みにくい）
  2. 同じ経緯が devlog と仕様書の2箇所に散る（片方だけ直ると矛盾する）
  3. 古い決定が消えないまま積もり、仕様書が更新履歴のログになる

検査（`docs/specification/**/*.md` が対象。devlog と design-notes は過程を書く場所なので対象外。
コードブロックとインラインコードは対象外＝データ例やファイル名の日付は履歴と見なさない）:

  1. 日付（YYYY-MM-DD）がある            -> FAIL（更新日も書かない。git log が正本）
  2. 履歴語（旧実装 / 従来 / 以前は …）  -> FAIL

「なぜこの設計なのか」の**理由**は仕様書に残してよい（現在形で書く）。禁止するのは
「いつ何から何へ変えたか」という**時系列**。理由を残しつつ経緯を落とす書き換え例:

  NG: 旧実装は blocked > working > idle だったため、対応待ちを取りこぼしていた（2026-07-26 変更）
  OK: 「状態の深刻さ」ではなく「ユーザーの番かどうか」で並べる（対応待ちを取りこぼさないため）

実行: python3 tests/test_spec_no_history.py   -> 末尾に ALL_PASS
"""
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SPEC_DIR = "docs/specification/"

DATE = re.compile(r"20\d\d-[01]\d-[0-3]\d")
# 履歴を表す語。仕様書の現在形の記述では使わない。
# 「以前は」は「それ以前は」（時刻表示の説明など）と紛れるので、直前の指示語を除外する。
HISTORY_WORDS = ("旧実装", "従来は", r"(?<![それこ])以前は", "当初は", "旧仕様", "変更前は", "だった経緯")
# 例外は理由付きで登録する（`docs/...md`: 理由）。
ALLOW: dict[str, str] = {}


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", REPO, "ls-files", SPEC_DIR],
                         capture_output=True, text=True).stdout
    return [p for p in out.splitlines() if p.endswith(".md")]


def read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


# コードブロックとインラインコードは検査対象外。データ例やファイル名の日付
# （`<time datetime="2025-12-10...">`・`docs/research/2026-04-25_.../`）まで履歴と判定すると、
# 回避のための ALLOW 登録が増えて検査が形骸化する。
INLINE = re.compile(r"`[^`]*`")

dates, words = [], []
docs = tracked()

for doc in docs:
    if doc in ALLOW:
        continue
    incode = False
    for num, line in enumerate(read(doc).splitlines(), 1):
        if line.lstrip().startswith("```"):
            incode = not incode
            continue
        if incode:
            continue
        bare = INLINE.sub("", line)
        if DATE.search(bare):
            dates.append(f"{doc}:{num}")
        for word in HISTORY_WORDS:
            if re.search(word, bare):
                words.append(f"{doc}:{num} ({word})")

checks = [
    ("仕様書を発見できている（0件ならパターンが空振り）", bool(docs)),
    (f"仕様書の本文に日付が無い（{sorted(dates) or 'なし'}）", not dates),
    (f"仕様書に履歴語が無い（{sorted(words) or 'なし'}）", not words),
]


def failures() -> list[str]:
    """満たされていない検査項目のラベル。"""
    return [label for label, res in checks if not res]


def test_spec_no_history() -> None:
    """pytest から収集されたときも同じ検査を行う（SystemExit は __main__ ガードの中だけ）。"""
    assert not failures(), "\n".join(failures())


if __name__ == "__main__":
    ok = True
    for label, res in checks:
        print(("PASS " if res else "FAIL ") + label)
        ok = ok and bool(res)
    print()
    print("ALL_PASS" if ok else "HAS_FAILURE")
    raise SystemExit(0 if ok else 1)
