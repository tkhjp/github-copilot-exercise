# GitHub Copilot → Claude Code

# Agent / Skill 移行ガイドライン

**Status:** Draft
**Version:** v0.1
**Last Updated:** 2026-09-03
**Target Audience:** AI Engineering / Developer Productivity / Agent Development Team

---

# 1. Executive Summary

当社では、GitHub Copilot から Claude Code への段階的な移行を予定している。

現時点では GitHub Copilot をベースとして、以下の資産がすでに多数存在している。

* Custom Agents
* Agent Skills
* Prompt Files
* Repository / Path-specific Instructions
* Agent-to-Agent Workflow
* Tool / MCP Integration
* Hooks

今回の移行は、単純な

```text
.github/*
    ↓
.claude/*
```

というファイル構成の変換ではない。

より正確には、

> **Agent Runtime / Agent Architecture Migration**

として扱う必要がある。

本移行では、主に以下の点を整理する。

1. 既存資産のうち、そのまま再利用できるもの
2. Copilot Agent から Claude Subagent へ移行すべきもの
3. Copilot Agent ではあるが、実際には Skill として再設計すべきもの
4. Instructions を `CLAUDE.md` または `.claude/rules/` のどちらに移行するか
5. Agent / Subagent / Skill の責務境界
6. Tool / Permission / MCP / Hooks の再設計
7. 移行前後の挙動を Regression Test でどのように検証するか
8. 最終的に、複数 Repository で再利用可能な社内標準 Claude Code 基盤をどのように構築するか

基本方針は以下とする。

> **Skill Migration は主に互換性とコンテンツ整理の問題である。**
> **Agent / Subagent Migration は主にアーキテクチャ設計の問題である。**

既存の Copilot Agent を機械的に 1:1 で Claude Agent に変換することは推奨しない。

---

# 2. Migration Goal

本 Migration の目的は、単に既存 Copilot Agent を Claude Code 上で動作可能にすることではない。

長期的に保守可能な Agent Configuration Architecture を構築することを目標とする。

想定する Target Architecture は以下。

```text
                    Claude Code
                         │
                  Main Conversation
                         │
              ┌──────────┴──────────┐
              │                     │
            Skills               Subagents
              │                     │
       Reusable Workflow      Isolated Workers
              │                     │
              └──────────┬──────────┘
                         │
                 Project Knowledge
                         │
          CLAUDE.md / .claude/rules
                         │
              ┌──────────┴─────────┐
              │                    │
             MCP                 Hooks
              │                    │
       External Systems     Deterministic Control
```

さらに将来的には、以下の 2 レイヤー構成を目指す。

```text
Company Shared Capability
        │
        ↓
Claude Plugin / Managed Configuration
        │
        ├── Shared Skills
        ├── Shared Agents
        ├── Hooks
        └── MCP Integration

Repository Specific Capability
        │
        ↓
CLAUDE.md
.claude/rules/
.claude/skills/
.claude/agents/
```

---

# 3. Current Platform Facts

本章では、2026-09-03 時点のプラットフォーム仕様上の事実を整理する。

ここで記載する内容は、後述する当社推奨アーキテクチャとは区別して扱う。

---

# 3.1 GitHub Copilot の主な Customization Object

GitHub Copilot では、主に以下の拡張要素が利用可能である。

| Object              | Purpose                                |
| ------------------- | -------------------------------------- |
| Custom Instructions | Repository / Coding Convention         |
| Prompt Files        | 再利用可能な Prompt Template                 |
| Custom Agents       | 特定用途向け Agent 定義                        |
| Subagents           | Main Agent から委譲される独立実行単位               |
| Agent Skills        | 再利用可能な Instruction / Script / Resource |
| Hooks               | Deterministic なイベント処理                  |
| MCP Servers         | 外部 Tool / System との統合                  |

GitHub Copilot の Agent Skills は以下のディレクトリに配置可能。

