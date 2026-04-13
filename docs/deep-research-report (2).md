# GitHub Copilot CLI Hooks（面向 VS Code 1.114 生态）的最新规格与实践研究

## 执行摘要

本报告聚焦 **GitHub Copilot CLI hooks** 在 **2026-04-01 发布的 VS Code 1.114 生态**中（以及同周期 Copilot CLI 版本演进）“**可用、可控、可审计**”的自动化能力：hooks 允许在 **会话生命周期、用户提交提示、工具调用前后、错误发生**等关键节点执行自定义脚本，并以 JSON 作为输入/输出载体，从而实现强制策略、审计日志、自动校验与通知等确定性自动化。citeturn3view0turn10view0turn12view0turn29view1

在 v1_114 时间点，hooks 的“版本特征”主要体现在三条主线：**(a)** VS Code 侧提供预览态的“Agent hooks”体系，支持 8 个事件、集中化诊断与多位置加载；**(b)** Copilot CLI 侧补齐了更强的 hook 生命周期覆盖（例如新增 `preCompact`、并在 2026-04-01 的 1.0.15 增加 `postToolUseFailure` 并调整 `postToolUse` 仅在成功时触发）；**(c)** hooks 的“作用域”从仓库级逐步扩展到用户级（`~/.copilot/hooks`），并在 VS Code 中被默认识别为用户级 hooks 位置。citeturn18view1turn16view0turn14view0turn26view1turn8search15

需要强调：hooks 并不是无限制的“插件系统”。在 GitHub 官方 hooks 参考中，很多事件的“输出”目前被标注为忽略（例如 `sessionStart`、`sessionEnd`、`userPromptSubmitted`、`postToolUse`、`errorOccurred` 等场景不支持修改输入/结果，只能用于记录/告警），真正具备“阻断/审批”能力的核心仍是 **pre-tool use** 一类钩子；同时 hooks 以同步方式阻塞 agent 执行，必须控制时延并隔离副作用。citeturn30view0turn22view4turn30view5

最后，从 VS Code 集成角度看，VS Code 既能作为 hooks 的“执行宿主”（Agent hooks），也能作为 Copilot CLI 的“可视化与上下文协作端”（/ide 连接、diff 审阅、会话转移与恢复）。但 Copilot CLI 会话在 VS Code 中存在明确限制：不能访问全部 VS Code 内建工具，不支持扩展提供的工具，MCP 也“当前仅能访问无需认证的本地 MCP”。citeturn23view0turn26view0

## 概述与架构

### 什么是 Copilot CLI hooks

在 GitHub 的定义中，hooks 是一种在 **agent 工作流的战略节点**执行“自定义 shell 命令”的机制：hook 脚本通过 **stdin 接收 JSON**（包含时间戳、工作目录、工具名称/参数、结果、错误等上下文），从而实现与上下文相关的自动化，例如审计、策略校验、工具调用阻断等。citeturn10view0turn12view0turn22view4

hooks 适用于 **Copilot cloud agent**（运行在 GitHub 上的云代理）以及 **GitHub Copilot CLI**（在本机终端中运行的代理）。citeturn10view0turn24view0

### hooks 的架构位置与数据流

hooks 的本质是“**在 agent/工具调用链上插入可执行的、确定性的拦截器**”，其输入/输出均以 JSON 表达：  
- 输入：由 Copilot CLI/agent 在触发点生成（例如 preToolUse 会携带 `toolName` 与 `toolArgs`）。citeturn22view4turn12view0  
- 输出：视事件而定。官方参考明确：多数事件输出被忽略，而 **pre-tool use** 的输出可用于做权限决策（至少支持 `deny` 生效；“allow/ask”在参考文档中标注“仅 deny 会被处理”，但 CLI 的变更日志显示“ask”在部分版本已可用于请求用户确认——需按版本验证）。citeturn30view3turn8search15turn22view0  

下面用 mermaid 展示典型的 CLI hooks 执行链路（从 prompt 到工具调用再到后置处理与错误钩子）：

```mermaid
flowchart LR
  U[用户在 Copilot CLI/VS Code 中提交 prompt] --> A[Copilot CLI Agent 会话]
  A -->|触发 userPromptSubmitted| H1[Hook: userPromptSubmitted 脚本]
  A -->|准备调用工具| P[触发 preToolUse]
  P --> H2[Hook: preToolUse 脚本\nstdin: toolName/toolArgs JSON]
  H2 -->|stdout: permissionDecision 等| D{是否允许执行?}
  D -- deny --> X[阻断工具调用\n记录原因/提示用户]
  D -- allow --> T[执行工具(如 bash/edit/view)]
  T -->|成功| Q[触发 postToolUse]
  Q --> H3[Hook: postToolUse 脚本\nstdin: toolResult JSON]
  T -->|失败| E[触发 errorOccurred 或 postToolUseFailure(新)]
  E --> H4[Hook: errorOccurred/postToolUseFailure]
  A -->|会话结束| S[触发 sessionEnd]
  S --> H5[Hook: sessionEnd]
```

