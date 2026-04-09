# Text vs Image Fidelity Test (全自動 LLM 評価版)

このテストは「画像を LLM に渡すとき、2 通りの経路（specialized 記述を経由 vs 画像を直接渡す）でどれだけ情報量に差が出るか」を 3 種類の**業務シナリオを再現した密度の高い画像**で検証する。

さらに「画像種別に合わせた specialized プロンプト」が generic プロンプトに比べてどれだけ記述精度を上げるかも同時に評価する。

**すべて自動**: 記述生成 → Case 1/Case 2 の回答生成 → LLM-as-judge によるファクト採点まで、ひとつのコマンドで完結する。

## 構成

```
tests/text_vs_image/
├── README.md                      # この文書
├── images/                        # 3 種類の検証用画像（PIL 生成）
│   ├── 01_mixed_slide.png         # flow+chart+table+code+text を 1 枚に
│   ├── 02_ui_change.png           # UI モックアップ + 赤吹き出しの変更要求
│   └── 03_complex_arch.png        # AWS Multi-AZ クラウド構成図
├── prompts/                       # 4 つのプロンプトテンプレート
│   ├── generic.md                 # 汎用記述プロンプト（ベースライン）
│   ├── mixed_slide.md             # 混合スライド → セクション別構造化出力
│   ├── ui_change.md               # UI 変更要求 → {対象要素, 変更内容} 表
│   └── architecture_mermaid.md    # アーキ → Mermaid + ノード/エッジ一覧
├── generate_test_images.py        # 3 画像を PIL で生成
├── test_cases.yaml                # 全データ（質問・GT・記述・回答・スコア）
├── run_evaluation.py              # 3 ステージすべてを自動実行
├── generate_report.py             # test_cases.yaml → report.html
└── report.html                    # 最終レポート（生成物、単一 HTML）
```

## 評価軸（4 列）

| 列 | 生成方法 | 種別 |
|---|---|---|
| ① **Generic 記述** | 画像 + `prompts/generic.md` → Gemini Vision | describe |
| ② **Specialized 記述** | 画像 + `prompts/<type>.md` → Gemini Vision | describe |
| ③ **Case 1: text→LLM 回答** | `② Specialized 記述 + 質問` → Gemini (text only) | answer |
| ④ **Case 2: image→LLM 回答** | `画像 + 質問` → Gemini Vision | answer |

これで以下の問いに答えられる:
1. **プロンプト工夫は効くか?** → ① vs ② の差
2. **テキスト経由で情報損失は起きるか?** → ④ vs ③ の差
3. **専用プロンプトで記述した後の情報損失は十分に小さいか?** → ② vs ③ の差

## テストケース

### tc01: 混合スライド (Flow + Chart + Table + Code)
pptx のスライドを丸ごと画像化するユースケースを模倣。1 枚の中に 5 種類のセクション（フローチャート / 棒グラフ / 売上表 / Python コード / フッター注釈）が同居している。Gemini が全セクションを漏れなく拾えるかを検証。**24 facts**。

### tc02: UI 変更要求 (RFP)
ShopApp の商品検索画面モックアップに、赤色の吹き出しで 4 つの変更要求（チェックボックス追加 / ボタン色変更 / CSV エクスポート追加 / ページ件数変更）が書き込まれている。LLM が「吹き出し内容」だけでなく「吹き出しが指す対象」まで正確に対応づけられるかを検証。**20 facts**。

### tc03: 複雑クラウドアーキテクチャ (AWS Multi-AZ)
本番環境クラスの AWS 構成図（VPC、2 AZ、Public/Private/DB Subnet、ALB、ECS Fargate、RDS Primary/Replica、ElastiCache、NAT GW、CloudFront、S3、Route 53、CloudWatch、IAM の合計 12+ コンポーネント）。Multi-AZ 冗長化構造と主要な接続（HTTPS/SQL write/read-only など）を LLM が抽出できるかを検証。**26 facts**。

### tc02_judge: [判断] UI 変更要求の工数見積 (tc02 と同じ画像)
tc02 の画像を再利用し、「PM として 4 つの変更要求の工数見積・バックエンド影響・リスク・依存関係を判断してください」という業務判断タスクを評価。LLM が視覚情報に基づいて推論できるかを検証。**16 facts**。

### tc03_judge: [判断] AWS 構成図の視覚的特徴読解 (tc03 と同じ画像)
tc03 の画像を再利用し、「VPC 内外の配置、4 層のトラフィックフロー、矢印の色による read/write 区別、凡例の色対応」など **図から直接読み取れる視覚的事実のみ** を問う。一般知識での補完は禁止。**21 facts**。

**合計 5 ケース / 107 facts**（extraction: 70, judgment: 37）。

