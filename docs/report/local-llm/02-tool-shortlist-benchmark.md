# ローカル LLM ホスト選定 Benchmark（Phase 3）

**ステータス:** 完了
**Phase:** 3
**日付:** 2026-04-17
**実施者:** Claude Opus 4.7（dev rig、RTX 5090、CPU-only モード強制）

---

## 1. 結論

**勝者: LM Studio** — Phase 4 以降はこのホストで進める。

| 項目 | 内容 |
|---|---|
| **勝者** | **LM Studio**（v0.4.11 Build 1） |
| **共通モデル** | Gemma 4 E4B（Q4_K_M 相当、約 5 GB） |
| **決定理由** | 生の tok/s が 3 ホストとも 20% 以内に収まり性能差がほぼない。選定ルール「20% 以内なら運用性優先」を適用、LM Studio が Windows 運用最良 |
| **落選 1: Ollama** | tok/s は最高だが S2 wall が遅め、CPU-only 強制を Modelfile alias に頼る点が運用上の煩雑さ。商用ライセンス問題発生時の差し替え先として温存 |
| **落選 2: llama.cpp** | S3 wall が最遅、Windows サービス化に NSSM/winsw 等の手作業が最多。デバッグ／参照用ホストとして温存 |

### LM Studio の決め手（3 点）

1. **Windows 運用性が最良** — `lms` CLI、headless mode (`lms server start` / `lms daemon up`)、`--gpu off` フラグで CPU-only 強制が一発、`lms import --hard-link` で他ホストと model ファイルを zero-copy 共有可能。
2. **生の tok/s は 3 ホスト同等**（14〜16）— 全て llama.cpp ggml バックエンドを共有しているため、性能差は実質的に運用面の差。
3. **モデルロード約 4 秒で 3 ホスト中最速の cold-start**。

### Hard gate 結果（3 ホスト全て通過）

- S2 と S3 が手動再起動なしで完走 ✅
- `tools/lib/local_llm_client.py` の疎通確認 ✅
  - LM Studio は `LLM_BACKEND=local python tools/describe_image.py samples/diagram.png` で end-to-end 実測、日本語 Markdown が正しく出力されることを確認
  - Ollama / llama.cpp は benchmark harness（同じ `openai_client.py` adapter を使用）経由で間接確認

---

## 2. 結果サマリ表

3 ホスト全てが S1/S2/S3 を end-to-end で完走。Ollama の S3 のみ 4 枚中 2 枚が 120 秒のデフォルト HTTP timeout を超えたため `--timeout 300` で再実行（再実行後は全成功）。

| Tool | S1 | S2 | S3 | S1 wall (s) | S2 wall (s) | S3 wall/画像 (s) | S2 tok/s | S3 tok/s | サービス化 | Gate |
|---|---|---|---|---|---|---|---|---|---|---|
| Ollama | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 19.3 | 108.7 | 137.8 | 16.0 | 15.6 | 手動（NSSM 要） | ✅ |
| llama.cpp | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 23.2 | 94.5 | 161.9 | 14.0 | 13.3 | 手動（NSSM/winsw） | ✅ |
| LM Studio | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 0.77 ¹ | **46.8** | **81.9** | 14.8 | 14.6 | native（`lms` headless） | ✅ |

¹ LM Studio の S1 wall は他 2 ホストと比較不可。応答長の差（後述「LM Studio が速く見える理由」参照）。

### wall 時間の差は応答長の違い（重要な caveat）

S2 / S3 で LM Studio が約 1/2 の wall 時間だが、生の tok/s は 3 ホストとも 14〜16 で実質同じ（llama.cpp ggml バックエンド共有のため）。差は主にデフォルト sampling の応答長：

| シナリオ | Ollama 平均 completion_tokens | llama.cpp 平均 | LM Studio 平均 |
|---|---|---|---|
| S2 | 約 1712 | 約 1378 | 約 698 |
| S3 | 約 2186/画像 | 約 2115/画像 | 約 1210/画像 |

LM Studio のデフォルト sampling は早めに stop し、より簡潔な記述を出す。Ollama は冗長な補足説明を続ける傾向。**短い記述が ground-truth の事実を十分カバーしているかは Phase 4 で品質スコアリング**（[03-model-selection.md](03-model-selection.md)）で検証済み。

---

## 3. 評価 protocol（固定条件）

