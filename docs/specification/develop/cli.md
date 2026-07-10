# CLI オプション

最終更新: 2026-07-10

エントリポイント: `memhog.cli:app`（typer、単一コマンド）。定義は `src/memhog/cli.py`。

## オプション一覧

| オプション | 短縮 | 既定 | 説明 |
|-----------|------|------|------|
| `--count` | `-n` | `15` | 表示する件数 |
| `--grep` | `-g` | なし | フルコマンドへの部分一致で絞り込み（大小無視） |
| `--json` | | `False` | 機械可読な JSON で出力 |
| `--watch` | | なし | 指定秒間隔で画面を更新し続ける（監視モード） |
| `--kill` | | `False` | 一覧から PID を選んで停止 |
| `--force` | | `False` | `--kill` 時に SIGKILL を使う（既定は SIGTERM） |
| `--yes` | `-y` | `False` | `--kill` の確認プロンプトを省略 |
| `--version` | | | バージョンを表示して終了 |

## 併用制約・挙動

- `--watch` は `--json` / `--kill` と**併用不可**（指定時はエラー終了 code 1）。
- `--watch`: 無限ループで `console.clear()` → 再描画 → `sleep(interval)`。`Ctrl-C`（KeyboardInterrupt）で終了。
- `--kill`（`_kill_process`、**不可逆操作**）:
  - 既定の停止対象 PID は一覧の先頭（最大消費元）。プロンプトで PID を入力。
  - `pid <= 1` または自分自身（`collect.current_pid()`）は停止拒否（code 1）。
  - `--yes` 未指定なら `PID N を SIG… で停止します。よいですか?` を確認。
  - 実際の送信は `collect.send_signal(pid, sig)`（副作用は collect 層）。戻り値で分岐:
    `"not_found"` → 「既に終了?」表示。`"denied"` → 「権限がありません」で code 1。`"ok"` → 送信済み表示。
- `--json`: `render.build_json` の出力（`system` と `processes[]`、各要素に `hidden_gpu` を含む）。
