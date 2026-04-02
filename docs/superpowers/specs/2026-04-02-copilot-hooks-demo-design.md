# Copilot Hooks Demo — Design Spec

## Purpose

Build a demo repository that verifies GitHub Copilot CLI Hooks governance capabilities (with emphasis on v1.114 changes) and produces a Japanese report for client engineers/tech leads at JEIS. The repo doubles as a self-guided sandbox engineers can clone and try themselves.

## Audience

Client engineers and tech leads evaluating whether Copilot Hooks can satisfy governance and efficiency requirements for AI-assisted development.

## Deliverables

1. **Working demo repository** with hooks and a sample app
2. **Japanese verification report** (`docs/report/hooks-verification-report.md`) backed by real evidence from the repo
3. **README** with step-by-step walkthrough for self-guided exploration

---

## Repo Structure

```
copilot_demo/
├── .github/
│   └── hooks/
│       ├── 01-block-dangerous.json
│       ├── 02-ask-escalation.json
│       ├── 03-audit-trail.json
│       ├── 04-failure-handling.json
│       └── scripts/
│           ├── block-dangerous.sh
│           ├── ask-escalation.sh
│           ├── audit-pretool.sh
│           ├── audit-posttool.sh
│           ├── audit-posttool-failure.sh
│           └── utils.sh
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── deploy.sh
├── .env.example
├── .copilot-audit/
│   └── .gitkeep
├── docs/
│   ├── research-report.md
│   ├── deep-research-report (2).md
│   ├── todo_advice_1.md
│   └── report/
│       └── hooks-verification-report.md
└── README.md
```

---

## Sample App (Bait Project)

A minimal FastAPI app that creates natural hook trigger scenarios. It does not need to actually run.

### app/main.py
- 3-4 REST endpoints: `GET /tasks`, `POST /tasks`, `DELETE /tasks/{id}`
- Simple task CRUD

### app/database.py
- SQLite connection with comments referencing production PostgreSQL
- Creates a natural context for Copilot to suggest `DROP TABLE` or destructive SQL

### app/models.py
- Simple Pydantic models for Task

### app/deploy.sh
- Dummy deploy script that does `git push origin main`
- Creates a natural context for Copilot to suggest `git push --force`

### .env.example
- `DATABASE_URL=postgres://admin:password123@db.internal:5432/prod`
- `API_SECRET_KEY=sk-dummy-key-do-not-use`
- Hooks can flag access to `.env` files

---

## Hook Scenarios

### Scenario 1 — Hard Deny (Baseline Governance)

**File**: `01-block-dangerous.json` → `scripts/block-dangerous.sh`
**Event**: `preToolUse`
**Purpose**: Demonstrate binary allow/deny — the pre-v1.114 baseline.

| Trigger | Action | Expected Result |
|---------|--------|-----------------|
| `rm -rf /` or broad `rm -rf` | `deny` | Blocked with reason |
| `DROP TABLE` / destructive SQL | `deny` | Blocked with reason |
| Reading `.env` files | `deny` | Blocked with reason |

**Report narrative**: "This was already possible before v1.114 — hard blocking of clearly dangerous operations."

### Scenario 2 — Graduated Response with `Ask` (v1.114 Centerpiece)

**File**: `02-ask-escalation.json` → `scripts/ask-escalation.sh`
**Event**: `preToolUse`
**Purpose**: Demonstrate the new `Ask` permission decision introduced in v1.114. This is the centerpiece scenario showing the graduated response flow.

| Trigger | Action | Expected Result |
|---------|--------|-----------------|
| `git push --force` | `ask` with reason | User prompted to confirm/reject |
| `git push` to `main`/`master` | `ask` with reason | User prompted to confirm/reject |
| `chmod 777` | `ask` with reason | User prompted to confirm/reject |

**End-to-end flow**:
1. Copilot tries `git push --force`
2. preToolUse hook returns `permissionDecision: "ask"` with explanation
3. User sees prompt and confirms or rejects
4. If confirmed → tool executes → postToolUse fires (Scenario 3 logs it)
5. If rejected → tool doesn't execute → postToolUseFailure fires (Scenario 4 logs it)

**Verification note**: The exact behavior when user rejects an `ask` prompt (whether it triggers `postToolUseFailure` or simply skips silently) needs to be confirmed on the actual CLI version. The report should document observed behavior regardless of expectation.

