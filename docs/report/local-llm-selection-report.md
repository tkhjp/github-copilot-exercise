# ローカル LLM 選定レポート（最終統合）

**ステータス:** 統合待ち（Phase 6 完了後に着手）
**日付:** _(記入)_
**作成者:** _(記入)_

> このレポートは Phase 1〜6 の調査結果を意思決定者向けに集約したもの。**§1 Executive summary だけで採否判断ができる**ように書き、詳細は §2 以降の各 phase 別セクション（および各 phase の個別レポートへのリンク）で補強する。

---

## 1. Executive summary（採否判断材料）

### 結論（1 段）

_(記入: 1〜2 段で「採用するか／どう配備するか／次にすべきか」を一目で読めるように)_

### 推奨スタック

| 項目 | 値 |
|---|---|
| **採用ホスト** | _(記入: 例「LM Studio v0.4.11 Build 1（Windows native、headless `lms` mode）」)_ |
| **第一候補モデル** | _(記入: 例「Gemma 4 E4B Q4_K_M」)_ |
| **backup モデル** | _(記入: 例「Gemma 4 E4B Q5_K_M」)_ |
| **配備対象** | 社内機房 mini PC（i5-14500T / 32 GB / iGPU only） |
| **アクセス経路** | Splashtop で隔離端末にログイン、端末内で完結 |
| **配備推奨度** | _(記入: 採用推奨 / 限定採用 / 見送り の 3 択 + 1 行理由)_ |

### 主要な発見（3〜5 件、ハイライト）

- _(記入)_
- _(記入)_
- _(記入)_

### 次に必要なアクション

- _(記入: 例「セキュリティレビュー」「mini PC 調達」「運用手順整備」など)_

---

## 2. 背景と目的

参照: [00-overview §1](./local-llm/00-overview.md#1-プロジェクトの目的)

- Copilot Chat の画像入力制約: _(記入)_
- Governance 要件（データを社外に出さない）: _(記入)_
- 隔離端末上で LLM を serve する構成を評価する理由: _(記入)_

---

## 3. ツール調査サマリ

参照: [01-tool-matrix](./local-llm/01-tool-matrix.md)

- 選定 3 ツール: _(記入)_
- 除外 4 ツールと除外理由（要約）: _(記入)_

---

## 4. ホスト選定 benchmark 結果

参照: [02-tool-shortlist-benchmark](./local-llm/02-tool-shortlist-benchmark.md)

- 勝者ホスト: _(記入)_
- 勝者の決め手: _(記入)_
- 落選ホストとその理由（要約）: _(記入)_

---

## 5. 量子化 sweep 結果

参照: [03-model-selection](./local-llm/03-model-selection.md)

- 第一候補量子化: _(記入)_
- backup 量子化: _(記入)_
- 速度／品質のトレードオフ要約: _(記入)_

---

## 6. Target 機検証結果

参照: [04-target-validation](./local-llm/04-target-validation.md)

- 検証環境: _(記入)_
- dev rig vs mini PC のギャップ: _(記入)_
- 配備可否の判定: _(記入: 使用可能 / 限界的 / 不可)_

---

## 7. ローカルバックエンドプロトタイプの使い方

```bash
# 既存（Gemini API 経由、デフォルト）
python tools/describe_image.py samples/diagram.png

# 本地 LLM（LM Studio + Gemma 4 E4B）に切替
LLM_BACKEND=local LLM_BASE_URL=http://127.0.0.1:1234/v1 LLM_MODEL=gemma4-e4b-bench \
  python tools/describe_image.py samples/diagram.png
```

- 環境変数の意味と設定方法: _(記入)_
- 既存 Gemini path との切替方法: _(記入)_
- pptx / docx 用の同等コマンド: _(記入)_

---

## 8. リスクと次ステップ

- 認証 / TLS の本番硬化: _(記入)_
- Windows サービス登録の方法: _(記入)_
- モデルライフサイクルとアップグレード経路: _(記入)_
- 推奨されるフォローアップ作業: _(記入)_
