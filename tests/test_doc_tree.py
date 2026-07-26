#!/usr/bin/env python3
"""【雛形】構成ツリーが実ファイルと合っているか、双方向で検証する。

コピー後に直すのは NO_TREE_DOCS / EXEMPT / STRICT_DIRS の3つだけ。

正本は2箇所で担当範囲が重ならない（全体＝ルート README / docs 配下＝docs/README.md）。
検証は「実在→ツリー（書き忘れ）」と「ツリー→実在（消したのに残る幽霊）」の両方向。
片方向だと、消したファイルの行が残る嘘を通してしまう。

標準ライブラリのみ。実行: python3 tests/test_doc_tree.py -> 末尾に ALL_PASS
"""
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPO_TREE_DOC = "README.md"
DOCS_TREE_DOC = "docs/README.md"
# ツリーを持ってはいけない文書（2箇所以外への複製を検出する）。
NO_TREE_DOCS = (
    "docs/specification/develop/README.md",
    "docs/specification/README.md",
    "docs/specification/client/README.md",
)
# ツリーに載せない追跡ファイル（lock ファイル等は宣言ファイルと対で自明）。
EXEMPT = {".gitignore", "poetry.lock", "deno.lock", "package-lock.json"}
# 1ファイル1行を要求する層。実装ディレクトリ（src/ 等）は束ね表記を許す
# （全ファイルに1行1対応を強いると表記の自由を奪い、逆に更新されなくなる）。
STRICT_DIRS = ("tests/", "scripts/", ".github/workflows/")


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "-C", REPO, "ls-files"], capture_output=True, text=True
    ).stdout
    return [p for p in out.splitlines() if p]


def read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def tree_text(rel: str) -> str:
    """「## ディレクトリ構成」以降で最初に現れるコードブロックの中身。

    見出しから任意行を挟んでブロックまでを1つの正規表現で書くと破滅的
    バックトラッキングに陥る（実測で終了しなかった）。位置検索で切ってから当てる。
    """
    body = read(rel)
    idx = body.find("## ディレクトリ構成")
    if idx < 0:
        return ""
    m = re.search(r"```[^\n]*\n(.*?)\n```", body[idx:], re.S)
    return m.group(1) if m else ""


def tokens(tree: str) -> list[str]:
    """ツリー各行からパスらしいトークンを拾う（コメント・罫線・束ね表記を除く）。"""
    out = []
    for line in tree.splitlines():
        token = line.split("#")[0].strip().lstrip("│├└─ ").strip()
        if token and token not in (".", "*") and "*" not in token:
            out.append(token)
    return out


files = tracked()


def in_repo(token: str) -> bool:
    """トークンが追跡パスの suffix / セグメントとして実在するか。

    ツリーは階層表記なので絶対パスで存在確認すると全部を幽霊と誤判定する
    （`design-notes/README.md` の実体は `docs/design-notes/README.md`）。
    """
    bare = token.rstrip("/").strip("/")
    if token.endswith("/"):
        return any(f"/{bare}/" in f"/{p}" for p in files)
    return any(p == bare or p.endswith("/" + bare) for p in files)


def listed(tree: str, path: str) -> bool:
    """ツリーに載っているか（README.md は同名が複数あるので親名も要求する）。"""
    name = os.path.basename(path)
    if name != "README.md":
        return name in tree
    parent = os.path.basename(os.path.dirname(path))
    if parent in ("", "docs"):
        return "README.md" in tree
    return parent in tree and "README.md" in tree


repo_tree = tree_text(REPO_TREE_DOC)
docs_tree = tree_text(DOCS_TREE_DOC)

# --- 実在 -> ツリー ---------------------------------------------------------
repo_missing, docs_missing = [], []
for path in files:
    if os.path.basename(path) in EXEMPT:
        continue
    if path.startswith("docs/"):
        if not listed(docs_tree, path):
            docs_missing.append(path)
        continue
    if path.startswith(STRICT_DIRS):
        if not listed(repo_tree, path):
            repo_missing.append(path)
        continue
    top = path.split("/")[0]
    if top not in repo_tree and os.path.basename(path) not in repo_tree:
        repo_missing.append(top)

# --- ツリー -> 実在 ---------------------------------------------------------
repo_ghosts = [t for t in tokens(repo_tree) if not in_repo(t)]
docs_ghosts = [t for t in tokens(docs_tree) if not in_repo(t)]

# --- 2箇所以外への複製 ------------------------------------------------------
extra_trees = []
for rel in NO_TREE_DOCS:
    if not os.path.exists(os.path.join(REPO, rel)):
        continue
    for block in re.findall(r"```[^\n]*\n(.*?)\n```", read(rel), re.S):
        if any(ch in block for ch in ("├──", "└──")):
            extra_trees.append(rel)
            break

checks = [
    ("全体ツリーを抽出できる", bool(repo_tree)),
    ("docs ツリーを抽出できる", bool(docs_tree)),
    (f"[全体] 実ファイルがツリーに載っている"
     f"（漏れ: {sorted(set(repo_missing)) or 'なし'}）", not repo_missing),
    (f"[全体] ツリーの記載が実在する"
     f"（幽霊: {sorted(set(repo_ghosts)) or 'なし'}）", not repo_ghosts),
    (f"[docs] 実ファイルがツリーに載っている"
     f"（漏れ: {sorted(set(docs_missing)) or 'なし'}）", not docs_missing),
    (f"[docs] ツリーの記載が実在する"
     f"（幽霊: {sorted(set(docs_ghosts)) or 'なし'}）", not docs_ghosts),
    ("全体ツリーは docs 配下を展開しない（docs/README.md へ委譲）",
     "specification/" not in repo_tree),
    ("docs ツリーが全体ツリーへリンクしている", "README.md" in docs_tree),
    ("全体ツリーが docs/ 自体は挙げている", "docs/" in repo_tree),
    (f"ツリーは2箇所だけ（複製: {sorted(set(extra_trees)) or 'なし'}）",
     not extra_trees),
]


def failures() -> list[str]:
    """満たされていない検査項目のラベル。"""
    return [label for label, res in checks if not res]


def test_doc_tree() -> None:
    """pytest から収集されたときも同じ検査を行う。

    トップレベルで raise SystemExit すると pytest が INTERNALERROR になり
    既存のテスト実行ごと壊れる（実測）。レポート出力は __main__ 側に置く。
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