该链路强调两点：**preToolUse 是策略控制核心**；其余钩子更多用于记录、告警、通知、生成报告等“旁路自动化”。citeturn22view4turn30view0turn30view5

### hooks 与 Copilot CLI、VS Code 的关系

- **Copilot CLI**：是一个“终端原生”的代理型 CLI，可交互或编程式运行，并具备 plan/autopilot 等模式；它可以执行/修改文件与 shell 命令，但默认要求用户审批并强调目录信任与权限风险。citeturn24view0turn33view1  
- **VS Code**：在 1.114（发布日期 2026-04-01）继续围绕 agentic chat 体验演进；同时提供 Copilot CLI 会话集成（后台会话、diff 视图、会话交接与恢复）与独立的 Agent hooks 体系（预览）。citeturn3view0turn23view0turn18view1  
- **/ide 连接**：Copilot CLI 可自动连接 VS Code（或在会话内用 `/ide` 管理连接），以共享选区上下文、在编辑器中展示 diffs、展现诊断并跨工具恢复会话。citeturn26view0turn23view0  

## 功能与规格

### v1_114 时间点的关键变更与新特性

本节按“与 hooks 直接相关、且在 2026-04-01 前后明确出现于官方文档/变更日志”的信息梳理。

**Copilot CLI：postToolUseFailure 与 postToolUse 语义收敛**  
Copilot CLI 2026-04-01 的 1.0.15 版本新增 **`postToolUseFailure` hooks**（用于工具错误），并将 `postToolUse` 调整为“仅在工具调用成功后运行”。这会改变你编排 hooks 的方式：失败通知/失败审计应迁移到 `postToolUseFailure`，避免过去用 `postToolUse` 同时处理成功/失败而导致逻辑混杂。citeturn14view0turn16view1

**Copilot CLI：用户级 hooks（全局 hooks）落地**  
CLI 变更日志明确加入：除仓库级 `.github/hooks` 外，开始从 **`~/.copilot/hooks` 加载个人 hooks**，使“跨项目统一策略”成为一等能力。citeturn8search15turn26view1

**Copilot CLI：Hook 事件覆盖扩展（preCompact 等）**  
CLI 变更日志显示新增 **`preCompact` hook**，在“上下文压缩（compaction）开始前”触发，从而允许你在对话被截断前导出关键上下文/落盘快照。citeturn16view0turn18view1

**VS Code：Agent hooks（预览）系统化与多源加载**  
VS Code 的 hooks 文档（落在 2026-04-01 更新点）给出：支持 8 个 hook 事件；默认从工作区 `.github/hooks/*.json`、用户 `~/.copilot/hooks`、以及 Claude 格式 `.claude/settings*.json` 等位置加载；并提供 `chat.hookFilesLocations`、`chat.useCustomAgentHooks` 等设置开关、以及“Load Hooks”诊断与 “GitHub Copilot Chat Hooks”输出通道。citeturn18view1turn18view2turn21view0

### hook 类型与触发点对照

为了在 VS Code + Copilot CLI 混合工作流中避免“写了钩子但没触发”，需要明确：**CLI hooks** 与 **VS Code Agent hooks** 的事件集并非完全相同，且命名风格不同（lowerCamelCase vs PascalCase）。VS Code 还会对 Copilot CLI hooks 配置做事件名与命令字段映射。citeturn21view4turn18view1turn29view1

下面给出一个“以实用为导向”的对照表（并标明来源差异点）：

| 维度 | Copilot CLI hooks（GitHub Docs/CLI 变更） | VS Code Agent hooks（Preview） |
|---|---|---|
| 典型触发点 | `sessionStart / sessionEnd / userPromptSubmitted / preToolUse / postToolUse / errorOccurred`（官方 hooks 文章与“Use hooks”模板列出）citeturn11view0turn29view1 | `SessionStart / UserPromptSubmit / PreToolUse / PostToolUse / PreCompact / SubagentStart / SubagentStop / Stop`（VS Code 明列 8 个事件）citeturn18view1turn19view2 |
| “上下文压缩前”事件 | `preCompact`（CLI 变更日志显示新增）citeturn16view0 | `PreCompact`（VS Code 支持）citeturn17view4turn18view1 |
| “工具失败后”事件 | `postToolUseFailure`（1.0.15 新增；并收敛 postToolUse 仅成功）citeturn14view0turn16view1 | 文档仅描述 `PostToolUse` 为“工具成功后”citeturn17view3 |
| 命名风格 | lowerCamelCase（如 `preToolUse`）citeturn29view1 | PascalCase（如 `PreToolUse`）citeturn17view2 |
| VS Code 对 CLI hooks 的适配 | — | 会将 CLI 的 lowerCamelCase 事件名转换为 VS Code PascalCase；并将 `bash/powershell` 映射为 `osx/linux/windows` 命令字段citeturn21view4 |

