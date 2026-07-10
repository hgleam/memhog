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

```
src/memhog/
├── __init__.py    # __version__
├── cli.py         # typer エントリポイント・--kill/--watch の制御
├── collect.py     # 外部コマンド(top/ps/sysctl/memory_pressure)を叩く I/O 層
├── parse.py       # top/memory_pressure のテキスト解析（純粋関数）
├── models.py      # ドメインモデル（Process / SystemMemory・hidden_gpu 判定）
├── report.py      # collect × parse を組み合わせ一覧・システム状況を構築
└── render.py      # 表 / JSON 出力
tests/             # test_models / test_parse / test_report
scripts/           # automerge.sh / check-spec-freshness.sh
.github/workflows/ # ci.yml
```

## トピック

| トピック | 概要 |
|---------|------|
| [architecture](architecture.md) | レイヤ構成（I/O・解析・組立・出力の分離）とデータフロー |
| [memory-detection](memory-detection.md) | 物理フットプリント vs RSS・GPU/Metal 常駐の判定式と閾値 |
| [cli](cli.md) | CLI オプション一覧と挙動 |
| [testing](testing.md) | テスト構成・件数・CI・仕様書鮮度チェック |
