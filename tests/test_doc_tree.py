#!/usr/bin/env python3
"""ディレクトリ構成ツリーが実ファイルと合っているか検証する（標準ライブラリのみ）。

**README を持つディレクトリは、それぞれが自分の直下を描く**。深い階層まで書き下ろすのは
その階層の README の仕事で、上位は1行に畳んでリンクする（例）:

  - ルート `README.md` -> リポジトリ直下（`docs/` は1行に畳む）
  - `docs/README.md` -> `docs/` 直下（`specification/` は1行に畳む）
  - `docs/specification/README.md` -> `specification/` 直下（`client/` `develop/` を畳む）
  - `client/` `develop/` の各 `README.md` -> それぞれの直下

こうすると、同じファイル名がツリーに現れるのは1箇所だけになり（＝二重化しない）、
ファイルを足す/消したときに直すのは**その親 README 1つ**で済む。ツリーを持つ文書は
固定リストではなく「追跡されている README.md すべて」なので、README を新設したら
そこにもツリーが要る（この検査が要求する）。

人手で維持すると静かに古くなる。そこで双方向で検証する。**片方向では不十分** —
追加漏れは検出できても、削除したファイルの行が残る「幽霊」を通す:

  1. 実在 -> ツリー: 直下の追跡エントリがツリーに現れるか（＝足したのに書き忘れた）
  2. ツリー -> 実在: ツリーが挙げるパスがその配下に実在するか（＝消したのに行が残った）
  3. 深さ: 直下より深いものを書いていないか（＝下位の担当を奪って二重化した）

深い階層のファイルは、そこに README があればその README が、無ければ仕様書の該当トピックが
説明する（テスト・スクリプトなら `develop/testing.md` 等）。ツリーに書き写すと同じ説明が
2箇所へ散る。

コピー後に直すのは **EXEMPT** だけ（ツリーに載せない追跡ファイルがあれば足す）。
リポジトリ固有の追加検査は `checks` の末尾に足す。

実行: python3 tests/test_doc_tree.py   -> 末尾に ALL_PASS
"""
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# ツリーに載せない追跡ファイル（自明・構成の理解に寄与しない）。
EXEMPT = {".gitignore", "poetry.lock", "deno.lock", "package-lock.json"}


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", REPO, "ls-files"],
                         capture_output=True, text=True).stdout
    return [p for p in out.splitlines() if p]


files = tracked()
# ツリーを持つべき文書＝追跡されている README.md すべて（README を足したらツリーも要る）。
TREE_DOCS = sorted(p for p in files if os.path.basename(p) == "README.md")


def read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def tree_text(rel: str) -> str:
    """その文書の「## ディレクトリ構成」以降で最初に現れるコードブロックの中身。

    見出しの後に説明文が入ることがあるため、正規表現1発で「見出し〜任意行〜```」を
    書くと破滅的バックトラッキングに陥る（実測: 2分でも終わらなかった）。
    見出しで前半を切り捨ててから最初のブロックを取る2段階にする。
    """
    body = read(rel)
    idx = body.find("## ディレクトリ構成")
    if idx < 0:
        return ""
    m = re.search(r"```[^\n]*\n(.*?)\n```", body[idx:], re.S)
    return m.group(1) if m else ""


def tokens(tree: str) -> list[str]:
    """ツリー各行から「パスらしいトークン」を拾う（コメント・罫線・束ね表記を除く）。

    コメントを落とすので、`# 構成は docs/README.md` のような案内文はトークンにならない
    （委譲の検査が案内文を「中身の書き下ろし」と誤判定しないために重要）。
    """
    out = []
    for line in tree.splitlines():
        token = line.split("#")[0].strip().lstrip("│├└─ ").strip()
        if token and token not in (".", "*") and "*" not in token:
            out.append(token)
    return out


def segments(tree: str) -> set[str]:
    """ツリー中のトークンを `/` で分解したセグメント集合。

    素の部分文字列一致で見ると、消した行を別の行が肩代わりして素通りする。
    実例（agent-office）: `deploy.ts` の行をツリーから消しても、同じディレクトリの
    `auto-deploy.ts` が "deploy.ts" を含むため検査が通ってしまった。セグメント単位の
    **完全一致**で判定する（`client/README.md` のような簡潔表記も拾える）。
    """
    return {seg for t in tokens(tree) for seg in t.rstrip("/").split("/") if seg}


def direct_entries(scope: str) -> tuple[set[str], set[str]]:
    """scope 直下の (ファイル名, サブディレクトリ名)。scope="" はリポジトリ直下。"""
    prefix = scope + "/" if scope else ""
    names, dirs = set(), set()
    for path in files:
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix):]
        if "/" in rest:
            dirs.add(rest.split("/")[0])
        elif rest not in EXEMPT:
            names.add(rest)
    return names, dirs


