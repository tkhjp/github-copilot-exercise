# Text vs Image Fidelity Test v2 (マルチモデル + 2 Phase)

Copilot Chat の画像アップロードが使えない環境で、**画像を LLM にテキスト化させてから別の LLM に渡す**方式 (A1) と、**画像を直接 LLM に渡す**方式 (A2) でどの程度の情報損失が起きるかを検証する。

v2 では describe (画像→テキスト記述) と answer (質問→回答) で**異なるモデルファミリー**を使い、自己参照バイアスを排除している。

## 構成

```
tests/text_vs_image/
├── README.md                      # この文書
├── INSIGHTS.md                    # 主要な業務インサイト (結果まとめ)
├── images/                        # 4 種類の検証用画像（PIL 生成）
│   ├── 01_mixed_slide.png         # flow+chart+table+code を 1 枚に
│   ├── 02_ui_change.png           # UI モックアップ + 赤吹き出しの変更要求
│   ├── 03_complex_arch.png        # AWS Multi-AZ クラウド構成図
│   └── 04_text_document.png       # テキストのみの仕様書ページ
├── prompts/                       # 5 つのプロンプトテンプレート
│   ├── generic.md                 # 汎用記述プロンプト（ベースライン）
│   ├── mixed_slide.md             # 混合スライド → セクション別構造化出力
│   ├── ui_change.md               # UI 変更要求 → {対象要素, 変更内容} 表
│   ├── architecture_mermaid.md    # アーキ → Mermaid + ノード/エッジ一覧
│   └── text_document.md           # テキスト文書 → 完全 Markdown 転写
├── generate_test_images.py        # 4 画像を PIL で生成
├── test_cases.yaml                # 全データ（質問・GT・記述・回答・スコア）
├── run_evaluation.py              # 2 Phase 自動実行パイプライン
├── generate_report.py             # test_cases.yaml → report.html
└── report.html                    # 最終レポート（生成物、単一 HTML）
```

## 2 Phase 実験設計

### Phase 1: Describe モデル比較 (Gemini のみ)

2 つの Gemini モデル × 2 つのプロンプト = 4 つの記述を生成し、ground truth facts で採点。

```
                    generic.md        specialized.md
gemini-3-flash          D1                D2
gemini-3.1-flash-lite   D3                D4
```

GPT-5.4 を judge として fact check (present/partial/missing) → スコアの高いモデルを Phase 2 で使用。

### Phase 2: Answer 比較 (GPT-5.4)

Phase 1 で選ばれたモデルの describe を使い、2 つの経路で GPT-5.4 に回答させる:

| 列 | 入力 | 説明 |
|---|---|---|
| **A1** text via GPT | D_generic + D_specialized + question (text only) | テキスト記述を経由 |
| **A2** image via GPT | 画像 + question (vision) | 画像を直接渡す |

**Extraction ケース** (tc01-tc04): A1/A2 を ground truth facts で fact check。
**Judgment ケース** (tc02_judge/tc03_judge): A1/A2 を reasoning_points で fact check。

### モデル構成

| 役割 | モデル | 用途 |
|---|---|---|
| Describe | gemini-3-flash / gemini-3.1-flash-lite | 画像 → テキスト記述 (Phase 1) |
| Answer | GPT-5.4 | テキスト/画像から質問に回答 (Phase 2) |
| Judge | GPT-5.4 | ファクト採点 (Phase 1 + Phase 2) |

## テストケース (6 ケース、107+ facts)

### Extraction (4 ケース)

| ID | タイトル | 画像タイプ | facts | 検証対象 |
|---|---|---|---|---|
| tc01 | 混合スライド | flow+chart+table+code | 24 | 複数種別が同居する高密度画像の抽出 |
| tc02 | UI 変更要求 | 画面+吹き出し | 20 | 空間的アノテーションの対応づけ |
| tc03 | AWS アーキ | 構成図 | 26 | 12+ コンポーネントの構造抽出 |
| tc04 | テキストのみ文書 | 仕様書ページ | 22 | テキスト→テキストの OCR 精度 |

### Judgment (2 ケース)

| ID | タイトル | 画像 (再利用) | reasoning points | 検証対象 |
|---|---|---|---|---|
| tc02_judge | UI 工数見積 | tc02 | 7 | 画面情報を基にした業務判断 |
| tc03_judge | 視覚特徴読解 | tc03 | 9 | 構成図の視覚的事実の推論 |

## 実行手順

### 1. 環境セットアップ

```bash
cd /Volumes/mac_hd/work/jeis/copilot_demo
eval "$(pyenv init --path)" && eval "$(pyenv init -)"
pip install -r tools/requirements.txt
```

`.env` に以下を設定:
```
GEMINI_API_KEY=...
OPENAI_API_KEY=sk-...
```