> 备注：GitHub 的“About hooks”概览页还列出 `agentStop / subagentStop` 等类型，但 GitHub 的 hooks configuration 参考主要展开 session/user/tool/error 等；而 VS Code hooks 则以自身 8 事件模型提供 Stop/SubagentStart/PreCompact 等。实践中应以“你所在宿主（CLI 或 VS Code）实际支持的事件集 + 当前版本变更日志”为准，并在 repo 内做最小验证。citeturn11view0turn12view0turn18view1turn16view0

### 可执行动作与 I/O 格式

#### 输入 JSON 的常见字段

在 GitHub 的 hooks configuration 参考中，不同事件输入不同，但常见围绕：  
- `timestamp`（毫秒时间戳）、`cwd`（当前工作目录）citeturn12view0turn30view0  
- `toolName` 与 `toolArgs`（pre-tool use）citeturn22view4  
- `toolResult`（post-tool use；包含 `resultType` 与 `textResultForLlm` 等）citeturn22view6turn30view0  
- `error`（error occurred；包含 message/name/stack）citeturn13view2turn30view0  

在 VS Code hooks 中，事件输入字段以 `tool_name/tool_input/tool_response` 等风格出现，并明确区分“common fields + hook 专属字段”。citeturn17view2turn17view3turn19view2

#### 输出 JSON 的控制面

**Copilot CLI / GitHub hooks 参考（更保守）**  
- 多数事件输出被标注为 “Ignored”（不处理返回值）；例如 sessionStart、sessionEnd、userPromptSubmitted（不支持修改 prompt）、postToolUse（不支持修改结果）、errorOccurred（不支持修改错误处理）。citeturn30view0turn30view1  
- preToolUse 支持输出 `permissionDecision` 与 `permissionDecisionReason`，且文档标注“allow/deny/ask 中当前只有 deny 会被处理”。citeturn22view0turn30view3  

**VS Code hooks（更强控制）**  
- 所有 hooks 支持 common output：`continue`、`stopReason`、`systemMessage` 来终止或提示（默认继续）。citeturn19view5  
- PreToolUse 的 `hookSpecificOutput` 可 `allow/deny/ask`，并可 `updatedInput`、`additionalContext`；并明确“最严格的决策优先”。citeturn19view4turn17view2  
- PostToolUse 可用 `decision:block` 阻断后续处理并注入上下文。citeturn17view3turn19view3  
- Stop 可 “block” 防止会话结束，但必须检查 `stop_hook_active` 防止无限运行与额外 premium requests 消耗。citeturn17view5  

**版本差异提示（重要）**：Copilot CLI changelog 显示 hooks 在部分版本已支持 `'ask' permission decision` 以请求用户确认，这与 GitHub hooks configuration 参考“仅 deny 生效”的描述存在张力。建议：在你的 CLI 版本上用最小脚本验证 `ask` 是否生效；若追求跨环境一致性，可优先用 `deny` + 让用户在对话中手动选择替代方案。citeturn8search15turn30view3

### 配置文件结构、加载位置与作用域

#### Copilot CLI 配置与 hooks 目录

Copilot CLI 的配置与会话数据默认落在 `~/.copilot`，其中包括 `hooks/` 目录（用户级 hooks），并且允许在 `config.json` 使用 `hooks` 键内联定义用户级 hooks，仓库级 hooks（`.github/hooks/`）会与用户级 hooks 一同加载。citeturn26view1turn27view0

同时，Copilot CLI 允许通过 `COPILOT_HOME` 或 `--config-dir` 改变配置目录位置；这会影响 hooks 的默认加载路径（因为 hooks/ 随配置目录迁移）。citeturn27view4turn25search22

#### VS Code hooks 加载位置与配置项

VS Code hooks 支持多个“hook files locations”：工作区 `.github/hooks/*.json`、用户 `~/.copilot/hooks`、Claude 配置等；并可通过 `chat.hookFilesLocations` 显式启用/禁用路径（仅支持相对路径与 `~`），工作区 hooks 对同一事件类型优先于用户 hooks。citeturn18view1turn18view2

