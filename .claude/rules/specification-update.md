# 仕様書更新の義務

機能実装・バグ修正・UI変更を行ったら、**同じコミット内で** `docs/specification/` を更新する。

## 発火条件

- `src/memhog/` 配下のコード変更を伴うコミット（`check-spec-freshness.sh` の `WATCH_PATTERNS` で定義）
- `scripts/` 配下のスクリプト追加・変更
- `.github/workflows/` 配下の CI/CD ワークフロー追加・変更
- 新しい CLI オプション・出力形式の追加
- 既存機能の挙動変更（判定式・閾値・表示ロジック含む）
- 環境変数・依存ライブラリの追加

## 必須アクション

1. `docs/specification/client/`（依頼者向け）: ユーザーに見える変更を該当トピック（無ければ `client/README.md`）に反映
2. `docs/specification/develop/`（開発者向け）: 構成・アルゴリズム・テスト・技術詳細を該当トピック（architecture / memory-detection / cli / testing、無ければ `develop/README.md`）に反映
3. `docs/specification/` が存在しない場合は作成する（`specification` スキル参照）

## 禁止

- 「後でまとめて更新する」
- 「内部実装だから仕様書不要」（判定式・閾値の変更はユーザー体感が変わるので仕様変更）
- 仕様書未更新のままコミット・PR作成する