```text
.github/skills/<skill>/SKILL.md
.claude/skills/<skill>/SKILL.md
.agents/skills/<skill>/SKILL.md
```

また、GitHub Copilot の Agent Skills は Agent Skills の Open Specification をベースとしている。

そのため、

> **既存 Skill は、今回の Migration において最も移植性の高い資産である。**

---

# 4. Claude Code Extension Model

Claude Code では、主に以下の要素でプロジェクトをカスタマイズする。

```text
CLAUDE.md
.claude/rules/
.claude/skills/
.claude/agents/
.claude/settings.json
.mcp.json
Plugins
```

各要素の責務を明確に分離することが重要である。

---

# 4.1 CLAUDE.md

`CLAUDE.md` は、Repository 全体で恒常的に有効となるプロジェクト情報を保存する。

代表例：

* Repository Architecture
* Build Command
* Test Command
* Coding Convention
* Directory Responsibility
* Important Architectural Decision
* Project-wide Restriction

Claude Code は `CLAUDE.md` をプロジェクトコンテキストとして読み込む。

したがって、

> `CLAUDE.md` は主に **Facts / Rules / Context** を記載する場所とし、複雑な Workflow は記述しない。

また、内容は簡潔に保つことが望ましい。

---

# 4.2 `.claude/rules/`

特定の Path、言語、ファイル種別だけに適用したいルールは、

```text
.claude/rules/
```

に配置する。

例：

```yaml
---
paths:
  - "**/*.java"
---

# Java Rules

...
```

そのため GitHub Copilot の、

```text
.github/instructions/*.instructions.md
```

は、基本的には

```text
.claude/rules/*.md
```

への移行候補となる。

---

# 5. Skills

# 5.1 Skill の位置付け

Skill は、

> **Reusable Capability / Knowledge / Procedure**

を表現する。

例えば以下。

* Unit Test をどのように生成するか
* Testability をどのように分析するか
* Test をどのように Review するか
* プロジェクト固有の標準作業フロー
* 内部 Script の利用方法
* Task 実行時の Checklist
* Domain-specific Knowledge

Claude Code では、

```text
.claude/skills/<skill-name>/SKILL.md
```

として管理する。

Skill は description に基づいて自動的に利用されるほか、

```text
/skill-name
```

のように明示的に実行することも可能。

そのため、

> **Skill は Agent Runtime に依存しない Canonical Asset として管理することを推奨する。**

---

# 5.2 Recommended Canonical Location

Migration 初期では、Skill の配置先を段階的に

```text
.claude/skills/
```

へ統一することを推奨する。

理由：

1. Claude Code が Native に利用可能
2. GitHub Copilot 側でも同ディレクトリを利用可能
3. Dual-run 期間に Skill を二重管理する必要がない

イメージ：

```text
                 .claude/skills
                    /       \
                   /         \
                  ↓           ↓
          GitHub Copilot   Claude Code
```

原則として、長期的に

```text
.github/skills/foo
.claude/skills/foo
```

という 2 系統管理は避ける。

---

# 6. Subagent

# 6.1 Claude Subagent の定義

Claude Code では、

```text
.claude/agents/*.md
```

により Custom Subagent を定義する。

Subagent は Main Agent から独立した実行単位であり、以下を個別に持つことができる。

* 独立した Context Window
* 独立した System Prompt
* 独立した Tools
* 独立した Permission
* Model 指定
* Skills Preload
* MCP
* Hooks
* Worktree Isolation
* 独立した Execution Context

実行後は、結果を Parent Agent に返す。

したがって Subagent は、単なる

> 「別 Persona の Agent」

ではない。

より重要なのは、

> **Context Isolation + Capability Isolation + Permission Isolation**

である。

---

# 7. Why Subagent Matters

例えば Main Agent が以下をすべて直接実行した場合、

```text
Search 500 files
↓
Read 50 files
↓
Run test
↓
Read 20,000 lines log
↓
Analyze stack trace
↓
Generate code
```

