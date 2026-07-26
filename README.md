# memhog

macOS の**実メモリ(物理フットプリント)を最も食っているプロセスを特定して提示する**診断 CLI。

## なぜ必要か

`ps aux` の RSS は **Metal/MPS（Apple Silicon の GPU 共有＝ユニファイドメモリ）を数えない**。
そのため ComfyUI 等の ML 系 Python は RSS 上「数十 MB」に見えるのに、実際は数十 GB を常駐している。
Activity モニタが示す本当の値＝`top` の MEM 列（物理フットプリント）。

memhog はこの物理フットプリントでランク付けし、`ps` の RSS との乖離が大きいプロセスに
**`⚠ GPU/Metal常駐(psに出ない)`** 印を付けて「小さく見えるのに実は巨大」を炙り出す。

詳しい仕様は [`docs/specification/`](docs/specification/README.md)（[依頼者向け](docs/specification/client/README.md) / [開発者向け](docs/specification/develop/README.md)）を参照。

```
== システムメモリ ==
  PhysMem: 63G used (7613M wired, 32G compressor), 217M unused.
  Swap: total = 32768.00M  used = 31855.94M  free = 912.06M
  空き: 37%

  実メモリ上位 (物理フットプリント = Activity モニタ「メモリ」相当)
    #    MEM   psRSS  %CPU    PID  COMMAND
    1  32.0G     26M   0.0  28632  .../Python main.py --port 8188  ⚠ GPU/Metal常駐(psに出ない)
    2   7.9G    2.6G   0.0  69624  com.apple.Virtualization.VirtualMachine
    3   6.6G     12M   0.0  29473  llama-server ...              ⚠ GPU/Metal常駐(psに出ない)
```

## 使い方

```bash
memhog                 # 実メモリ上位15件
memhog -n 30           # 上位30件
memhog -g python       # フルコマンドに "python" を含むものだけ
memhog --json          # 機械可読 JSON（他スクリプト/通知連携/定期実行向け）
memhog --watch 2       # 2秒ごとに更新し続ける監視モード（Ctrl-C で終了）
memhog --kill          # 一覧から PID を選んで停止（既定で確認、不可逆操作）
memhog --kill --force  # SIGKILL で停止
```

## セットアップ

### 開発（Poetry）

```bash
cd memhog
python -m venv .venv          # .venv を先に作る（pyenv グローバル汚染を防ぐ）
poetry install
git config core.hooksPath .githooks   # pre-commit フック（仕様書鮮度チェック）を有効化
poetry run pytest             # テスト
poetry run ruff check .       # lint
poetry run mypy src           # 型チェック
poetry run memhog             # 実行
```

> `core.hooksPath` はローカル git 設定でコミットされない。**クローンごとに上記 `git config core.hooksPath .githooks` を一度実行**すること（`src/memhog/` 等を変更したのに `docs/specification/` を更新していないコミットをブロックする）。

### グローバル実行（pipx）

```bash
pipx install --editable /path/to/memhog   # 開発中の即反映
pipx install /path/to/memhog              # 通常インストール
memhog                                    # どこからでも
```

## CI / auto-merge

- PR / main への push で GitHub Actions（`test` ジョブ = ruff + mypy + pytest）が走る。main 保護 ruleset で `test` を必須チェックにしているため、緑にならないとマージできない。
- 自動マージのトグル:
  ```bash
  scripts/automerge.sh status        # 現在の状態
  scripts/automerge.sh on            # 有効化
  scripts/automerge.sh off           # 無効化（手動マージのみ）
  gh pr merge <N> --auto --squash    # ON 時: CI 緑で自動マージ予約
  ```

## ディレクトリ構成

リポジトリ全体の構成図の正本はここ（`docs/` 配下の構成図は [docs/README.md](docs/README.md)）。

```
.
├── pyproject.toml                  # Poetry（依存・entry point memhog）
├── src/memhog/
│   ├── cli.py                      # typer の CLI（-n / -g / --json / --watch / --kill）
│   ├── collect.py                  # top / ps / sysctl の実行と収集
│   ├── parse.py                    # 出力のパース（macOS 依存の書式）
│   ├── models.py                   # データモデル＋GPU 常駐の判定しきい値
│   ├── report.py                   # 集計・並べ替え・JSON 化
│   └── render.py                   # 端末描画（rich）
├── tests/
│   ├── test_collect.py             # 収集（top/ps をモック）
│   ├── test_parse.py               # パース
│   ├── test_models.py              # GPU 常駐判定
│   ├── test_report.py              # 集計・JSON
│   ├── test_render.py              # 描画
│   ├── test_spec_freshness.py      # 仕様書ゲートの構造テスト
│   ├── test_doc_tree.py            # 構成ツリーと実ファイルの整合（双方向・2ツリー）
│   ├── test_doc_facts.py           # 文書の数値がコード実値と一致するか
│   └── test_doc_dedup.py           # 文書間の再掲（同一文の重複）検出
├── scripts/
│   ├── check-spec-freshness.sh     # 仕様書の鮮度チェック（pre-commit から呼ぶ）
│   └── automerge.sh                # auto-merge の ON/OFF トグル
├── .github/workflows/ci.yml        # CI（main の必須チェック）
├── .githooks/pre-commit            # 仕様書の鮮度＋ドキュメント整合の検査
├── .claude/rules/
│   └── specification-update.md     # 仕様書更新の義務（このリポジトリ限定ルール）
└── docs/                           # 仕様書 / 設計メモ（構成図は docs/README.md）
```

## 対応環境

macOS 専用（`top` / `ps` / `sysctl` / `memory_pressure` に依存）。
テストは `top`/`ps` をモックするため CI（Linux ランナー）でも動く。