**ポイント**: tc02_judge と tc03_judge は既存画像を再利用しているので追加の画像生成は不要。同じ画像に対して extraction 質問と judgment 質問の両方を投げることで、「LLM は見えているか」と「見た上で判断できるか」を切り分けられる。

## 実行手順

### 1. 依存インストール（一度だけ）

```bash
cd /Volumes/mac_hd/work/jeis/copilot_demo
eval "$(pyenv init --path)" && eval "$(pyenv init -)"
pip install python-pptx python-docx  # 既に入っていれば不要
```

`.env` に `GEMINI_API_KEY` が設定済であることを確認。

### 2. テスト画像生成（一度だけ / 生成物の変更時のみ）

```bash
python tests/text_vs_image/generate_test_images.py
```

出力: `images/01_mixed_slide.png`, `02_ui_change.png`, `03_complex_arch.png`

### 3. 全自動評価の実行

```bash
python tests/text_vs_image/run_evaluation.py
```

3 ステージを順に実行（5 ケース、107 facts、4 列 × バッチ 10 facts 単位の LLM-as-judge）:

| ステージ | 内容 | 呼び出し数 |
|---|---|---|
| **descriptions** | generic + specialized 記述を生成 (extraction 3 ケースのみ、judgment 2 ケースは同じ画像を再利用) | 3 × 2 = 6 |
| **answers** | Case 1 (text) + Case 2 (image) の回答を生成 | 5 × 2 = 10 |
| **scoring** | 各 fact × 各列を **10 件バッチ** で LLM-as-judge 判定 | (107 × 4) / 10 ≈ 50 |

**合計: ~66 API 呼び出し**。バッチ化前の 1 fact ずつ呼ぶ方式だと 450+ 回だったので、約 **85% の削減**。

**所要時間**: 約 10-15 分（Gemini 3.1 Pro preview、バッチ化後）

部分実行:

```bash
# 特定のケースだけ
python tests/text_vs_image/run_evaluation.py --case tc02

# 特定のステージだけ
python tests/text_vs_image/run_evaluation.py --stage descriptions
python tests/text_vs_image/run_evaluation.py --stage answers
python tests/text_vs_image/run_evaluation.py --stage scoring

# 既存データを上書き再生成
python tests/text_vs_image/run_evaluation.py --force
```

再実行に対応: 既に埋まっているフィールドは `--force` なしだとスキップされるので、途中で中断しても安全。

### 4. レポート生成

```bash
python tests/text_vs_image/generate_report.py
open tests/text_vs_image/report.html  # ブラウザで開く
```

単一 HTML に全データ（画像は data URI 埋め込み、Mermaid は mermaid.js でライブレンダリング）。採点アイコンにマウスオーバーすると **LLM judge の判定理由** がツールチップ表示される。

## 編集サイクル

ground truth facts を追加/変更した場合:

```bash
# 1. test_cases.yaml を編集して新しい fact を追加
# 2. 新しい fact だけを採点
python tests/text_vs_image/run_evaluation.py --stage scoring
# 3. レポート更新
python tests/text_vs_image/generate_report.py
```

scoring ステージは既採点のフィールドをスキップするので、新規追加した fact だけが判定される。

## 設計上の判断

- **完全自動化**: 手動採点は循環バイアスが少ないが時間がかかる。今回は手動の労力を 0 にするため全自動に振った。
- **Copilot Chat 非依存**: Copilot Chat には公開 API がないので、Case 1/Case 2 は同じ Gemini を使って再現する。Copilot Chat 本番の振る舞いとは **完全一致しない** ことに留意。
- **同一モデルでの判定**: 記述生成・回答生成・採点のすべてを Gemini で行うため、**自己参照バイアス** が乗り得る。Specialized 記述と Case 1 回答は同じモデルが生成しているので、「Specialized → Case 1 の情報損失」は過小評価される傾向がある。
- **LLM-as-judge は必ずしも決定論的ではない**: 再実行で verdict が揺れることがある。大きな数値比較には向かないが、傾向を見るには十分。
- **Playwright を使ったレンダリング検証済み**: 集計サマリー・4 列の記述/回答カード・ground truth table・Mermaid 図のすべてが描画されることを確認。

## 既知の限界

1. **同一モデル内の自己参照バイアス** — 上記
2. **LLM-as-judge の非決定性** — 再実行で数 % スコアが揺れる
3. **3 ケースでは統計的有意性はない** — 傾向を見るための探索的テスト
4. **Gemini thinking モード** — `gemini-3.x-pro-preview` は稀に思考テキストを混入させるが、`_extract_answer_text()` で除去されている（JEIS detection pipeline のノウハウを流用）
5. **UI 変更要求の空間的対応** — tc02 の吹き出し→対象要素の紐付けは、人間が目で見ても曖昧な場合がある。judge LLM の判定精度に依存