すべての情報が Main Context に蓄積される。

一方、Subagent を利用した場合、

```text
Main Agent
    │
    ↓
Test Runner Subagent
    │
    ├── execute tests
    ├── consume 20,000 lines logs
    └── analyze failures
    │
    ↓
Structured Summary
    │
    ↓
Main Agent
```

Main Agent 側には、例えば以下だけを返すことができる。

```text
3 tests failed.

Root causes:
1. ...
2. ...
3. ...

Recommended actions:
...
```

その結果、

* Main Context の肥大化抑制
* Context Pollution の削減
* Agent ごとの責務分離
* Tool Permission の分離

が可能になる。

---

# 8. Built-in Subagents

Claude Code には Built-in Subagent が存在する。

代表的なもの：

```text
Explore
Plan
General-purpose
```

### Explore

主に以下の用途。

```text
Repository Search
File Discovery
Code Analysis
```

Read-only な Codebase Exploration に向いている。

### Plan

Planning 時の Codebase Research に利用される。

### General-purpose

探索と実行を伴う比較的複雑な Multi-step Task に向く。

したがって Migration 時には、

> 既存 Copilot Agent が Claude の Built-in Subagent で代替可能か

を必ず確認する。

例えば、

```text
repository-explorer.agent
```

の役割が単に

```text
Search code
Read code
Explain architecture
```

であれば、Custom Subagent として移行せず、Built-in Explore を利用できる可能性が高い。

---

# 9. Core Migration Mapping

推奨する基本マッピングは以下。

| GitHub Copilot Asset             | Claude Code Target                       | Migration Strategy |
| -------------------------------- | ---------------------------------------- | ------------------ |
| Agent Skill                      | Skill                                    | 可能な限り再利用           |
| Custom Agent - Workflow-oriented | Skill                                    | 再設計                |
| Custom Agent - Specialist Worker | Subagent                                 | 変換                 |
| Custom Agent - Entry Persona     | Main Agent / Skill / Subagent Definition | Case-by-case       |
| Repository Instructions          | CLAUDE.md                                | 整理して移行             |
| Path-specific Instructions       | `.claude/rules/`                         | 変換                 |
| Prompt File                      | Skill                                    | 原則統合               |
| Tool Restrictions                | Subagent Tools / Permission              | 再定義                |
| MCP                              | `.mcp.json` / Subagent MCP               | 再設定                |
| Hooks                            | Claude Hooks                             | 再設定                |
| Agent Handoff                    | Subagent Delegation                      | 再設計                |
| Shared Company Assets            | Claude Plugin / Managed Configuration    | Phase 2            |

---

# 10. 1:1 Agent Conversion を行わない

今回の Migration で最も重要な原則の一つ。

以下のような機械変換は原則禁止とする。

```text
.github/agents/foo
        ↓
.claude/agents/foo
```

すべての既存 Agent に対して、まず Classification を実施する。

---

# 11. Agent Classification

既存 Copilot Agent ごとに、以下を確認する。

## Question 1

この Agent の実態は固定的な Workflow / Procedure か。

例：

```text
Analyze production code
↓
Find existing tests
↓
Generate tests
↓
Run tests
```

この場合：

```text
→ Skill
```

---

## Question 2

独立 Context が必要か。

例：

```text
Repository-wide search
Large log analysis
Large document analysis
Test execution
```

この場合：

```text
→ Subagent
```

---

## Question 3

独立 Tool Permission が必要か。

例：

```text
Reviewer → Read-only

Writer → Write allowed

Runner → Bash allowed
```

この場合：

```text
→ Subagent
```

---

## Question 4

単なる Coding Rule か。

例：

```text
Java service should use constructor injection.
```

この場合：

```text
→ Rule / CLAUDE.md
```

---

## Question 5

外部システム連携が主目的か。

例：

