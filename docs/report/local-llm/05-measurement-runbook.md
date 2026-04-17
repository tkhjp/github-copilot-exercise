# Local LLM Appliance 実測詳細手順書

**対象リポジトリ:** `D:\Work\github-copilot-exercise`  
**対象フェーズ:** Phase 3 / 4 / 6 / 7  
**前提 OS:** Windows 11 + PowerShell 7 以上推奨  
**対象読者:** 実際に benchmark と選定レポートを埋める担当者

## 1. 目的

この手順書は、以下を**人手で再現可能な形**で実施するための runbook です。

1. `Ollama / llama.cpp / LM Studio` の shortlist benchmark
2. 勝者 host 上での model selection
3. target mini PC での validation
4. 最終統合レポートの作成

この手順書では**既存コードを変更しません**。使うのは既存の:

- `python -m benchmarks.harness`
- `tools/describe_image.py`
- `tools/describe_pptx.py`
- `tools/lib/local_llm_client.py`
- `tests/text_vs_image/test_cases.yaml`

のみです。

## 2. 出力物

この手順を最後まで回すと、最低限以下が埋まります。

- [02-tool-shortlist-benchmark.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/02-tool-shortlist-benchmark.md)
- [03-model-selection.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/03-model-selection.md)
- [04-target-validation.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/04-target-validation.md)
- [local-llm-selection-report.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm-selection-report.md)

raw 出力は以下に置きます。

- `benchmarks/out/phase3/`
- `benchmarks/out/phase4/`
- `benchmarks/out/phase6/`

## 3. 事前に決めておくこと

実測開始前に、以下だけは担当者が埋めておいてください。

| 項目 | 値 |
|---|---|
| 実施日 | |
| 実施者 | |
| 開発機の Windows ホスト名 | |
| target mini PC のホスト名 or IP | |
| mini PC の OS / CPU / RAM | |
| llama.cpp の `llama-server.exe` 実体パス | |
| llama.cpp の Gemma 4 E4B GGUF パス（`gemma-4-E4B-it-Q4_K_M.gguf`） | |
| llama.cpp の `mmproj` パス（Gemma 4 vision に必須） | |
| LM Studio で使う local model key | |

## 4. One-time 準備

### 4.1 PowerShell を 2 本開く

- **Terminal A:** host 起動用
- **Terminal B:** benchmark 実行用

以後、host を切り替えるたびに Terminal A は再利用し、Terminal B は benchmark / smoke / report 更新に使います。

### 4.2 repo root に移動

両方の terminal で以下を実行:

```powershell
$Repo = "D:\Work\github-copilot-exercise"
Set-Location $Repo
```

### 4.3 Python と pip を確認

```powershell
py -3.13 --version
py -3.13 -m pip --version
```

期待値:

- Python 3.13.x
- pip が使える

`py -3.13 -m pip --version` が失敗する場合は、**この手順書はそこで一旦停止**です。Python 3.13 + pip を入れてから再開してください。

### 4.4 依存を同期

```powershell
py -3.13 -m pip install -r tools/requirements.txt -r requirements-dev.txt
```

### 4.5 baseline test を実行

```powershell
py -3.13 -m pytest tests/benchmarks tests/lib/test_local_llm_client.py
py -3.13 -m benchmarks.harness --help
```

期待値:

- pytest が green
- harness の usage が表示される

失敗した場合:

- 実測に進まず、失敗内容を [02-tool-shortlist-benchmark.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/02-tool-shortlist-benchmark.md) の冒頭に記録する

### 4.6 出力ディレクトリを作成

```powershell
New-Item -ItemType Directory -Force benchmarks\out\phase3\ollama | Out-Null
New-Item -ItemType Directory -Force benchmarks\out\phase3\llama-cpp | Out-Null
New-Item -ItemType Directory -Force benchmarks\out\phase3\lm-studio | Out-Null
New-Item -ItemType Directory -Force benchmarks\out\phase4 | Out-Null
New-Item -ItemType Directory -Force benchmarks\out\phase6 | Out-Null
```

