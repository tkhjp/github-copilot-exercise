# ローカル LLM ホスティングツール 調査マトリクス

**調査日:** 2026-04-16
**調査者:** Codex

---

## 1. 調査結論

**Phase 3 で実測評価する 3 ツール（選定）:**

| ツール | 選定の理由 |
|---|---|
| **Ollama** | OpenAI 互換 API と Windows インストーラが最もシンプル。baseline appliance に最適 |
| **llama.cpp** | 最も低レベルで閉域運用しやすい。GGUF 互換性と Intel 最適化余地の参照実装 |
| **LM Studio** | Windows 運用性が最良。`lms` headless / サービス化の摩擦が最小 |

**除外した 4 ツール:**

| ツール | 除外の理由 |
|---|---|
| vLLM | Linux/GPU 高並発サーバ向け、Windows single-user appliance と運用軸が不一致 |
| OpenVINO-GenAI | 独立 OpenAI 互換 HTTP host ではなく「推論ライブラリ」に近い |
| IPEX-LLM | Intel 向け acceleration / integration layer。単独ホストとしては境界が曖昧 |
| text-generation-webui | Web UI / extension の自由度が高すぎ、Windows サービス化のコスト大 |

**判断基準の要約:**

本プロジェクトは「社内機房の Windows PC に置き、遠隔デスクトップ（VM / Splashtop）経由で利用する single-user 〜 small-team appliance」を前提にしている。したがって選定軸は次の 3 点に絞った。

1. **Windows native で OpenAI 互換 HTTP を素直に出せること**
2. **閉域運用のしやすさ**（`localhost` bind、オフライン運転、アウトバウンド通信の明確さ）
3. **サービス化と現場運用の摩擦が小さいこと**（installer / headless CLI / 再起動）

純粋な Intel 最適化性能では OpenVINO-GenAI / IPEX-LLM が有力だが、今回の軸では「ホスト製品」として置きやすい 3 ツールを優先し、両者は必要に応じて Phase 3 の結果を見て再検討する。

---

## 2. 運用前提（社内機房 / 遠隔デスクトップ）

- 対象 PC は社内機房に設置された開発用 Windows PC。利用者は VM / Splashtop 等の遠隔デスクトップ経由でログインして使う。
- Primary use case は「社内 LAN に API を広く公開する shared inference server」ではなく、「遠隔ログインした利用者が当該 PC 内で使う single-user 〜 small-team appliance」。
- したがって LAN 公開の容易さより、`localhost` bind、オフライン運転、アウトバウンド通信先の明確さ、Windows Firewall / GPO での閉域化のしやすさを重く見る。
- 初期構成では LLM endpoint を社内 LAN へ公開しなくても主要ユースケースは満たせる。API 公開は後段要件として扱う。

この前提で重視する追加評価軸：

| 観点 | 何を見るか | 重み |
|------|-----------|------|
| 既定 bind | `127.0.0.1` / `localhost` が既定か | 高 |
| API 認証 | product 自身で token / API key を持てるか | 高 |
| オフライン運転 | モデル配布後は外部通信なしで推論できるか | 高 |
| アウトバウンド依存 | モデル検索 / 更新 / クラウド連携 / MCP などの外部通信面が限定的か | 高 |
| Windows 閉域化 | 固定 port / service / firewall rule / proxy 配下に載せやすいか | 中〜高 |

なお、Windows Defender Firewall は既定で outbound を許可する（[Microsoft 公式](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure)）。「推論時は外部通信なし」を担保するには、ツール選定とは別に outbound allowlist / block rule を入れる前提で評価する必要がある。

---

## 3. 選定 3 ツールの詳細

### 3.1 Ollama