```text
Jira
GitHub
Database
Internal API
```

この場合：

```text
→ MCP
```

---

## Question 6

決定論的な制御か。

例：

```text
After editing *.java
always run formatter.
```

この場合：

```text
→ Hook
```

とするべきであり、Agent に依存させない。

---

# 12. Recommended Agent Classification Model

Inventory 時に、各 Agent を以下のいずれかに分類する。

```text
ENTRY
WORKER
WORKFLOW
RULE
INTEGRATION
ENFORCEMENT
REDUNDANT
```

対応関係：

```text
ENTRY
  ↓
Main Claude / Main Agent Configuration

WORKER
  ↓
Subagent

WORKFLOW
  ↓
Skill

RULE
  ↓
CLAUDE.md / Rule

INTEGRATION
  ↓
MCP

ENFORCEMENT
  ↓
Hook

REDUNDANT
  ↓
Delete / Built-in Capability
```

---

# 13. Subagent Design Guideline

Subagent に移行する Agent は、単純なフォーマット変換ではなく再設計する。

少なくとも以下を定義する。

```text
Purpose
Trigger / Description
Input Contract
Output Contract
Context Boundary
Tool Boundary
Skill Dependency
Permission Boundary
Model
Side Effects
Spawn Policy
```

---

# 14. Context Boundary

例：

## Test Runner Subagent

### Input

```text
Target modules
Relevant test files
Test scope
```

### Internal Context

以下は Subagent 内部で処理する。

```text
Test commands
Build logs
Stack traces
Failure logs
Coverage results
```

### Output

Parent Agent には要約された構造化結果だけを返す。

```yaml
status: failed

failures:
  - test: FooServiceTest.testCreate
    type: assertion
    root_cause: unexpected null

recommended_actions:
  - ...
```

原則：

> Parent Agent に Full Test Log を返さない。

---

# 15. Tool Boundary

Subagent には Least Privilege を適用する。

## Explorer / Analyzer

```text
Read
Grep
Glob
```

原則禁止：

```text
Write
Edit
```

---

## Reviewer

```text
Read
Grep
Glob
```

原則 Read-only。

---

## Test Writer

```text
Read
Grep
Glob
Edit
Write
```

必要に応じて：

```text
Bash
```

---

## Test Runner

```text
Read
Grep
Glob
Bash
```

原則として Production Code の変更は禁止。

---

理想的には以下のように責務を分ける。

```text
Analyzer
    → read

Reviewer
    → read

Writer
    → write

Runner
    → execute
```

以下のような構成は避ける。

```text
Every Agent
    → all tools
```

---

# 16. Skill vs Subagent

Skill と Subagent の役割は明確に分離する。

### Skill

以下に答える。

> **How should this task be done?**

例：

```text
How to generate UT
How to review tests
How to analyze failure
```

### Subagent

以下に答える。

> **Which isolated execution context should perform this work?**

推奨構造：

```text
Subagent
    │
    ├── Skill A
    ├── Skill B
    └── Skill C
```

避けるべき構造：

```text
Subagent Prompt
    │
    └── Copy 500 lines Skill content
```

Skill は Single Source of Truth とし、Subagent から参照・Preload する。

---

# 17. Example: UT Agent Migration

現状の Copilot が以下だとする。

```text
UT Agent
   │
   ├── Code Analyze Agent
   ├── Test Generate Agent
   ├── Test Runner Agent
   └── Test Review Agent
```

これを単純に Claude の 4 Agent に変換するのではなく、例えば以下のように再設計する。

```text
                    Main Claude
                         │
                         ↓
                 generate-ut Skill
                         │
             ┌───────────┴────────────┐
             ↓                        ↓
        Analyzer                  UT Writer
        Subagent                  Subagent
             │                        │
             └──────────┬─────────────┘
                        ↓
                  Test Runner
                   Subagent
                        │
                        ↓
                   Reviewer
                   Subagent
                        │
                        ↓
                    Summary
```

