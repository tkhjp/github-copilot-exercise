# GitHub Copilot → Claude Code Tool Migration Guide

**Status:** Draft  
**Version:** v0.1  
**Last Updated:** 2026-09-10  
**Purpose:** GitHub Copilot から Claude Code への Skill / Agent 移行時における Tool 差分の整理と、実装担当者向け Migration Guideline

---

# 1. Executive Summary

GitHub Copilot と Claude Code の Tool は、**Capability の観点では大きく異ならない**。

両者とも、主に以下の Capability を提供している。

- File Read
- File Search
- File Edit / Write
- Shell Execution
- Web Access
- Agent Delegation
- Skill Invocation
- User Interaction
- MCP Integration

一方で、Tool の**粒度、命名、Permission の扱い**には差がある。

特に GitHub Copilot では、以下のような比較的抽象度の高い Alias が使われる。

```text
read
search
edit
execute
web
agent
```

Claude Code では、同じ Capability がより具体的な Tool に分割される。

```text
Read

Glob
Grep

Edit
Write

Bash

WebFetch
WebSearch

Agent
```

そのため、Migration の本質は単純な Tool Name の置換ではない。

> **Copilot の Abstract Capability を、Claude Code の Concrete Tool に再マッピングすること**

が基本となる。

Skill Migration において、特に確認が必要なのは以下の 6 項目である。

1. `search`
2. `edit`
3. `web`
4. `agent / task`
5. MCP Tool
6. `allowed-tools` / Permission

それ以外の多くの Tool は、基本的に Rename / Normalize で対応可能。

---

# 2. Big Picture — Tool Design に本質的な違いはあるか

まず全体像を以下に示す。

| 観点 | GitHub Copilot | Claude Code | Migration への影響 |
|---|---|---|---|
| Core Capability | Read / Search / Edit / Execute / Web / Agent / MCP | ほぼ同等 | 大きな再設計は不要 |
| Tool Granularity | 比較的抽象的な Alias が多い | より具体的な Tool に分割 | 1:N Mapping が発生 |
| Tool Naming | `read`, `search`, `edit`, `execute` など | `Read`, `Glob`, `Grep`, `Edit`, `Write`, `Bash` など | Normalize / Expand が必要 |
| Permission | Availability と Permission が分離 | 同様に分離 | 単純コピーせず再確認 |
| Migration の基本方針 | Capability ベースで解釈 | Concrete Tool に再マッピング | String Replace は避ける |

この章で押さえるべきポイントは 2 つだけである。

1. **Core Capability はほぼ共通**
2. **最大の差分は Tool の粒度と Permission の表現**

## 2.1 Capability 自体はほぼ共通

GitHub Copilot と Claude Code は、Agent が開発作業を行うために必要な主要 Capability をほぼ共通して持っている。

```text
Read
Search
Edit
Write
Execute
Web
Delegate
Skill
MCP
```

したがって Migration は、

```text
Copilot Tool Model
        ↓
完全に再実装
        ↓
Claude Tool Model
```

ではない。

より正確には、

```text
Same Core Capabilities
        +
Different Tool Granularity
        +
Different Naming
        +
Different Permission Semantics
```

として捉えるべきである。

---

## 2.2 最大の違いは Tool Granularity

GitHub Copilot では、比較的広い Capability を 1 つの Alias で表現するケースが多い。

例：

```text
search
```

は、実際には以下の両方を含み得る。

```text
File Discovery
Content Search
```

Claude Code では、それぞれ独立した Tool として定義される。

```text
Glob
→ Path / File Pattern Search

Grep
→ Content Search
```

同様に、

```text
edit
```

も Claude Code では、

```text
Edit
Write
NotebookEdit
```

に分解される。

したがって Migration では、以下のような **1:N Mapping** が発生する。

```text
Copilot
search
   ↓
Claude
Glob + Grep
```

```text
Copilot
edit
   ↓
Claude
Edit + Write
```

---

# 3. Migration Impact — 実際にどの Tool を対応すればよいか

Migration 対象は、大きく 3 Pattern に分けて考える。