### 4.7 GPU 無効確認用の監視 terminal を任意で開く

開発機が NVIDIA GPU 搭載なら、別 terminal で以下を流しっぱなしにします。

```powershell
nvidia-smi -l 1
```

期待値:

- benchmark 実行中も GPU-Util は `0%`
- VRAM 使用量は `0 MiB` が理想

## 5. Phase 3 — shortlist benchmark

### 5.1 固定条件

Phase 3 は以下で固定です。

- tool: `Ollama`, `llama.cpp`, `LM Studio`
- model family: `Gemma 4 E4B`
- inputs:
  - S1: text-only
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/`
- run counts:
  - S1 smoke: 1 run
  - S1 full: 3 runs
  - S2 full: 3 runs
  - S3 full: 1 pass per image

### 5.2 共通ルール

- **manual restart 禁止:** S2 か S3 の途中で host を再起動したら hard gate fail
- **tool ごとの別モデル救済禁止:** Gemma 4 E4B が 0.5 日以内に安定起動できない tool は除外
- **host 切替時は env を捨てる:**

```powershell
Remove-Item Env:LLM_BACKEND -ErrorAction SilentlyContinue
Remove-Item Env:LLM_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LLM_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
```

### 5.3 Ollama 実測

参照:

- [candidates/ollama/notes.md](/mnt/d/Work/github-copilot-exercise/candidates/ollama/notes.md)
- [candidates/ollama/start.ps1](/mnt/d/Work/github-copilot-exercise/candidates/ollama/start.ps1)

#### Step A: benchmark model を準備

Terminal A:

```powershell
Set-Location $Repo
.\candidates\ollama\start.ps1 -PrepareBenchmarkModel
```

別 terminal で model を確認:

```powershell
ollama list
Invoke-WebRequest http://127.0.0.1:11434/v1/models | Select-Object -Expand Content
```

期待値:

- `gemma4-e4b-bench` が見える

#### Step B: S1 smoke

Terminal B:

```powershell
Set-Location $Repo
py -3.13 -m benchmarks.harness `
  --tool ollama `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:11434/v1 `
  --scenario s1 `
  --n-runs 1 `
  --out-dir benchmarks/out/phase3/ollama
```

#### Step C: full benchmark

```powershell
py -3.13 -m benchmarks.harness `
  --tool ollama `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:11434/v1 `
  --scenario s1 `
  --n-runs 3 `
  --out-dir benchmarks/out/phase3/ollama

py -3.13 -m benchmarks.harness `
  --tool ollama `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:11434/v1 `
  --scenario s2 `
  --image samples/diagram.png `
  --n-runs 3 `
  --out-dir benchmarks/out/phase3/ollama

py -3.13 -m benchmarks.harness `
  --tool ollama `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:11434/v1 `
  --scenario s3 `
  --pptx-dir tests/text_vs_image/images `
  --out-dir benchmarks/out/phase3/ollama
```

#### Step D: local client smoke

```powershell
$env:LLM_BACKEND = "local"
$env:LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:LLM_MODEL = "gemma4-e4b-bench"

py -3.13 tools/describe_image.py samples/diagram.png `
  | Tee-Object -FilePath benchmarks/out/phase3/ollama/local-smoke-describe-image.md

py -3.13 tools/describe_pptx.py samples/sample.pptx `
  | Tee-Object -FilePath benchmarks/out/phase3/ollama/local-smoke-describe-pptx.md
```

#### Step E: report 記録

[02-tool-shortlist-benchmark.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/02-tool-shortlist-benchmark.md) に以下を記録:

- raw output path
- install friction
- launch friction
- restart stability
- S1/S2/S3 status
- OpenAI API の可否
- `local_llm_client` の可否
- Windows service path = `manual`

#### Step F: 停止

Terminal A で `Ctrl + C`。

### 5.4 llama.cpp 実測

参照:

- [candidates/llama-cpp/notes.md](/mnt/d/Work/github-copilot-exercise/candidates/llama-cpp/notes.md)
- [candidates/llama-cpp/start.ps1](/mnt/d/Work/github-copilot-exercise/candidates/llama-cpp/start.ps1)

#### Step A: env を設定

Terminal A:

```powershell
Set-Location $Repo
$env:LLAMA_SERVER_BIN = "C:\path\to\llama-server.exe"
$env:LLAMA_CPP_MODEL_PATH = "C:\path\to\gemma-4-E4B-it-Q4_K_M.gguf"
$env:LLAMA_CPP_MMPROJ_PATH = "C:\path\to\mmproj.gguf"   # 必要な場合のみ
```

#### Step B: host 起動

```powershell
.\candidates\llama-cpp\start.ps1
```

別 terminal で health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8080/v1/models | Select-Object -Expand Content
```

#### Step C: S1 smoke

Terminal B:

```powershell
Set-Location $Repo
py -3.13 -m benchmarks.harness `
  --tool llama-cpp `
  --model gemma-4-E4B-it-GGUF `
  --base-url http://127.0.0.1:8080/v1 `
  --scenario s1 `
  --n-runs 1 `
  --out-dir benchmarks/out/phase3/llama-cpp
```

#### Step D: full benchmark

```powershell
py -3.13 -m benchmarks.harness `
  --tool llama-cpp `
  --model gemma-4-E4B-it-GGUF `
  --base-url http://127.0.0.1:8080/v1 `
  --scenario s1 `
  --n-runs 3 `
  --out-dir benchmarks/out/phase3/llama-cpp

py -3.13 -m benchmarks.harness `
  --tool llama-cpp `
  --model gemma-4-E4B-it-GGUF `
  --base-url http://127.0.0.1:8080/v1 `
  --scenario s2 `
  --image samples/diagram.png `
  --n-runs 3 `
  --out-dir benchmarks/out/phase3/llama-cpp

py -3.13 -m benchmarks.harness `
  --tool llama-cpp `
  --model gemma-4-E4B-it-GGUF `
  --base-url http://127.0.0.1:8080/v1 `
  --scenario s3 `
  --pptx-dir tests/text_vs_image/images `
  --out-dir benchmarks/out/phase3/llama-cpp
```

#### Step E: local client smoke

```powershell
$env:LLM_BACKEND = "local"
$env:LLM_BASE_URL = "http://127.0.0.1:8080/v1"
$env:LLM_MODEL = "gemma-4-E4B-it-GGUF"

py -3.13 tools/describe_image.py samples/diagram.png `
  | Tee-Object -FilePath benchmarks/out/phase3/llama-cpp/local-smoke-describe-image.md

py -3.13 tools/describe_pptx.py samples/sample.pptx `
  | Tee-Object -FilePath benchmarks/out/phase3/llama-cpp/local-smoke-describe-pptx.md
```

#### Step F: report 記録

[02-tool-shortlist-benchmark.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/02-tool-shortlist-benchmark.md) に以下を記録:

- `mmproj` の有無
- install friction
- launch friction
- restart stability
- S1/S2/S3 status
- OpenAI API の可否
- `local_llm_client` の可否
- Windows service path = `manual`

#### Step G: 停止

Terminal A で `Ctrl + C`。

### 5.5 LM Studio 実測

参照:

- [candidates/lm-studio/notes.md](/mnt/d/Work/github-copilot-exercise/candidates/lm-studio/notes.md)
- [candidates/lm-studio/start.ps1](/mnt/d/Work/github-copilot-exercise/candidates/lm-studio/start.ps1)

#### Step A: model key を確認

LM Studio を一度起動し、Gemma 4 E4B が local model として見えることを確認します。`<MODEL_KEY>` を控えてください。

#### Step B: host 起動

Terminal A:

```powershell
Set-Location $Repo
.\candidates\lm-studio\start.ps1 -ModelKey <MODEL_KEY>
```

別 terminal で health check:

```powershell
Invoke-WebRequest http://127.0.0.1:1234/v1/models | Select-Object -Expand Content
```

#### Step C: S1 smoke

Terminal B:

```powershell
Set-Location $Repo
py -3.13 -m benchmarks.harness `
  --tool lm-studio `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:1234/v1 `
  --scenario s1 `
  --n-runs 1 `
  --out-dir benchmarks/out/phase3/lm-studio
```