此外，VS Code 支持“Agent-scoped hooks”：可在自定义 agent 的 `.agent.md` frontmatter 中直接定义 hooks，但需要启用 `chat.useCustomAgentHooks`。citeturn18view3

#### 统一视角的“作用域优先级”建议

综合 GitHub 与 VS Code 两侧信息，可将 hooks 作用域设计为：

1) **仓库级（`.github/hooks/`）**：团队共享、可审计、可随 PR 评审。citeturn29view1turn18view1  
2) **用户级（`~/.copilot/hooks`）**：个人全局策略（例如一刀切禁止危险命令、统一通知）。citeturn26view1turn18view1turn8search15  
3) **Agent 级（`.agent.md` frontmatter）**：仅对特定角色/子代理生效的强约束（例如“严格格式化 agent”）。citeturn18view3  

### 权限与安全边界

#### Copilot CLI 的权限模型（与 hooks 的关系）

Copilot CLI 的核心风险来自：它可以代表你执行 shell 命令与修改文件，因此默认要求你审批工具使用，并要求你在启动时确认“信任目录”；官方强调权限作用域是启发式的、不保证所有目录外文件都被保护，且不建议从 home 目录启动。citeturn24view0turn26view2

在工具层面，Copilot CLI 提供：  
- `--allow-all-tools`（允许所有工具无需确认）；  
- `--deny-tool` / `--allow-tool`（精细允许/拒绝某些工具或子命令）；  
并警告这会提高误操作与安全风险。citeturn24view0turn25search22

hooks 常用于在 preToolUse 上“再加一层企业/个人策略”，例如屏蔽 `rm -rf /` 或对 `git push` 强制 deny/ask。citeturn22view0turn22view4turn10view0

#### VS Code hooks 的安全边界

VS Code 文档明确：hooks 执行的 shell 命令具有与 VS Code 相同的权限，来自不可信来源的 hooks 必须审查；并建议限制 agent 对 hook 脚本的可编辑性（例如通过 `chat.tools.edits.autoApprove` 避免 agent 自改 hook 脚本并执行）。citeturn21view0turn21view4

另外，VS Code 组织策略可能禁用 hooks（预览功能），这对企业环境尤为常见。citeturn17view9

## 限制与不能做的事

### 官方明确的“输出不生效”限制

在 GitHub hooks configuration 参考中，多数事件的输出被标注为忽略：  
- `sessionStart`/`sessionEnd`：输出不处理（只能做记录/清理）；citeturn30view0turn22view4  
- `userPromptSubmitted`：不支持通过 hook 修改 prompt；citeturn30view0turn30view2  
- `postToolUse`：不支持修改工具结果；citeturn30view0  
- `errorOccurred`：不支持通过 hook 改写错误处理；citeturn30view0turn13view2  

因此，“想用 hooks 改写用户输入、或篡改工具输出再喂给模型”的思路，在官方参考框架下通常不可行；更现实的做法是：把 hooks 用于 **阻断、记录、告警、生成附加上下文文件**，再通过 prompt/说明让 agent 自行读取。citeturn30view0turn10view0

### 性能、并发与稳定性风险

- **同步阻塞**：GitHub 明确 hooks 同步运行并阻塞 agent 执行，并建议尽可能将 hook 执行时间控制在 5 秒内，避免同步 I/O 与昂贵计算。citeturn30view5turn30view6  
- **并行子代理带来的竞态**：Copilot CLI `/fleet` 会把任务拆成子任务并行由 subagents 执行；这意味着多个工具调用可能更密集地产生 hooks 触发，从而引入日志写入冲突、锁竞争、以及“hook 自身成为瓶颈”的风险。citeturn33view0turn11view0  
- **工具并行执行**：CLI 命令参考中存在 `--disable-parallel-tools-execution`，并注明即使禁用，LLM 仍可能发起并行工具调用但会按顺序执行；这暗示 hooks 在高并发工具场景必须做好幂等与互斥。citeturn25search22turn32search7  

### 网络、隐私与合规风险

- GitHub 明确警告：hooks 若进行外部网络调用可能引入延迟、失败、并向第三方暴露数据；同时不要记录敏感数据（token/password），要做输入校验与正确的 shell 转义以防注入。citeturn30view6turn11view4  
- Copilot CLI 会把会话数据存储在本机（用于恢复、/chronicle 等能力）；这提高了可追溯性，但也意味着日志与会话文件可能包含敏感上下文，必须配套访问控制与清理策略。citeturn33view2turn26view1  