責務：

```text
generate-ut
    = Workflow

Analyzer
    = Isolated Research Worker

UT Writer
    = Write Capability

Runner
    = High-volume Execution Worker

Reviewer
    = Independent Read-only Verification
```

---

# 18. Prompt Files

Copilot の

```text
.github/prompts/generate-ut.prompt.md
```

のような Prompt File は、Claude Code では原則 Skill に統合する。

例：

```text
.claude/skills/generate-ut/SKILL.md
```

長期的に、

```text
Prompt
Skill
Agent
```

の 3 種類で同じ Workflow を表現する状態は避ける。

---

# 19. MCP Migration

MCP は、

> External Capability Integration

を担当する。

例：

```text
GitHub
Jira
Database
Slack
Internal API
Monitoring
```

Migration 時には、単純な Config 変換だけでは不十分。

以下を再確認する。

```text
Which Agent needs this MCP?
Which Tool should be exposed?
Read-only or writable?
Authentication model?
Secret management?
Permission approval?
```

原則：

> MCP Capability と Agent Responsibility は分離して設計する。

---

# 20. Hooks Migration

Hook は、

> Deterministic Enforcement

を担当する。

例：

```text
PreToolUse
PostToolUse
SessionStart
Stop
```

以下のような内容は Prompt に依存させるべきではない。

```text
AI should remember to do X
```

X が必須の Security / Quality Rule である場合は、

```text
→ Hook
```

を検討する。

例：

```text
prevent destructive command
run formatter
validate generated files
security policy check
```

---

# 21. Company-level Distribution

長期的には、共通能力を Claude Plugin 等にまとめ、Repository ごとの重複を減らすことを推奨する。

例：

```text
company-claude-plugin/
│
├── .claude-plugin/
│   └── plugin.json
│
├── skills/
│
├── agents/
│
├── hooks/
│
└── .mcp.json
```

Repository 内には、Repository 固有の設定のみを保持する。

ただし、Plugin と Project-level Configuration では利用可能な権限や設定範囲に差があるため、Plugin 化は PoC 後に判断する。

したがって、

> **Company Plugin 化は Migration Phase 2 とし、初期 Migration の Blocking Task にはしない。**

---

# 22. Recommended Target Repository Structure

移行後の推奨構造：

```text
repository/
│
├── CLAUDE.md
│
├── .mcp.json
│
└── .claude/
    │
    ├── agents/
    │   ├── test-runner.md
    │   ├── test-reviewer.md
    │   └── architecture-reviewer.md
    │
    ├── skills/
    │   ├── generate-unit-tests/
    │   │   ├── SKILL.md
    │   │   ├── references/
    │   │   └── scripts/
    │   │
    │   └── analyze-testability/
    │       └── SKILL.md
    │
    ├── rules/
    │   ├── java.md
    │   ├── testing.md
    │   └── security.md
    │
    ├── hooks/
    │
    └── settings.json
```

---

# 23. Migration Phases

Migration は 6 Phase に分割する。

---

# Phase 0 — Inventory

## Goal

既存 GitHub Copilot Customization 全体を可視化する。

## TODO

### MIG-001

以下を Scan する。

```text
.github/
```

対象：

```text
agents
skills
prompts
instructions
hooks
MCP
```

---

### MIG-002

各資産について Migration Inventory を作成する。

例：

```yaml
name: unit-test-agent

type: copilot-agent

source:
  path: .github/agents/unit-test.md

responsibility:
  - generate-tests
  - run-tests

tools:
  - ...

skills:
  - ...

dependencies:
  agents:
    - test-reviewer

side_effects:
  - write-test-files

target:
  undecided
```

---

### MIG-003

Agent Dependency Graph を作成する。

```text
Agent
 ↓
Agent

Agent
 ↓
Skill

Agent
 ↓
MCP

Agent
 ↓
Script
```