#### Step D: full benchmark

```powershell
py -3.13 -m benchmarks.harness `
  --tool lm-studio `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:1234/v1 `
  --scenario s1 `
  --n-runs 3 `
  --out-dir benchmarks/out/phase3/lm-studio

py -3.13 -m benchmarks.harness `
  --tool lm-studio `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:1234/v1 `
  --scenario s2 `
  --image samples/diagram.png `
  --n-runs 3 `
  --out-dir benchmarks/out/phase3/lm-studio

py -3.13 -m benchmarks.harness `
  --tool lm-studio `
  --model gemma4-e4b-bench `
  --base-url http://127.0.0.1:1234/v1 `
  --scenario s3 `
  --pptx-dir tests/text_vs_image/images `
  --out-dir benchmarks/out/phase3/lm-studio
```

#### Step E: local client smoke

```powershell
$env:LLM_BACKEND = "local"
$env:LLM_BASE_URL = "http://127.0.0.1:1234/v1"
$env:LLM_MODEL = "gemma4-e4b-bench"

py -3.13 tools/describe_image.py samples/diagram.png `
  | Tee-Object -FilePath benchmarks/out/phase3/lm-studio/local-smoke-describe-image.md

py -3.13 tools/describe_pptx.py samples/sample.pptx `
  | Tee-Object -FilePath benchmarks/out/phase3/lm-studio/local-smoke-describe-pptx.md
```

#### Step F: report 記録

[02-tool-shortlist-benchmark.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/02-tool-shortlist-benchmark.md) に以下を記録:

- GUI required か
- install friction
- launch friction
- restart stability
- S1/S2/S3 status
- OpenAI API の可否
- `local_llm_client` の可否
- Windows service path = `native`

#### Step G: 停止

```powershell
lms server stop
```

### 5.6 shortlist winner の決め方

[02-tool-shortlist-benchmark.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/02-tool-shortlist-benchmark.md) を埋めた後、以下の順で winner を決めます。

1. hard gate を満たす host のみ残す
   - S2 完走
   - S3 完走
   - manual restart なし
   - `tools/lib/local_llm_client.py` で接続成功
2. hard gate 通過 host 同士で比較する
3. 性能差が 20% 以内なら運用性を優先する
4. fastest でも運用上の致命傷がある host は採用しない

## 6. Phase 4 — 量子化 sweep

本プロジェクトのスコープは 1 つのモデルファミリー（**Gemma 4 E4B**）に固定されています。したがって Phase 4 は異なるモデル同士を比べるのではなく、その 1 モデルの量子化バリアントを比較する構成です。目的は target mini PC にとっての「品質と速度のスイートスポット」を特定することです。

### 6.1 Phase 4 の固定条件

- ホスト: Phase 3 の勝者のみ
- モデルファミリー: **Gemma 4 E4B**（固定）
- 量子化プール:
  - `Q4_K_M`（約 5 GB、Phase 3 baseline）
  - `Q5_K_M`（約 6 GB）
  - `Q8_0`（約 8 GB）
  - `FP16` / `BF16`（約 15 GB、RAM に余裕があるときのみ、任意）
- 速度入力:
  - S2: `samples/diagram.png`
  - S3: `tests/text_vs_image/images/`
- 品質テストケース:
  - `tc01`
  - `tc02`
  - `tc03`
  - `tc04`
- スコアリング規則:
  - `present = 1`
  - `partial = 0.5`
  - `missing = 0`

### 6.2 ホスト側 identifier を先に確定する

[03-model-selection.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/03-model-selection.md) の `Host identifier` 列を**最初に**埋めます。

この列には、対象ホスト上で benchmark コマンドに渡す `--model` の値を量子化ごとに記入します。

例:

- Ollama: 量子化ごとに別 Modelfile と alias を作成（例: `gemma4-e4b-q4km-bench`、`gemma4-e4b-q5km-bench`、`gemma4-e4b-q8-bench`）
- llama.cpp: 量子化ごとの GGUF を別 path に置き、そのファイル名を identifier として使う
- LM Studio: `lms load --identifier` で量子化ごとに別 ID を付ける

**ここで決めた identifier は、以降の速度／品質の全コマンドで固定**します。

### 6.3 speed benchmark

winner host を起動した状態で、各 model について以下を繰り返します。

出力ディレクトリ作成:

```powershell
New-Item -ItemType Directory -Force benchmarks\out\phase4\speed | Out-Null
```

各 model 共通コマンド:

```powershell
py -3.13 -m benchmarks.harness `
  --tool <WINNER_HOST_TAG> `
  --model <MODEL_ID> `
  --base-url <WINNER_BASE_URL> `
  --scenario s2 `
  --image samples/diagram.png `
  --n-runs 3 `
  --out-dir benchmarks/out/phase4/speed

py -3.13 -m benchmarks.harness `
  --tool <WINNER_HOST_TAG> `
  --model <MODEL_ID> `
  --base-url <WINNER_BASE_URL> `
  --scenario s3 `
  --pptx-dir tests/text_vs_image/images `
  --out-dir benchmarks/out/phase4/speed
```