def in_scope(scope: str, token: str) -> bool:
    """トークンが scope 配下に実在するか（末尾一致。絶対パス化すると全部幽霊になる）。"""
    prefix = scope + "/" if scope else ""
    cands = [p for p in files if p.startswith(prefix)]
    bare = token.rstrip("/").strip("/")
    if token.endswith("/"):  # ディレクトリ: パスのセグメントとして現れるか
        return any(f"/{bare}/" in f"/{p}" for p in cands)
    return any(p == bare or p.endswith("/" + bare) for p in cands)


def deep_segments(scope: str) -> set[str]:
    """scope の**直下より深い**パスセグメント（そのツリーが書いてはいけないもの）。

    ツリーは自分の直下だけを描く。深い階層は、そこに置かれた README が描くか、
    仕様書の該当トピックが説明する。上位に書き下ろすと、同じ説明が2箇所に散る。
    """
    prefix = scope + "/" if scope else ""
    out = set()
    for path in files:
        if not path.startswith(prefix):
            continue
        parts = path[len(prefix):].split("/")
        out.update(parts[1:])
    return out


def preamble(rel: str) -> str:
    """「## ディレクトリ構成」見出しとコードブロックの間に挟まった散文。

    ここに「ここは client/ 直下を描く」のような**書き手向けのメタ説明**を貼ると、
    読者には何の情報も無い前置きが全 README に並ぶ（2026-07-27 の指摘）。ツリーの
    維持規約は `.claude/rules/specification-update.md` の担当で、文書に書くものではない。
    """
    body = read(rel)
    idx = body.find("## ディレクトリ構成")
    if idx < 0:
        return ""
    seg = body[idx:]
    m = re.search(r"```", seg)
    return seg[len("## ディレクトリ構成"):m.start()].strip() if m else ""


missing, ghosts, undelegated, no_tree = [], [], [], []
# ツリーの前置きはルート README のみ許す（`→` が何かは読者に要る情報）。
preambles = [d for d in TREE_DOCS if d != "README.md" and preamble(d)]

for doc in TREE_DOCS:
    scope = os.path.dirname(doc)
    tree = tree_text(doc)
    if not tree:
        no_tree.append(doc)
        continue
    segs = segments(tree)
    names, dirs = direct_entries(scope)

    # 1. 実在 -> ツリー（直下のファイル・サブディレクトリが載っているか）
    for name in names:
        if name not in segs:
            missing.append(f"{doc}: {name}")
    for sub in dirs:
        if sub not in segs:
            missing.append(f"{doc}: {sub}/")

    # 2. ツリー -> 実在
    ghosts += [f"{doc}: {t}" for t in tokens(tree) if not in_scope(scope, t)]

    # 3. 深さ（直下より深いものを書いていないか）
    for name in sorted((deep_segments(scope) - names - dirs) & segs):
        undelegated.append(f"{doc}: {name}")

checks = [
    (f"README を持つ全ディレクトリにツリーがある（欠落: {sorted(no_tree) or 'なし'}）",
     not no_tree),
    (f"直下の実エントリがツリーに載っている（漏れ: {sorted(set(missing)) or 'なし'}）",
     not missing),
    (f"ツリーの記載が実在する（幽霊: {sorted(set(ghosts)) or 'なし'}）", not ghosts),
    (f"ツリーに書き手向けの前置きを付けていない（前置き: {sorted(preambles) or 'なし'}）",
     not preambles),
    (f"各ツリーが自分の直下だけを描いている（深すぎ: {sorted(set(undelegated)) or 'なし'}）",
     not undelegated),
    # リポジトリ固有の追加検査（ツリーに載せたい別情報がある場合）はここに足す。
    # 例: symlink を張るリポジトリなら「ルートのツリーが symlink 先を併記しているか」。
]


def failures() -> list[str]:
    """満たされていない検査項目のラベル。"""
    return [label for label, res in checks if not res]


def test_doc_tree() -> None:
    """pytest から収集されたときも同じ検査を行う。

    pytest は tests/test_*.py を import するため、トップレベルで `raise SystemExit` すると
    INTERNALERROR になり**既存の pytest 実行ごと壊す**（実測）。検査は import 時に済んでいるので、
    ここでは結果だけを assert し、レポート出力は __main__ ガードの中に置く。
    """
    assert not failures(), "\n".join(failures())


if __name__ == "__main__":
    ok = True
    for label, res in checks:
        print(("PASS " if res else "FAIL ") + label)
        ok = ok and bool(res)
    print()
    print("ALL_PASS" if ok else "HAS_FAILURE")
    raise SystemExit(0 if ok else 1)
