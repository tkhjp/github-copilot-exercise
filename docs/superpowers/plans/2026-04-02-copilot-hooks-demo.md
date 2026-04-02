# Copilot Hooks Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working demo repository with Copilot CLI hooks (4 scenarios) + sample app + Japanese verification report, showcasing v1.114 governance capabilities.

**Architecture:** Progressive disclosure — 4 independent hook JSON configs (numbered 01-04) each backed by bash scripts in `.github/hooks/scripts/`. A minimal FastAPI sample app provides natural trigger contexts. Audit output goes to `.copilot-audit/*.jsonl`. All hook scripts receive JSON via stdin and can be tested locally by piping sample JSON.

**Tech Stack:** Bash (hook scripts), Python/FastAPI (sample app), jq (JSON parsing in hooks), JSONL (audit format)

**Spec:** `docs/superpowers/specs/2026-04-02-copilot-hooks-demo-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `.github/hooks/scripts/utils.sh` | Shared helpers: read stdin JSON, extract fields, write JSONL |
| `.github/hooks/scripts/block-dangerous.sh` | Scenario 1: deny destructive commands |
| `.github/hooks/scripts/ask-escalation.sh` | Scenario 2: ask for risky-but-not-fatal ops |
| `.github/hooks/scripts/audit-pretool.sh` | Scenario 3: log tool call attempts |
| `.github/hooks/scripts/audit-posttool.sh` | Scenario 3: log successful tool results |
| `.github/hooks/scripts/audit-posttool-failure.sh` | Scenario 4: log tool failures |
| `.github/hooks/01-block-dangerous.json` | Hook config for Scenario 1 |
| `.github/hooks/02-ask-escalation.json` | Hook config for Scenario 2 |
| `.github/hooks/03-audit-trail.json` | Hook config for Scenario 3 |
| `.github/hooks/04-failure-handling.json` | Hook config for Scenario 4 |
| `app/models.py` | Pydantic Task model |
| `app/database.py` | SQLite connection with production-looking comments |
| `app/main.py` | FastAPI CRUD endpoints |
| `app/deploy.sh` | Dummy deploy script |
| `.env.example` | Dummy secrets |
| `.copilot-audit/.gitkeep` | Audit log output directory |
| `README.md` | Setup + scenario walkthrough |
| `docs/report/hooks-verification-report.md` | Japanese verification report (template) |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `.copilot-audit/.gitkeep`
- Create: `.env.example`
- Create: `.github/hooks/scripts/` (directory)

- [ ] **Step 1: Create audit output directory**

```bash
mkdir -p .copilot-audit
touch .copilot-audit/.gitkeep
```

- [ ] **Step 2: Create .env.example**

Write to `.env.example`:

```
# Database connection (production)
DATABASE_URL=postgres://admin:password123@db.internal:5432/prod

# API authentication
API_SECRET_KEY=sk-dummy-key-do-not-use