### 2. テスト画像生成（一度だけ）

```bash
python tests/text_vs_image/generate_test_images.py
```

### 3. Phase 1 実行

```bash
python tests/text_vs_image/run_evaluation.py --phase 1
```

出力: 4 extraction ケース × 4 descriptions + GPT-5.4 judge による fact scoring。
Phase 1 完了時に最適モデルが自動選択される。

### 4. Phase 2 実行

```bash
python tests/text_vs_image/run_evaluation.py --phase 2
```

出力: 全 6 ケース × A1/A2 回答 + fact scoring。

### 5. レポート生成

```bash
python tests/text_vs_image/generate_report.py
open tests/text_vs_image/report.html
```

### 部分実行

```bash
# 特定ケースのみ
python tests/text_vs_image/run_evaluation.py --phase 1 --case tc01

# 全フェーズ一気に（モデル自動選択）
python tests/text_vs_image/run_evaluation.py --phase all --auto-select

# モデルを手動指定
python tests/text_vs_image/run_evaluation.py --phase 2 --describe-model gemini_3_flash

# 既存データを上書き
python tests/text_vs_image/run_evaluation.py --phase 1 --force
```

### API 呼び出し数

| Phase | Gemini | GPT-5.4 | 合計 |
|---|---|---|---|
| Phase 1 (describe + scoring) | 16 | 48 | 64 |
| Phase 2 (answer + scoring) | 0 | 36 | 36 |
| **合計** | **16** | **84** | **~100** |

## v2 実行結果

`gemini-3-flash-preview` + `gpt-5.4`、2026-04-11 実行:

### Phase 1: Describe マトリクス

```
                    generic     specialized
gemini-3-flash       95.5%       94.6%         ← 採用
gemini-3.1-flash-lite 93.0%      93.2%
```

### Phase 2: Answer 比較

| ケース | タイプ | A1 text→GPT | A2 img→GPT | A2−A1 |
|---|---|---|---|---|
| tc01 混合スライド | extraction | **95.8%** | 91.7% | −4.2pp |
| tc02 UI 変更要求 | extraction | 77.5% | **87.5%** | +10.0pp |
| tc03 AWS アーキ | extraction | 90.4% | 90.4% | 0pp |
| tc04 テキストのみ | extraction | **100%** | **100%** | 0pp |
| tc02_judge UI 工数見積 | judgment | 85.7% | 85.7% | 0pp |
| tc03_judge 視覚特徴 | judgment | **88.9%** | 77.8% | −11.1pp |

## 設計上の判断

- **マルチモデル構成**: describe (Gemini) と answer/judge (GPT-5.4) を分離し、自己参照バイアスを排除。
- **2 Phase 設計**: Phase 1 でモデルを選定してから Phase 2 に進むことで、Phase 2 の結果が describe モデルの品質に依存するリスクを最小化。
- **自己採点の廃止**: LLM に品質スコア (1-5) をつけさせると常に 5/5/5/5 を返すことが判明。交差採点 (Gemini → GPT) も同様。fact check 方式 (present/partial/missing) に統一。
- **A1 に generic + specialized の両方を渡す**: テキスト経由で使える情報は全部渡すのが公平な比較。
- **tc04 (テキストのみ)**: 「image 直接の価値は図表にこそある」仮説を定量的に裏付けるための対照実験。

## 既知の限界

1. 全結果は 1 回の実行のみ。再実行で数 pp 揺れる可能性がある。
2. テスト画像は PIL 生成のクリーンな画像。実際の pptx/PDF の解像度・圧縮・複雑な背景での検証は未実施。
3. 日本語テキストの OCR 精度は未検証 (tc04 は英語のみ)。
4. Copilot Chat での E2E 検証は手順書を作成済みだが、実行記録は未取得。
5. LLM-as-judge (品質スコア方式) は信頼性が低い。fact check 方式のみ有効。

## 関連ファイル

| ファイル | 役割 |
|---|---|
| [INSIGHTS.md](INSIGHTS.md) | 業務インサイトまとめ |
| [test_cases.yaml](test_cases.yaml) | データの単一ソース |
| [run_evaluation.py](run_evaluation.py) | 2 Phase 自動実行パイプライン |
| [generate_report.py](generate_report.py) | HTML レポート生成 |
| [generate_test_images.py](generate_test_images.py) | PIL で 4 画像を生成 |
| [prompts/generic.md](prompts/generic.md) | ベースライン汎用プロンプト |
| [prompts/mixed_slide.md](prompts/mixed_slide.md) | tc01 用 |
| [prompts/ui_change.md](prompts/ui_change.md) | tc02 用 |
| [prompts/architecture_mermaid.md](prompts/architecture_mermaid.md) | tc03 用 |
| [prompts/text_document.md](prompts/text_document.md) | tc04 用 |
