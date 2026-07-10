# memhog

macOS の**実メモリ(物理フットプリント)を最も食っているプロセスを特定して提示する**診断 CLI。

## なぜ必要か

`ps aux` の RSS は **Metal/MPS（Apple Silicon の GPU 共有＝ユニファイドメモリ）を数えない**。
そのため ComfyUI 等の ML 系 Python は RSS 上「数十 MB」に見えるのに、実際は数十 GB を常駐している。
Activity モニタが示す本当の値＝`top` の MEM 列（物理フットプリント）。

memhog はこの物理フットプリントでランク付けし、`ps` の RSS との乖離が大きいプロセスに
**`⚠ GPU/Metal常駐(psに出ない)`** 印を付けて「小さく見えるのに実は巨大」を炙り出す。

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
poetry run pytest             # テスト
poetry run ruff check .       # lint
poetry run mypy src           # 型チェック
poetry run memhog             # 実行
```

### グローバル実行（pipx）

```bash
pipx install --editable /path/to/memhog   # 開発中の即反映
pipx install /path/to/memhog              # 通常インストール
memhog                                    # どこからでも
```

## 対応環境

macOS 専用（`top` / `ps` / `sysctl` / `memory_pressure` に依存）。
