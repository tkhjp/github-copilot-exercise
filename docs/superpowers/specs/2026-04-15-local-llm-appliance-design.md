# 本地 LLM Appliance 選定・検証 設計書

**作成日:** 2026-04-15
**依頼元:** 広瀬さん（生成AI開発支援MTG フォローアップ）
**対象リポジトリ:** `d:\Work\github-copilot-exercise`
**ステータス:** Draft — ユーザーレビュー待ち

---

## 1. 目的と範囲

### 1.1 背景

現状の因果関係：

1. **Copilot Chat の preview 機能が社内ポリシーで無効化**されており、Copilot Chat 自身は画像を認識できない
2. この制約を回避するため、先行 PoC（[image-describer-poc-verification.md](../../report/image-describer-poc-verification.md)）では Copilot Chat が `run_in_terminal` 経由で CLI を呼び出し、CLI が**外部 Gemini API** に画像を送って Markdown を得る構成を採った
3. しかし Gemini API は外部呼び出しであり、データが社外に出る — governance 上の問題が残る
4. また、社内では LLM 資源の共有に Splashtop でワークステーションを遠隔操作する運用も存在し、これも効率・安全の両面で改善余地がある

### 1.2 核心命題（Thesis）

> **社内 mini PC 上にデプロイする本地 LLM appliance** により、先行 image-describer PoC の**外部 Gemini API 呼び出しを本地エンドポイントに置き換える**ことが本作業の主目的である。副次的効果として、Splashtop ベースのワークステーション共有ワークフローも同一 appliance に集約できる。チームメンバーは該 mini PC の OpenAI 互換エンドポイントをネットワーク経由で利用し、**画像データを含め一切社外に出さない**。

### 1.3 目的

1. **本地 LLM ホスティングツールの選定**（モデルより先に決定）
2. **目標 mini PC で実用可能な vision モデルの選定**（image-describer の現行用途を支える）
3. 目標 mini PC の**性能上限**の把握（モデルサイズ／スループット／vision 処理コスト）
4. **最小プロトタイプの実装**（[tools/lib/gemini_client.py](../../../tools/lib/gemini_client.py) を本地エンドポイント向け client に差し替え、既存 3 スクリプトを本地バックエンドで疎通）
5. **調査・評測レポート**の産出（後続の調達／配備判断の根拠とする）

### 1.4 範囲内

- 主流ホスティングツールの横断調査（5〜7 種） + 短名単（2〜3 種）の深度評測
- Vision モデルの横断評測（3〜5 種、3B〜13B レンジ）
- 開発機（RTX 5090）上での全 benchmark（**CPU-only モード強制**で目標機挙動を模擬）
- 目標 mini PC 上で 1 回の検証パス
- 最小プロトタイプ: 本地エンドポイント adapter + image-describer 配線
- 調査／評測レポート

### 1.5 範囲外（Out of Scope）

- 多人並発（複数ユーザー同時呼び出し）を想定した本番設計 — **単一ユーザー／低並発**を前提
- 認証、TLS、リバースプロキシ等の本番硬化 — プロトタイプでは最小構成
- ファインチューニング、LoRA、RAG 等のモデル能力拡張
- Splashtop 代替の**UI／フロントエンド**設計（API エンドポイントのみ；利用側は引き続き Copilot Chat／スクリプト経由）
- 非 vision テキストタスクの個別評測（vision が通れば text は暗黙に通る前提）
- Windows ドメイン加入 / AD 統合等の IT 側配備詳細

**明示的に作らないもの：**
- ❌ Web UI（Open WebUI 等） — ホスティングツール自体が同梱する場合を除き、評測項目に含めない
- ❌ vLLM / TGI（GPU-only 方式） — 調査マトリクスに「除外理由付き」で記録するのみ
- ❌ Apple Silicon / macOS 関連スタック

---

## 2. アーキテクチャとデータフロー

### 2.1 目標状態アーキテクチャ（配備後）

```
[開発者 PC (複数)]                         [社内 LAN]              [目標 mini PC]
  VS Code + Copilot Chat                                           i5-14500T / 32GB / iGPU only
    │ （preview 無効のため画像を直接扱えない）
    │ run_in_terminal で CLI を呼ぶ
    ▼
  tools/describe_image.py   ─── HTTP ─────────────────────▶     ┌─────────────────────┐
  tools/describe_pptx.py    (OpenAI 互換 API)                    │ LLM Host            │
  .env:                                                          │ (Ollama/llama.cpp/  │
    LLM_BACKEND=local                                            │  LM Studio のどれか)│
    LLM_BASE_URL=http://mini-pc:port/v1                          │ + Vision Model      │
                                                                  │ (Qwen2.5-VL 7B 等)  │
                                                                  └─────────────────────┘
                                                                   Windows Service 化
                                                                   LAN ポート公開
```