| Pattern | 内容 | 代表 Tool | 対応方針 |
|---|---|---|---|
| **Pattern A — Direct Migration** | ほぼ 1:1 で移行可能 | `read`, `grep`, `glob`, `execute`, `web_fetch` | Rename / Normalize |
| **Pattern B — Semantic Migration** | 1:N または意味解釈が必要 | `search`, `edit`, `web`, `agent`, `task`, MCP | Skill の用途を確認して変換 |
| **Pattern C — Security Migration** | Tool 名ではなく Permission / Security の再設計が必要 | `allowed-tools`, URL, MCP Permission, Shell Permission | 別途 Security Review |

実務上、通常の Skill Migration で重点的に見るべきなのは **Pattern B と Pattern C** である。

Pattern A は原則として機械変換可能であり、Pattern B / C は Migration Engineer の判断が必要になる。

まず、Migration 対象を 3 つに分類する。

## Category A — 原則そのまま移行可能

| GitHub Copilot | Claude Code | Mapping | Migration Action |
|---|---|---|---|
| `read` / `view` | `Read` | 1:1 | Normalize |
| `grep` | `Grep` | 1:1 | Direct |
| `glob` | `Glob` | 1:1 | Direct |
| `execute` / `shell` / `bash` | `Bash` | 1:1 | Normalize |
| `web_fetch` | `WebFetch` | 1:1 | Direct |
| `ask_user` | `AskUserQuestion` | 1:1 | Direct |
| `skill` | `Skill` | 1:1 | Direct |

これらは基本的に、Skill の Workflow 自体を再設計する必要はない。

---

## Category B — 変換ロジックが必要

| GitHub Copilot | Claude Code | Mapping | Migration Action |
|---|---|---|---|
| `search` | `Glob` / `Grep` | 1:N | 要分析 |
| `edit` | `Edit` / `Write` / `NotebookEdit` | 1:N | 要分析 |
| `web` | `WebFetch` / `WebSearch` | 1:N | 要分析 |
| `agent` | `Agent` | Semantic | 要確認 |
| `task` | `Agent` or Task APIs | Semantic | 要確認 |
| `todo` | Task APIs | Different Model | Manual Review |
| MCP Tool | MCP Tool | Naming / Permission 差分 | Manual Review |

---

## Category C — Security / Permission として別途扱う

以下は単純な Tool Mapping ではなく、Permission Model の Migration として扱う。

- `allowed-tools`
- Tool Allow / Deny
- Shell Command Permission
- URL Access Control
- MCP Permission
- Subagent Tool Allowlist
- Sandbox / Hook による Enforcement

---

# 4. Migration 対応が必要な Tool

この章では、Pattern B / C に該当する Tool を個別に扱う。

| Tool / Theme | 主な差分 | Migration 時に判断すること | Risk |
|---|---|---|---|
| `search` | 1 Tool → `Glob` / `Grep` | File Search か Content Search か | Medium |
| `edit` | 1 Tool → `Edit` / `Write` / `NotebookEdit` | 既存編集か、新規作成か | Medium |
| `web` | 1 Tool → `WebFetch` / `WebSearch` | Known URL か Discovery か | Medium |
| `agent / task` | 名前と意味が一致しない場合あり | Delegation か Task Tracking か | High |
| MCP | Tool Naming / Permission が異なる | Runtime-specific ID をどう扱うか | High |
| Permission | Tool Mapping とは別問題 | Availability / Approval / Enforcement | High |

以下、上から順に Migration Rule を整理する。

---

# 4.1 Search

## GitHub Copilot

GitHub Copilot では、以下のように定義されることがある。

```yaml
tools:
  - search
```

`search` は抽象 Capability であり、実際には以下を含み得る。

```text
File Discovery
Content Search
```

---

## Claude Code

Claude Code では明確に 2 つの Tool に分かれる。

```text
Glob
→ ファイル名・Path Pattern による検索

Grep
→ ファイル内容の検索
```

---

## Migration Rule

単純に、

```text
search → Glob + Grep
```

と変換しても動作するケースは多いが、推奨は Skill の用途に応じて判断すること。

```text
ファイルを探す
→ Glob

コード・文字列を検索する
→ Grep

両方必要
→ Glob + Grep
```

---

## Example

### Before