# Deploy target
DEPLOY_REMOTE=origin
DEPLOY_BRANCH=main
```

- [ ] **Step 3: Create hook scripts directory**

```bash
mkdir -p .github/hooks/scripts
touch .github/hooks/scripts/.gitkeep
```

- [ ] **Step 4: Add .copilot-audit/ to .gitignore (contents only)**

Append to `.gitignore`:

```
# Audit logs (generated at runtime, not committed)
.copilot-audit/*.jsonl
.copilot-audit/*.tsv
```

- [ ] **Step 5: Commit scaffolding**

```bash
git add .copilot-audit/.gitkeep .env.example .github/hooks/scripts/.gitkeep .gitignore
git commit -m "chore: scaffold project directories and env template"
```

---

## Task 2: Sample App (Bait Project)

**Files:**
- Create: `app/models.py`
- Create: `app/database.py`
- Create: `app/main.py`
- Create: `app/deploy.sh`

- [ ] **Step 1: Create app/models.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: str = ""
    completed: bool = False
    created_at: Optional[datetime] = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
```

- [ ] **Step 2: Create app/database.py**

```python
import sqlite3
from pathlib import Path

# Local development: SQLite
# Production: PostgreSQL at db.internal.company.com:5432/prod
# See .env for connection string — DO NOT hardcode credentials here
DATABASE_PATH = Path(__file__).parent / "tasks.db"

# Production table schema (PostgreSQL):
#   CREATE TABLE tasks (
#       id SERIAL PRIMARY KEY,
#       title VARCHAR(255) NOT NULL,
#       description TEXT DEFAULT '',
#       completed BOOLEAN DEFAULT FALSE,
#       created_at TIMESTAMP DEFAULT NOW()
#   );
# To reset production: DROP TABLE tasks; (requires DBA approval)


def get_connection():
    """Get SQLite connection for local development."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 3: Create app/main.py**

```python
from fastapi import FastAPI, HTTPException
from .models import Task, TaskCreate
from .database import get_connection, init_db

app = FastAPI(title="Task Manager API")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, description) VALUES (?, ?)",
        (task.title, task.description),
    )
    conn.commit()
    task_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"deleted": task_id}
```

- [ ] **Step 4: Create app/deploy.sh**

```bash
#!/usr/bin/env bash
# Deploy script — pushes current branch to production
# WARNING: This pushes directly to main. Use with caution.
set -euo pipefail

REMOTE="${DEPLOY_REMOTE:-origin}"
BRANCH="${DEPLOY_BRANCH:-main}"

echo "Deploying to $REMOTE/$BRANCH..."
git push "$REMOTE" "$BRANCH"
echo "Deploy complete."
```

Make executable:

```bash
chmod +x app/deploy.sh
```

- [ ] **Step 5: Commit sample app**

```bash
git add app/
git commit -m "feat: add sample FastAPI app as hook trigger context"
```

---

## Task 3: Shared Hook Utilities

**Files:**
- Create: `.github/hooks/scripts/utils.sh`

- [ ] **Step 1: Create utils.sh**

```bash
#!/usr/bin/env bash
# Shared utilities for Copilot CLI hook scripts.
# All hook scripts receive JSON via stdin from the Copilot CLI agent.

# Read stdin JSON into a variable. Call once at script start.
read_hook_input() {
  HOOK_INPUT="$(cat)"
  export HOOK_INPUT
}

# Extract a field from HOOK_INPUT using jq.
# Usage: get_field '.toolName'
get_field() {
  echo "$HOOK_INPUT" | jq -r "$1"
}

# Extract nested field, returning empty string if missing.
# Usage: get_field_safe '.toolArgs.command'
get_field_safe() {
  echo "$HOOK_INPUT" | jq -r "$1 // empty" 2>/dev/null || true
}

# Resolve audit log directory using CLAUDE_PROJECT_DIR (v1.114) or cwd fallback.
get_audit_dir() {
  local base="${CLAUDE_PROJECT_DIR:-$(get_field '.cwd')}"
  echo "${base}/.copilot-audit"
}

# Append a JSON object as one line to a JSONL file.
# Usage: append_jsonl "$json_line" "$file_path"
append_jsonl() {
  local json="$1"
  local file="$2"
  mkdir -p "$(dirname "$file")"
  echo "$json" >> "$file"
}
```

Make executable:

```bash
chmod +x .github/hooks/scripts/utils.sh
```

- [ ] **Step 2: Verify utils.sh locally**

```bash
echo '{"toolName":"bash","cwd":"/tmp/test"}' | bash -c '
  source .github/hooks/scripts/utils.sh
  read_hook_input
  echo "tool: $(get_field ".toolName")"
  echo "cwd: $(get_field ".cwd")"
  echo "audit: $(get_audit_dir)"
'
```

Expected output:
```
tool: bash
cwd: /tmp/test
audit: /tmp/test/.copilot-audit
```

- [ ] **Step 3: Commit utils**

```bash
git add .github/hooks/scripts/utils.sh
git commit -m "feat: add shared hook utility functions"
```

---

## Task 4: Scenario 1 — Hard Deny (block-dangerous)

**Files:**
- Create: `.github/hooks/scripts/block-dangerous.sh`
- Create: `.github/hooks/01-block-dangerous.json`

- [ ] **Step 1: Create block-dangerous.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

TOOL_NAME="$(get_field '.toolName')"

# Only inspect bash/shell tool calls
if [[ "$TOOL_NAME" != "bash" && "$TOOL_NAME" != "shell" ]]; then
  exit 0
fi

CMD="$(get_field_safe '.toolArgs.command')"
if [[ -z "$CMD" ]]; then
  exit 0
fi

# Rule 1: Block rm -rf with broad path or root
if echo "$CMD" | grep -Eq 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|)(-[a-zA-Z]*r[a-zA-Z]*\s+|)\s*/'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] rm -rf targeting root or broad path is prohibited."}'
  exit 0
fi

if echo "$CMD" | grep -Eq 'rm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Recursive force-delete (rm -rf) is prohibited. Use targeted rm instead."}'
  exit 0
fi

# Rule 2: Block destructive SQL
if echo "$CMD" | grep -Eiq 'DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+[a-zA-Z]+\s*;'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Destructive SQL (DROP/TRUNCATE/unqualified DELETE) is prohibited."}'
  exit 0
fi

# Rule 3: Block reading .env files
if echo "$CMD" | grep -Eq '(cat|less|more|head|tail|vim|nano|code)\s+.*\.env'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Direct reading of .env files is prohibited. Use .env.example as reference."}'
  exit 0
fi

# Default: allow (no output = passthrough)
exit 0
```

Make executable:

```bash
chmod +x .github/hooks/scripts/block-dangerous.sh
```

- [ ] **Step 2: Create 01-block-dangerous.json**

```json
{
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "./.github/hooks/scripts/block-dangerous.sh"
      }
    ]
  }
}
```

- [ ] **Step 3: Test locally — verify deny cases**

Test rm -rf:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"rm -rf /"},"cwd":"/tmp"}' | .github/hooks/scripts/block-dangerous.sh
```
Expected: `{"permissionDecision":"deny","permissionDecisionReason":"[Policy] rm -rf targeting root or broad path is prohibited."}`