### VS Code 集成上的能力边界

在 VS Code 中运行的 Copilot CLI sessions 明确存在：  
- 不能访问全部 VS Code 内建工具；  
- 不支持扩展提供的工具；  
- 模型受 CLI 工具可用模型限制；  
- 目前只能访问“不需要认证”的本地 MCP servers。citeturn23view0turn26view0  

这些限制决定了：你不能指望通过 hooks “调用某个 VS Code 扩展工具”来实现自动化；更可靠的是在 hooks 中调用你可控的命令行工具（例如 `jq`、`git`、`npm`、`pytest`）并把结果落盘。citeturn23view0turn10view0

## 与 VS Code 集成

### 启用与配置路径

**VS Code Agent hooks（在编辑器内的 hooks）**  
- 默认加载位置包括：`.github/hooks/*.json`、`~/.copilot/hooks`、`.claude/settings*.json` 等；可用 `chat.hookFilesLocations` 调整启用/禁用路径。citeturn18view1turn18view2  
- 如需自定义 agent frontmatter hooks，需开启 `chat.useCustomAgentHooks`。citeturn18view3  
- monorepo 场景可启用 `chat.useCustomizationsInParentRepositories` 以发现父仓库根的 hooks。citeturn18view1  

**Copilot CLI sessions（在 VS Code 内托管/可视化的 CLI 会话）**  
VS Code 文档说明：Copilot CLI sessions 在本机后台独立运行，VS Code 通过 Copilot SDK 启动/停止/监控，并会自动安装配置 Copilot CLI。citeturn23view0  
创建会话可通过 Chat 视图的 Session Target 选择 Copilot CLI，或命令面板运行 “Chat: New Copilot CLI”。citeturn23view0

### 连接机制与调试协作体验

**CLI → VS Code 的 /ide 连接（推荐开启）**  
Copilot CLI 能在启动时自动连接 VS Code：它会检查 CLI 当前工作目录是否匹配已在 VS Code “trusted mode”打开的 workspace；并在启动信息中显示已连接 VS Code（或 Insiders）。若同一 workspace 多窗口打开，CLI 只能连接其中一个且不能同时连接多个，可用 `/ide` 切换。citeturn26view0  
建立连接后可：  
- 直接用 VS Code 选区作为上下文；citeturn26view0  
- 在 VS Code 中以 side-by-side diff 审阅文件修改（接受/拒绝）；citeturn26view0  
- 在 VS Code Sessions 视图查看 CLI 会话记录并在终端恢复。citeturn26view0turn23view0  

**重要交互细节**：如果启用了 `--allow-all` / `--yolo` 或等价自动许可，diff 视图不会出现，修改会直接落盘；这会改变你基于 hooks 的“先审后写”策略，需谨慎。citeturn26view0turn24view0

### hooks 的调试与诊断

VS Code 提供两条“可操作的排障路径”：  
- View Logs 中查找 “Load Hooks” 以确认加载了哪些 hooks、从哪些位置加载；citeturn21view0  
- Output 面板选择 “GitHub Copilot Chat Hooks” 查看 hook 输出与错误；并列出常见问题：未执行、权限错误（缺 `chmod +x`）、timeout、JSON parse error 等。citeturn21view0  

此外，VS Code FAQ 明确：会解析 Copilot CLI hooks 并将事件名 lowerCamelCase → PascalCase，`bash/powershell` → OS-specific 字段，这对“同一套 hooks 同时用于 CLI 与 VS Code”很关键。citeturn21view4

## 最佳实践

### 开发与测试策略

hooks 的工程化建议可归纳为“**小、快、可回滚**”：  
- 保持 hooks **短执行路径**（尽量 <5 秒），不要在 hook 内做重计算；将重任务异步化或交给后台作业（例如写入队列/文件后由独立进程处理）。citeturn30view5turn30view6  
- hooks 脚本必须进行输入校验与转义，避免命令注入；尤其是从 JSON 中拼接 shell 命令时。citeturn30view6turn11view4  
- 用 “dry-run” 模式（环境变量开关）让同一脚本可在本地手动喂入样例 JSON 进行测试，避免把调试成本压到 agent 执行链路上（GitHub 官方也建议通过脚本开启 verbose debug 并将输入打印到 stderr）。citeturn29view5turn12view0  

### 部署、版本控制与审计