### 6.4 quality output を採取

この repo では、model quality 比較の canonical prompt は [tools/lib/describe_prompts.py](/mnt/d/Work/github-copilot-exercise/tools/lib/describe_prompts.py) の `DESCRIBE_PROMPT` です。  
Phase 4 では **全モデルに対して同じ prompt** を使います。

出力ディレクトリ作成:

```powershell
New-Item -ItemType Directory -Force benchmarks\out\phase4\quality | Out-Null
```

各 model ごとに env をセット:

```powershell
$env:LLM_BACKEND = "local"
$env:LLM_BASE_URL = "<WINNER_BASE_URL>"
$env:LLM_MODEL = "<MODEL_ID>"
```

4 ケースの describe を保存:

```powershell
py -3.13 tools/describe_image.py tests/text_vs_image/images/01_mixed_slide.png `
  | Tee-Object -FilePath benchmarks/out/phase4/quality/<MODEL_ID>__tc01.md

py -3.13 tools/describe_image.py tests/text_vs_image/images/02_ui_change.png `
  | Tee-Object -FilePath benchmarks/out/phase4/quality/<MODEL_ID>__tc02.md

py -3.13 tools/describe_image.py tests/text_vs_image/images/03_complex_arch.png `
  | Tee-Object -FilePath benchmarks/out/phase4/quality/<MODEL_ID>__tc03.md

py -3.13 tools/describe_image.py tests/text_vs_image/images/04_text_document.png `
  | Tee-Object -FilePath benchmarks/out/phase4/quality/<MODEL_ID>__tc04.md
```

### 6.5 manual scoring

truth source は [tests/text_vs_image/test_cases.yaml](/mnt/d/Work/github-copilot-exercise/tests/text_vs_image/test_cases.yaml) の `ground_truth_facts` です。

各 case について:

1. `test_cases.yaml` を開く
2. 対応する `ground_truth_facts` を 1 行ずつ読む
3. `benchmarks/out/phase4/quality/<MODEL_ID>__tcXX.md` と照合する
4. 各 fact に対して以下を付ける
   - `present`
   - `partial`
   - `missing`
5. 数値化する
   - `present = 1`
   - `partial = 0.5`
   - `missing = 0`
6. `sum(score) / fact_count` を case score とする
7. `tc01`〜`tc04` の平均を model average とする

### 6.6 model selection の決め方

[03-model-selection.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/03-model-selection.md) を埋めた後、以下で決めます。

