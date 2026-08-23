# テスト・CI

## テスト構成

`tests/` 配下、pytest。`collect`（外部コマンド I/O）をモックするため macOS 非依存で CI（Linux）でも動く。

件数は pytest 収集数（parametrize 展開後）。合計 81（ドキュメント整合の 3 ファイルを除く）。

| ファイル | 件数 | 対象 |
|---------|------|------|
| `test_models.py` | 6 | `Process.hidden_gpu` の判定（境界値・GPU 常駐/非常駐） |
| `test_parse.py` | 23 | `parse_mem_to_mb` / `parse_top_processes` / `parse_phys_mem` / `parse_free_percentage` / `parse_ps_snapshot` |
| `test_report.py` | 16 | `build_processes` / `build_groups` / `build_app_processes` / 走査幅 / `build_system_memory`（collect をモック） |
| `test_group.py` | 17 | `app_label` / `group_label`（親子・器の素通り・循環）/ `group_processes`（合算・順位） |
| `test_render.py` | 8 | `format_mb`（MB→G/M 整形）/ 他プロセス由来文字列のマークアップ escape / 提案コマンドの shlex クォート |
| `test_collect.py` | 4 | `send_signal`（os.kill をモック・例外→結果コード翻訳）/ `current_pid` |
| `test_spec_freshness.py` | 7 | 仕様書鮮度チェックの仕組みが揃っていることの構造テスト |
| `test_doc_tree.py` | 10 | 構成ツリー ↔ 実ファイルの双方向照合（漏れ／幽霊）＋2箇所以外への複製検出 |
| `test_doc_facts.py` | 6 | 文書の数値 ↔ コード実値（`--count` 既定・`HIDDEN_GPU_MIN_MB` ・`HIDDEN_GPU_RSS_RATIO` ・`GROUP_SAMPLE_MIN` ・`_MAX_CMD`） |
| `test_doc_dedup.py` | 2 | 文書間の再掲（本文で 40 文字以上の同一行が2文書にあれば FAIL） |

### ドキュメント整合のテスト

コードを直して**文書だけ古い**状態は、通常のテストが緑でも起こる。閾値を変えたのに
`memory-detection.md` の定数表が古いと「なぜこの警告が出た/出ないか」の説明が実装と食い違う。
**正本＝コード**として機械照合する。

- 構成ツリーは **README を持つディレクトリがそれぞれ自分の直下だけを描く**（上位は1行に畳んで委譲）。
  同じファイル名がツリーに現れるのは1箇所だけなので二重化しない。
- 標準ライブラリのみで動くので、CI では**依存 install より前**に `Doc integrity` として走る
  （install が失敗しても文書のズレは検出できる）。`pytest` でも収集される。
- 雛形は `~/claude-private/.claude/skills/init/templates/`。他プロジェクトへも同手順で入る。

実行:

```bash
poetry run pytest -q      # テスト
poetry run ruff check .   # lint
poetry run mypy src       # 型チェック
```

## CI（GitHub Actions）

- `.github/workflows/ci.yml`。PR / main への push で `test` ジョブ（ruff → mypy → pytest）が走る。
- main 保護 ruleset で `test` を必須チェックにしており、緑にならないとマージできない。
- 自動マージのトグルは `scripts/automerge.sh`（`on` / `off` / `status`）。ON 時は `gh pr merge <N> --auto --squash` で CI 緑後に自動マージ予約。

## 仕様書鮮度チェック（pre-commit）

- `scripts/check-spec-freshness.sh` が、監視対象コード（`WATCH_PATTERNS`）を変更したのに
  `docs/specification/` を更新していないコミットをブロックする。
- 有効化は `.githooks/` を `core.hooksPath` に設定する方式（husky は使わない）。
  **別クローンでは `git config core.hooksPath .githooks` を再実行する必要がある**（README のセットアップ手順参照）。
- 仕様変更でない場合は `git commit --no-verify` でスキップ可能。

## 自動マージ

PR を作るだけで「CI 緑 → 自動マージ → ブランチ削除」まで無人で進む。

| ワークフロー | 役割 |
|---|---|
| `.github/workflows/auto-merge.yml` | PR の open / reopen / ready_for_review で auto-merge を予約（draft は除外） |
| `.github/workflows/cleanup-merged-branches.yml` | マージ済みブランチを毎日 00:00 JST に削除 |

前提として、リポジトリ設定の `allow_auto_merge` と main 保護 ruleset の
`required_status_checks`（CI のジョブ名）を有効にしてある。**必須チェックが無いと
`--auto` は待つ対象が無く即マージになる**ため、両方揃って初めて「緑を待つ」動作になる。

掃除を別ワークフローに分けているのは、`GITHUB_TOKEN` 起点のマージが
`push` / `pull_request closed` を発火せず、`--delete-branch` も
`delete_branch_on_merge` も効かないため（schedule はこの制約を受けない）。