## 実行結果と発見 (2026-04-09 更新)

`gemini-3.1-pro-preview`、全 5 ケース（extraction 3 + judgment 2）:

| ケース | カテゴリ | ① Generic 記述 | ② Specialized 記述 | ③ Case 1 (text→LLM) | ④ Case 2 (image→LLM) | **C2 − C1 差** |
|---|---|---|---|---|---|---|
| **tc01** 混合スライド | extraction | 100% | 100% | 52% | **85%** | **+33 pp** |
| **tc02** UI 変更要求 | extraction | 98% | 85% | **68%** | 48% | **−20 pp** |
| **tc02_judge** UI 工数見積 | **judgment** | 13% | 0% | 75% | **88%** | **+13 pp** |
| **tc03** 複雑アーキ | extraction | 100% | 98% | 94% | 98% | +4 pp |
| **tc03_judge** 視覚特徴読解 | **judgment** | 81% | 83% | 95% | 95% | 0 pp |
| **合計 (70+16+21 facts)** | | 82.7% | 78.5% | 77.1% | **83.6%** | **+6.5 pp** |

### 5 つの発見

**発見 1: Case 1 / Case 2 の勝敗は質問タイプだけでは決まらない**
tc01 (混合スライド extraction) で Case 2 が +33pp 圧勝、tc02 (UI extraction) では Case 1 が +20pp 逆転、tc02_judge (判断) で Case 2 が +13pp と、方向・大きさが大きくばらつく。

**発見 2: 質問が tc02 のような構造化データ抽出の場合、specialized プロンプトは image 直接より強い**
tc02 の `ui_change.md` プロンプトが「対象要素 → 変更内容」表形式を強制したため、Case 1 は構造的に漏れの少ない形で解答した。Case 2 (自由形式) は空間的対応を取りこぼした。**適切な specialized プロンプトは image 優位を逆転する可能性がある**。

**発見 3: 混合スライド (pptx 丸ごと) では Case 2 が圧倒的に有利**
tc01 で +33pp 差。複数種別（flow/chart/table/code/text）が 1 枚に同居すると、text 化で情報圧縮が起き、判断で重要な細部が落ちる。**pptx スライドを丸ごと渡すユースケースこそ image 直接の真価が出る**。

**発見 4: Case 1 のプロンプト文言がスコアを支配する**
初回の tc02_judge で Case 1 に「記述に書かれていない情報を推測しないで」と書いたところ、LLM は「工数情報は記述に無い → 判断不可能」と答えて **全 16 facts missing (0%)** になった。「判断には一般知識を使ってよい」に緩めると 0% → 75% に急回復。**プロンプト設計自体が評価結果を完全にひっくり返せる**。

**発見 5: describe 列は judgment 質問の採点対象にならない**
tc02_judge の Specialized 記述列は 0%。specialized 記述は UI 要素を列挙するだけで「工数見積もり」は含まないので、judgment の ground truth に対してはほぼ全部 missing になるのが正しい挙動。集計サマリーを extraction と judgment で分離せずに表示しているので、合計値は参考程度に見るべき。

### 解釈

- **pptx 丸ごと image を LLM に渡す業務なら、Copilot Chat の画像機能復活を待つ価値がある** (+33pp は大きすぎて text 記述では埋められない)
- **RFP のような「画面要素 + 変更指示」の構造化タスクなら、specialized prompt で text 化する方が安定** (対応表の構造が解答に引き継がれる)
- **判断タスク (工数見積・視覚特徴読解) では image/text の差は中程度** (13pp / 0pp)
- **Case 1 を評価する際は "domain knowledge 使用可" を明示**。制約が強すぎると LLM は「判断不可能」に逃げる

## 関連ファイル

| ファイル | 役割 |
|---|---|
| [test_cases.yaml](test_cases.yaml) | データの単一ソース、手動編集 OK |
| [run_evaluation.py](run_evaluation.py) | 3 ステージ自動実行の本体 |
| [generate_report.py](generate_report.py) | HTML レポート生成 |
| [generate_test_images.py](generate_test_images.py) | PIL で 3 画像を生成 |
| [prompts/generic.md](prompts/generic.md) | ベースライン汎用プロンプト |
| [prompts/mixed_slide.md](prompts/mixed_slide.md) | tc01 用 |
| [prompts/ui_change.md](prompts/ui_change.md) | tc02 用 |
| [prompts/architecture_mermaid.md](prompts/architecture_mermaid.md) | tc03 用 |
| [../../tools/lib/gemini_client.py](../../tools/lib/gemini_client.py) | Gemini SDK ラッパー（共通） |
