# CLI オプション

エントリポイント: `memhog.cli:app`（typer、単一コマンド）。定義は `src/memhog/cli.py`。

## オプション一覧

| オプション | 短縮 | 既定 | 説明 |
|-----------|------|------|------|
| `--count` | `-n` | `15` | 表示する件数 |
| `--sort` | | `mem` | 並べる基準（`mem` = 実メモリ / `cpu` = CPU 使用率） |
| `--grep` | `-g` | なし | フルコマンドへの部分一致で絞り込み（大小無視） |
| `--json` | | `False` | 機械可読な JSON で出力 |
| `--group` | | `False` | プロセス単位でなくアプリ単位に合算して表示 |
| `--app` | | なし | 指定したアプリ名に属するプロセスだけを一覧（`--group` の内訳） |
| `--watch` | | なし | 指定秒間隔で画面を更新し続ける（監視モード） |
| `--kill` | | `False` | 一覧から PID を選んで停止 |
| `--force` | | `False` | `--kill` 時に SIGKILL を使う（既定は SIGTERM） |
| `--yes` | `-y` | `False` | `--kill` の確認プロンプトを省略 |
| `--version` | | | バージョンを表示して終了 |

## 併用制約・挙動

- `--sort` は `mem` / `cpu` 以外を渡すとエラー終了 code 1。
- `--sort` は表示側の並べ替えではなく **`top` の `-o` を切り替える**。取得後に並べ替えると
  母集団が「メモリ上位 N 件」のままになり、CPU 上位のプロセスがそもそも含まれない。
  `--group` / `--app` にも同じ値を渡す（集約の並び順・グループ内の最大単体の選び方に効く）。
- `--watch` は `--json` / `--kill` と**併用不可**（指定時はエラー終了 code 1）。
- `--watch`: 無限ループで `console.clear()` → 再描画 → `sleep(interval)`。`Ctrl-C`（KeyboardInterrupt）で終了。
- `--kill`（`_kill_process`、**不可逆操作**）:
  - 既定の停止対象 PID は一覧の先頭（最大消費元）。プロンプトで PID を入力。
  - `pid <= 1` または自分自身（`collect.current_pid()`）は停止拒否（code 1）。
  - `--yes` 未指定なら `PID N を SIG… で停止します。よいですか?` を確認。
  - 実際の送信は `collect.send_signal(pid, sig)`（副作用は collect 層）。戻り値で分岐:
    `"not_found"` → 「既に終了?」表示。`"denied"` → 「権限がありません」で code 1。`"ok"` → 送信済み表示。
- `--group` は `--kill` / `--app` と**併用不可**（いずれもエラー終了 code 1）。`--kill` は停止対象を
  PID で選ぶ必要があるため、`--app` は「合計か内訳か」が排他のため。
- `--app` は所属判定を `group.group_label`（親子関係）で行う。`-g`（コマンド文字列の部分一致）では
  実行ファイル名に親アプリ名を含まない子プロセス（MCP サーバ等）を取りこぼすため、集約と同じ規則を使う。
  出力はプロセス単位の表（`render.render_table`）で、`--kill` / `--json` / `--watch` と併用できる。
- `--group` の `-n` は「表示するグループ数」、`-g` は**合算前**のプロセスに掛かる
  （一致したプロセスだけが合計に入る）。この場合は部分合計であることを表の見出しに出す。`--watch` とは併用可。
- `--json`: `render.build_json` の出力（`system` と `processes[]`、各要素に `hidden_gpu` を含む）。
- `--group --json`: `render.build_group_json` の出力（`system` と `groups[]`。各要素は
  `label` / `total_mb` / `count` / `hidden_gpu` / `largest{pid, mem_mb, command}`）。