```text
Search for all unit test files related to FooService.
```

### After

```text
Locate candidate test files using file-pattern search.
Search file contents when necessary to identify tests related to FooService.
```

---

## Migration Decision

```text
IF file discovery is required
    → Glob

IF content search is required
    → Grep

IF both are required
    → Glob + Grep
```

---

# 4.2 Edit / Write

## GitHub Copilot

Copilot の `edit` は、広い意味で File Modification Capability として扱われる。

以下を含む可能性がある。

```text
Modify existing file
Create new file
Modify Notebook
```

---

## Claude Code

Claude Code では用途別に分かれる。

```text
Edit
→ 既存ファイルの部分編集

Write
→ 新規ファイル作成 / ファイル全体の書き込み

NotebookEdit
→ Notebook Cell の編集
```

---

## Migration Rule

```text
既存ファイルのみ変更
→ Edit

新規ファイルを作成する可能性あり
→ Edit + Write

Notebook を操作
→ NotebookEdit を追加
```

---

## Example — Unit Test Skill

以下の Skill が存在するとする。

```text
Generate unit tests for FooService.
```

Test File が存在しない場合、新規ファイル作成が必要になる。

したがって、

```text
edit
→ Edit
```

だけでは不十分。

推奨：

```text
edit
→ Edit + Write
```

---

## Migration Decision

```text
Does the skill create files?

YES
→ Edit + Write

NO
→ Edit
```

Notebook を扱う場合のみ `NotebookEdit` を追加する。

---

# 4.3 Web

## GitHub Copilot

Copilot では以下のような抽象 Alias を利用できる。

```text
web
```

これは Web Fetch と Web Search の両方を意味し得る。

---

## Claude Code

Claude Code では分離されている。

```text
WebFetch
→ 既知 URL の取得

WebSearch
→ Web 上で情報を検索
```

---

## Migration Rule

```text
URL が既知
→ WebFetch

Web 上から情報を探す
→ WebSearch

検索後にページ取得も必要
→ WebSearch + WebFetch
```

---

## Example

### Case A

```text
Read the official API documentation at the provided URL.
```

→ `WebFetch`

### Case B

```text
Find the latest official API documentation.
```

→ `WebSearch`

### Case C

```text
Find the official documentation and inspect the relevant page.
```

→ `WebSearch + WebFetch`

---

# 4.4 Agent / Task

ここは Tool 名だけを見ると誤変換しやすいため注意が必要。

---

## GitHub Copilot

Copilot で、

```text
agent
task
```

が以下の意味で使われる場合がある。

> 他の Agent に Task を委譲する

---

## Claude Code

Claude Code で Subagent を起動する Tool は、

```text
Agent
```

である。

一方 Claude Code には別途、

```text
TaskCreate
TaskGet
TaskList
TaskUpdate
```

が存在する。

これは **Task Tracking** 用であり、Subagent Spawn ではない。

---

## Migration Rule

名前ではなく、意味で判断する。

```text
Copilot task
```

が、

```text
Delegate work to another agent
```

を意味する場合：

```text
→ Claude Agent
```

一方、

```text
Track work items
```

を意味する場合：

```text
→ Claude Task APIs
```

---

## Important

以下の変換は避ける。

```text
Copilot task
→ Claude TaskCreate
```

単に Tool Name が似ているだけでは Migration できない。

---

# 4.5 MCP

MCP 自体の基本 Concept は両者で共通している。

```text
Agent
 ↓
MCP Server
 ↓
MCP Tool
```

しかし、Tool Naming と Permission Expression には差がある。

---

## GitHub Copilot Example

```text
github/create_issue
```

あるいは Server / Tool 単位の指定。

---

## Claude Code Example

```text
mcp__github__create_issue
```

---

## Migration Recommendation

Skill 本文では、Runtime-specific な Tool Name をできるだけ直接記述しない。

### Avoid

```text
Call mcp__github__create_issue.
```

### Prefer

```text
Create a GitHub issue using the configured GitHub integration.
```

Tool Name や Permission は、

- Agent Definition
- MCP Configuration
- Permission Configuration

側で管理する。

---

## Reason

Skill 内に Tool ID を Hard-code すると、