- **バージョン:** 0.20.7
- **公式:** [ollama.com](https://ollama.com)
- **選定理由:** OpenAI 互換 API と Windows インストーラが最も素直。Phase 5 の本地 endpoint 置換先として baseline appliance を作りやすい。
- **ネットワーク / 安全:**
  - `127.0.0.1:11434` 既定 bind、ローカル API は認証不要。
  - `cloud model` / `ollama.com` 連携を使うと外部通信が発生するため、機房 PC では `disable_ollama_cloud` もしくは `OLLAMA_NO_CLOUD=1` で cloud 機能を無効化して評価するのが安全。
- **総合所見:** baseline として有力。運用時は **local-only + cloud 無効化** を初期値とする。
- **公式ドキュメント:** [API Introduction](https://docs.ollama.com/api/introduction), [Authentication](https://docs.ollama.com/api/authentication), [FAQ](https://docs.ollama.com/faq)

### 3.2 llama.cpp

- **バージョン:** b8808
- **公式:** [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- **選定理由:** GGUF / multimodal の最小コアで制御性が高い。Intel SYCL / oneMKL を含む最適化余地が大きく、性能上限と互換性の参照実装として外せない。
- **ネットワーク / 安全:**
  - `llama-server` は `--host` 既定 `127.0.0.1`、`--port` 既定 `8080`。
  - `--api-key`、`--ssl-key-file`、`--ssl-cert-file`、`--offline` を備え、露出制御が最も明快。
  - experimental の MCP proxy / agent tools は既定 OFF。untrusted environment では有効化しないよう公式 README に明記。
- **総合所見:** 今回の前提では最もセキュアに閉じやすい。反面、Windows サービス化は NSSM / winsw での手作業寄り。
- **公式ドキュメント:** [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

### 3.3 LM Studio

- **バージョン:** 0.4.11 Build 1
- **公式:** [lmstudio.ai](https://lmstudio.ai)
- **選定理由:** Windows での運用性が最良。`lms` CLI、OpenAI 互換 server、headless mode（`lms server start` / `lms daemon up`）がすべて揃っており、サービス化と現場運用の摩擦が最も低い。
- **ネットワーク / 安全:**
  - 既定 `http://localhost:1234`、認証は既定 OFF だが API token 要求可能。
  - `Serve on Local Network` は UI で明示的に切替可能。
  - `mcp.json` の server 利用は file system / private data 到達の risk と公式で注意喚起あり。MCP 全般について「arbitrary code / local files / network connection」に注意。
  - model catalog / download / runtime update / app update は Internet 前提。
- **総合所見:** 運用性最良。機房 PC では **local network 無効 + 認証 ON + MCP 最小化** を前提にすべき。更新類は保守許可時間帯に限定する。
- **公式ドキュメント:** [Quickstart](https://lmstudio.ai/docs/developer/rest/quickstart), [Authentication](https://lmstudio.ai/docs/developer/core/authentication), [Server Settings](https://lmstudio.ai/docs/developer/core/server/settings), [Use MCP Servers](https://lmstudio.ai/docs/app/mcp), [Offline Operation](https://lmstudio.ai/docs/app/offline)

**補足：Remote desktop 層について:** Splashtop は TLS 1.2 / AES-256、device authentication、2FA、session timeout、session/file transfer logs 等を公開している（[Splashtop 公式](https://www.splashtop.com/security/features)）。これは補助統制として有効だが、LLM API を `localhost` に閉じる判断の代替にはならない。

---

## 4. 除外ツールの詳細

### 4.1 vLLM（0.19.0）

- 2026-04-16 時点で CPU / Intel XPU 対応はあるが、Windows native が弱く Linux/GPU サーバでの高並発 serving に主眼。
- 本プロジェクトの single-user Windows mini PC appliance とは運用軸が一致しない。

### 4.2 OpenVINO-GenAI（2026.1.0.0）

- Intel 最適化は強いが、単体で OpenAI 互換 HTTP host を提供しない。
- 本プロジェクトの評価軸では「ホスト製品」より「推論ライブラリ」に近い。Phase 3 の結果次第では後段で再検討する。

### 4.3 IPEX-LLM（2.2.0）

- 独立ホストというより Intel 向け acceleration / integration layer。
- patched Ollama / llama.cpp / vLLM と評価軸が重複し、Phase 3 の比較対象として境界が曖昧。

### 4.4 text-generation-webui（4.5.2）

- 機能は豊富だが Web UI / backend / extension の自由度が高く、Windows service hardening と再現性のコストが大きい。
- single-user appliance としては overengineered。

---

## 5. 評価マトリクス（全 7 ツール）

読者が独自に検証したい場合の生データ。

### 調査対象一覧

| # | ツール | バージョン | 公式サイト |
|---|-------|-----------|-----------|
| 1 | Ollama | 0.20.7 | [ollama.com](https://ollama.com) |
| 2 | llama.cpp | b8808 | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| 3 | LM Studio | 0.4.11 Build 1 | [lmstudio.ai](https://lmstudio.ai) |
| 4 | IPEX-LLM | 2.2.0 | [intel.github.io/ipex-llm](https://intel.github.io/ipex-llm/) |
| 5 | OpenVINO-GenAI | 2026.1.0.0 | [openvino.genai](https://openvinotoolkit.github.io/openvino.genai/) |
| 6 | text-generation-webui | 4.5.2 | [text-generation-webui](https://github.com/oobabooga/text-generation-webui) |
| 7 | vLLM | 0.19.0 | [vllm.ai](https://vllm.ai) |

### 評価軸マトリクス

| ツール | Windows native | CPU 推論品質 | AMX / iGPU 加速 | 対応量子化 / モデル形式 | 対応 vision モデル族 | OpenAI 互換 API | Windows サービス化 | ライセンス | 直近 release | 判定 |
|-------|---------------|------------|-----------------|--------------------|--------------------|----------------|-----------------|----------|-------------|-----|
| Ollama | ○ | ○ | △ | GGUF import, Safetensors import, Ollama registry blobs | Qwen2.5-VL, Llama 3.2 Vision, MiniCPM-V 系 | ○ | △ | MIT | v0.20.7 (2026-04-13) | 選定 |
| llama.cpp | ○ | ○ | ○ | GGUF (Q4_K_M, Q5_K_M, Q8_0 等) | Qwen2.5-VL, LLaVA 系, MiniCPM-V, Llama 3.2 Vision, InternVL 系（GGUF/manual） | ○ | △ | MIT | b8808 (2026-04-16) | 選定 |
| LM Studio | ○ | ○ | △ | GGUF (llama.cpp runtime), MLX (macOS) | Qwen2.5-VL, Llama 3.2 Vision, ほか GGUF multimodal | ○ | ○ | プロプライエタリ（personal / internal business use） | v0.4.11 Build 1 (2026-04-10) | 選定 |
| IPEX-LLM | ○ | ○ | ○ | native HF, FP8/FP6/FP4/INT4, patched Ollama / llama.cpp portable zip | Qwen-VL, MiniCPM-V, Llama 3.2 Vision, Phi-3 Vision | △ | △ | Apache-2.0 | v2.2.0 (2025-04-07) | 除外 |
| OpenVINO-GenAI | ○ | ○ | ○ | OpenVINO IR, HF/Optimum export, INT8/INT4 (NNCF) | Qwen2.5-VL, MiniCPM-V 2.6, InternVL2.5, LLaVA 系, Gemma 3 | × | △ | Apache-2.0 | 2026.1.0.0 (2026-04-07) | 除外 |
| text-generation-webui | ○ | △ | △ | GGUF, HF/Transformers, bitsandbytes, ExLlamaV3, TensorRT-LLM | multimodal backend 依存（LLaVA / Qwen-VL / Phi 系） | ○ | △ | AGPL-3.0 | v4.5.2 (2026-04-15) | 除外 |
| vLLM | △ | △ | ○ | native HF, AWQ, GPTQ, GGUF, FP8/MXFP4 | Qwen2.5-VL, MiniCPM-V, InternVL 系, ほか HF multimodal | ○ | △ | Apache-2.0 | v0.19.0 (2026-04-03) | 除外 |

---

## 6. 選定 3 ツールのネットワーク / 安全比較

| ツール | 既定の露出面 | オフライン適性 | 運用時の推奨設定 |
|-------|-------------|---------------|-----------------|
| **Ollama** | `127.0.0.1:11434` 既定。ローカル API は認証不要。必要なら `OLLAMA_HOST` や proxy で外部公開可能。 | ローカル実行自体は閉域化しやすい。ただし cloud model / private model / publish を使うと `ollama.com` 連携が入る。 | **local-only + cloud 無効化**（`OLLAMA_NO_CLOUD=1`） |
| **llama.cpp** | `llama-server` は `127.0.0.1:8080` 既定。`--api-key` と TLS 証明書指定で露出制御が最も明快。 | `--offline` があり、ローカル GGUF 前提なら最も閉域運用しやすい。 | **API key 必須化 + `--offline` + MCP 無効化** |
| **LM Studio** | `http://localhost:1234` 既定。認証は既定 OFF だが API token を要求可能。`Serve on Local Network` は UI で切替可。 | モデル / runtime 配布後の推論は offline 可能。model catalog / download / runtime update / app update は Internet 前提。 | **local network 無効 + API token ON + MCP 最小化 + 更新は許可時間帯のみ** |

---

## 7. Vision モデル対応状況

| ツール | Qwen2.5-VL (3B/7B) | MiniCPM-V 2.6 (8B) | Llama 3.2 Vision (11B) | InternVL2.5 (4B/8B) | 備考 |
|-------|-------------------|--------------------|------------------------|---------------------|-----|
| Ollama | ○ | ○ | ○ | × | Ollama registry で pull 可能。InternVL は 2026-04-16 時点で 3 / 3.5 系ヒットはあるが 2.5 は確認できず。 |
| llama.cpp | △ | △ | △ | △ | いずれも GGUF/manual import 前提。family ごとに converter / mmproj / runtime version の整合確認が必要。 |
| LM Studio | ○ | △ | ○ | △ | Qwen2.5-VL と Llama 3.2 Vision は catalog / OpenAI-compatible image path との親和性が高い。MiniCPM / InternVL は手動 import 前提で扱うのが安全。 |

凡例: `○` 公式 registry 有 / `△` GGUF 手動変換要 / `×` 非対応 / `?` 未確認

---

## 付録 A. 凡例（セクション 5 評価マトリクスの各軸）

- **Windows native**: `○` 動く / `△` WSL 経由のみ / `×` 非対応
- **CPU 推論品質**: `○` 主力経路 / `△` 可能だが遅い / `×` 非推奨
- **Intel AMX / iGPU 加速**: `○` 公式サポート / `△` 第三者パッチ / `×` 非対応
- **対応量子化 / モデル形式**: 自由記述。対応形式をカンマ区切りで列挙（例: `GGUF (Q4_K_M, Q5_K_M, Q8_0)`、`AWQ`、`OpenVINO IR`、`GPTQ`、`native HF`）。**iGPU のみの目標機では量子化サポートがモデルカタログを直接決める first-order 指標**
- **対応 vision モデル族**: 自由記述。主要対応ファミリをカンマ区切り（例: `Qwen2.5-VL, LLaVA, MiniCPM-V`）。vision 非対応なら `なし`
- **OpenAI 互換 API**: `○` native / `△` プロキシ経由 / `×` なし
- **Windows サービス化**: `○` 公式 installer + サービス登録 / `△` NSSM / winsw 手動 / `×` 対話的起動のみ
- **ライセンス**: SPDX 識別子または正式名称（例: `MIT`、`Apache-2.0`、`AGPL-3.0`、`プロプライエタリ（商用可）`）
- **直近 release**: `vX.Y.Z (YYYY-MM-DD)` 形式。不定期リリースのツールは最新 commit ハッシュ + 日付でも可
- **判定**: `選定`（Phase 3 の詳細評測対象）/ `除外`（後者には必ず理由を別記）

---

## 付録 B. 参考ソース（公式）

- **Ollama**: [README](https://github.com/ollama/ollama/blob/main/README.md), [API Introduction](https://docs.ollama.com/api/introduction), [Authentication](https://docs.ollama.com/api/authentication), [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility), [FAQ](https://docs.ollama.com/faq), [Importing a Model](https://github.com/ollama/ollama/blob/main/docs/import.mdx), [Windows](https://github.com/ollama/ollama/blob/main/docs/windows.mdx), [Releases](https://github.com/ollama/ollama/releases), [qwen2.5vl](https://ollama.com/library/qwen2.5vl), [llama3.2-vision search](https://ollama.com/search?q=llama3.2-vision)
- **llama.cpp**: [README](https://github.com/ggml-org/llama.cpp/blob/master/README.md), [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md), [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [multimodal.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md), [Releases](https://github.com/ggml-org/llama.cpp/releases)
- **LM Studio**: [Welcome / system support](https://lmstudio.ai/docs/app), [Offline Operation](https://lmstudio.ai/docs/app/offline), [Use MCP Servers](https://lmstudio.ai/docs/app/mcp), [Quickstart](https://lmstudio.ai/docs/developer/rest/quickstart), [Authentication](https://lmstudio.ai/docs/developer/core/authentication), [Server Settings](https://lmstudio.ai/docs/developer/core/server/settings), [OpenAI Compatibility Endpoints](https://lmstudio.ai/docs/developer/openai-compat), [Run LM Studio as a service (headless)](https://lmstudio.ai/docs/developer/core/headless), [Changelog](https://lmstudio.ai/changelog), [App Terms](https://lmstudio.ai/app-terms)
- **IPEX-LLM**: [README](https://github.com/intel/ipex-llm/blob/main/README.md), [Windows GPU install](https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/install_windows_gpu.md), [Run Ollama with IPEX-LLM](https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/ollama_quickstart.md), [FastChat quickstart](https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/fastchat_quickstart.md), [Releases](https://github.com/intel/ipex-llm/releases)
- **OpenVINO-GenAI**: [README](https://github.com/openvinotoolkit/openvino.genai/blob/master/README.md), [Supported Models](https://openvinotoolkit.github.io/openvino.genai/docs/supported-models/), [OpenVINO Release Notes](https://docs.openvino.ai/releasenotes)
- **text-generation-webui**: [README](https://github.com/oobabooga/text-generation-webui/blob/main/README.md), [Model Tab](https://github.com/oobabooga/text-generation-webui/blob/main/docs/04%20-%20Model%20Tab.md), [Releases](https://github.com/oobabooga/text-generation-webui/releases)
- **vLLM**: [README](https://github.com/vllm-project/vllm/blob/main/README.md), [Installation](https://docs.vllm.ai/en/latest/getting_started/installation/), [OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/), [Supported Models](https://docs.vllm.ai/en/latest/models/supported_models/), [Releases](https://github.com/vllm-project/vllm/releases)
- **Windows / Remote access**: [Windows Defender Firewall configuration](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure), [Splashtop Security Features](https://www.splashtop.com/security/features)