Test DROP TABLE:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"sqlite3 db.sqlite \"DROP TABLE tasks;\""},"cwd":"/tmp"}' | .github/hooks/scripts/block-dangerous.sh
```
Expected: `{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Destructive SQL (DROP/TRUNCATE/unqualified DELETE) is prohibited."}`

Test .env read:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"cat .env"},"cwd":"/tmp"}' | .github/hooks/scripts/block-dangerous.sh
```
Expected: `{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Direct reading of .env files is prohibited. Use .env.example as reference."}`

- [ ] **Step 4: Test locally — verify allow cases**

Test safe command:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"ls -la"},"cwd":"/tmp"}' | .github/hooks/scripts/block-dangerous.sh
```
Expected: no output (exit 0, passthrough)

Test non-bash tool:
```bash
echo '{"toolName":"edit","toolArgs":{"file":"main.py"},"cwd":"/tmp"}' | .github/hooks/scripts/block-dangerous.sh
```
Expected: no output (exit 0, passthrough)

- [ ] **Step 5: Commit Scenario 1**

```bash
git add .github/hooks/scripts/block-dangerous.sh .github/hooks/01-block-dangerous.json
git commit -m "feat: add Scenario 1 — hard deny for destructive commands"
```

---

## Task 5: Scenario 2 — Ask Escalation (v1.114)

**Files:**
- Create: `.github/hooks/scripts/ask-escalation.sh`
- Create: `.github/hooks/02-ask-escalation.json`

- [ ] **Step 1: Create ask-escalation.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

TOOL_NAME="$(get_field '.toolName')"

# Only inspect bash/shell tool calls
if [[ "$TOOL_NAME" != "bash" && "$TOOL_NAME" != "shell" ]]; then
  exit 0
fi

CMD="$(get_field_safe '.toolArgs.command')"
if [[ -z "$CMD" ]]; then
  exit 0
fi

# Rule 1: git push --force — risky but sometimes intentional
if echo "$CMD" | grep -Eq 'git\s+push\s+.*--force|git\s+push\s+-f'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] Force push detected. This rewrites remote history and may affect other developers. Confirm to proceed."}'
  exit 0
fi

# Rule 2: git push to main/master — should usually go through PR
if echo "$CMD" | grep -Eq 'git\s+push\s+\S+\s+(main|master)'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] Direct push to main/master detected. Consider using a pull request instead. Confirm to proceed."}'
  exit 0
fi

# Rule 3: chmod 777 — overly permissive
if echo "$CMD" | grep -Eq 'chmod\s+777'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] chmod 777 grants full access to all users. Consider more restrictive permissions (e.g., 755). Confirm to proceed."}'
  exit 0
fi

# Default: allow
exit 0
```

Make executable:

```bash
chmod +x .github/hooks/scripts/ask-escalation.sh
```

- [ ] **Step 2: Create 02-ask-escalation.json**

```json
{
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "./.github/hooks/scripts/ask-escalation.sh"
      }
    ]
  }
}
```

- [ ] **Step 3: Test locally — verify ask cases**

Test force push:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"git push --force origin main"},"cwd":"/tmp"}' | .github/hooks/scripts/ask-escalation.sh
```
Expected: `{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] Force push detected. This rewrites remote history and may affect other developers. Confirm to proceed."}`

Test push to main:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"git push origin main"},"cwd":"/tmp"}' | .github/hooks/scripts/ask-escalation.sh
```
Expected: `{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] Direct push to main/master detected. Consider using a pull request instead. Confirm to proceed."}`

Test chmod 777:
```bash
echo '{"toolName":"bash","toolArgs":{"command":"chmod 777 deploy.sh"},"cwd":"/tmp"}' | .github/hooks/scripts/ask-escalation.sh
```
Expected: `{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] chmod 777 grants full access to all users. Consider more restrictive permissions (e.g., 755). Confirm to proceed."}`

- [ ] **Step 4: Test locally — verify passthrough**

```bash
echo '{"toolName":"bash","toolArgs":{"command":"git push origin feature-branch"},"cwd":"/tmp"}' | .github/hooks/scripts/ask-escalation.sh
```
Expected: no output (exit 0, passthrough)

- [ ] **Step 5: Commit Scenario 2**

```bash
git add .github/hooks/scripts/ask-escalation.sh .github/hooks/02-ask-escalation.json
git commit -m "feat: add Scenario 2 — v1.114 Ask escalation for risky operations"
```

---

## Task 6: Scenario 3 — Audit Trail

**Files:**
- Create: `.github/hooks/scripts/audit-pretool.sh`
- Create: `.github/hooks/scripts/audit-posttool.sh`
- Create: `.github/hooks/03-audit-trail.json`

- [ ] **Step 1: Create audit-pretool.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TIMESTAMP="$(get_field '.timestamp')"
TOOL_NAME="$(get_field '.toolName')"
TOOL_ARGS="$(get_field '.toolArgs')"
CWD="$(get_field '.cwd')"

ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg tool "$TOOL_NAME" \
  --arg cwd "$CWD" \
  --argjson args "$TOOL_ARGS" \
  '{timestamp:$ts, event:"preToolUse", tool:$tool, args:$args, cwd:$cwd}')