```text
GitHub Copilot
Claude Code
Future Runtime
```

間で Skill を再利用しにくくなる。

---

# 4.6 Permission / allowed-tools

Tool Migration と Permission Migration は分けて考える必要がある。

---

## Important Concept

```text
Tool Availability
≠
Tool Permission
```

---

## Tool Availability

Agent が Tool を利用可能かどうか。

例：

```yaml
tools:
  - Read
  - Grep
  - Glob
```

これは Agent の Capability Boundary。

---

## Tool Permission

Tool を呼び出す際に、追加 Approval が必要かどうか。

Skill で利用される、

```yaml
allowed-tools:
```

は、単純な Tool Sandbox と考えるべきではない。

より正確には、

> Tool の Pre-approval / Permission Control

として扱う。

---

## Migration Guideline

Security Boundary を本当に保証する必要がある場合、

```text
Skill allowed-tools
```

だけに依存しない。

以下を組み合わせる。

```text
Subagent tools
Permission Rules
Sandbox
Hooks
```

---

# 5. Full Migration Matrix

| Copilot Tool / Alias | Claude Code | Mapping Type | Action |
|---|---|---|---|
| `read` | `Read` | 1:1 | Auto |
| `view` | `Read` | 1:1 | Auto |
| `grep` | `Grep` | 1:1 | Auto |
| `glob` | `Glob` | 1:1 | Auto |
| `search` | `Glob` + `Grep` | 1:N | Review |
| `execute` | `Bash` | 1:1 | Auto |
| `shell` | `Bash` | 1:1 | Auto |
| `bash` | `Bash` | 1:1 | Auto |
| `powershell` | `PowerShell` | 1:1 | Auto |
| `edit` | `Edit` / `Write` / `NotebookEdit` | 1:N | Review |
| `create` | `Write` | 1:1 | Auto |
| `apply_patch` | `Edit` | Behavior Mapping | Review |
| `web_fetch` | `WebFetch` | 1:1 | Auto |
| `web` | `WebFetch` / `WebSearch` | 1:N | Review |
| `agent` | `Agent` | Semantic | Review |
| `task` | `Agent` or Task APIs | Semantic | Review |
| `todo` | Task APIs | Different Model | Manual |
| `ask_user` | `AskUserQuestion` | 1:1 | Auto |
| `skill` | `Skill` | 1:1 | Auto |
| MCP Tool | MCP Tool | Naming / Permission | Manual |
| URL Permission | Web / Bash / Sandbox Policy | Security | Manual |

---

# 6. Skill Migration Procedure

Skill Migration は、以下の 4 Phase に分けて進める。

| Phase | 目的 | 主な確認対象 | Output |
|---|---|---|---|
| **Phase 1 — Discover** | Tool 使用箇所を洗い出す | Frontmatter / Skill Body | Tool Inventory |
| **Phase 2 — Classify** | Mapping Type を判定 | 1:1 / 1:N / Semantic / Permission | Migration Decision |
| **Phase 3 — Convert** | Claude 向けに変換 | Tool Name / Skill Body / Permission | Converted Skill |
| **Phase 4 — Validate** | 挙動を確認 | Tool Selection / File Change / Command | Validation Result |

1 つの `SKILL.md` を移行する際には、以下の順序で確認する。

```text
STEP 1
Open SKILL.md

↓

STEP 2
Check Frontmatter

tools:
allowed-tools:

↓

STEP 3
Search Tool References in Body

read
search
edit
execute
web
task
agent
MCP

↓

STEP 4
Classify Mapping

1:1
1:N
Semantic
Permission

↓

STEP 5
Convert Tool References

↓

STEP 6
Clean Runtime-specific Instructions

↓

STEP 7
Run Behavioral Test
```

---

# 7. Decision Tree

## 7.1 Search

```text
Found "search"
      │
      ↓
Is file discovery required?
   ┌──┴──┐
  YES   NO
   ↓
 Glob
        │
        ↓
Is content search required?
   ┌──┴──┐
  YES   NO
   ↓
 Grep
```

両方必要な場合：

```text
Glob + Grep
```

---

## 7.2 Edit

