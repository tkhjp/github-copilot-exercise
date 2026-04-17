# 本地 LLM ホスティングツール 調査マトリクス

**調査日:** 2026-04-16
**調査者:** Codex

## 候補一覧

| # | ツール | バージョン | 公式サイト |
|---|-------|-----------|-----------|
| 1 | Ollama | 0.20.7 | [ollama.com](https://ollama.com) |
| 2 | llama.cpp | b8808 | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| 3 | LM Studio | 0.4.11 Build 1 | [lmstudio.ai](https://lmstudio.ai) |
| 4 | IPEX-LLM | 2.2.0 | [intel.github.io/ipex-llm](https://intel.github.io/ipex-llm/) |
| 5 | OpenVINO-GenAI | 2026.1.0.0 | [openvino.genai](https://openvinotoolkit.github.io/openvino.genai/) |
| 6 | text-generation-webui | 4.5.2 | [text-generation-webui](https://github.com/oobabooga/text-generation-webui) |
| 7 | vLLM（除外項） | 0.19.0 | [vllm.ai](https://vllm.ai) |

## 評価軸

| ツール | Windows native 対応 | CPU 推論品質 | Intel AMX / iGPU 加速 | 対応量子化/モデル形式 | 対応 vision モデル族 | OpenAI 互換 API | Windows サービス化難度 | ライセンス | 直近 release | 評価 |
|-------|--------------------|------------|---------------------|--------------------|--------------------|----------------|---------------------|----------|-------------|-----|
| Ollama | ○ | ○ | △ | GGUF import, Safetensors import, Ollama registry blobs | Qwen2.5-VL, Llama 3.2 Vision, MiniCPM-V 系 | ○ | △ | MIT | v0.20.7 (2026-04-13) | 短名単 |
| llama.cpp | ○ | ○ | ○ | GGUF (Q4_K_M, Q5_K_M, Q8_0 等) | Qwen2.5-VL, LLaVA 系, MiniCPM-V, Llama 3.2 Vision, InternVL 系（GGUF/manual） | ○ | △ | MIT | b8808 (2026-04-16) | 短名単 |
| LM Studio | ○ | ○ | △ | GGUF (llama.cpp runtime), MLX (macOS) | Qwen2.5-VL, Llama 3.2 Vision, ほか GGUF multimodal | ○ | ○ | プロプライエタリ（personal / internal business use） | v0.4.11 Build 1 (2026-04-10) | 短名単 |
| IPEX-LLM | ○ | ○ | ○ | native HF, FP8/FP6/FP4/INT4, patched Ollama / llama.cpp portable zip | Qwen-VL, MiniCPM-V, Llama 3.2 Vision, Phi-3 Vision | △ | △ | Apache-2.0 | v2.2.0 (2025-04-07) | 除外 |
| OpenVINO-GenAI | ○ | ○ | ○ | OpenVINO IR, HF/Optimum export, INT8/INT4 (NNCF) | Qwen2.5-VL, MiniCPM-V 2.6, InternVL2.5, LLaVA 系, Gemma 3 | × | △ | Apache-2.0 | 2026.1.0.0 (2026-04-07) | 除外 |
| text-generation-webui | ○ | △ | △ | GGUF, HF/Transformers, bitsandbytes, ExLlamaV3, TensorRT-LLM | multimodal backend 依存（LLaVA / Qwen-VL / Phi 系） | ○ | △ | AGPL-3.0 | v4.5.2 (2026-04-15) | 除外 |
| vLLM | △ | △ | ○ | native HF, AWQ, GPTQ, GGUF, FP8/MXFP4 | Qwen2.5-VL, MiniCPM-V, InternVL 系, ほか HF multimodal | ○ | △ | Apache-2.0 | v0.19.0 (2026-04-03) | 除外 |

凡例:
- **Windows native**: `○` 動く / `△` WSL 経由のみ / `×` 非対応
- **CPU 推論品質**: `○` 主力経路 / `△` 可能だが遅い / `×` 非推奨
- **Intel AMX / iGPU 加速**: `○` 公式サポート / `△` 第三者パッチ / `×` 非対応
- **対応量子化/モデル形式**: 自由記述。対応形式をカンマ区切りで列挙（例: `GGUF (Q4_K_M, Q5_K_M, Q8_0)`、`AWQ`、`OpenVINO IR`、`GPTQ`、`native HF`）。**iGPU のみの目標機では量子化サポートがモデルカタログを直接決める first-order 指標**
- **対応 vision モデル族**: 自由記述。主要対応ファミリをカンマ区切り（例: `Qwen2.5-VL, LLaVA, MiniCPM-V`）。vision 非対応なら `なし`
- **OpenAI 互換 API**: `○` native / `△` プロキシ経由 / `×` なし
- **Windows サービス化難度**: `○` 公式 installer + サービス登録 / `△` NSSM/winsw 手動 / `×` 対話的起動のみ
- **ライセンス**: SPDX 識別子または正式名称（例: `MIT`、`Apache-2.0`、`AGPL-3.0`、`プロプライエタリ（商用可）`）
- **直近 release**: `vX.Y.Z (YYYY-MM-DD)` 形式。不定期リリースのツールは最新 commit ハッシュ + 日付でも可
- **評価**: `短名単` / `除外`（後者には必ず理由を別記）

## 今回追加する運用前提（社内機房 / VM 接続）

- 対象 PC は社内機房に設置された開発用 Windows PC。利用者は VM / Splashtop 等の遠隔デスクトップ経由で当該 PC にログインして利用する。
- したがって primary use case は「社内 LAN に広く API を公開する shared inference server」ではなく、「遠隔ログインした利用者が当該 PC 内で使う single-user 〜 small-team appliance」である。
- この前提では LAN 公開の容易さより、`localhost` bind、オフライン運転、アウトバウンド通信先の明確さ、Windows Firewall / GPO での閉域化のしやすさを重く見る。
- 推論: remote desktop 経由で当該 PC に入れるため、初期構成では LLM endpoint を社内ネットワークに公開しなくても主要ユースケースは満たせる。API 公開は後段要件として扱うのが安全。

## 追加評価軸（ネットワーク / 安全）

| 観点 | 何を見るか | 今回の重み |
|------|-----------|-----------|
| 既定 bind | `127.0.0.1` / `localhost` が既定か | 高 |
| API 認証 | product 自身で token / API key を持てるか | 高 |
| オフライン運転 | モデル配布後は外部通信なしで推論できるか | 高 |
| アウトバウンド依存 | モデル検索 / 更新 / クラウド連携 / MCP などの外部通信面が限定的か | 高 |
| Windows 閉域化 | 固定 port / service / firewall rule / proxy 配下に載せやすいか | 中〜高 |

補足:
- Microsoft の公式ドキュメントでは、Windows Defender Firewall は **既定で outbound を許可** する。したがって「推論時は外部通信なし」を担保したい場合、ツール選定とは別に outbound allowlist / block rule を入れる前提で評価する必要がある。

## 短名単と除外理由

### 短名単（Phase 3 で深度評測、2〜3 種）

選定数は 2〜3 種。3 種とも埋まらなくてよい — 欠番はそのまま空欄。

1. **Ollama** — 選定理由: OpenAI 互換 API と Windows インストーラが最も素直で、Phase 5 の本地 endpoint 置換先として baseline appliance を作りやすい。
2. **llama.cpp** — 選定理由: GGUF / multimodal の最小コアで制御性が高く、Intel SYCL / oneMKL を含む最適化余地が大きい。性能上限と互換性の確認用として外せない。
3. **LM Studio** — 選定理由: Windows での運用性が最良。`llmster` / `lms` / OpenAI 互換 server が揃っており、サービス化と現場運用の摩擦が最も低い。

### 除外（理由付き）

- **vLLM** — 除外理由: 2026-04-16 時点で CPU / Intel XPU 対応はあるが、Windows native が弱く Linux/GPU サーバーでの高並発 serving に主眼がある。今回の single-user Windows mini PC appliance とは運用軸が噛み合わない。
- **OpenVINO-GenAI** — 除外理由: Intel 最適化は強いが、単体で OpenAI 互換 HTTP host ではない。今回の比較軸では「ホスト製品」より「推論ライブラリ」に近い。
- **IPEX-LLM** — 除外理由: 単独ホストというより Intel 向け acceleration / integration layer。patched Ollama / llama.cpp / vLLM と評価軸が重複し、Phase 3 の比較対象としては境界が曖昧。
- **text-generation-webui** — 除外理由: 機能は豊富だが Web UI / backend / extension の自由度が高く、Windows service hardening と再現性のコストが大きい。

## 短名単 3 種のネットワーク / 安全補足

| ツール | 既定の露出面 | オフライン適性 | 今回の判断 |
|-------|-------------|---------------|-----------|
| Ollama | `127.0.0.1:11434` 既定。ローカル API は認証不要。必要なら `OLLAMA_HOST` や proxy で外部公開可能。 | ローカル実行自体は閉域化しやすいが、cloud model / private model / publish を使うと `ollama.com` 連携が入る。 | baseline として有力。ただし機房 PC では **local-only + cloud 無効化** を初期値にするのが安全。 |
| llama.cpp | `llama-server` は `127.0.0.1:8080` 既定。`--api-key` と TLS 証明書指定があり、露出制御が最も明快。 | `--offline` があり、ローカル GGUF 前提なら最も閉域運用しやすい。 | 今回の前提では最もセキュアに閉じやすい。反面、Windows サービス化は手作業寄り。 |
| LM Studio | `http://localhost:1234` 既定。認証は既定 OFF だが API token を要求可能。`Serve on Local Network` も UI で切替可。 | モデル / runtime 配布後の推論は offline 可能。ただし model catalog / download / runtime update / app update は Internet 前提。 | 運用性は最良。機房 PC では **local network 無効 + 認証 ON + MCP 最小化** を前提にすべき。 |

公式確認メモ:
- **Ollama**: API は既定で `http://localhost:11434/api`。ローカル API は認証不要、`127.0.0.1:11434` bind が既定。`disable_ollama_cloud` または `OLLAMA_NO_CLOUD=1` で cloud 機能を無効化できる。([API Introduction](https://docs.ollama.com/api/introduction), [Authentication](https://docs.ollama.com/api/authentication), [FAQ](https://docs.ollama.com/faq))
- **llama.cpp**: `llama-server` は `--host` 既定 `127.0.0.1`、`--port` 既定 `8080`。`--api-key`、`--ssl-key-file`、`--ssl-cert-file`、`--offline` を持つ。加えて experimental の MCP proxy / agent tools は既定 OFF で、README 上も untrusted environment では有効化しないよう明記されている。([server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md))
- **LM Studio**: API server は既定で `http://localhost:1234`、認証は既定 OFF だが API token を要求可能。`Serve on Local Network` は明示的な switch。さらに `mcp.json` の server 利用は file system / private data へ到達し得るため security risk と公式に注意喚起されている。MCP 全般についても「arbitrary code / local files / network connection」に注意とある。([Quickstart](https://lmstudio.ai/docs/developer/rest/quickstart), [Authentication](https://lmstudio.ai/docs/developer/core/authentication), [Server Settings](https://lmstudio.ai/docs/developer/core/server/settings), [Use MCP Servers](https://lmstudio.ai/docs/app/mcp), [Offline Operation](https://lmstudio.ai/docs/app/offline))
- **Windows host control**: Windows Defender Firewall は既定で outbound を許可するため、外部通信の禁止は host 側ルールで明示的に閉じる必要がある。([Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure))
- **Remote desktop layer**: Splashtop は TLS 1.2 / AES-256、device authentication、2FA、session timeout、session/file transfer logs 等を公開している。これは補助統制として有効だが、LLM API を `localhost` に閉じる判断の代替にはならない。([Splashtop Security Features](https://www.splashtop.com/security/features))

## Vision モデル対応状況（各ツールで確認）

| ツール | Qwen2.5-VL (3B/7B) | MiniCPM-V 2.6 (8B) | Llama 3.2 Vision (11B) | InternVL2.5 (4B/8B) | 備考 |
|-------|-------------------|--------------------|------------------------|---------------------|-----|
| Ollama | ○ | ○ | ○ | × | Ollama registry で pull 可能。InternVL は 2026-04-16 時点で 3 / 3.5 系ヒットはあるが 2.5 は確認できず。 |
| llama.cpp | △ | △ | △ | △ | いずれも GGUF/manual import 前提。family ごとに converter / mmproj / runtime version の整合確認が必要。 |
| LM Studio | ○ | △ | ○ | △ | Qwen2.5-VL と Llama 3.2 Vision は catalog / OpenAI-compatible image path との親和性が高い。MiniCPM / InternVL は手動 import 前提で扱うのが安全。 |

凡例: `○` 公式 registry 有 / `△` GGUF 手動変換要 / `×` 非対応 / `?` 未確認

## 結論

Phase 1 の desk research 結論として、Phase 3 の深度評測対象は **Ollama / llama.cpp / LM Studio** の 3 種とする。  

- **Ollama**: 最も簡単に OpenAI 互換 endpoint を出せる baseline appliance。機房 PC 前提では **LAN 公開より local-only 運用** を基本にし、cloud 機能は明示的に無効化して評価するのがよい。
- **llama.cpp**: 最も低レベルで柔軟。GGUF 互換性と Intel 最適化余地の確認用に加え、**閉域運用のしやすさ** でも最も明快。
- **LM Studio**: Windows native の headless/service 運用が最も楽な本命候補。現場導入性は高いが、**認証 OFF / local network ON / MCP 開放** のまま使わないことが前提。

Intel 最適化の純粋性能では **OpenVINO-GenAI** と **IPEX-LLM** が有力だが、今回の主目的は「Windows 上でそのまま OpenAI 互換 host として置きやすい製品」を選ぶことなので、Phase 1 では除外とし、必要なら Phase 3 の結果を見て再検討する。

運用前提を「社内機房 PC を遠隔デスクトップで使う appliance」と置くなら、Phase 3 の評価では次の最小構成を共通前提にする。

1. まず全候補を `localhost` bind のまま評価し、社内 LAN への直接公開は行わない。
2. モデル / runtime の取得は保守用の許可時間帯または allowlist proxy 経由に限定し、通常運転時のアウトバウンド通信は host firewall で閉じる。
3. 将来どうしても複数端末から共用 API 化する場合は、各ツールの素の port を直接公開せず、reverse proxy / API gateway / 認証基盤の後ろに置く。

上記前提では、閉域化しやすさは `llama.cpp` が最も強く、現場運用の摩擦の低さは `LM Studio` が最も強い。`Ollama` は baseline として有効だが、社内機房の運用では cloud 連携とネットワーク露出を明示的に絞る前提で扱うのが適切。

## 参考ソース（公式）

- Ollama: [README](https://github.com/ollama/ollama/blob/main/README.md), [API Introduction](https://docs.ollama.com/api/introduction), [Authentication](https://docs.ollama.com/api/authentication), [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility), [FAQ](https://docs.ollama.com/faq), [Importing a Model](https://github.com/ollama/ollama/blob/main/docs/import.mdx), [Windows](https://github.com/ollama/ollama/blob/main/docs/windows.mdx), [Releases](https://github.com/ollama/ollama/releases), [qwen2.5vl](https://ollama.com/library/qwen2.5vl), [llama3.2-vision search](https://ollama.com/search?q=llama3.2-vision)
- llama.cpp: [README](https://github.com/ggml-org/llama.cpp/blob/master/README.md), [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md), [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [multimodal.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md), [Releases](https://github.com/ggml-org/llama.cpp/releases)
- LM Studio: [Welcome / system support](https://lmstudio.ai/docs/app), [Offline Operation](https://lmstudio.ai/docs/app/offline), [Use MCP Servers](https://lmstudio.ai/docs/app/mcp), [Quickstart](https://lmstudio.ai/docs/developer/rest/quickstart), [Authentication](https://lmstudio.ai/docs/developer/core/authentication), [Server Settings](https://lmstudio.ai/docs/developer/core/server/settings), [OpenAI Compatibility Endpoints](https://lmstudio.ai/docs/developer/openai-compat), [Run LM Studio as a service (headless)](https://lmstudio.ai/docs/developer/core/headless), [Changelog](https://lmstudio.ai/changelog), [App Terms](https://lmstudio.ai/app-terms)
- IPEX-LLM: [README](https://github.com/intel/ipex-llm/blob/main/README.md), [Windows GPU install](https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/install_windows_gpu.md), [Run Ollama with IPEX-LLM](https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/ollama_quickstart.md), [FastChat quickstart](https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/fastchat_quickstart.md), [Releases](https://github.com/intel/ipex-llm/releases)
- OpenVINO-GenAI: [README](https://github.com/openvinotoolkit/openvino.genai/blob/master/README.md), [Supported Models](https://openvinotoolkit.github.io/openvino.genai/docs/supported-models/), [OpenVINO Release Notes](https://docs.openvino.ai/releasenotes)
- text-generation-webui: [README](https://github.com/oobabooga/text-generation-webui/blob/main/README.md), [Model Tab](https://github.com/oobabooga/text-generation-webui/blob/main/docs/04%20-%20Model%20Tab.md), [Releases](https://github.com/oobabooga/text-generation-webui/releases)
- vLLM: [README](https://github.com/vllm-project/vllm/blob/main/README.md), [Installation](https://docs.vllm.ai/en/latest/getting_started/installation/), [OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/), [Supported Models](https://docs.vllm.ai/en/latest/models/supported_models/), [Releases](https://github.com/vllm-project/vllm/releases)
- Windows / Remote access: [Windows Defender Firewall configuration](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure), [Splashtop Security Features](https://www.splashtop.com/security/features)
