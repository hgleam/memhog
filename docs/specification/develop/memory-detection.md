# メモリ検出ロジック（算出仕様）

最終更新: 2026-07-10

memhog の中核。「なぜ物理フットプリントでランクするか」と「GPU/Metal 常駐の判定式」を実コード
（`src/memhog/models.py`・`src/memhog/parse.py`）を根拠に記す。

## 物理フットプリント vs RSS

| 指標 | 出所 | 特性 |
|------|------|------|
| MEM（物理フットプリント） | `top -o mem` の MEM 列 | Activity モニタ「メモリ」列相当。GPU 共有メモリを含む |
| psRSS | `ps -o rss` | Metal/MPS（GPU 共有＝ユニファイドメモリ）を**数えない**ため過小に出る |

ランク付けは常に **MEM（物理フットプリント）降順**（top の並びをそのまま保つ）。

## GPU/Metal 常駐の判定式

`Process.hidden_gpu`（`models.py`）。ps の RSS に現れない GPU/Metal 常駐メモリを抱えているかを判定する。

```
hidden_gpu = (mem_mb >= HIDDEN_GPU_MIN_MB) and (mem_mb > rss_mb * HIDDEN_GPU_RSS_RATIO)
```

| 定数 | 値 | 意味 |
|------|-----|------|
| `HIDDEN_GPU_MIN_MB` | `2000` | この MB 以上の物理フットプリントを持つプロセスのみ対象（小物を除外） |
| `HIDDEN_GPU_RSS_RATIO` | `4` | MEM が psRSS の 4 倍を**超える**とき「小さく見えるのに巨大」とみなす |

- 境界: MEM がちょうど RSS の 4 倍（`==`）は **False**（`>` のため）。4 倍を少しでも超えると True。
- 例: ComfyUI（MEM 32G / RSS 26M）・llama-server（MEM 6.6G / RSS 12M）は True。
  仮想マシン（MEM 7.9G / RSS 2.6G）は比が約 3 倍で False。

True のプロセスは表・JSON で `⚠ GPU/Metal常駐(psに出ない)`（`hidden_gpu: true`）として印付けされる。

## メモリ値の解析（`parse.py`）

### `parse_mem_to_mb(value)`

top の MEM 文字列を MB(float) に変換。末尾の増減記号（`+`/`-`、前サンプルからの変化）は無視する。

| 単位 | 係数（→ MB） |
|------|-------------|
| `G` | ×1024 |
| `M` | ×1 |
| `K` | ×1/1024 |
| `B` | ×1/(1024×1024) |
| （無単位） | ×1 |

解釈できない文字列は `ValueError`。正規表現 `^([0-9]+(?:\.[0-9]+)?)([GMKB]?)$`。

### `parse_top_processes(output)`

`PID` で始まるヘッダ行以降のみを対象に `(pid, mem_mb, cpu)` を抽出。3 列未満・PID が数値でない行、
MEM がパース不能な行はスキップ。CPU がパース不能なら 0.0。top の並び（メモリ降順）を保つ。

### `format_mb(mb)`

表示整形。1024 以上なら `12.3G`、未満なら `512M`（四捨五入）。

## 表示上の強調（`render.py`）

- MEM が `8000` MB 以上の行は赤字で強調（大口消費の視認性）。
- コマンドは 96 文字で末尾省略（`_MAX_CMD = 96`）。