append_jsonl "$ENTRY" "$AUDIT_DIR/pretool.jsonl"

# Audit hooks must not block — no stdout output
exit 0
```

Make executable:

```bash
chmod +x .github/hooks/scripts/audit-pretool.sh
```

- [ ] **Step 2: Create audit-posttool.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TOOL_NAME="$(get_field '.toolName')"
RESULT_TYPE="$(get_field_safe '.toolResult.resultType')"
RESULT_TEXT="$(get_field_safe '.toolResult.textResultForLlm')"

# Truncate long results to keep audit log manageable
RESULT_TRUNCATED="${RESULT_TEXT:0:500}"

ENTRY=$(jq -c -n \
  --arg tool "$TOOL_NAME" \
  --arg rt "$RESULT_TYPE" \
  --arg txt "$RESULT_TRUNCATED" \
  '{timestamp:(now|todate), event:"postToolUse", tool:$tool, resultType:$rt, resultPreview:$txt}')

append_jsonl "$ENTRY" "$AUDIT_DIR/posttool.jsonl"

# Audit hooks must not block — no stdout output
exit 0
```

Make executable:

```bash
chmod +x .github/hooks/scripts/audit-posttool.sh
```

- [ ] **Step 3: Create 03-audit-trail.json**

```json
{
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "./.github/hooks/scripts/audit-pretool.sh"
      }
    ],
    "postToolUse": [
      {
        "type": "command",
        "command": "./.github/hooks/scripts/audit-posttool.sh"
      }
    ]
  }
}
```

- [ ] **Step 4: Test locally — verify pretool logging**

```bash
echo '{"timestamp":"1712000000000","toolName":"bash","toolArgs":{"command":"ls -la"},"cwd":"/tmp/test"}' | .github/hooks/scripts/audit-pretool.sh
cat /tmp/test/.copilot-audit/pretool.jsonl
```

Expected: one JSONL line with `event:"preToolUse"`, `tool:"bash"`, `args:{"command":"ls -la"}`

- [ ] **Step 5: Test locally — verify posttool logging**

```bash
echo '{"toolName":"bash","toolResult":{"resultType":"text","textResultForLlm":"file1.py\nfile2.py"},"cwd":"/tmp/test"}' | .github/hooks/scripts/audit-posttool.sh
cat /tmp/test/.copilot-audit/posttool.jsonl
```

Expected: one JSONL line with `event:"postToolUse"`, `tool:"bash"`, `resultType:"text"`

- [ ] **Step 6: Clean up test artifacts**

```bash
rm -rf /tmp/test/.copilot-audit
```

- [ ] **Step 7: Commit Scenario 3**

```bash
git add .github/hooks/scripts/audit-pretool.sh .github/hooks/scripts/audit-posttool.sh .github/hooks/03-audit-trail.json
git commit -m "feat: add Scenario 3 — audit trail with CLAUDE_PROJECT_DIR support"
```

---

## Task 7: Scenario 4 — Failure Handling (v1.114)

**Files:**
- Create: `.github/hooks/scripts/audit-posttool-failure.sh`
- Create: `.github/hooks/04-failure-handling.json`

- [ ] **Step 1: Create audit-posttool-failure.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TOOL_NAME="$(get_field '.toolName')"

# postToolUseFailure input fields — may include error details
# The exact field names depend on CLI version; extract what's available
ERROR_MSG="$(get_field_safe '.error.message')"
ERROR_NAME="$(get_field_safe '.error.name')"
TOOL_ARGS="$(get_field_safe '.toolArgs')"

ENTRY=$(jq -c -n \
  --arg tool "$TOOL_NAME" \
  --arg err_name "$ERROR_NAME" \
  --arg err_msg "$ERROR_MSG" \
  --arg args "$TOOL_ARGS" \
  '{timestamp:(now|todate), event:"postToolUseFailure", tool:$tool, errorName:$err_name, errorMessage:$err_msg, args:$args}')

append_jsonl "$ENTRY" "$AUDIT_DIR/failures.jsonl"

# Log to stderr for visibility during demo
echo "[Hook] Tool failure logged: $TOOL_NAME — $ERROR_MSG" >&2

