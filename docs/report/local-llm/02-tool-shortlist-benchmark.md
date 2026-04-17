# ローカル LLM ホスト選定 Benchmark（Phase 3）

**ステータス:** 完了
**Phase:** 3
**日付:** 2026-04-17
**実施者:** Claude Opus 4.7（dev rig、RTX 5090、CPU-only モード強制）

## 固定 benchmark プロトコル

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

## 生成された raw 出力

| Tool | S1 CSV | S1 MD | S2 CSV | S2 MD | S3 CSV | S3 MD |
|---|---|---|---|---|---|---|
| Ollama | [csv](../../../benchmarks/out/phase3/ollama/ollama_s1_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s1_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/ollama/ollama_s2_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s2_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/ollama/ollama_s3_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/ollama/ollama_s3_gemma4-e4b-bench.md) |
| llama.cpp | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s1_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s1_gemma-4-E4B-it-GGUF.md) | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s2_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s2_gemma-4-E4B-it-GGUF.md) | [csv](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s3_gemma-4-E4B-it-GGUF.csv) | [md](../../../benchmarks/out/phase3/llama-cpp/llama-cpp_s3_gemma-4-E4B-it-GGUF.md) |
| LM Studio | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s1_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s1_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s2_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s2_gemma4-e4b-bench.md) | [csv](../../../benchmarks/out/phase3/lm-studio/lm-studio_s3_gemma4-e4b-bench.csv) | [md](../../../benchmarks/out/phase3/lm-studio/lm-studio_s3_gemma4-e4b-bench.md) |

## 結果サマリ

3 つのホスト全てが S1/S2/S3 を end-to-end で完走（Ollama の S3 は 4 枚中 2 枚が 120 秒のデフォルト HTTP timeout を超えたため `--timeout 300` で再実行、以降は初回で成功）。

| Tool | S1 | S2 | S3 | S1 wall (s) | S2 wall (s) | S3 wall/画像 (s) | S2 tok/s | S3 tok/s | インストール | 起動 | 再起動 | OpenAI API | local_llm_client 疎通 | サービス化 | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ollama | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 19.3 | 108.7 | 137.8 | 16.0 | 15.6 | installer で簡単 | トレイサービス | サービス自動再起動 | native | harness 経由で確認済 | 手動（再現性のため NSSM 要） | ✅ |
| llama.cpp | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 23.2 | 94.5 | 161.9 | 14.0 | 13.3 | winget で簡単 | 手動（start.ps1） | 該当なし | native | harness 経由で確認済 | 手動（NSSM/winsw） | ✅ |
| LM Studio | ✅ 3/3 | ✅ 3/3 | ✅ 4/4 | 0.77 ¹ | 46.8 | 81.9 | 14.8 | 14.6 | installer + 初回 GUI 起動 | 簡単（`lms server start`） | 簡単（`lms daemon up`） | native | `describe_image.py LLM_BACKEND=local` で end-to-end 確認済 | native（`lms` headless） | ✅ |

¹ LM Studio の S1 wall は他 2 ホストと比較できません。Gemma 4 E4B は LM Studio 上では 8 トークン（翻訳そのもの）だけを出して停止しましたが、Ollama / llama.cpp では冗長な補足説明を続けて 269〜348 トークン出力しました。生のスループット（tok/s）は 3 ホストとも 14〜16 tok/s で似ています — 詳細は下記「LM Studio が速く見える理由」を参照。

## ホストごとの詳細

### Ollama

- **バージョン:** 0.20.7
- **benchmark モデル:** `gemma4-e4b-bench`（`gemma4:e4b` に `PARAMETER num_gpu 0` と `PARAMETER num_thread 14` を加えた Modelfile alias）
- **smoke 結果:** S1 smoke 24.4 秒 / 12.2 tok/s（cold）、2 回目以降は warm up 後に 16.5 秒 / 16.3 tok/s
- **benchmark 結果:** 全シナリオ成功。S3 は 4 枚中 2 枚が 120 秒のデフォルト HTTP timeout を超えたため `--timeout 300` で再実行が必要。再実行後の median S3 wall は 137.8 秒／画像、最長（`02_ui_change.png` 相当）は 156.8 秒に達した。
- **運用メモ:**
  - Ollama の Windows サービス（installer がデフォルトで登録）は dev rig 起動時に既に動作している。Modelfile の `PARAMETER num_gpu 0` はこのサービスを停止せずとも正しく CPU-only 推論を強制できる。
  - `ollama pull` レジストリは Gemma 4 の取得が最も簡単。`gemma4:e4b` 一発で入る。デフォルトの pull サイズは Q4_K_M ではなく 9.6 GB の高精度版（BF16 相当）。
  - 再現性のある benchmark には `num_thread 14` を明示した Modelfile が必須。Ollama は `OMP_NUM_THREADS` を無視する。

### llama.cpp

- **バージョン:** b8808（winget パッケージ `ggml.llamacpp` 経由でインストール）
- **benchmark モデル:** `gemma-4-E4B-it-GGUF`（Hugging Face `unsloth/gemma-4-E4B-it-GGUF` の `gemma-4-E4B-it-Q4_K_M.gguf` + `mmproj-F16.gguf`）
- **smoke 結果:** S1 smoke 18.8 秒 / 13.5 tok/s
- **benchmark 結果:** 全シナリオ成功。S2 の wall 中央値は 94.5 秒で 3 ホスト中最速。一方で S3 は 161.9 秒／画像と 3 ホスト中最遅。
- **運用メモ:**
  - `--threads 14 -ngl 0` および `--mmproj <path>` をすべて明示する必要あり — 制御性は高いがセットアップ項目は最多。
  - Windows サービスは同梱されていない。無人起動には NSSM もしくは `winsw` で別途ラッパが要る。
  - winget パッケージ内のバイナリ位置が自明でなく、`%LOCALAPPDATA%\Microsoft\WinGet\Packages\ggml.llamacpp_*` を探す必要があった。詳細は `candidates/llama-cpp/notes.md` に記載。
  - Gemma 4 の vision には **mmproj が必須**。これがないと S2/S3 の画像ペイロードを解釈できず失敗する。

