# memhog — 開発者向け仕様書

最終更新: 2026-07-10

## 技術スタック

- 言語: Python >= 3.11
- CLI: [typer](https://typer.tiangolo.com/) >= 0.15
- 表示: [rich](https://rich.readthedocs.io/) >= 13.9
- 依存管理: Poetry（src layout、in-project `.venv`）
- テスト: pytest / lint: ruff / 型: mypy（`disallow_untyped_defs`）
- 配布: pipx（`memhog = "memhog.cli:app"`）
- CI: GitHub Actions（ruff + mypy + pytest）

外部ランタイム依存なし（標準ライブラリ＋ macOS の外部コマンドのみ）。

## ディレクトリ構成

リポジトリ全体の構成図の正本は**ルート [README.md](../../../README.md)**、`docs/` 配下は
[docs/README.md](../../README.md)。ここでは重複を持たない（同じ事実を2箇所に置くと
静かにドリフトするため。`tests/test_doc_tree.py` が複製を検出する）。

各モジュールの責務と処理の流れは [architecture.md](architecture.md) を参照。

## トピック

| トピック | 概要 |
|---------|------|
| [architecture](architecture.md) | レイヤ構成（I/O・解析・組立・出力の分離）とデータフロー |
| [memory-detection](memory-detection.md) | 物理フットプリント vs RSS・GPU/Metal 常駐の判定式と閾値 |
| [cli](cli.md) | CLI オプション一覧と挙動 |
| [testing](testing.md) | テスト構成・件数・CI・仕様書鮮度チェック |