**先行 PoC からの差分：**

- 先行 image-describer PoC との違いは**本 appliance への呼び出し先を差し替えるだけ**（`.env` の `LLM_BACKEND` で `gemini` → `local` に切替）
- Copilot Chat → CLI → 画像処理 API という全体構造は変えない
- 置き換え対象は「Gemini API 呼び出し」のみ

**設計原則：**

- 対外インタフェースは **OpenAI 互換 HTTP エンドポイント 1 本**のみ（本方案の契約面）
- クライアント側（image-describer スクリプト）は標準 OpenAI SDK／HTTP のみに依存し、**具体ツールから解耦**
- ツール切替（Ollama → llama.cpp → LM Studio）はクライアントコード非改修、`.env` の `LLM_BASE_URL` / `LLM_MODEL` のみ変更
- **副次効果（非主目的）**: Splashtop を使っていたワークステーション共有用途も、同じ appliance に集約可能。「他人のワークステーションに remote desktop で入って LLM を使う」 → 「全員がこの mini PC の API を叩く」に統一可能。ただし本作業の成功基準には含まない。

### 2.2 PoC 段階アーキテクチャ（開発機上の評測環境）

```
[開発機 (RTX 5090 PC)]
 ├─ benchmarks/
 │    harness.py         ← 統一 benchmark ドライバ
 │    scenarios/         ← 標準化 workload (text-only / vision-single / vision-pptx-batch)
 │    metrics.py         ← 遅延／スループット／リソース採取
 │
 ├─ candidates/          ← 候補ツール 1 つにつき 1 サブディレクトリ + 起動スクリプト
 │    ollama/
 │    llama-cpp/
 │    lm-studio/
 │
 ├─ adapter/
 │    openai_client.py   ← 統一 OpenAI 互換 client
 │                        （= 後続プロトタイプのクライアントコードそのもの）
 │
 └─ [CPU-only モード強制]  ← 環境変数／ツール flag で CUDA 無効化、目標機を模擬
```

**分割理由：**

- `benchmarks/` は**ツール非依存**の測定層 — 同一 scenario を複数候補で走らせて結果を比較可能にする
- `candidates/` は各ツールを独立に起動／停止でき、相互汚染しない
- `adapter/` は**唯一の呼び出し入口** — 評測期に書くコードが Phase 5 のプロトタイプでそのまま再利用される

### 2.3 データフロー（Vision workload 1 回呼び出し）

```
1. describe_image.py がローカル画像読み込み（既存ロジック不変）
2. adapter/openai_client.py:
   - 画像 → base64 data URL
   - OpenAI 形式の multimodal messages を構築（image + prompt）
   - POST LLM_BASE_URL/v1/chat/completions
3. 候補ツール側:
   - 画像デコード → vision encoder → projector → LLM → Markdown 生成
4. adapter が response 受信 → content 抽出 → stdout 返却
5. benchmarks/metrics.py が並行して記録: TTFT、総時間、入力 tokens、出力 tokens、RSS peak
```

### 2.4 インタフェース契約（評測とプロトタイプ共通）

| 項目 | 仕様 |
|------|------|
| 入力形式 | OpenAI Chat Completions v1 形式（`image_url` を含む multimodal） |
| 出力形式 | 標準 chat completion、`content` フィールドに Markdown |
| 環境変数 `LLM_BASE_URL` | 例: `http://127.0.0.1:11434/v1`（ツールごとに異なる） |
| 環境変数 `LLM_MODEL` | モデル名（ツール／registry により異なる） |
| 環境変数 `LLM_API_KEY` | 本地多くのツールでは無視される placeholder |
| 環境変数 `LLM_BACKEND` | `gemini` \| `local` — 既存 Gemini 経路とのスイッチ |

この契約面が**プロトタイプにおける唯一の差替え箇所**。最終段階で [tools/lib/gemini_client.py](../../../tools/lib/gemini_client.py) を残したまま新規 `tools/lib/local_llm_client.py` を追加し、バックエンド切替を `.env` で行う。

---

## 3. 作業フェーズ（Phases）

7 フェーズを順次実行。各フェーズに**明示的な退出条件**を設け、通過しなければ次に進まない。

### Phase 0 — 立項とベースライン（0.5 日）

**作業内容：**