## Deliverable

```text
migration-inventory.yaml
agent-dependency-graph
```

---

# Phase 1 — Skill Canonicalization

## Goal

再利用性の高い Skill を先に共通化する。

## TODO

### SKILL-001

既存 `SKILL.md` を Inventory。

### SKILL-002

Agent Skills Specification との互換性確認。

### SKILL-003

Skill name / description を標準化。

### SKILL-004

Copilot-specific Instruction を特定。

### SKILL-005

Copilot-specific Tool 表現を除去。

### SKILL-006

大きすぎる Skill を分割。

推奨：

```text
SKILL.md
references/
scripts/
examples/
```

### SKILL-007

Canonical Skill を段階的に

```text
.claude/skills/
```

へ移行。

### SKILL-008

Copilot / Claude Code 双方で動作確認。

## Deliverable

```text
Canonical Skill Repository
Skill Compatibility Report
```

---

# Phase 2 — Agent / Subagent Redesign

## Goal

Agent Architecture を再設計する。

## TODO

### SUB-001

既存 Agent を以下に分類する。

```text
ENTRY
WORKER
WORKFLOW
RULE
INTEGRATION
ENFORCEMENT
REDUNDANT
```

---

### SUB-002

以下の候補を特定。

```text
Agent → Skill
```

---

### SUB-003

以下で代替可能か確認。

```text
Agent → Claude Built-in Explore / Plan
```

---

### SUB-004

本当に Custom Subagent が必要な Worker を特定。

---

### SUB-005

各 Subagent の以下を定義。

```text
Purpose
Context Boundary
Input Contract
Output Contract
```

---

### SUB-006

以下を定義。

```text
Tool Allowlist
Tool Denylist
Permission
```

---

### SUB-007

Skill Dependency を定義。

---

### SUB-008

Model Strategy を定義。

例：

```text
Simple Search
→ lower-cost model

Complex Review
→ stronger model
```

最終 Policy は PoC 後に決定。

---

### SUB-009

Agent Spawn Policy を定義。

無制限な Agent Delegation を避ける。

---

### SUB-010

Parallel Execution 可能な Task を特定。

例：

```text
Security Review ─┐
Test Review ─────┼→ Summary
Architecture ────┘
```

## Deliverable

```text
Claude Agent Architecture
Subagent Definitions
Agent Responsibility Matrix
```

---

# Phase 3 — Instructions / Prompt Migration

## TODO

### CFG-001

`copilot-instructions.md` を分析し、内容を以下に分類。

```text
Project Fact
Rule
Workflow
```

---

### CFG-002

Project Fact：

```text
→ CLAUDE.md
```

---

### CFG-003

Path-specific Rule：

```text
→ .claude/rules/
```

---

### CFG-004

Workflow：

```text
→ Skill
```

---

### CFG-005

以下を分析。

```text
.github/prompts/
```

Skill に統合可能なものを特定。

## Deliverable

```text
CLAUDE.md
.claude/rules/*
Additional Skills
```

---

# Phase 4 — Tool / MCP / Hook / Security

## TODO

### SEC-001

既存 Agent Tool を Inventory。

### SEC-002

Copilot → Claude Tool Mapping を整理。

ただし、

> Tool Name / Permission / Runtime Semantics が完全な 1:1 対応であるとは仮定しない。

実際の利用シナリオで確認する。

### SEC-003

Subagent ごとの Least Privilege Policy を作成。

### SEC-004

MCP を移行。

### SEC-005

Secret / Authentication Strategy を再設計。

### SEC-006

Hooks を移行。

### SEC-007

Prompt Rule の中から、Deterministic Hook に昇格すべきルールを特定。

## Deliverable

```text
Tool Permission Matrix
MCP Configuration
Hook Configuration
Security Baseline
```

---

# Phase 5 — Regression Evaluation

これは Optional QA ではなく、P0 Task として扱う。

単に