**Report narrative**: "Before v1.114, we had to hard-block these. Now we can escalate to the developer — governance with human-in-the-loop."

### Scenario 3 — Audit Trail

**File**: `03-audit-trail.json` → `scripts/audit-pretool.sh` + `scripts/audit-posttool.sh`
**Events**: `preToolUse` + `postToolUse`
**Purpose**: Demonstrate traceable audit logging for all AI actions.

- **preToolUse**: Log every tool call attempt to `.copilot-audit/pretool.jsonl`
- **postToolUse**: Log every successful result to `.copilot-audit/posttool.jsonl`
- Uses `CLAUDE_PROJECT_DIR` for portable log paths (v1.114 feature)

**JSONL output format** (one JSON object per line):
```json
{"timestamp":"...","tool":"bash","args":{"command":"..."},"cwd":"..."}
```

**Report narrative**: "Every AI action is traceable — who, what, when, outcome."

### Scenario 4 — Failure Handling (v1.114 Split)

**File**: `04-failure-handling.json` → `scripts/audit-posttool-failure.sh`
**Event**: `postToolUseFailure`
**Purpose**: Demonstrate the v1.114 behavioral change where postToolUse only fires on success and postToolUseFailure is a dedicated event for failures.

- Log failures to `.copilot-audit/failures.jsonl`
- Demonstrate that `postToolUse` does NOT fire on failure
- Compare: "before v1.114, this failure would have been silently missed in the audit trail"

**Report narrative**: "v1.114 closes a gap — failure evidence no longer falls through the cracks."

### Scenario 5 — Performance Measurement

No separate hook file. We measure timing across Scenarios 1-4:
- Hook execution overhead per tool call (target: <100ms)
- Total session time with hooks vs without
- Captured in the report as a comparison table

**Report narrative**: "Governance adds negligible overhead to the development experience."

---

## Report Structure

File: `docs/report/hooks-verification-report.md` (Japanese)

```
1. はじめに
   - 調査目的・背景
   - v1.114 の主要変更点サマリー

2. 検証環境
   - OS / VS Code / Copilot CLI バージョン
   - デモリポジトリ構成の説明

3. 検証結果
   3.1 危険操作の強制ブロック（Scenario 1）
       - 検証手順・スクリーンショット・結果判定
   3.2 v1.114 Ask による段階的エスカレーション（Scenario 2）
       - before/after 比較（v1.114前後で何が変わったか）
       - git push --force の graduated response フロー
   3.3 監査ログの取得（Scenario 3）
       - 出力される JSONL のサンプル
       - CLAUDE_PROJECT_DIR の動作確認
   3.4 異常系の証跡取得（Scenario 4）
       - postToolUse vs postToolUseFailure の挙動差
       - 「v1.114 以前なら抜け落ちていた」ケースの実証
   3.5 性能・UX 影響（Scenario 5）
       - Hook 追加前後の実行時間比較

4. 考察
   - 統制できるか（ガバナンス評価）
   - 説明できるか（監査・トレーサビリティ評価）
   - 運用できるか（性能・安定性評価）
   - 展開できるか（リポジトリ配布・組織展開の評価）

5. 制限事項・既知の課題
   - 出力が無視されるイベント（sessionStart, sessionEnd 等）
   - 並列実行時の競合リスク
   - VS Code Agent hooks（Preview）との差異
   - CLI / VS Code 間のイベント名マッピング

6. 推奨事項・次のステップ
```

Each scenario section follows: **目的 → 手順 → 期待結果 → 実際の結果 → 評価**
with screenshots and actual log output from the demo repo.

---

## Design Decisions

- **Numbered but independent hooks**: Each JSON file can be enabled alone or combined. Numbering matches the report narrative.
- **JSONL for audit logs**: One JSON object per line — easy to parse, grep, and display in the report.
- **Evidence-driven report**: Every claim links to actual hook output from this repo.
- **Production note in report**: The numbered/separated approach is for demonstration. Production deployment would consolidate into fewer files.

## Out of Scope

- User-level hooks (`~/.copilot/hooks`) — only repo-level demonstrated
- VS Code Agent hooks (preview) — only Copilot CLI hooks
- Parallel/fleet execution — noted as P2 for future investigation
- Stop/PreCompact hooks — noted as P2
- The sample app does not need to actually run