- 本設計書を確定しコミット
- 開発機での CPU-only 模擬設定を固定（環境変数スクリプト: `CUDA_VISIBLE_DEVICES=""`、`OMP_NUM_THREADS` を目標機 6P+8E 相当に近似調整）
- 標準化テスト素材の準備: 既存 [samples/](../../../samples/) の `diagram.png` / `sample.pptx` を流用、代表的画像 3〜5 枚を追加（フロー図、表スクリーンショット、UI キャプチャ、日本語スライド、手書きメモ）

**退出条件：** 設計書コミット済み; CPU-only モードスクリプトを走らせて `nvidia-smi` がモデル実行中に 0% 使用率であることを確認。

### Phase 1 — ツール調査マトリクス（1 日）

**作業内容：**

- 候補 5〜7 種のツールについて桌面調査を実施し、最低以下の列を含むマトリクス表を作成：
  - 対応プラットフォーム（Windows native / WSL / Linux-only）
  - CPU 推論品質（native / 第三者 / 非対応）
  - Intel AMX / iGPU 加速サポート
  - 対応 vision モデルファミリ
  - OpenAI 互換 API（native / プロキシ要 / 非対応）
  - Windows サービス化難度
  - ライセンス／商用可否
  - 活発度（直近 release、issue 応答）
- 候補集合: **Ollama、llama.cpp、LM Studio、IPEX-LLM、OpenVINO-GenAI、text-generation-webui、vLLM（除外項として記録）**

**退出条件：** マトリクス表が完成し、**短名単 2〜3 種が明文で確定、除外されたツールは各々除外理由を 1 行記載**。

### Phase 2 — Benchmark harness 構築（1 日）

**作業内容：**

- `benchmarks/harness.py` を作成: 実行ドライバ、メトリクス採取、CSV + Markdown 出力
- `adapter/openai_client.py` を作成: 統一 OpenAI 互換 client（= Phase 5 のプロトタイプ client 本体）
- 3 つの標準 workload scenario を定義:
  - **S1: text-only** — 短対話、レイテンシ／スループットのベースライン
  - **S2: vision-single** — 単一画像 describe、vision encoder コストの把握
  - **S3: vision-pptx-batch** — 1 pptx 分の N 枚連続処理、定常スループット／メモリリーク確認
- メトリクス: TTFT（time-to-first-token）、tok/s、end-to-end 時間、RSS peak、CPU%、リクエスト失敗率

**退出条件：** harness が任意 1 候補上で S1/S2/S3 を通し、レポートファイルが生成できる。

### Phase 3 — 短名単深度評測（2〜3 日）

**作業内容：**

- 短名単の各ツールに対して順次:
  1. インストール／起動（Windows native 経路優先、WSL は代替、両方記録）
  2. **共通 vision モデル**（基準: Qwen2.5-VL 7B Q4_K_M または等価）をロード
  3. CPU-only モードで S1/S2/S3 実行
  4. 記録項目: インストール摩擦、安定性、ドキュメント品質、Windows サービス化経路（NSSM / winsw / ツール同梱）
- 横断比較表を出力: 性能 + 運用 + API の 3 軸

**退出条件：** 短名単の全ツールで完全な benchmark データ取得済み; 勝者ツールが**書面で選定**され、否決可能な粒度で理由が明示されている。

### Phase 4 — モデル横断評測（勝者ツール上）（2 日）

**作業内容：**

- Phase 3 の勝者ツール上で vision モデル 3〜5 種を横断評測:
  - **候補池**: Qwen2.5-VL（3B / 7B）、MiniCPM-V 2.6（8B）、Llama 3.2 Vision（11B）、InternVL2.5（4B / 8B）、Gemma 3（vision variant があれば）
  - **量子化レベル**: Q4_K_M を優先、メモリ余裕があれば Q5 / Q6 も試行
- 各モデルで S2 / S3 + **品質評価**を実施: image-describer の実用例（`diagram.png` 等）で出力 Markdown と Gemini ベースラインの差分を比較
- 品質評価軸: OCR 正確率、構造理解、色／レイアウト記述、幻覚率
- 出力: 速度-品質象限図 + 推奨

**退出条件：** **第一候補モデル** 1 種 + **代替候補モデル** 1 種（異なるサイズティア）が書面で確定。

### Phase 5 — 最小プロトタイプ（1 日）

**作業内容：**