```text
Claude can load the agent.
```

だけでは Migration Complete としない。

確認すべきなのは、

> Claude が元の Business Task を同等以上に実行できるか

である。

---

## Test Case Format

例：

```yaml
case: generate-java-unit-test

repository_fixture:
  ...

input:
  Generate tests for FooService

expected:
  inspect_existing_tests: true
  generate_test: true
  run_test: true
  test_pass: true

forbidden:
  modify_production_code: true
```

---

## Compare

```text
Copilot
   │
   ├─────────────┐
   │             │
   ↓             ↓
Expected       Claude
Behavior       Code
```

評価指標例：

```text
Task Success Rate
Test Pass Rate
Build Success
Code Quality
Coverage Delta
Unnecessary Modification
Forbidden Behavior
Tool Usage
Iteration Count
Latency
Token Usage
Cost
```

## Deliverable

```text
Agent Regression Dataset
Copilot vs Claude Evaluation Report
```

---

# Phase 6 — Company Distribution

Project-level Migration が安定した後、Company Standardization を実施する。

## TODO

### PLATFORM-001

Company Shared Skills を特定。

### PLATFORM-002

Company Shared Subagents を特定。

### PLATFORM-003

Company Security Rules を特定。

### PLATFORM-004

Claude Plugin PoC を実施。

### PLATFORM-005

Versioning Strategy を定義。

### PLATFORM-006

Plugin Distribution / Update Process を定義。

### PLATFORM-007

Project-specific Override Policy を定義。

最終イメージ：

```text
                    Company Platform
                          │
                          ↓
                    Claude Plugin
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
       Project A       Project B       Project C
          │               │               │
       CLAUDE.md        CLAUDE.md       CLAUDE.md
       Rules            Rules           Rules
```

---

# 29. Migration Backlog Summary

| ID           | Task                            | Priority |
| ------------ | ------------------------------- | -------- |
| MIG-001      | Copilot Assets Inventory        | P0       |
| MIG-002      | Dependency Graph 作成             | P0       |
| MIG-003      | Agent Classification            | P0       |
| SKILL-001    | Skill Compatibility Audit       | P0       |
| SKILL-002    | Skill Canonicalization          | P0       |
| SKILL-003    | Copilot / Claude Dual Test      | P0       |
| SUB-001      | Entry / Worker Classification   | P0       |
| SUB-002      | Agent → Skill 判定                | P0       |
| SUB-003      | Built-in Subagent 代替確認          | P1       |
| SUB-004      | Custom Subagent Conversion      | P0       |
| SUB-005      | Context Boundary 定義             | P0       |
| SUB-006      | Tool / Permission Boundary      | P0       |
| SUB-007      | Skill Dependency 定義             | P0       |
| SUB-008      | Subagent Output Contract        | P0       |
| SUB-009      | Parallel / Nested Orchestration | P1       |
| CFG-001      | CLAUDE.md Migration             | P1       |
| CFG-002      | Rules Migration                 | P1       |
| CFG-003      | Prompt → Skill                  | P1       |
| SEC-001      | Tool Mapping                    | P0       |
| SEC-002      | Permission Baseline             | P0       |
| SEC-003      | MCP Migration                   | P1       |
| SEC-004      | Hook Migration                  | P1       |
| EVAL-001     | Regression Dataset              | P0       |
| EVAL-002     | Copilot / Claude Comparison     | P0       |
| PLATFORM-001 | Company Plugin PoC              | P2       |
| PLATFORM-002 | Distribution / Versioning       | P2       |
| CLEANUP-001  | Legacy Copilot Assets 削除        | P2       |

---

# 30. Migration Definition of Done

Agent / Skill は、

```text
Claude can load it
```

だけでは Migration Complete としない。

最低限、以下を満たすこと。

## Configuration

* Claude Code が正常に認識できる
* Unsupported Configuration がない
* Skill / Agent Dependency が正常
* Tool Permission が設計通り