- **第一候補**
  - quality 最高
  - S3 完走
  - fastest model の 2x 以内
- **代替候補**
  - 可能なら第一候補より小さい size tier
  - 25% 以上速い、または明確に軽量
  - 第一候補 quality の 80% 以上

## 7. Phase 6 — target mini PC validation

### 7.1 mini PC に入れるもの

- Phase 3 winner host
- Phase 4 first-choice model

それ以外は入れません。

### 7.2 mini PC 上の local benchmark

mini PC 上で host を起動後、mini PC 側 terminal で:

```powershell
Set-Location D:\Work\github-copilot-exercise

py -3.13 -m benchmarks.harness `
  --tool <WINNER_HOST_TAG> `
  --model <FIRST_CHOICE_MODEL_ID> `
  --base-url <MINI_PC_BASE_URL> `
  --scenario s2 `
  --image samples/diagram.png `
  --n-runs 1 `
  --out-dir benchmarks/out/phase6

py -3.13 -m benchmarks.harness `
  --tool <WINNER_HOST_TAG> `
  --model <FIRST_CHOICE_MODEL_ID> `
  --base-url <MINI_PC_BASE_URL> `
  --scenario s3 `
  --pptx-dir tests/text_vs_image/images `
  --out-dir benchmarks/out/phase6
```

### 7.3 開発機からの end-to-end smoke

開発機側から mini PC endpoint を叩きます。

```powershell
Set-Location D:\Work\github-copilot-exercise

$env:LLM_BACKEND = "local"
$env:LLM_BASE_URL = "<MINI_PC_BASE_URL>"
$env:LLM_MODEL = "<FIRST_CHOICE_MODEL_ID>"

$sw = [System.Diagnostics.Stopwatch]::StartNew()
py -3.13 tools/describe_image.py samples/diagram.png `
  | Tee-Object -FilePath benchmarks/out/phase6/describe-image-mini-pc.md
$sw.Stop()
$sw.Elapsed.TotalSeconds
```

記録方法:

- `describe_image.py` run は **end-to-end 秒数だけ**測る
- [04-target-validation.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm/04-target-validation.md) の run 3 では
  - `TTFT = n/a`
  - `tok/s = n/a`
  - `end-to-end = 実測秒数`
  - `Notes = exit 0 / stderr 無し / 出力妥当性`

### 7.4 判定

dev rig CPU-only baseline と mini PC 実測を比較し、2x 超の乖離がある場合は結論を次のいずれかに落とします。

- `使用可能`
- `限界的`
- `不可`

無理に Phase 4 の結論を維持しないでください。

## 8. Phase 7 — 最終統合レポート

[local-llm-selection-report.md](/mnt/d/Work/github-copilot-exercise/docs/report/local-llm-selection-report.md) を以下の順で埋めます。

1. Executive summary
2. 背景と目的
3. tool matrix 要約
4. shortlist benchmark 結果
5. model selection 結果
6. target validation 結果
7. local backend prototype の使い方
8. リスクと次ステップ

最終的に必ず 3 つを書きます。

- 採用 host
- 第一候補 model
- 代替候補 model

## 9. 実測完了条件

この手順書における完了条件は以下です。

- shortlist 3 本のうち 2 本以上で S1/S2/S3 完走
- host winner が 1 本に確定
- first-choice / backup model が各 1 本に確定
- mini PC 結論が `使用可能 / 限界的 / 不可` のいずれかで確定
- 最終レポートが review 可能な状態で保存済み

## 10. 失敗時の扱い

### Python / pip が使えない

- 実測開始前の環境不備として停止
- benchmark は回さない
- その旨を shortlist report の冒頭に記載

### host が S1 smoke で落ちる

- その tool は Phase 3 から除外
- 02 report に除外理由を記載

### host が S2/S3 で再起動を要する

- hard gate fail
- 02 report に「manual restart required」と明記

### mini PC が first-choice model を実用速度で回せない

- `限界的` か `不可`
- backup model の deploy を提案