- 新規 `tools/lib/local_llm_client.py` を作成 — Phase 2 の adapter をベースに、[tools/lib/gemini_client.py](../../../tools/lib/gemini_client.py) と同一インタフェース（`describe_image` / `describe_pptx_images` 等）を公開
- `gemini_client.py` は変更せず保持したまま、`.env` に `LLM_BACKEND=gemini|local` スイッチを追加
- [tools/describe_image.py](../../../tools/describe_image.py) と [tools/describe_pptx.py](../../../tools/describe_pptx.py) をスイッチに応じて client を選択するよう改修
- End-to-end 検証: 既存 3 コマンド（`describe_image` / `describe_pptx` / `describe_docx`）が `LLM_BACKEND=local` で全て exit 0 かつ妥当な Markdown を出力

**退出条件：** 3 コマンド全て疎通; `LLM_BACKEND=gemini` のフォールバックでも動作（現状を壊さない）。

### Phase 6 — 目標機（mini PC）検証（0.5 日）

**作業内容：**

- 目標 mini PC 上に勝者ツール + 第一候補モデルをインストール
- S2 + S3 を 1 回実行し、開発機 CPU-only モードの結果と比較
- 開発機から mini PC エンドポイントを叩く end-to-end `describe_image` を 1 回実行
- 差分が大きい場合（> 2×）: 差分の由来を記録（AMX サポート、iGPU 加速、メモリ帯域）し、Phase 3/4 の結論を**修正する**（無理押ししない）

**退出条件：** 目標機上の S3 スループットがレポートに記録され、「第一候補モデルは目標機上で **使用可能／限界的／不可** の 3 択で結論」が確定。

### Phase 7 — レポートと収束（1 日）

**作業内容：**

- 全データを統合し `docs/report/local-llm-selection-report.md` を作成、以下の構造:
  1. Executive summary（1 ページで「何を選ぶか／なぜか／何が走るか」）
  2. 背景と命題（Copilot preview 無効化 → Gemini 経由化 → governance 問題 → 本地化検証; 副次効果として Splashtop 統合可能性）
  3. ツールマトリクス + 短名単 + 除外理由
  4. Benchmark 方法とデータ
  5. モデル横断評測と選定
  6. 目標機検証結果
  7. プロトタイプ説明と使用方法
  8. リスクと制限
  9. 次ステップ提言（調達／硬化／拡張）
- 全コード、benchmark データ、レポートをコミット

**退出条件：** レポートをコミット済み; 関係者が読んで判断可能。

### 総工数見積もり

**9〜10 営業日**（buffer 込み）; Phase 1 の桌面調査を一部削って短名単を直接評測に進める場合は **7 日**まで圧縮可能。

---

## 4. 交付物、リスク、成功基準

### 4.1 交付物一覧

| # | 交付物 | 位置 | Phase |
|---|--------|------|-------|
| D1 | Design doc（本文書） | `docs/superpowers/specs/2026-04-15-local-llm-appliance-design.md` | Phase 0 |
| D2 | ツール調査マトリクス | `docs/report/local-llm/01-tool-matrix.md` | Phase 1 |
| D3 | Benchmark harness + adapter コード | `benchmarks/`、`adapter/` | Phase 2 |
| D4 | 短名単深度評測データ + 結論 | `docs/report/local-llm/02-tool-shortlist-benchmark.md` + CSV | Phase 3 |
| D5 | モデル横断評測データ + 選定結論 | `docs/report/local-llm/03-model-selection.md` + CSV | Phase 4 |
| D6 | 本地 LLM client コード | `tools/lib/local_llm_client.py` + `.env.example` 更新 | Phase 5 |
| D7 | 目標機検証データ | `docs/report/local-llm/04-target-validation.md` | Phase 6 |
| D8 | 最終統合レポート | `docs/report/local-llm-selection-report.md` | Phase 7 |

### 4.2 リスクと緩和策