- 選定 3 ツール: `Ollama`, `llama.cpp`, `LM Studio`
- 共通モデル: `Gemma 4 E4B`（`Q4_K_M` 相当、約 5 GB）
- 入力:
  - S1: text-only
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/`（4 画像）
- 実行回数:
  - S1: 3 回
  - S2: 3 回
  - S3: 各画像 1 回（計 4 回）

dev rig 側 GPU はホストごとに個別に無効化：

- Ollama: `PARAMETER num_gpu 0` を含む Modelfile で `gemma4-e4b-bench` alias を作成
- llama.cpp: `llama-server --threads 14 -ngl 0`
- LM Studio: `lms load --gpu off`

---

## 4. ホスト別の詳細

### 4.1 Ollama

- **バージョン:** 0.20.7
- **benchmark モデル:** `gemma4-e4b-bench`（`gemma4:e4b` に `PARAMETER num_gpu 0` と `PARAMETER num_thread 14` を加えた Modelfile alias）
- **smoke 結果:** S1 smoke 24.4 秒 / 12.2 tok/s（cold）、warm-up 後 16.5 秒 / 16.3 tok/s
- **benchmark 結果:** 全シナリオ成功。S3 は 4 枚中 2 枚が 120 秒 timeout 超過、`--timeout 300` で再実行が必要。最長は 156.8 秒。
- **運用メモ:**
  - Windows サービスがデフォルトで稼働。Modelfile の `PARAMETER num_gpu 0` でサービスを停止せず CPU-only 推論を強制可能。
  - `ollama pull gemma4:e4b` 一発で取得可能（デフォルトは Q4_K_M ではなく 9.6 GB の高精度版）。
  - 再現性のある benchmark には `num_thread 14` を Modelfile に明示する必要あり（`OMP_NUM_THREADS` を無視するため）。

### 4.2 llama.cpp

- **バージョン:** b8808（winget パッケージ `ggml.llamacpp` 経由）
- **benchmark モデル:** `gemma-4-E4B-it-GGUF`（HF `unsloth/gemma-4-E4B-it-GGUF` の `gemma-4-E4B-it-Q4_K_M.gguf` + `mmproj-F16.gguf`）
- **smoke 結果:** S1 smoke 18.8 秒 / 13.5 tok/s
- **benchmark 結果:** 全シナリオ成功。S2 wall 中央値は 94.5 秒で 3 ホスト中最速。S3 は 161.9 秒/画像で最遅。
- **運用メモ:**
  - `--threads 14 -ngl 0` および `--mmproj <path>` をすべて明示する必要あり — 制御性は最高だがセットアップ項目最多。
  - Windows サービスは同梱なし。NSSM / winsw でラッパが要る。
  - winget パッケージ内のバイナリ位置は `%LOCALAPPDATA%\Microsoft\WinGet\Packages\ggml.llamacpp_*` を探す必要あり（詳細は `candidates/llama-cpp/notes.md`）。
  - Gemma 4 vision には **mmproj が必須**。これがないと S2/S3 の画像ペイロードを解釈できず失敗する。

### 4.3 LM Studio

- **バージョン:** 0.4.11 Build 1
- **benchmark モデル:** `gemma4-e4b-bench`（`lms load gemma-4-e4b-it@q4_k_m --identifier gemma4-e4b-bench --gpu off --context-length 16384` で alias 作成）
- **smoke 結果:** S1 smoke 1.23 秒 / 6.5 tok/s（応答が短い、後述）
- **benchmark 結果:** 全シナリオ成功。S2/S3 wall は他 2 ホストの約 1/2 だが、生の tok/s は近い（応答長の差）。
- **運用メモ:**
  - `lms import --hard-link` で llama.cpp 用の GGUF をコピーせず Hub エントリ登録可能 — 3 ホスト中最もクリーンな運用パス。
  - `lms server start` は headless 起動、GUI は CLI bootstrap の初回のみ必要。
  - `--gpu off` がロード時オプションで CPU-only 強制が最も明快（環境変数も Modelfile も不要）。
  - モデルロード約 4 秒で 3 ホスト中最速の cold-start。

---

## 5. 生データ

| Tool | S1 CSV | S1 MD | S2 CSV | S2 MD | S3 CSV | S3 MD |
|---|---|---|---|---|---|---|
| Ollama | [csv](../../../benchmarks/out/phase3/ollama/ollama_s1_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s1_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/ollama/ollama_s2_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s2_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/ollama/ollama_s3_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s3_gemma4-e4b-bench.md) |
| llama.cpp | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s1_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s1_gemma-4-E4B-it-GGUF.md) | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s2_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s2_gemma-4-E4B-it-GGUF.md) | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s3_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s3_gemma-4-E4B-it-GGUF.md) |
| LM Studio | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s1_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s1_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s2_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s2_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s3_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s3_gemma4-e4b-bench.md) |

---

## 6. 次のアクション

Phase 4（量子化 sweep）では **LM Studio** 上で Gemma 4 E4B の Q4_K_M / Q5_K_M / Q8_0 をロードし、`tc01..tc04` で出力品質をスコアリングして first-choice と backup の量子化を選定する。詳細は [03-model-selection.md](03-model-selection.md) を参照。