```text
Found "edit"
      │
      ↓
Does the Skill create files?
   ┌──┴──┐
  YES   NO
   ↓     ↓
Write   Edit
 +
Edit
```

Notebook を扱う場合：

```text
+ NotebookEdit
```

---

## 7.3 Web

```text
Found "web"
      │
      ↓
Known URL?
 ┌────┴────┐
YES       NO
 ↓          ↓
WebFetch   Need discovery?
              ↓
          WebSearch
```

---

## 7.4 Task

```text
Found "task"
      │
      ↓
Does it delegate work to another agent?
   ┌──┴──┐
  YES   NO
   ↓
 Agent
        │
        ↓
Does it track work items?
   ┌──┴──┐
  YES   NO
   ↓
Task APIs
```

---

# 8. Skill Migration Example

## Before — GitHub Copilot

```yaml
---
name: generate-unit-tests
description: Generate unit tests for existing implementation code.
allowed-tools:
  - read
  - search
  - edit
  - execute
---

1. Search for the target implementation.
2. Read existing tests.
3. Generate a new test file.
4. Execute the tests.
```

---

## Mapping Analysis

```text
read
→ Read

search
→ Glob + Grep

edit
→ Skill may create new test files
→ Edit + Write

execute
→ Bash
```

---

## After — Claude Code

```yaml
---
name: generate-unit-tests
description: Generate unit tests for existing implementation code.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
---

1. Locate the target implementation and relevant existing tests.
2. Inspect the relevant source and test files.
3. Create or modify the required test files.
4. Run the relevant tests.
```

---

# 9. Skill 本文の書き方

Migration を機に、Skill 本文は Runtime-specific Tool Name に依存しすぎない形に統一することを推奨する。

---

## Avoid

```text
Use search.
Call read.
Use edit.
Run execute.
```

この書き方は GitHub Copilot の Tool Abstraction に強く依存する。

---

## Prefer

```text
Locate the relevant files.
Inspect their contents.
Create or modify the necessary files.
Run the relevant validation command.
```

Runtime 側では以下のように解決できる。

```text
Locate
→ Glob / Grep

Inspect
→ Read

Create / Modify
→ Write / Edit

Run
→ Bash
```

---

# 10. Recommended Canonical Capability Model

社内で Skill / Agent Standard を作成する場合、Runtime Tool Name を直接標準化するより、Capability を標準化する方が望ましい。

例：

```text
READ
SEARCH_FILE
SEARCH_CONTENT
EDIT
WRITE
EXECUTE
WEB_FETCH
WEB_SEARCH
DELEGATE
ASK_USER
USE_SKILL
MCP
```

Runtime Adapter のイメージ：

```text
                 Canonical Capability
                         │
             ┌───────────┴───────────┐
             ↓                       ↓
      GitHub Copilot             Claude Code

READ
→ read / view                  → Read

SEARCH_FILE
→ search / glob                → Glob

SEARCH_CONTENT
→ search / grep                → Grep

EDIT
→ edit                         → Edit

WRITE
→ edit / create                → Write

EXECUTE
→ execute / shell / bash       → Bash

DELEGATE
→ agent / task                 → Agent
```

これにより、将来的に Runtime が変更されても Skill 自体の変更量を抑えられる。

---

# 11. Migration Checklist

Checklist は 4 Category で確認する。

| Category | 目的 | 代表確認項目 |
|---|---|---|
| **Tool** | Tool Mapping の正しさ | `search`, `edit`, `web`, `agent/task`, MCP |
| **Permission** | Security / Approval の正しさ | `allowed-tools`, Shell, URL, MCP |
| **Skill Body** | Runtime 依存の削減 | Tool 名の Hard-code、Capability-oriented 表現 |
| **Validation** | 実行結果の確認 | Read / Write / Command / Forbidden Behavior |

Skill 単位で以下を確認する。

## Tool

- [ ] `read` / `view` を確認
- [ ] `search` を `Glob` / `Grep` に分解
- [ ] `edit` が File Creation を含むか確認
- [ ] `web` が Fetch / Search のどちらか確認
- [ ] `agent` / `task` の意味を確認
- [ ] MCP Tool Name を確認

## Permission

