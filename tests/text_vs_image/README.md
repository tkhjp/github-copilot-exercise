# Text vs Image — Copilot Chat Fidelity Test

このテストは「画像を Copilot Chat に渡すとき、テキスト記述経由（Case 1）と画像直接（Case 2）でどれだけ情報量に差が出るか」を 5 種類の画像で検証する。同時に「画像種別に合わせたプロンプト工夫（Mermaid / Markdown table / コード転写など）が generic プロンプトに比べてどれだけ記述精度を上げるか」も評価する。

## 構成

```
tests/text_vs_image/
├── README.md                      # この文書
├── images/                        # 5 種類の検証用画像
│   ├── 01_flowchart.png           # フローチャート
│   ├── 02_barchart.png            # 棒グラフ
│   ├── 03_table.png               # 表（4 行 × 5 列）
│   ├── 04_code.png                # Python コードのスクショ
│   └── 05_architecture.png        # システム構成図
├── prompts/                       # プロンプトテンプレート
│   ├── generic.md                 # 既存の汎用記述プロンプト
│   ├── flowchart_mermaid.md       # フローチャート → Mermaid
│   ├── chart_table.md             # チャート → Markdown table
│   ├── table_markdown.md          # 表 → Markdown table
│   ├── code_transcription.md      # コード → 言語タグ付き転写
│   └── architecture_mermaid.md    # 構成図 → Mermaid
├── generate_test_images.py        # 5 枚の画像を生成
├── test_cases.yaml                # 全データ（質問・GT・記述・回答・スコア）
├── run_descriptions.py            # Gemini で generic + specialized 記述を生成
├── generate_report.py             # test_cases.yaml → report.html
└── report.html                    # 最終レポート（生成物）
```

## 評価軸（4 列）

各テストケースで、ground truth fact リストに対し以下 4 列をスコアリング:

| 列 | 何を測るか | 自動 / 手動 |
|---|---|---|
| **Generic 記述** | 汎用プロンプトの Gemini 記述 | 記述: 自動 / 採点: 手動 |
| **Specialized 記述** | 種別別プロンプトの Gemini 記述 | 記述: 自動 / 採点: 手動 |
| **Case 1: text → Copilot** | Specialized 記述を Copilot Chat に渡した回答 | すべて手動 |
| **Case 2: image → Copilot** | 画像を Copilot Chat に直接渡した回答 | すべて手動 |

これで以下の問いに答えられる:
1. **プロンプト工夫は効くか?** → Generic vs Specialized
2. **テキスト経由で情報損失は起きるか?** → Specialized vs Case 2
3. **Copilot は記述を正しく理解できるか?** → Specialized vs Case 1

## 実行手順

### 一度だけ実行

```bash
cd /Volumes/mac_hd/work/jeis/copilot_demo
eval "$(pyenv init --path)" && eval "$(pyenv init -)"

# 1. 5 枚の画像を生成（既存の samples/ 2 枚を流用 + 新規 3 枚）
python tests/text_vs_image/generate_test_images.py

# 2. Gemini で全画像 × generic + specialized の記述を生成
python tests/text_vs_image/run_descriptions.py
#   → test_cases.yaml の descriptions セクションが埋まる
```

`run_descriptions.py` は再実行に対応:
- 既に記述が入っている場合はスキップ
- `--force` で上書き
- `--case tc01` で 1 ケースだけ
- `--only generic` または `--only specialized` で片方だけ

### 手動採点（記述）

`test_cases.yaml` を開き、各テストケースの `description_scores` セクションを埋める:

```yaml
description_scores:
  generic:
    f1: present     # ground truth fact f1 が記述に含まれているか
    f2: partial     # 部分的に
    f3: missing     # 含まれていない
    ...
  specialized:
    f1: present
    ...
```

スコアの値:
- `present` (1.0) — fact が完全に含まれている
- `partial` (0.5) — 部分的に含まれている／曖昧
- `missing` (0.0) — 含まれていない

### Copilot Chat で手動テスト

VS Code を起動し、Copilot Chat を **agent mode** に切り替えてから以下を 5 ケース × 2 回繰り返す。

#### Case 1（specialized description → Copilot Chat）

1. `test_cases.yaml` から該当ケースの `descriptions.specialized` を全文コピー
2. Copilot Chat に貼り付け、続けて `question` を貼り付けて送信
   - 例: `<specialized 記述全文>\n\n質問: <test_cases.yaml の question>`
3. Copilot の回答全文をコピーして `case1.copilot_answer` に貼り付け
4. `case1.fact_scores` を埋める

#### Case 2（image → Copilot Chat 直接）

1. Copilot Chat の入力欄に `images/<対応する画像>` をドラッグ&ドロップ（または添付ボタン）
2. 同じ `question` を入力して送信
3. Copilot の回答全文をコピーして `case2.copilot_answer` に貼り付け
4. `case2.fact_scores` を埋める

> **クライアント環境で画像アップロードが無効な場合**: Case 2 はスキップ可。Generic vs Specialized vs Case 1 の 3 列だけでも、プロンプト工夫の効果と Copilot の理解度は十分測定できる。

### レポート生成

```bash
python tests/text_vs_image/generate_report.py
#   → tests/text_vs_image/report.html を生成

# ローカルブラウザで開く
open tests/text_vs_image/report.html
```

レポートには以下が含まれる:
- 集計サマリー: 4 列それぞれのカバー率（present + 0.5 × partial）／50 facts
- TOC: 5 ケースへのリンク
- 各ケース詳細:
  - 画像サムネイル
  - 質問
  - Ground truth fact 表（4 列の採点アイコン）
  - 4 列の出力（Mermaid は mermaid.js でその場でレンダリング、Markdown は marked.js でレンダリング）

## 編集サイクル

```
1. test_cases.yaml を編集（採点 or 回答貼付）
2. python tests/text_vs_image/generate_report.py
3. ブラウザで report.html を再読込（または open)
4. 1 に戻る
```

`generate_report.py` は冪等で速い（< 1 秒）。`run_descriptions.py` は API を叩くので一度生成したら再実行不要。

## 設計上の判断

- **手動採点に統一**: LLM ジャッジは循環バイアスを生むので不採用。ground truth は 50 facts と少なく、全採点でも 15 分程度
- **5 ケース × 2 プロンプト**: 統計的有意性ではなく「カテゴリごとの傾向」を見ることが目的。1 時間で完結する規模に最適化
- **mermaid.js / marked.js は CDN**: ローカルで完結する単一 HTML を保ちつつ、Mermaid 図と Markdown を描画できる
- **画像を data URI で埋め込み**: report.html を 1 ファイルで完結させる（共有・添付が容易）

## ground truth の総数

| ケース | facts |
|---|---|
| tc01 フローチャート | 8 |
| tc02 棒グラフ | 9 |
| tc03 売上テーブル | 10 |
| tc04 コードスクリーンショット | 12 |
| tc05 アーキテクチャ図 | 11 |
| **合計** | **50** |

## 既知の制約

- ground truth は人手で作成しており、画像の主観的な要素（美的、強調されているか等）は含めない事実ベースのみ
- Copilot Chat の回答は LLM 非決定性により再実行で揺れる。気になる場合は同じ質問を 2-3 回試して安定回答を採用
- specialized プロンプトは「画像種別を事前に知っている」前提。実運用ではディスパッチ層が必要だが本テストでは直接指定
