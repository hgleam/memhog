# テスト・CI

最終更新: 2026-07-10

## テスト構成

`tests/` 配下、pytest。`collect`（外部コマンド I/O）をモックするため macOS 非依存で CI（Linux）でも動く。

件数は pytest 収集数（parametrize 展開後）。合計 48。

| ファイル | 件数 | 対象 |
|---------|------|------|
| `test_models.py` | 6 | `Process.hidden_gpu` の判定（境界値・GPU 常駐/非常駐） |
| `test_parse.py` | 20 | `parse_mem_to_mb` / `parse_top_processes` / `parse_phys_mem` / `parse_free_percentage` |
| `test_report.py` | 6 | `build_processes` / `build_system_memory`（collect をモック） |
| `test_render.py` | 5 | `format_mb`（MB→G/M 整形） |
| `test_collect.py` | 4 | `send_signal`（os.kill をモック・例外→結果コード翻訳）/ `current_pid` |
| `test_spec_freshness.py` | 7 | 仕様書鮮度チェックの仕組みが揃っていることの構造テスト |

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