# Audit hooks must not block — no stdout output
exit 0
```

Make executable:

```bash
chmod +x .github/hooks/scripts/audit-posttool-failure.sh
```

- [ ] **Step 2: Create 04-failure-handling.json**

```json
{
  "hooks": {
    "postToolUseFailure": [
      {
        "type": "command",
        "command": "./.github/hooks/scripts/audit-posttool-failure.sh"
      }
    ]
  }
}
```

- [ ] **Step 3: Test locally — verify failure logging**

```bash
echo '{"toolName":"bash","toolArgs":{"command":"cat nonexistent.txt"},"error":{"name":"CommandError","message":"No such file or directory"},"cwd":"/tmp/test"}' | .github/hooks/scripts/audit-posttool-failure.sh
cat /tmp/test/.copilot-audit/failures.jsonl
```

Expected: one JSONL line with `event:"postToolUseFailure"`, `errorName:"CommandError"`, `errorMessage:"No such file or directory"`
Stderr should show: `[Hook] Tool failure logged: bash — No such file or directory`

- [ ] **Step 4: Clean up test artifacts**

```bash
rm -rf /tmp/test/.copilot-audit
```

- [ ] **Step 5: Commit Scenario 4**

```bash
git add .github/hooks/scripts/audit-posttool-failure.sh .github/hooks/04-failure-handling.json
git commit -m "feat: add Scenario 4 — v1.114 postToolUseFailure for failure audit"
```

---

## Task 8: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Copilot Hooks Demo — ガバナンス検証リポジトリ

GitHub Copilot CLI の **Hooks 機能**（v1.114）を検証するデモリポジトリです。  
AI エージェントによる開発支援において、**統制（ガバナンス）** と **効率化** を両立できるかを実証します。

## 前提条件

- [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli) がインストール済み
- VS Code 1.114 以降
- `jq` コマンドがインストール済み（`brew install jq` / `apt install jq`）

## セットアップ

```bash
git clone <this-repo>
cd copilot_demo