## Functional

* Core Business Task を完了できる
* Output Quality が Baseline を満たす
* Required Command が正常実行される
* Generated Code が Build / Test を通過する

## Safety

* 禁止 Tool を利用しない
* 禁止 File を変更しない
* MCP Permission が設計通り
* Side Effect が管理されている

## Architecture

* 不要な重複 Skill がない
* Agent 内に巨大な重複 Workflow Instruction がない
* Subagent Context Boundary が明確
* Skill / Agent / Rule / Hook の責務が明確

## Evaluation

* Regression Case を通過
* Copilot Baseline との差分を記録
* Known Regression に対する判断が完了

---

# 31. Key Risks

## Risk 1 — Mechanical Agent Conversion

以下は常に正しいとは限らない。

```text
Copilot Agent
    ↓
Claude Subagent
```

既存 Agent の多くは、実際には以下に再分類される可能性がある。

```text
Skill
Rule
Hook
Built-in Subagent
```

---

## Risk 2 — Prompt Duplication

以下のような状態を避ける。

```text
CLAUDE.md
Skill
Agent

すべてに同じ 300 行の Instruction
```

Single Source of Truth を維持する。

---

## Risk 3 — Overuse of Subagents

Subagent は追加の、

```text
Inference
Context
Latency
Cost
```

を発生させる。

したがって、

> Context Isolation や Permission Isolation に明確な価値がある場合のみ Subagent を作成する。

---

## Risk 4 — Too Much CLAUDE.md

Copilot Instructions をすべて `CLAUDE.md` にコピーすると、

```text
Context Pollution
↓
Lower Instruction Adherence
↓
Higher Token Usage
```

につながる。

Procedure は Skill に、Path-specific な Rule は `.claude/rules/` に分離する。

---

## Risk 5 — Excessive Tool Permission

以下をデフォルトにしない。

```text
tools: all
```

推奨：

```text
Least Privilege by Role
```

---

## Risk 6 — Migration Without Evaluation

Agent は Probabilistic System である。

たとえ、

```text
Prompt
Skill
Tool
```

が類似していても、Runtime / Model が変われば挙動は変化しうる。

したがって、

> Regression Evaluation は Migration の必須工程とする。

---

# 32. Recommended Migration Order

推奨順序：

```text
STEP 1
Inventory Existing Assets
        ↓

STEP 2
Build Dependency Graph
        ↓

STEP 3
Canonicalize Skills
        ↓

STEP 4
Classify Existing Agents
        ↓

STEP 5
Agent
 ├→ Skill
 ├→ Subagent
 ├→ Rule
 ├→ Hook
 ├→ MCP
 ├→ Built-in
 └→ Remove
        ↓

STEP 6
Build Claude Agent Architecture
        ↓

STEP 7
Migrate CLAUDE.md / Rules / MCP / Hooks
        ↓

STEP 8
Regression Evaluation
        ↓

STEP 9
Dual-run Copilot + Claude
        ↓

STEP 10
Company Plugin / Distribution
        ↓

STEP 11
Remove Legacy Copilot Configuration
```

---

# 33. Final Architecture Principle

Migration 完了後は、以下の責務モデルを基本原則とする。

```text
CLAUDE.md
    =
Project Facts / Always-on Context


Rules
    =
Conditional Constraints


Skills
    =
Reusable Knowledge / Workflow / Capability


Subagents
    =
Isolated Execution Workers


Hooks
    =
Deterministic Enforcement


MCP
    =
External System Capability


Plugin
    =
Company-level Distribution
```

したがって今回の Migration の目的は、

> **GitHub Copilot の Architecture を Claude Code 上にそのまま再現することではない。**

目的は、

> **既存の Business Capability を維持しながら、Claude Code の Native Execution Model に合わせて再設計すること。**

この方針を、今後のすべての Copilot → Claude Code Migration Decision における基本 Guideline とする。
