# アーキテクチャ

最終更新: 2026-07-10

副作用（外部コマンド実行）を `collect.py` に隔離し、解析ロジックを純粋関数（`parse.py`）に
分けることで、テスト時は `collect` をモックするだけで macOS 非依存に検証できる構成。

## レイヤ構成

| モジュール | 役割 | 副作用 |
|-----------|------|--------|
| `collect.py` | `top` / `ps` / `sysctl` / `memory_pressure` を叩く薄い I/O 層 | あり（subprocess） |
| `parse.py` | top・memory_pressure の出力を解析する純粋関数群 | なし |
| `models.py` | ドメインモデル（`Process` / `SystemMemory`）と判定ロジック | なし |
| `report.py` | `collect` × `parse` を組み合わせて一覧・システム状況を構築 | あり（collect 経由） |
| `render.py` | `Process` / `SystemMemory` を表 / JSON に整形 | なし（出力のみ） |
| `cli.py` | typer エントリ・オプション制御・`--kill` / `--watch` | あり |

## データフロー

```
cli.main
  └─ report.build_processes(count, grep)
       ├─ collect.top_sample(sample_count)          # top ワンショット
       ├─ parse.parse_top_processes(raw)            # (pid, mem_mb, cpu) 抽出
       ├─ collect.ps_command(pid)                   # フルコマンド
       └─ collect.ps_rss_mb(pid)                    # ps RSS(MB)
     → list[Process], top の生出力
  └─ report.build_system_memory(top_raw)
       ├─ parse.parse_phys_mem(top_raw)             # PhysMem 行（top 生出力を再利用）
       ├─ collect.swap_usage()                      # sysctl vm.swapusage
       └─ parse.parse_free_percentage(memory_pressure())
     → SystemMemory
  └─ render.render_table(...) / render.build_json(...)
```

## 設計判断

- **`top` の生出力を使い回す**: `build_processes` が返す top 生出力から PhysMem 行も取り出し、
  `build_system_memory` に渡すことで top の二重起動を避ける。
- **エラーは握り潰さず空を返す**: `collect._run` は `OSError` / `ValueError` を捕捉して空文字を返し、
  取得できたぶんだけ表示する（診断ツールとして「一部欠損でも動く」ことを優先）。
- **フィルタ時は多めにサンプリング**: `-g` 指定時は取り漏らしを防ぐため top を `count * 4`（最低 40 件）
  取得してから絞り込む。