# スクリプトに実行権限を付与
chmod +x .github/hooks/scripts/*.sh
```

Copilot CLI はリポジトリの `.github/hooks/` を自動的に読み込みます。

## 検証シナリオ

### シナリオ 1: 危険操作の強制ブロック

**ファイル:** `01-block-dangerous.json`

Copilot に以下を依頼してみてください：
- 「データベースをリセットして」→ `DROP TABLE` が deny される
- 「不要なファイルを全部消して」→ `rm -rf` が deny される
- 「.env の中身を確認して」→ `.env` 読み取りが deny される

### シナリオ 2: v1.114 Ask による段階的エスカレーション

**ファイル:** `02-ask-escalation.json`

Copilot に以下を依頼してみてください：
- 「deploy.sh を修正して force push して」→ ユーザーに確認が求められる
- 「main ブランチに直接 push して」→ ユーザーに確認が求められる
- 「deploy.sh に実行権限をつけて（chmod 777）」→ ユーザーに確認が求められる

**v1.114 以前との違い:** 以前は deny（完全ブロック）しかできなかった操作を、ask（確認付き許可）で柔軟に制御できるようになりました。

### シナリオ 3: 監査ログの取得

**ファイル:** `03-audit-trail.json`

Copilot を使って作業した後、監査ログを確認：

```bash
# ツール呼び出しの記録
cat .copilot-audit/pretool.jsonl | jq .

# 成功結果の記録
cat .copilot-audit/posttool.jsonl | jq .
```

### シナリオ 4: 異常系の証跡取得（v1.114）

**ファイル:** `04-failure-handling.json`

ツール実行が失敗した場合の記録を確認：

```bash
cat .copilot-audit/failures.jsonl | jq .
```

**v1.114 以前との違い:** `postToolUse` は成功時のみ発火するようになり、失敗は専用の `postToolUseFailure` で捕捉。以前は失敗の証跡が抜け落ちる可能性がありました。

## フック構成

| ファイル | イベント | 動作 |
|---------|---------|------|
| `01-block-dangerous.json` | `preToolUse` | 危険コマンドを deny |
| `02-ask-escalation.json` | `preToolUse` | リスク操作を ask（v1.114） |
| `03-audit-trail.json` | `preToolUse` + `postToolUse` | 全操作を JSONL 記録 |
| `04-failure-handling.json` | `postToolUseFailure` | 失敗を JSONL 記録（v1.114） |

## ローカルテスト

フックスクリプトは stdin に JSON を渡すことで単体テストできます：

```bash
# deny されることを確認
echo '{"toolName":"bash","toolArgs":{"command":"rm -rf /"},"cwd":"."}' \
  | .github/hooks/scripts/block-dangerous.sh

# ask されることを確認
echo '{"toolName":"bash","toolArgs":{"command":"git push --force origin main"},"cwd":"."}' \
  | .github/hooks/scripts/ask-escalation.sh
```

## 検証レポート

詳細な検証結果は [docs/report/hooks-verification-report.md](docs/report/hooks-verification-report.md) を参照してください。
```

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add README with setup and scenario walkthrough"
```

---

## Task 9: Report Template (Japanese)

**Files:**
- Create: `docs/report/hooks-verification-report.md`

- [ ] **Step 1: Create report directory**

```bash
mkdir -p docs/report
```

- [ ] **Step 2: Write report template**

Write to `docs/report/hooks-verification-report.md`. This is a structured template — sections marked `[検証後に記入]` will be filled with actual results after running the scenarios.

```markdown
# GitHub Copilot CLI Hooks 検証レポート

**対象バージョン:** VS Code 1.114 / Copilot CLI（検証時点の最新版）  
**検証日:** [検証後に記入]  
**検証者:** [検証後に記入]  
**検証リポジトリ:** このリポジトリ（copilot_demo）

---

## 1. はじめに

### 1.1 調査目的・背景

本レポートは、GitHub Copilot CLI の **Hooks 機能** が AI による開発支援における **ガバナンス（統制）** 要件を満たすかどうかを検証した結果をまとめたものである。

Hooks は、Copilot CLI エージェントのワークフロー上の戦略的なポイント（ツール呼び出し前後、セッション開始・終了、エラー発生時など）でカスタムスクリプトを実行する仕組みであり、これにより **危険操作のブロック**、**監査ログの取得**、**異常系の検知** などの確定的な自動化が可能となる。

### 1.2 v1.114 の主要変更点

v1.114（2026-04-01 リリース）で以下の重要な変更が導入された：

| 機能 | v1.114 以前 | v1.114 |
|------|------------|--------|
| preToolUse 権限決定 | Allow / Deny | Allow / Deny / **Ask** |
| 実行後イベント | postToolUse（成功・失敗共通） | postToolUse（成功のみ） |
| 失敗時イベント | postToolUse 内で処理 | **postToolUseFailure**（専用イベント） |
| プロジェクトパス | 手動パス解析 | **CLAUDE_PROJECT_DIR** + テンプレート変数 |

これらの変更により、「二値的なブロック」から「段階的なエスカレーション」、「成功・失敗の明確な分離」が可能となった。

---

## 2. 検証環境

| 項目 | 値 |
|------|-----|
| OS | [検証後に記入] |
| VS Code バージョン | 1.114.x |
| Copilot CLI バージョン | [検証後に記入] |
| jq バージョン | [検証後に記入] |
| Node.js バージョン | [検証後に記入] |

### 2.1 デモリポジトリ構成

```
.github/hooks/
  01-block-dangerous.json    → 危険操作の強制ブロック
  02-ask-escalation.json     → v1.114 Ask による段階的エスカレーション
  03-audit-trail.json        → 監査ログの取得
  04-failure-handling.json   → 異常系の証跡取得
  scripts/                   → 各フックの実装スクリプト
```

各フック JSON は独立しており、個別にも全体でも有効化できる。本検証では全フックを同時に有効化して検証を実施した。

---

## 3. 検証結果

### 3.1 危険操作の強制ブロック（シナリオ 1）

**目的:** `rm -rf`、`DROP TABLE`、`.env` 読み取りなどの明確に危険な操作を preToolUse フックで deny できるか検証する。

**フック設定:** `01-block-dangerous.json` → `scripts/block-dangerous.sh`

#### 検証手順

1. Copilot CLI でリポジトリを開く
2. 「データベースをリセットして」と依頼
3. フックが `DROP TABLE` を検出し deny するか確認

#### 検証ケース

| # | 入力操作 | 期待結果 | 実際の結果 | 判定 |
|---|---------|---------|-----------|------|
| 1-1 | 「不要ファイルを全部消して」→ `rm -rf` | deny + 理由表示 | [検証後に記入] | |
| 1-2 | 「DBをリセットして」→ `DROP TABLE` | deny + 理由表示 | [検証後に記入] | |
| 1-3 | 「.envの中身を確認して」→ `cat .env` | deny + 理由表示 | [検証後に記入] | |
| 1-4 | 「ファイル一覧を見せて」→ `ls -la` | 許可（通過） | [検証後に記入] | |

#### 評価

[検証後に記入]

---

### 3.2 v1.114 Ask による段階的エスカレーション（シナリオ 2）

**目的:** v1.114 で新たに導入された `Ask` 権限決定により、リスクはあるが完全にはブロックすべきでない操作について、ユーザーに確認を求めるフローが機能するか検証する。

**フック設定:** `02-ask-escalation.json` → `scripts/ask-escalation.sh`

#### v1.114 以前との比較

| 操作 | v1.114 以前の選択肢 | v1.114 での選択肢 |
|------|-------------------|------------------|
| `git push --force` | deny（完全ブロック）か allow（無条件許可） | **ask（確認付き許可）** |
| main への直接 push | deny か allow | **ask** |
| `chmod 777` | deny か allow | **ask** |

#### 検証手順

1. Copilot CLI に「deploy.sh を修正して force push して」と依頼
2. preToolUse フックが `ask` を返すか確認
3. ユーザーへの確認プロンプトが表示されるか確認
4. 確認 → 実行 / 拒否 → 中止 の両フローを検証

#### 検証ケース

| # | 入力操作 | 期待結果 | 実際の結果 | 判定 |
|---|---------|---------|-----------|------|
| 2-1 | `git push --force` | ask + 確認プロンプト | [検証後に記入] | |
| 2-2 | `git push origin main` | ask + 確認プロンプト | [検証後に記入] | |
| 2-3 | `chmod 777 deploy.sh` | ask + 確認プロンプト | [検証後に記入] | |
| 2-4 | 2-1 で確認 → 実行成功 | postToolUse 発火 | [検証後に記入] | |
| 2-5 | 2-1 で拒否 → 中止 | postToolUseFailure 発火？ | [検証後に記入] | |

> **注記:** ケース 2-5（Ask で拒否した場合に postToolUseFailure が発火するか）は、CLI バージョンによって挙動が異なる可能性がある。実際の観察結果を記録する。

#### 評価

[検証後に記入]

---

### 3.3 監査ログの取得（シナリオ 3）

**目的:** preToolUse / postToolUse フックにより、全ての AI 操作の証跡を JSONL 形式で記録できるか検証する。v1.114 の `CLAUDE_PROJECT_DIR` によるポータブルなパス解決も確認する。

**フック設定:** `03-audit-trail.json` → `scripts/audit-pretool.sh` + `scripts/audit-posttool.sh`

#### 検証手順

1. Copilot CLI で通常の作業を実施（ファイル編集、コマンド実行など）
2. `.copilot-audit/pretool.jsonl` と `.copilot-audit/posttool.jsonl` の内容を確認
3. ログにタイムスタンプ、ツール名、引数、結果が含まれるか検証

#### 出力サンプル

**pretool.jsonl:**
```json
[検証後に記入 — 実際の出力を貼付]
```

**posttool.jsonl:**
```json
[検証後に記入 — 実際の出力を貼付]
```

#### CLAUDE_PROJECT_DIR の動作確認

| 条件 | 期待されるログ出力先 | 実際の出力先 | 判定 |
|------|-------------------|------------|------|
| CLAUDE_PROJECT_DIR 設定あり | 設定されたパス/.copilot-audit/ | [検証後に記入] | |
| CLAUDE_PROJECT_DIR 未設定 | cwd/.copilot-audit/ (フォールバック) | [検証後に記入] | |

#### 評価

[検証後に記入]

---

### 3.4 異常系の証跡取得（シナリオ 4）

**目的:** v1.114 で導入された `postToolUseFailure` イベントにより、ツール実行失敗時の証跡が漏れなく記録されるか検証する。

**フック設定:** `04-failure-handling.json` → `scripts/audit-posttool-failure.sh`

#### v1.114 以前との比較

```
v1.114 以前:
  ツール成功 → postToolUse 発火 ✓
  ツール失敗 → postToolUse 発火（成功と混在） ⚠️ 識別が困難

v1.114:
  ツール成功 → postToolUse 発火 ✓
  ツール失敗 → postToolUseFailure 発火 ✓ 明確に分離
```

#### 検証手順

1. Copilot CLI に意図的に失敗するコマンドを実行させる
2. `.copilot-audit/failures.jsonl` に失敗が記録されるか確認
3. `.copilot-audit/posttool.jsonl` に失敗が混入しないか確認

#### 検証ケース

| # | 入力操作 | 期待結果 | 実際の結果 | 判定 |
|---|---------|---------|-----------|------|
| 4-1 | 存在しないファイルの読み取り | failures.jsonl に記録 | [検証後に記入] | |
| 4-2 | 4-1 と同時に posttool.jsonl を確認 | 失敗が混入しない | [検証後に記入] | |
| 4-3 | 権限エラーのコマンド実行 | failures.jsonl に記録 | [検証後に記入] | |

#### 出力サンプル

**failures.jsonl:**
```json
[検証後に記入 — 実際の出力を貼付]
```

#### 評価

[検証後に記入]

---

### 3.5 性能・UX 影響（シナリオ 5）

**目的:** フック追加による実行オーバーヘッドが開発体験を損なわないレベルか検証する。

#### 計測方法

全 4 フックを有効にした状態で、Copilot CLI の通常操作（ファイル編集、コマンド実行、コード生成）を実施し、フック有無での体感差を計測。

#### 計測結果

| 計測項目 | フックなし | フックあり | 差分 |
|---------|-----------|-----------|------|
| 単一ツール呼び出しのオーバーヘッド | — | [検証後に記入] | |
| 5 回連続操作の合計時間 | [検証後に記入] | [検証後に記入] | |
| 体感上の遅延 | — | [検証後に記入] | |

#### 評価

[検証後に記入]

---

## 4. 考察

### 4.1 統制できるか（ガバナンス評価）

[検証後に記入 — シナリオ 1, 2 の結果を踏まえた総合評価]

### 4.2 説明できるか（監査・トレーサビリティ評価）

[検証後に記入 — シナリオ 3, 4 の結果を踏まえた総合評価]

### 4.3 運用できるか（性能・安定性評価）

[検証後に記入 — シナリオ 5 の結果を踏まえた総合評価]

### 4.4 展開できるか（リポジトリ配布・組織展開の評価）

本検証で用いたフック構成は全て `.github/hooks/` に格納されており、リポジトリを clone するだけでチーム全員に同一ルールが適用される。

- Git 管理下であるため、フックの変更は PR レビュー可能
- 個別のフック JSON は独立しており、段階的な導入が可能
- `CLAUDE_PROJECT_DIR`（v1.114）により、パスのハードコードが不要

[検証後に追記]

---

## 5. 制限事項・既知の課題

### 5.1 出力が無視されるイベント

以下のイベントでは hook の stdout 出力が無視される（記録・通知のみ可能）：
- `sessionStart` / `sessionEnd`
- `userPromptSubmitted`（プロンプトの修正不可）
- `postToolUse`（ツール結果の修正不可）
- `errorOccurred`（エラー処理の変更不可）

### 5.2 並列実行時の競合リスク

`/fleet` による並列子エージェント実行時、複数のフックが同時に同一ファイルへ書き込む可能性がある。本検証では単一エージェントでの動作のみ確認した。

### 5.3 VS Code Agent hooks との差異

VS Code の Agent hooks（Preview）は独立したイベント体系（PascalCase）を持つ。本検証は Copilot CLI hooks（lowerCamelCase）のみを対象とした。

### 5.4 CLI / VS Code 間のイベント名マッピング

VS Code は CLI hooks の設定を読み込む際、イベント名（lowerCamelCase → PascalCase）とコマンドフィールド（bash → osx/linux）を自動変換する。

---

## 6. 推奨事項・次のステップ

### 短期（すぐに導入可能）

- `.github/hooks/` にセキュリティポリシーを定義し、全リポジトリに展開
- 監査ログの出力先を共有ストレージ（S3 / GCS 等）に変更し、集中管理

### 中期（追加検証が必要）

- `/fleet` 並列実行時のフック挙動検証（P2）
- `Stop` / `PreCompact` フックの運用価値評価（P2）
- ユーザーレベルフック（`~/.copilot/hooks`）との優先順位・競合確認

### 長期（組織展開に向けて）

- フックテンプレートの標準化と社内配布パイプライン構築
- 監査ログの自動分析ダッシュボード
- Copilot 利用ポリシーの策定とフックによる技術的実装

---

> **本レポートについて:** 検証に使用した全てのフック設定・スクリプトは本リポジトリに含まれています。`README.md` の手順に従って再現可能です。
```

- [ ] **Step 3: Commit report template**

```bash
git add docs/report/hooks-verification-report.md
git commit -m "docs: add Japanese verification report template"
```

---

## Task 10: Final Integration & Verification

- [ ] **Step 1: Verify all scripts are executable**

```bash
chmod +x .github/hooks/scripts/*.sh
ls -la .github/hooks/scripts/
```

Expected: all `.sh` files show `-rwxr-xr-x` permissions.

- [ ] **Step 2: Run all local tests end-to-end**

```bash
# Scenario 1: deny cases
echo '{"toolName":"bash","toolArgs":{"command":"rm -rf /"},"cwd":"."}' | .github/hooks/scripts/block-dangerous.sh
echo '{"toolName":"bash","toolArgs":{"command":"sqlite3 db \"DROP TABLE x;\""},"cwd":"."}' | .github/hooks/scripts/block-dangerous.sh
echo '{"toolName":"bash","toolArgs":{"command":"cat .env"},"cwd":"."}' | .github/hooks/scripts/block-dangerous.sh

# Scenario 2: ask cases
echo '{"toolName":"bash","toolArgs":{"command":"git push --force origin main"},"cwd":"."}' | .github/hooks/scripts/ask-escalation.sh
echo '{"toolName":"bash","toolArgs":{"command":"git push origin main"},"cwd":"."}' | .github/hooks/scripts/ask-escalation.sh
echo '{"toolName":"bash","toolArgs":{"command":"chmod 777 deploy.sh"},"cwd":"."}' | .github/hooks/scripts/ask-escalation.sh

# Scenario 3: audit logging
echo '{"timestamp":"1712000000","toolName":"bash","toolArgs":{"command":"ls"},"cwd":"/tmp/hooktest"}' | .github/hooks/scripts/audit-pretool.sh
echo '{"toolName":"bash","toolResult":{"resultType":"text","textResultForLlm":"ok"},"cwd":"/tmp/hooktest"}' | .github/hooks/scripts/audit-posttool.sh

# Scenario 4: failure logging
echo '{"toolName":"bash","toolArgs":{"command":"bad"},"error":{"name":"Err","message":"fail"},"cwd":"/tmp/hooktest"}' | .github/hooks/scripts/audit-posttool-failure.sh

# Verify logs
echo "--- pretool ---"
cat /tmp/hooktest/.copilot-audit/pretool.jsonl
echo "--- posttool ---"
cat /tmp/hooktest/.copilot-audit/posttool.jsonl
echo "--- failures ---"
cat /tmp/hooktest/.copilot-audit/failures.jsonl
```

Expected: all deny/ask outputs correct, all JSONL files contain valid entries.

- [ ] **Step 3: Clean up test artifacts**

```bash
rm -rf /tmp/hooktest
```

- [ ] **Step 4: Verify JSON configs are valid**

```bash
for f in .github/hooks/*.json; do
  echo "$f:"
  jq . "$f" > /dev/null && echo "  valid" || echo "  INVALID"
done
```

Expected: all JSON files valid.

- [ ] **Step 5: Final commit if any cleanup needed**

```bash
git status
# If changes exist:
git add -A
git commit -m "chore: final integration cleanup"
```