- [ ] `allowed-tools` の意味を確認
- [ ] Shell Permission を確認
- [ ] URL Permission を確認
- [ ] MCP Permission を確認
- [ ] Subagent Tool Allowlist を確認

## Skill Body

- [ ] Copilot-specific Tool Name を検索
- [ ] Runtime-specific Instruction を減らす
- [ ] Capability-oriented Expression に変更

## Validation

- [ ] Claude Code で Skill が Discovery される
- [ ] 正しい Tool が選択される
- [ ] 必要な File を Read できる
- [ ] 必要な File を Create / Edit できる
- [ ] Command が正しく実行される
- [ ] 不要な Tool を使用していない

---

# 12. Migration Priority

## P0

以下は必ず確認する。

```text
search
edit
web
agent/task
MCP
allowed-tools / Permission
```

---

## P1

以下は自動 Normalize 可能。

```text
read
view
grep
glob
execute
shell
bash
web_fetch
ask_user
skill
```

---

## P2

Claude 固有の追加機能は、初期 Migration では原則導入しない。

例えば：

```text
LSP
Monitor
EnterPlanMode
Worktree
Task APIs
Workflow
Agent Messaging
```

初期 Migration では、

> **Copilot の既存 Capability を Claude Code 上で同等に再現すること**

を優先する。

Claude 固有の最適化は Migration 完了後に行う。

---

# 13. Final Guideline

Tool Migration では、以下の順序で判断する。

```text
Tool Name
    ↓
Capability
    ↓
Claude Tool
```

単純な String Replace は行わない。

---

## Rule 1

Core Capability は大きく変わらない。

---

## Rule 2

Copilot は比較的 Abstract、Claude Code は比較的 Concrete。

そのため、

```text
1 Copilot Alias
      ↓
N Claude Tools
```

になるケースがある。

---

## Rule 3

特に注意する Tool は以下。

```text
search
edit
web
agent/task
MCP
Permission
```

---

## Rule 4

Skill は、

```text
What should be done
```

を表現する。

Runtime-specific Tool Name は必要な場合のみ明示する。

---

## Rule 5

Security Boundary は Skill の自然言語だけに依存しない。

```text
Subagent Tool Availability
Permission
Sandbox
Hooks
```

で Enforcement する。

---

# Appendix A — GitHub Copilot Tool Catalog

Appendix は以下の目的で分けている。

| Appendix | Purpose |
|---|---|
| **Appendix A** | GitHub Copilot 側の Tool / Alias を確認する |
| **Appendix B** | Claude Code 側の Tool を確認する |
| **Appendix C** | Capability 単位で両者を Cross-reference する |
| **Appendix D** | Migration Tool / Linter 実装時の分類ルールとして利用する |

本文で Migration 方針を理解した後、個別 Tool を確認する際に参照することを想定する。

以下は Migration 時に参照する主要 Tool / Alias。

| Tool / Alias | Definition | Migration Note |
|---|---|---|
| `read` | File Read Capability | Claude `Read` |
| `view` | File / Directory Read | Claude `Read` |
| `search` | Abstract Search Capability | `Glob` / `Grep` に分解 |
| `grep` | Content Search | Claude `Grep` |
| `glob` | File Pattern Search | Claude `Glob` |
| `edit` | Broad File Modification Capability | `Edit` / `Write` |
| `create` | Create File | Claude `Write` |
| `apply_patch` | Patch-based File Modification | Claude `Edit` 相当として要確認 |
| `execute` | Command Execution Capability | Claude `Bash` |
| `shell` | Shell Execution | Claude `Bash` |
| `bash` | Bash Execution | Claude `Bash` |
| `powershell` | PowerShell Execution | Claude `PowerShell` |
| `web` | Web Capability | `WebFetch` / `WebSearch` |
| `web_fetch` | URL Fetch | Claude `WebFetch` |
| `agent` | Agent Delegation | Claude `Agent` |
| `task` | Subagent Delegation または Task | Semantic Review |
| `todo` | Todo / Work Tracking | Claude Task APIs を要確認 |
| `ask_user` | User Interaction | Claude `AskUserQuestion` |
| `skill` | Skill Invocation | Claude `Skill` |
| MCP Tool | External MCP Capability | Naming / Permission 差分あり |