- **仓库级 hooks 进 Git**：将 `.github/hooks/*.json` 与脚本纳入 PR 评审流程，确保 hooks 变更可追溯。citeturn29view1turn18view1  
- **用户级 hooks 走个人策略**：把 `~/.copilot/hooks` 用作“个人全局护栏/通知”，但避免把企业策略只放在个人目录（不可控、难审计）。citeturn26view1turn18view1  
- **审计日志落盘**：利用 `userPromptSubmitted`、`preToolUse`、`postToolUse`、`errorOccurred` 输入 JSON 做 JSONL 追加写，形成“可索引审计轨迹”；注意并发写入加锁或使用原子追加。citeturn12view0turn22view6turn30view6  

### 安全策略建议

- **最小权限**：不要在 hooks 中调用会扩大权限面的命令（例如直接操作生产凭证/密钥库）；如必须访问机密，使用安全的凭证注入方式（环境变量/安全存储）且不输出到日志。citeturn30view6turn11view4  
- **避免让 agent 自改 hooks**：VS Code 建议通过 `chat.tools.edits.autoApprove` 等策略防止 agent 在执行过程中修改 hook 脚本并立即执行，从而形成“自我修改—自我执行”的高风险闭环。citeturn21view0  
- **autopilot 与 hooks 的组合要有“刹车”**：autopilot 允许连续步骤执行；但官方强调它在未授予完整权限时不能执行需要许可的动作，并建议用 `--max-autopilot-continues` 限制连续步数避免无限循环。citeturn33view1turn25search22  

## 示例

> 说明：以下示例同时覆盖 “Copilot CLI hooks” 与 “VS Code Agent hooks”。每个示例均标注前提假设、预期行为与错误处理方式。示例中涉及的命令名/工具名请以你实际环境为准（macOS/Linux/Windows、Shell、Node/Python 等）。citeturn24view0turn18view1turn29view1  

### 示例一：全局安全护栏，阻断破坏性 shell 命令

**前提假设**  
- 未指定 OS；假设为 macOS/Linux（bash 可用）。  
- Copilot CLI 使用的配置目录为默认 `~/.copilot`，且已支持从 `~/.copilot/hooks` 加载个人 hooks。citeturn26view1turn8search15  
- 目标：在所有仓库中统一阻断 `rm -rf /`、高危 `rm -rf`、以及包含 `DROP TABLE` 等明显危险模式。  

**配置文件（用户级 hooks）**：`~/.copilot/hooks/security.json`  
（事件名使用 CLI 的 lowerCamelCase；脚本用 bash 字段；timeoutSec 可按需调整）citeturn29view1turn11view0turn22view4

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "bash": "~/.copilot/hooks/scripts/pretool-guard.sh",
        "timeoutSec": 5
      }
    ]
  }
}
```

**脚本**：`~/.copilot/hooks/scripts/pretool-guard.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"

TOOL_NAME="$(echo "$INPUT" | jq -r '.toolName')"
TOOL_ARGS_RAW="$(echo "$INPUT" | jq -r '.toolArgs')"

# 仅对 bash/shell 工具做策略示例（真实 toolName 以你的环境为准）
if [[ "$TOOL_NAME" != "bash" ]]; then
  exit 0
fi

# toolArgs 是 JSON 字符串；尝试解析出 command
CMD="$(echo "$TOOL_ARGS_RAW" | jq -r '.command // empty' 2>/dev/null || true)"

# 简单高危规则（示例）
if echo "$CMD" | grep -Eq 'rm -rf[[:space:]]*/($|[[:space:]])'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"Policy: rm -rf / is blocked"}'
  exit 0
fi

if echo "$CMD" | grep -Eq 'rm -rf'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"Policy: rm -rf is blocked by default"}'
  exit 0
fi

if echo "$CMD" | grep -Eiq 'drop[[:space:]]+table'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"Policy: destructive SQL patterns are blocked"}'
  exit 0
fi