| # | リスク | 確率 | 影響 | 緩和策 |
|---|--------|------|------|--------|
| R1 | **開発機 CPU-only モードが目標機を完全に模擬できない** — Intel AMX の 14500T 上での加速比は別発行版 CPU と異なり、メモリ帯域も差分大 | 高 | 中 | Phase 6 で実測を 1 回; 結論上「開発機 CPU モード観測値」と「目標機実測値」を明確に区別; 開発機データのみで絶対的な約束をしない |
| R2 | **目標機アクセスが遅延する** — 現状 Q4 の回答で「D に近い A、ほぼ確定」 | 中 | 高 | Phase 6 を最後に置き阻塞を最小化; Phase 5 末時点で未確定なら、Phase 6 を「申請提出 + 報告の残り部分完成 + 検証は後続タスクとして明記」に切替 |
| R3 | **目標機性能が 7B vision モデルの実用速度に不足** | 中 | 高 | Phase 4 で小モデル（3B / 4B）を事前準備; レポートでは「速度 vs 品質」のトレードオフ区間を明示; 3B でも不足なら結論で**素直にハードウェア引き上げまたは CPU テキスト + 外部 vision のハイブリッド案**を推奨 |
| R4 | **Windows native でのツールインストール摩擦超過**（特に llama.cpp 自コンパイル経験があってもサービス化は別; IPEX-LLM Windows 安定性） | 中 | 中 | Phase 1 調査時点で記録; Phase 3 では各ツール**固定 0.5 日予算**、超過時は「除外 + 理由記録」に降格 |
| R5 | **Qwen2.5-VL の Ollama / llama.cpp 公式サポートが追い付かない** | 中 | 中 | Phase 1 で短名単ツールの**候補モデル対応状況**を事前検証（最低限ロード可能／vision 推論可能であること）; サポート不十分なモデルは候補池から事前除外 |
| R6 | **品質評価に主観バイアス** — 「出力の良し悪し」に定量基準がない | 高 | 中 | Gemini 出力を**参照ベースライン**（正解ではない）とし、差分記述を基本に、点数化はしない; 各テスト画像に対し 3〜5 個の「必ず正しく抽出されるべき事実」を定義し、これを hard check point とする |
| R7 | **範囲蔓延** — 評測中に「ついでに Open WebUI も」等の衝動 | 中 | 低 | 1 節で明示的 out-of-scope を設置済み; 評測中に類似衝動が出たら「後続提言」に記録、本 Phase には入れない |
| R8 | **並発需求の後期突発** — 「複数人同時に使えないの?」 | 低 | 高 | 単一ユーザー前提は範囲説明書で明示済み; 真に必要になれば**独立した次フェーズ**として扱い、本回結論に影響させない |

### 4.3 成功基準

**ハード（全て達成必須）:**

- ✅ ツールマトリクス + 短名単理由が書面化され、review で否決可能な粒度である
- ✅ 短名単ツール 2 種以上が S1/S2/S3 完全 benchmark を通過
- ✅ 第一候補 vision モデル 1 種 + 代替候補 1 種（異なるサイズティア）が書面で確定
- ✅ 最小プロトタイプが `LLM_BACKEND=local` で [tools/describe_image.py](../../../tools/describe_image.py)、[tools/describe_pptx.py](../../../tools/describe_pptx.py)、[tools/describe_docx.py](../../../tools/describe_docx.py) の 3 コマンドを通過
- ✅ `LLM_BACKEND=gemini` のフォールバックでも正常動作（現状を壊さない）
- ✅ 目標 mini PC 上で S2/S3 を最低 1 回実行し結果をレポートに記録
- ✅ 最終レポートが「調達するか／配備するか」の判断を支えられる水準

**ソフト（達成目標、未達でも理由と共に受容可能）:**

- ◯ 第一候補モデルが目標機上で「**使用可能**」水準に到達 — S2 TTFT ≤ 5s、tok/s ≥ 5
- ◯ 第一候補モデルの品質が hard check point において**≥ 80% 命中**（Gemini ベースライン比）
- ◯ 総工数 ≤ 10 営業日

### 4.4 再度の非目標明示

本作業は以下を**約束しない**:

- 複数ユーザー並発配備方案
- 生産レベルの認証／TLS／監査
- Web UI フロントエンド
- Splashtop 淘汰の変更管理／ユーザー教育
- モデル能力拡張（RAG、ファインチューニング、agent workflow）
- 最終調達決定（本作業の産出は判断材料であり判断そのものではない）

---

## 5. 参照ファイル

| ファイル | 役割 |
|---------|------|
| [tools/lib/gemini_client.py](../../../tools/lib/gemini_client.py) | 現行 Gemini API client（保持、スイッチ経由で共存） |
| [tools/describe_image.py](../../../tools/describe_image.py) | 単一画像 CLI（Phase 5 で改修） |
| [tools/describe_pptx.py](../../../tools/describe_pptx.py) | pptx CLI（Phase 5 で改修） |
| [tools/describe_docx.py](../../../tools/describe_docx.py) | docx CLI（Phase 5 で改修） |
| [docs/report/image-describer-poc-verification.md](../../report/image-describer-poc-verification.md) | 先行 PoC 検証ガイド（本作業の前身） |
| [docs/deep-research-report (2).md](../../deep-research-report%20(2).md) | Copilot Hooks 調査レポート（関連文脈） |