---

# Appendix B — Claude Code Tool Catalog

| Claude Tool | Definition | GitHub Copilot Equivalent |
|---|---|---|
| `Read` | File Content Read | `read`, `view` |
| `Glob` | File / Path Pattern Search | `glob`, `search` |
| `Grep` | Content Search | `grep`, `search` |
| `Edit` | Existing File Modification | `edit`, `apply_patch` |
| `Write` | File Create / Full Write | `edit`, `create` |
| `NotebookEdit` | Notebook Cell Modification | `edit` |
| `Bash` | Shell Command Execution | `execute`, `shell`, `bash` |
| `PowerShell` | PowerShell Execution | `powershell` |
| `WebFetch` | Fetch Known URL | `web_fetch`, `web` |
| `WebSearch` | Search Web | `web` |
| `Agent` | Spawn / Delegate to Subagent | `agent`, `task` |
| `Skill` | Invoke Skill | `skill` |
| `AskUserQuestion` | Ask User for Input | `ask_user` |
| `TaskCreate` | Create Tracked Task | `todo` / task management |
| `TaskGet` | Get Task | task management |
| `TaskList` | List Tasks | task management |
| `TaskUpdate` | Update Task | task management |
| `LSP` | Code Intelligence | No simple 1:1 mapping |
| `Monitor` | Monitor long-running command / event | Runtime-specific |
| `EnterPlanMode` | Enter Planning Mode | No direct Copilot alias |
| `ExitPlanMode` | Exit Planning Mode | No direct Copilot alias |
| `EnterWorktree` | Enter isolated Worktree | No direct Copilot alias |
| `ExitWorktree` | Exit Worktree | No direct Copilot alias |
| MCP Tool | External MCP Capability | MCP |

---

# Appendix C — Cross-platform Tool Mapping Matrix

| Capability | GitHub Copilot | Claude Code | Risk |
|---|---|---|---|
| Read File | `read`, `view` | `Read` | Low |
| Find File | `search`, `glob` | `Glob` | Medium |
| Search Content | `search`, `grep` | `Grep` | Medium |
| Modify Existing File | `edit`, `apply_patch` | `Edit` | Medium |
| Create File | `edit`, `create` | `Write` | Medium |
| Notebook Edit | `edit` | `NotebookEdit` | Medium |
| Execute Shell | `execute`, `shell`, `bash` | `Bash` | Low |
| PowerShell | `powershell` | `PowerShell` | Low |
| Fetch URL | `web`, `web_fetch` | `WebFetch` | Medium |
| Search Web | `web` | `WebSearch` | Medium |
| Delegate Agent | `agent`, `task` | `Agent` | High |
| Track Work | `todo`, task-related behavior | Task APIs | High |
| Ask User | `ask_user` | `AskUserQuestion` | Low |
| Invoke Skill | `skill` | `Skill` | Low |
| External Tool | MCP | MCP | High |
| Tool Pre-approval | `allowed-tools` | `allowed-tools` | High |
| Tool Availability | Agent `tools` | Agent `tools` | Medium |
| URL Restriction | URL Permission | Web / Bash / Sandbox Policy | High |

---

# Appendix D — Recommended Migration Classification

Migration Tool / Linter を実装する場合、各 Tool を以下の 5 種類に分類することを推奨する。

```text
SAFE_AUTO_CONVERT
EXPAND
SEMANTIC_REVIEW
SECURITY_REVIEW
ARCHITECTURE_REVIEW
```

例：

```yaml
read:
  target:
    - Read
  migration: SAFE_AUTO_CONVERT

search:
  target:
    - Glob
    - Grep
  migration: EXPAND

edit:
  target:
    - Edit
    - Write
  migration: SEMANTIC_REVIEW

web:
  target:
    - WebFetch
    - WebSearch
  migration: SEMANTIC_REVIEW

agent:
  target:
    - Agent
  migration: ARCHITECTURE_REVIEW

mcp:
  migration: SECURITY_REVIEW
```

この分類を利用することで、Skill Migration を単純な文字列変換ではなく、再現性のある Migration Process として実施できる。