# 默认放行：不输出或显式 allow（参考文档中 allow 可能被忽略，但不影响“放行”语义）
echo '{"permissionDecision":"allow"}'
```

**预期行为**  
- 当 Copilot CLI 准备调用 `bash` 且命令匹配高危模式时，hook 输出 `permissionDecision=deny`，工具执行被阻断并给出原因。citeturn22view0turn22view4turn30view3  
- 对非 bash 工具调用不拦截。  

**错误处理**  
- 若 `jq` 不存在或脚本不可执行，会导致 hooks 失败或超时；官方 troubleshooting 建议检查 JSON、`chmod +x`、shebang、以及 `timeoutSec`。citeturn29view2turn29view8  
- 若你发现 `permissionDecision:"allow"` 在 CLI 上无效果（参考文档提示只处理 deny），可改为“默认不输出任何 stdout”，仍可达到放行目的。citeturn30view3turn22view0  

### 示例二：仓库级审计轨迹，记录每次工具调用与结果

**前提假设**  
- 未指定 OS；假设为 macOS/Linux。  
- 你希望把审计留在仓库中，便于团队审阅与合规（`.github/hooks/`）。citeturn29view1turn18view1  
- 仅做日志，不尝试修改工具结果（因为官方参考标注 postToolUse 输出不支持修改结果）。citeturn30view0turn22view6  

**配置文件（仓库级）**：`.github/hooks/audit.json`

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      { "type": "command", "bash": "./.github/hooks/scripts/log-pretool.sh", "timeoutSec": 5 }
    ],
    "postToolUse": [
      { "type": "command", "bash": "./.github/hooks/scripts/log-posttool.sh", "timeoutSec": 5 }
    ],
    "errorOccurred": [
      { "type": "command", "bash": "./.github/hooks/scripts/log-error.sh", "timeoutSec": 5 }
    ]
  }
}
```

**脚本一（preToolUse）**：`./.github/hooks/scripts/log-pretool.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
INPUT="$(cat)"

ts="$(echo "$INPUT" | jq -r '.timestamp')"
cwd="$(echo "$INPUT" | jq -r '.cwd')"
tool="$(echo "$INPUT" | jq -r '.toolName')"

# toolArgs 是 JSON 字符串，直接落盘留痕
args="$(echo "$INPUT" | jq -r '.toolArgs')"

printf '%s\t%s\t%s\t%s\n' "$ts" "$cwd" "$tool" "$args" >> .copilot-audit/pretool.tsv
```

**脚本二（postToolUse）**：`./.github/hooks/scripts/log-posttool.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
INPUT="$(cat)"

tool="$(echo "$INPUT" | jq -r '.toolName')"
resultType="$(echo "$INPUT" | jq -r '.toolResult.resultType')"
resultText="$(echo "$INPUT" | jq -r '.toolResult.textResultForLlm')"

jq -c -n \
  --arg tool "$tool" \
  --arg rt "$resultType" \
  --arg txt "$resultText" \
  '{tool:$tool,resultType:$rt,text:$txt}' >> .copilot-audit/posttool.jsonl
```

**脚本三（errorOccurred）**：`./.github/hooks/scripts/log-error.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
INPUT="$(cat)"

msg="$(echo "$INPUT" | jq -r '.error.message')"
name="$(echo "$INPUT" | jq -r '.error.name')"

printf '%s\t%s\t%s\n' "$(date -Is)" "$name" "$msg" >> .copilot-audit/errors.tsv
```

**预期行为**  
- 每次工具调用前后与错误发生时都会追加写入审计文件，形成可检索轨迹；输入字段结构与 `toolResult`/`error` 字段来自官方 hooks configuration 参考。citeturn22view4turn22view6turn13view2  
- 不依赖输出 JSON 生效能力（因为 postToolUse 与 errorOccurred 输出在参考中标注忽略）。citeturn30view0turn30view1  

**错误处理**  
- 并发写入风险：在 `/fleet` 并行子代理或并行工具调用时，多个 hook 可能同时写同一文件；建议改为写入单独文件（按 session/tool_use_id 分片）或加文件锁。并行执行机制来自 `/fleet` 文档与 CLI 并行工具执行选项的提示。citeturn33view0turn25search22  

### 示例三：VS Code Stop hook 强制“先跑测试再结束”，并避免无限循环

**前提假设**  
- 未指定 OS；假设 VS Code 在本地运行，且启用了 VS Code Agent hooks（预览）。citeturn17view9turn18view1  
- 你的项目存在可执行的测试命令（示例用 `npm test`，可替换为 `pytest`、`go test` 等）。  
- 目标：当 agent 即将结束会话时自动跑测试；若失败则阻断停止并提示原因；需检查 `stop_hook_active` 避免无限运行与额外 premium requests。citeturn17view5turn33view1  

**配置文件（工作区）**：`.github/hooks/stop-test.json`（VS Code PascalCase）

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "./.github/hooks/scripts/stop-run-tests.sh",
        "timeout": 120
      }
    ]
  }
}
```

**脚本**：`./.github/hooks/scripts/stop-run-tests.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"

# VS Code Stop hook 特有字段：stop_hook_active
ACTIVE="$(echo "$INPUT" | jq -r '.stop_hook_active // false')"

# 防止无限循环：如果已经处于 stop hook 继续态，就放行
if [[ "$ACTIVE" == "true" ]]; then
  echo '{"hookSpecificOutput":{"hookEventName":"Stop","decision":"allow"}}'
  exit 0
fi