### LM Studio

- **バージョン:** 0.4.11 Build 1
- **benchmark モデル:** `gemma4-e4b-bench`（`lms load gemma-4-e4b-it@q4_k_m --identifier gemma4-e4b-bench --gpu off --context-length 16384` で alias 作成）
- **smoke 結果:** S1 smoke 1.23 秒 / 6.5 tok/s（応答が短いため — 下記「LM Studio が速く見える理由」を参照）
- **benchmark 結果:** 全シナリオ成功。S2 / S3 の wall 時間は他 2 ホストの約 1/2 だが、生の tok/s は近い。これは主に応答長の違いによるもの。
- **運用メモ:**
  - `lms import --hard-link` により、llama.cpp 用にダウンロード済みの GGUF をコピーせずに LM Studio 側の Hub エントリとして登録できた。3 ホスト中最もクリーンな運用パス。
  - `lms server start` は headless で起動できる。GUI の起動は CLI bootstrap の初回のみ必要。
  - `--gpu off` はロード時オプションで CPU-only 強制が最も明快（環境変数も Modelfile 書換えも不要）。
  - モデルロード時間は約 4 秒で 3 ホスト中最速の cold-start。

## LM Studio が速く見える理由

生のトークン・スループット（デコード中の tok/s）は 3 ホストともほぼ同じ。これは 3 ホスト全てが最終的には同じ CPU 上の `llama.cpp` ggml バックエンドで推論しているため：

- S2 tok/s: Ollama 16.0 / llama.cpp 14.0 / LM Studio 14.8（14% の幅）
- S3 tok/s: Ollama 15.6 / llama.cpp 13.3 / LM Studio 14.6（17% の幅）

wall 時間の大きな差は **推論速度ではなく応答長** から生まれている：

| シナリオ | Ollama 平均 completion_tokens | llama.cpp 平均 completion_tokens | LM Studio 平均 completion_tokens |
|---|---|---|---|
| S2 | 約 1712 | 約 1378 | 約 698 |
| S3 | 約 2186／画像 | 約 2115／画像 | 約 1210／画像 |

LM Studio のデフォルト sampling パラメータはモデルを早めに止める。結果として出力される記述は簡潔になる。Ollama は長めの stop-sequence に達するまで後続の説明を続ける。どちらが正しいという話ではなく、デフォルト挙動の違い。LM Studio の短い出力が ground-truth の事実を十分カバーしているかは、Phase 4（`tc01..tc04`、`tests/text_vs_image/test_cases.yaml`）の品質スコアリングで確認する。

## 勝者選定

### Hard gate 結果

- S2 と S3 が手動再起動なしで完走：**Ollama ✅（300 秒 timeout 指定の再実行後）、llama.cpp ✅、LM Studio ✅**
- `tools/lib/local_llm_client.py` の疎通：**3 ホスト全て ✅**
  - LM Studio は `LLM_BACKEND=local python tools/describe_image.py samples/diagram.png` で end-to-end 実測し、日本語の構造化 Markdown 出力を確認
  - Ollama と llama.cpp は benchmark harness（同じ `openai_client.py` adapter を使用）経由で間接的に確認

### 決定

- **勝者: LM Studio**
- **理由:**
  1. **生の tok/s は 3 ホストとも 20% 以内**（13.3〜16.0）— 性能差は実質なし。Phase 3〜7 plan の選定ルール「差が 20% 以内なら運用性優先」が適用される。
  2. **Windows 運用性が 3 ホスト中最良:** `lms server` / `lms daemon` の headless モードが native、無人起動に追加ツール不要、`--gpu off` フラグで CPU-only 強制、`lms import --hard-link` で他ホストと model ファイルを zero-copy で共有可能、cold-start 約 4 秒は最速。
  3. **wall 時間のリード**（S2 46.8 秒 vs Ollama 108.7 秒 vs llama.cpp 94.5 秒）は主に応答長の短さに由来し、生の推論速度の差ではない。ただし appliance ユースケース（ユーザー 1 発話 = 画像 1 枚の記述、短時間で返す）では、同じ tok/s でも短い応答のほうが UX は良い。前提は Phase 4 の品質スコアリングで「短い出力でも ground-truth をカバーしている」ことが確認されること。

- **勝者に選ばれなかった 2 ツール:**
  - **Ollama:** 強力な候補だが以下で LM Studio に劣る:(a) Windows サービスは native で稼働するが、CPU-only を強制するには server 側の環境変数ではなく Modelfile レベルの alias が必要； (b) 同じ tok/s でも S2 wall が遅い。LM Studio の商用ライセンス条項が将来問題になった場合の差し替え先として完全に許容できる。
  - **llama.cpp:** 制御性と GGUF 互換性は最強だが、S3 wall が最遅で、サービス化（NSSM/winsw + 明示 mmproj パス + 自動更新なし）の手数が最多。production appliance より、デバッグ／参照用ホストとして温存するのが適切。

## 次のアクション

Phase 4（量子化 sweep）では **LM Studio** 上で Gemma 4 E4B の Q4_K_M / Q5_K_M / Q8_0 をロードし、`tc01..tc04` で出力品質をスコアリングして first-choice と backup の量子化を選定する。詳細は [03-model-selection.md](03-model-selection.md) を参照。