# 运行测试（可替换）
if npm test; then
  # 通过：允许停止（不输出也可）
  echo '{"hookSpecificOutput":{"hookEventName":"Stop","decision":"allow"}}'
else
  # 失败：阻断停止，要求继续修复
  echo '{
    "hookSpecificOutput":{
      "hookEventName":"Stop",
      "decision":"block",
      "reason":"Tests failed. Please fix failures before finishing."
    },
    "systemMessage":"Stop hook blocked session end because tests failed."
  }'
fi
```

**预期行为**  
- Stop hook 在会话结束时执行；若测试失败，返回 `decision:"block"` 阻断会话结束并提示 reason；同时通过 `stop_hook_active` 防止重复阻断导致无限回合。citeturn17view5turn19view5  

**错误处理**  
- 若脚本超时或不可执行，VS Code troubleshooting 建议检查文件位置、`type:"command"`、执行权限、以及 timeout 设置。citeturn21view0  
- 若你在 autopilot 模式下使用，注意 autopilot 的持续步数与权限策略（例如 `--max-autopilot-continues`），避免“测试失败→继续→仍失败”的高成本循环。citeturn33view1turn25search22  

## 迁移与兼容性

### 从早期版本迁移的关注点

**从“仓库级 hooks”迁移到“用户级 hooks”**  
早期 hooks 文档强调 `.github/hooks/`（并指出 CLI 从当前工作目录加载 hooks），而在 v1_114 周期内，CLI 配置目录文档与 CLI changelog 已明确支持 `~/.copilot/hooks` 用户级 hooks，并且 VS Code hooks 也默认识别该位置。迁移建议：把跨项目通用策略（安全护栏、通知）迁移到用户级；把团队策略留在仓库级。citeturn29view1turn26view1turn18view1turn8search15  

**事件命名与字段映射（CLI ↔ VS Code）**  
如果你希望“一套配置跨 CLI 与 VS Code 共用”，必须处理：  
- CLI lowerCamelCase → VS Code PascalCase（例如 `preToolUse` → `PreToolUse`）；citeturn21view4  
- CLI `bash/powershell` → VS Code `linux/osx/windows`；citeturn21view4  
- tool 输入字段命名风格差异（VS Code 与 Claude/CLI 并不一致；VS Code FAQ 对 Claude 配置还强调 snake_case vs camelCase、以及 matcher 目前被忽略）。citeturn21view3turn21view4  

**postToolUse 行为变化**  
若你早期在 CLI 用 `postToolUse` 同时处理成功与失败，需注意 1.0.15 起 `postToolUse` 仅在成功后触发，失败应迁移到 `postToolUseFailure`（否则会漏报失败事件）。citeturn14view0turn16view1  

### 参考与优先来源

以下来源按“官方优先 → 官方问题追踪 → 社区补充”的顺序列出（中文优先；但官方多数为英文/日文版本）：

- VS Code 1.114 发布说明（发布日期 2026-04-01）citeturn3view0  
- GitHub 官方：About hooks（hooks 定义、支持范围、性能/安全注意）citeturn10view0turn30view6  
- GitHub 官方：Hooks configuration（hook 类型、输入输出样例、哪些输出被忽略、preToolUse 权限决策字段）citeturn12view0turn22view0turn30view0  
- GitHub 官方：Using hooks with GitHub Copilot CLI（`.github/hooks/`、模板、troubleshooting、debugging）citeturn29view1turn29view8turn29view5  
- VS Code 官方：Agent hooks in VS Code（Preview）（8 事件、加载位置、chat.hookFilesLocations、诊断通道、Stop 防无限运行）citeturn18view1turn19view5turn21view0turn17view5  
- VS Code 官方：Copilot CLI sessions in VS Code（后台会话、隔离模式、限制）citeturn23view0  
- GitHub 官方：Connecting Copilot CLI to VS Code（/ide、diff、选区上下文、会话恢复）citeturn26view0  
- GitHub 官方：Copilot CLI configuration directory（`~/.copilot` 结构、hooks/、COPILOT_HOME、--config-dir）citeturn26view1turn27view4  
- GitHub 官方：Copilot CLI releases / changelog（1.0.15 的 hooks 变化；历史版本对用户级 hooks 与 ask 的演进）citeturn14view0turn16view1turn8search15  
- GitHub 官方：/fleet 并行子代理（并行带来的 hooks 触发密度/竞态风险）citeturn33view0  
- GitHub Issues（供理解需求与变更动机）：用户级 hooks 的诉求与讨论（例如“Global Hooks Configuration”“User Level Hooks”）citeturn8search4turn8search7