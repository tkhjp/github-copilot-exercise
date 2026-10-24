# 研发台账与 PR Review 知识平台
## 初步开发设计文档 v0.2

**用途：** 产品、架构与开发评审；确认边界后拆解实施任务。  
**日期：** 2026-10-24。**状态：** 设计草案，非已上线能力。  
**沿用模型：** v0.1 的 30 类 Entity、67 类 Edge；本版补充字段、基数、生命周期、数据流程和 SKILL 契约。  
**关键约束：** 首版不采用 embedding、向量库或以相似度 top-K 为核心的 RAG。

> 本文中的组件划分、接口名称、状态机、数据样例和验收条件均为本项目设计提案。外部产品/API 事实在相应位置标明来源。尚未连接你的真实 GitHub、Confluence、Jira 数据，也未运行真实仓库的效果测试。

# 01 背景、目标与边界

## 1.1 要解决的问题

当前设想的输入来自三套系统：Jira 记录工作项与状态，Confluence 记录需求与设计，GitHub 记录代码、PR 和审查。单个系统中的状态不足以回答“这项需求是否已实现、是否被验证、为什么这样设计、过去出现的问题是否重演”。

需要建设的不是一份每日自动写的项目总结，而是一套**有实体、有关系、有证据和版本的研发台账**，以及由真实 Review 活动积累的团队知识。自动 PR Review 是第一个消费这些知识的 Agent，后续 IDE 和其他 SKILL 使用同一层能力。

## 1.2 两条必须打通的链

**研发追溯链：** `Document ─DESCRIBES→ Requirement ←TRACKS─ WorkItem ←IMPLEMENTS─ PullRequest ─CONTAINS_COMMIT→ Commit ─INTRODUCES_CHANGE→ CodeChange`，再连接测试与部署证据。

**知识复用链：** `ReviewComment → ReviewFinding ← 修复 CodeChange ← ReviewCase ← ReviewRule ← 下一次 Review`。这里箭头应按实际 Edge 方向读取，具体定义见第 02 章。

产品必须能回答：某个工作项的要求和实现证据在哪里；某组件过去的 Review 问题如何处理；新 PR 适用哪些已批准规则；哪些旧经验因需求或代码变化需要重新确认。

## 1.3 范围与非目标

| 范围 | 首版处理方式 |
|---|---|
| 输入 | 先登记少数 GitHub 仓库、Confluence 空间/页面、Jira 项目；禁止默认全组织扫描 |
| 台账 | 按 WorkItem、PR、Component 提供结构化视图和证据链 |
| Review 知识 | 评论拆分为 Finding，关联修复与结果，形成 Case、Pattern、Rule 候选 |
| 新 PR 审查 | 固定代码版本，载入适用知识，生成草稿；先静默运行，再经批准开放自动评论 |
| SKILL | 提供追溯、历史经验、PR 审查、知识整理、失效检查五类工作流 |
| 不做 | 通用企业问答、全组织知识搜索、自动 merge/approve、无人审批的规则发布、在线自改安全策略 |
| 延后 | 完整发布/部署/事故链、多组织交叉检索、图数据库、自动跨语言精确符号解析 |

**未确认的部署假设：** 参考接口以 GitHub 与 Atlassian Cloud 文档为起点，不等于你的实际环境为 Cloud。GitHub Enterprise Server / Jira、Confluence Data Center 的版本、认证、分页、事件与权限必须在连接器接入阶段单独确认。不能将 Cloud API 地址直接套用到 Data Center。

# 02 Ontology：实体、关系与具体约束

## 2.1 模型是什么

Ontology 定义三件事：**允许存哪些 Entity、允许哪些类型通过什么 Edge 连接、怎样才算一条有效关系。**数据库表、同步任务和 API 是实现方式，不代替领域定义。

实体层分为七组：需求与设计、代码与实现、审查活动、经验与规则、测试与验证、交付与运行反馈、人员与责任。完整 30 类实体、所有属性和 67 类关系在本文末尾附录中可逐项查阅，并与随附 YAML 保持一致。

## 2.2 首先必须区分的对象

| 不可混用的对象 | 定义边界 |
|---|---|
| Document / Requirement / DesignDecision | 页面是载体；要求是应满足的条件；决策是选择某方案及其理由 |
| WorkItem / Requirement | 工单负责跟踪工作，不能以工单标题自动替代需求 |
| PullRequest / Commit / CodeChange | PR 是协作对象；Commit 是确定提交；CodeChange 是指定版本差异中的局部修改 |
| Review / ReviewThread / ReviewComment | 审查提交、讨论线程、单条评论不同；线程可跨多轮审查 |
| ReviewComment / ReviewFinding | 评论原文与原子问题不同；支持一评多问题、多评一问题 |
| ReviewCase / DefectPattern / SolutionPattern / ReviewRule | 历史案例、失败机制、解决方法、下次要检查的规则不同 |
| TestCase / TestRun / TestResult | 测试定义、执行、单项结果不同；运行成功不等于所有要求通过 |
| Release / Deployment | 发布记录不等于制品已经进入生产环境 |

GitHub API 本身区分 Review、Thread、ReviewComment，且 PR 行内审查评论与 issue comments 并非同一种源对象。本平台应保留这种差异，而不是把所有文本拼成一条 PR 摘要。[S02][S03]

## 2.3 研发事实图：主干 Edge

```text
Document ──DESCRIBES─────────────→ Requirement
Document ──RECORDS_DECISION──────→ DesignDecision
DesignDecision ──ADDRESSES_REQUIREMENT→ Requirement
DesignDecision ──CONSTRAINS──────→ Component
Requirement ──HAS_CRITERION──────→ AcceptanceCriterion
WorkItem ──TRACKS────────────────→ Requirement
PullRequest ──REFERENCES_WORK_ITEM→ WorkItem     # 明确提及
PullRequest ──IMPLEMENTS─────────→ WorkItem     # 待确认 / 已确认实现
PullRequest ──CONTAINS_COMMIT────→ Commit
Commit ──INTRODUCES_CHANGE───────→ CodeChange
CodeChange ──MODIFIES────────────→ CodeElement
Component ──CONTAINS_ELEMENT─────→ CodeElement
Repository ──HOSTS───────────────→ Component
Team ──OWNS─────────────────────→ Component

TestCase ──VERIFIES_CRITERION────→ AcceptanceCriterion
TestRun ──TESTS_COMMIT───────────→ Commit
TestRun ──PRODUCES_RESULT────────→ TestResult
TestResult ──RESULT_OF_CASE──────→ TestCase
BuildArtifact ──BUILT_FROM───────→ Commit
Release ──INCLUDES_ARTIFACT──────→ BuildArtifact
Deployment ──DEPLOYS_ARTIFACT────→ BuildArtifact
Deployment ──TARGETS_ENVIRONMENT─→ Environment
```

`IMPLEMENTS` 的存在不直接把 WorkItem 设为完成。台账分别展示源工作状态、实现关联、验收证据与部署证据，允许“Jira Done，但测试未接入”。

## 2.4 Review 知识图：核心 Edge

```text
PullRequest ──HAS_REVIEW──────────→ Review
PullRequest ──HAS_THREAD──────────→ ReviewThread
ReviewThread ──HAS_COMMENT────────→ ReviewComment
ReviewComment ──RAISES────────────→ ReviewFinding
ReviewComment ──SUPPORTS_FINDING───→ ReviewFinding
ReviewComment ──DISPUTES_FINDING───→ ReviewFinding
ReviewFinding ──OBSERVED_IN_PR────→ PullRequest
ReviewFinding ──LOCATED_IN_CHANGE─→ CodeChange
CodeChange ──ADDRESSES_FINDING────→ ReviewFinding
CodeChange ──FIXES────────────────→ ReviewFinding
TestResult ──SUPPORTS_RESOLUTION──→ ReviewFinding

ReviewCase ──DOCUMENTS_FINDING────→ ReviewFinding
ReviewCase ──HAS_FIX──────────────→ CodeChange
ReviewCase ──HAS_EVIDENCE─────────→ ReviewComment / CodeChange / TestResult / DesignDecision
ReviewCase ──INSTANCE_OF_PATTERN──→ DefectPattern
ReviewCase ──DEMONSTRATES_SOLUTION→ SolutionPattern
SolutionPattern ──MITIGATES───────→ DefectPattern
ReviewRule ──DERIVED_FROM─────────→ ReviewCase / Requirement / DesignDecision
ReviewRule ──DETECTS_PATTERN──────→ DefectPattern
ReviewRule ──RECOMMENDS_SOLUTION──→ SolutionPattern
ReviewRule ──APPLIES_TO───────────→ Component / Repository
ReviewRule ──EXCEPTION_DEFINED_BY─→ DesignDecision
Review ──USES_RULE────────────────→ ReviewRule
Review ──CONSULTS_CASE────────────→ ReviewCase
```

**正式规则不是每个 PR 都要产出的结果。**一个 Case 可以被记录为误报或合理例外，也可以长期不生成 Rule。已有架构要求可以直接通过 `DERIVED_FROM → Requirement / DesignDecision` 成为规则来源，无需伪造历史案例。

## 2.5 主键、版本与身份

| 对象 | 主键策略 | 必须保留的版本／位置 |
|---|---|---|
| GitHub 对象 | source instance + 原生稳定 ID；PR number 仅作展示／查找别名 | PR 快照的 base/head SHA；评论 ID、原始 commit/line/side |
| Jira WorkItem | Atlassian site/实例 + issue ID；issue key 可作为会变化的别名 | 源 updated、相关 changelog、我们观察到的正文快照哈希 |
| Confluence Document | site/实例 + page ID | page version + 章节/内容块定位 + 原文哈希 |
| Requirement / Decision | 平台 canonical ID；经确认的章节锚点或显式编号映射 | 独立 revision；页面更新不自动创建全新逻辑要求 |
| Component | 人工登记或受保护组件目录的稳定 ID | repo/path 映射的版本与生效范围 |
| CodeElement | repo + 文件/符号身份映射；无法确认重命名时保持独立 | SHA + path + symbol/line；重命名匹配记录候选与确认 |
| Finding / Case / Rule | 平台稳定 ID | 不可变 revision；引用源与规则版本 |
| Actor | 各系统账号先独立；可信身份目录或人工确认后关联 | 不用同名、邮箱猜测自动合并；保留映射来源 |

**实体 ID 不携带版本。**如 `rule:CACHE-001` 是逻辑对象，`rule:CACHE-001@r3` 是示例 revision ID。旧实例文件 v0.1 曾将版本写在部分节点 ID 中，仅作历史示意；新实现采用“稳定 ID + revision”的形式。

每个记录还必须有 `tenant_id`。repo ID、Jira issue ID、page ID 都必须带 source instance/site 范围，不能假设不同实例的数字 ID 全局唯一。

## 2.6 Edge 不是一条裸三元组

```yaml
id: edge:fix-01
revision_id: edge:fix-01@r2
tenant_id: demo
from_id: change:fix-01
from_version: change:fix-01@r1
type: FIXES
to_id: finding:F-01
to_version: finding:F-01@r2
assertion_status: confirmed
evidence_basis: human_confirmation
evidence_refs: [evidence:comment-02@r1, evidence:test-02@r1]
asserted_by: actor:reviewer-01
recorded_at: 2026-10-20T03:00:00Z
system_from: 2026-10-20T03:00:00Z
system_to: null
valid_from: 2026-10-20T03:00:00Z
valid_to: null
freshness_status: current
context:
  repository_id: repo:demo-backend
  head_sha: 2222222222222222222222222222222222222222
```

以上为虚构样例。`confirmed` 表示符合平台既定证据/批准流程，不是模型置信分数，也不意味着形式化证明。

| 状态 | 可由谁产生 | 查询时如何使用 |
|---|---|---|
| observed | 连接器或确定性转换 | 证明源系统直接记录的关系，不扩大其含义 |
| proposed | LLM、启发式匹配或待确认人工输入 | 候选区可见；不能冒充事实参与正式完成判断 |
| confirmed | 有权限的人工或被批准的确定性验证流程 | 作为已确认语义关系，仍需校验版本和范围 |
| rejected | 有权限的审阅者／策略 | 保留拒绝原因；不进入有效事实图 |
| superseded | 受控状态更新 | 保留历史，仅用于历史查询 |

`assertion_status` 与 `freshness_status` 分开：以前确认过的边，也可能在依赖更新后变为 `needs_revalidation`。来源编辑、撤权、失效不会被一个过期的 confirmed 标签掩盖。

## 2.7 基数和语义校验

v0.1 中统一写入的 `many-to-many` 是概念占位，不应直接成为数据库校验。本版 YAML 已逐关系补充 out/in 基数。基数只作用于**同一有效上下文快照**，不是把所有历史版本合在一起计算。

关键约束：每个 PR 恰好一个目标仓库；一个 Finding 恰好针对一个 PR；一个 ReviewCase 围绕一个 Finding；单项 TestResult 属于一个 TestRun 和一个 TestCase；Thread 属于 PR，Comment 最多归属一个源 Review；Jira 层级子项最多一个父项且不可成环。

不完整导入暂时缺边时，记录 `completeness=partial` 并进入修复队列，不能为了满足基数而编造节点。`FIXES`、`IMPLEMENTS`、`VIOLATES`、`APPROVED_RULE` 等敏感语义还要执行专门校验，不仅检查起终点类型。

**代码差异注意事项：** `CodeChange` 可以描述 commit-parent 差异，也可以描述一次固定 base/head 的 PR 聚合差异。后者由 ReviewSnapshot 的变更清单引用，不强行建立 `INTRODUCES_CHANGE` 指向 PR 最后一个提交。`LOCATED_IN_CHANGE` 必须能回到当次审查的准确代码。

# 03 数据源接入与映射

## 3.1 三个连接器的职责

| 来源 | 必采数据 | 首先直接生成 | 候选抽取／关联 |
|---|---|---|---|
| GitHub | 仓库、PR、提交列表、diff、Reviews、Threads、Comments、可用 CI 结果 | Repository、PullRequest、Commit、CodeChange、Review、Thread、Comment、Actor | Finding、修复对应关系、Case、工作项实现关系 |
| Confluence | 页面正文、page ID、版本、章节结构、关联链接、访问范围 | Document、源快照、作者账号 | Requirement、AcceptanceCriterion、DesignDecision，以及与工单/组件的关联 |
| Jira | Issue ID/key、类型、状态、父子/链接、描述、验收字段、负责人、可用 changelog | WorkItem、Actor、明确层级关系 | TRACKS、需求/组件关联、事故处理关系 |
| 人工／受保护配置 | 项目映射、组件边界、repo/path/owner、规则审批 | Project、Component、Team、可信映射 | 消解歧义并批准语义关系 |

Confluence v2 提供页面正文与页面版本相关接口；Jira v3 提供工单和 changelog。**存在版本元数据不代表能恢复所有过去的正文或权限状态**，导入时要标记历史可用范围，之后保存每次观察到的快照。[S04][S05][S06]

## 3.2 抽取原则

明确字段、原生父子关系、稳定 ID、URL 与 commit SHA 先用代码解析。自然语言中的需求、决策、问题和修复理由再交给 LLM，输出必须通过 schema 校验且附原文定位。

Jira 自定义验收字段、组件字段、issue link 方向必须做项目级配置。没有“所有项目统一叫 acceptance_criteria”的假设。Confluence 的同名章节或工单标题也不用于自动合并实体。

PR 一般讨论区的 issue comments 可作为证据；不能伪装成原生 review thread。连接器确有需要时创建标记为 `synthetic=true` 的讨论容器，保留 `source_kind=issue_comment` 和真实源对象 ID；不得合成“已 resolved”状态。

## 3.3 来源与派生内容的权限

连接器账号能读取内容，不代表所有台账用户都能读取。每次构建上下文都必须根据调用身份检查当前 source permissions。派生 Case/Rule 默认继承**所有支持来源的可读权限交集**；去掉敏感来源并重写成通用规则，需要单独脱敏与审批。

源权限未知或授权状态超过允许的缓存窗口时，拒绝返回相关内容；后台重新核验。首版可用单一试点团队和显式允许名单简化，但必须保证共享访问范围，不以“内部系统”为由省略控制。

# 04 整个数据流程

## 4.1 总体分层

```text
GitHub / Confluence / Jira
          │ API 全量回填 + Webhook/轮询 + 定期对账
          ▼
事件收件箱 → 原始快照 → 确定性标准化与身份映射
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
           Entity / 结构 Edge      LLM 候选抽取 + 原文证据
                 │                         │
                 │               类型/证据/冲突校验 → 审核队列
                 └────────────┬────────────┘
                              ▼
               版本化事实图 + Case / Pattern / Rule
                              │
               按权限、版本、repo/path/component 选取
                              ▼
                      Context / Trace API
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
              研发台账      SKILL / IDE    PR Review Worker
                                              │
                                 草稿 → 证据核验 → 独立发布器
                                              │
                                人工反馈 → 知识修订候选 / 评测
```

同步和后台抽取由任务系统驱动，不依赖用户打开一个 SKILL。SKILL 是消费或受控整理知识的入口，不承担整个数据管道。

## 4.2 流程 A：历史数据首次导入

| 步骤 | 处理 | 输出与检查 |
|---|---|---|
| A1 范围登记 | 指定 repo、Jira project、Confluence space/page、团队和字段映射 | Integration 配置；能读哪些对象、历史覆盖区间清楚 |
| A2 启动事件捕获 | 记录起始 watermark；先接收事件再做回填 | 回填期间的新变化不会依赖一次枚举碰巧读到 |
| A3 分页抓取 | 读取 PR 全链路、相关工单和文档；限速与断点续传 | 原始快照、源版本、访问状态、抓取失败清单 |
| A4 确定性建图 | 建立实体和源结构边；解析显式链接和代码位置 | observed 关系；无法解析的映射进入待确认队列 |
| A5 候选抽取 | 按页面章节或完整线程抽取，不按任意 token 长度切片 | Requirement/Decision/Finding/Case 候选及证据 |
| A6 治理确认 | 优先复核高价值案例、规则和冲突 | reviewed Case、active Rule；未确认内容仍为候选 |
| A7 追赶与验收 | 重放回填以来事件；再做一次对账 | 来源更新时间、对象数、SHA、权限与覆盖报告 |

回填历史 PR 不等于获得真实历史世界。缺少某时点的源正文、规则批准记录或代码快照时，不能把该样本列入严格时间回放的金标准集。

## 4.3 流程 B：增量更新与一致性

```text
收到事件 → 验证来源 → inbox 持久化 → 快速应答
         → worker 重新读取源对象当前版本
         → 比较 source version / content hash
         → 原始快照与标准化版本同事务落库
         → outbox 生成受影响的抽取、失效与审查任务
         → 成功后推进同步游标；失败重试 / 死信队列
```

GitHub 官方建议 Webhook 异步处理，并提供 `X-GitHub-Delivery` 标识投递；手动重投沿用相同标识。因此，收件箱去重键与处理状态必须分开，不能把“曾收到但未成功处理”当作完成。[S01]

**一致性要求：** 同一事件重投不重复生成实体；旧事件不把新版本覆盖回去；不同源不共享单一版本序号；不能按 SHA 字符串大小判断 Git 新旧。推送事件只作为刷新提示，重新获取 PR 当前 head，再用条件更新防止并发覆盖。

Jira 的事件注册、重试和可订阅类型取决于接入方式。Confluence 无可用事件订阅时，使用有重叠窗口的分页轮询和定期对账；不把任何一个源的 Webhook 当作“无丢失事实日志”。[S07]

## 4.4 流程 C：Review 知识沉淀

1. **收齐上下文：** 一条线程的全部评论、审查版本、相关 diff、后续提交和可用验证结果。
2. **拆分 Finding：** 每项问题分别记录触发条件、后果、位置；支持/反驳评论连接到同一问题。跨线程去重先生成候选，不删原评论。
3. **关联处理：** 后续修改先生成 `ADDRESSES_FINDING(proposed)`。经确认才生成 `FIXES(confirmed)`；证据不足保持 unresolved。
4. **形成 Case：** 保存背景、结果、依据和适用限制。结果可为修复、误报、合理例外或未解决。
5. **归纳知识：** 提出 Pattern、Solution 和 Rule 候选。重复案例按 canonical ID 或确认后的模式合并，不自动把每个 PR 变成新规则。
6. **批准发布：** 负责人确认 Rule 的 scope、例外和证据，形成已批准版本。只给查询层和 SKILL 暴露 active 且适用的版本。

上述 1–5 可自动运行，但“自动生成”不等于“自动批准”。一条充分有据的架构约束可成为规则候选，无需硬性等待出现 N 个案例；反之，多次合并的错误习惯也不能靠出现次数获得正确性。

## 4.5 流程 D：新 PR 自动 Review

| 阶段 | 动作 | 确定性产物 |
|---|---|---|
| D1 固定快照 | 取 repo、base/head SHA、diff、规则集 revision、graph watermark | ReviewSnapshot 与运行 ID |
| D2 定位范围 | 将变更映射到组件、文件、可解析符号和依赖版本 | 变更清单与未知映射，不靠 LLM 猜全部范围 |
| D3 构建上下文 | 按 scope 找规则，沿 DERIVED_FROM 取案例，补关联要求/决策 | 带来源、权限和新鲜度的 ContextBundle |
| D4 两类检查 | 规则驱动检查 + 同仓库、限预算的通用代码检查 | 结构化 Finding 候选；新缺陷可没有历史案例 |
| D5 核验 | 校验行号、SHA、源证据、适用性、例外、重复和可操作性 | 核验结果与每条规则的覆盖状态 |
| D6 发布 gate | 核对最新 head、最新强制策略、授权与披露范围 | 草稿／允许发布／已过期，不允许“部分完成=通过” |
| D7 反馈 | 收集明确反馈与后续修改 | Finding 状态与 Case 候选，不将沉默等同采纳 |

首轮运行在 shadow mode：真实输入，内部显示，不写 GitHub。正式开放评论后仍不自动 merge、approve 或阻止合并。

# 05 更新、失效与维护成本

## 5.1 四种不同的变化

| 变化 | 触发处理 | 不应采取的做法 |
|---|---|---|
| 源文本被编辑 | 新 source revision；重抽相关章节/线程；沿证据依赖标记待复核 | 全组织重新抽取 |
| 代码、接口、依赖变化 | 查 path/symbol/dependency 关联；匹配规则标记待复核 | 仅凭“最近同步成功”继续当有效 |
| 语义冲突／决策被推翻 | 新旧版本并存；负责人确认 supersedes 或例外 | 无声覆盖旧规则与过去结论 |
| 删除／撤权 | 立即停止提供相关派生上下文；清缓存；按保留策略删除/脱敏 | 为了审计永久保留所有原文且仍可访问 |

历史不可变是逻辑设计，不是无限保留承诺。删除请求或保密策略要求清除时，应清除受影响正文、派生资料、缓存和导出物，审计仅保留允许的最小标记；备份清理遵从已批准的保留周期。

## 5.2 状态机与上下文有效性

```text
Rule: draft → [授权批准] → active
                         → needs_revalidation → active / superseded / retired
Case: candidate → reviewed → retired
Finding.disposition: proposed / confirmed / rejected / accepted_exception / unresolved
Finding.resolution:  not_fixed / fix_proposed / verified_fixed / not_applicable / unknown
```

规则不是全局只有“过时/不过时”。同一规则可能仍适用于维护分支，但不适用于新 SDK 版本。按 repo、分支/发布线、依赖版本与目标代码快照计算有效性；不能仅以 `valid_from/valid_to` 替代代码适用条件。

`last_synced_at` 只表示同步；`last_verified_revision` 表示核验依据；`scope_evaluation` 表示本次快照是否适用。三者分别展示。

## 5.3 降低维护量的具体机制

基于 source content hash 只处理变化单元；依赖表追踪哪些 Case/Rule 使用了哪些原始版本；同一线程连续更新采用短暂合并窗口；相同 snapshot + rule pack + model/prompt 配置重用已完成结果。人工只处理规则批准、冲突、失效和抽样质检，不逐条批准全部抓取数据。

审核队列过多时，降低非关键候选的抽取优先级、合并重复建议，并暂停未审核规则进入正式上下文；不能让积压自动转成 active。定期统计“每周知识审核分钟数”和“规则误报造成的返工”，与模型费用一起衡量。

# 06 不依赖向量 RAG 的查询与上下文

## 6.1 主流程

```text
调用身份与租户 → 明确 repo/工作项/PR
              → 解析稳定 ID 与别名
              → 当前权限过滤 + 有效版本过滤
              → component/path/symbol/依赖条件匹配
              → 有界图遍历取 Case、Rule、Requirement、Decision
              → 按需读取当前代码或关键词查找
              → 返回证据包 + 未覆盖范围
```

这里仍然存在信息选取，也仍会有漏掉上下文的可能；区别是优先使用**可解释、可测试的对象关系和范围**，而非把正确性押在语义相似度召回。函数重命名、跨模块隐式业务约束和未被抽取的历史知识仍是风险，需要单独测覆盖，不宣称无向量等于零漏检。

## 6.2 预定义查询，不让 Agent 任意执行 SQL

| 查询 | 起点与具体路径 | 返回结果 |
|---|---|---|
| 工作项追溯 | WorkItem → TRACKS → Requirement；反向 IMPLEMENTS → PR；再连接提交/测试 | 状态、实现、验证、部署分别列示，标出缺口 |
| 组件历史经验 | Component → CONTAINS_ELEMENT → CodeElement ← MODIFIES ← Change ← LOCATED_IN_CHANGE ← Finding ← DOCUMENTS_FINDING ← Case | 已复核案例、修复、误报与例外 |
| 新 PR 适用规则 | 从 PR 快照得到组件；Component/Repository ← APPLIES_TO ← Rule | active 且 scope 匹配的完整规则集合 |
| 规则依据 | Rule → DERIVED_FROM → Case/Requirement/Decision | 来源文本、版本、确认者、例外 |
| 变更影响 | SourceRevision ← EvidenceDependency ← 派生 revision | 待复核清单；这是配套依赖索引，不新增领域 Entity |

适用规则的枚举不做 top-K 静默截断；超出预算应分组运行，或把未检查规则列为 `not_evaluated`。附加案例可以限量，并披露裁剪方式和候选数（仅限当前身份可见范围）。

## 6.3 ContextBundle 契约

```json
{
  "schema_version": "0.2",
  "snapshot_id": "snapshot:demo-236-01",
  "repository_id": "repo:demo-backend",
  "head_sha": "3333333333333333333333333333333333333333",
  "graph_watermark": "graph:demo-57",
  "rule_revision_ids": ["rule:CACHE-001@r1"],
  "case_revision_ids": ["case:CASE-01@r2"],
  "evidence_refs": ["evidence:comment-01@r1"],
  "completeness": "partial",
  "gaps": ["未接入单项测试结果"],
  "history_cutoff": null,
  "policy_epoch": "policy:demo-4",
  "truncated": false
}
```

ContextBundle 不能自己授予权限。`tenant_id`、身份、权限、实际模型预算由服务器根据会话和配置确定，不信任 Agent 在请求体里自报“我是管理员”。历史回放仍须使用**现在的访问权限**，不得回放旧 ACL 来恢复已经被撤销的访问。

# 07 服务接口与模块边界

## 7.1 建议模块

| 模块 | 负责 | 不负责 |
|---|---|---|
| Connectors / Sync | 采集、分页、游标、快照、权限同步、对账 | 直接宣布需求已实现 |
| Ontology Service | Entity/Edge revision、合法类型、映射、版本查询 | 把任意 JSON 当有效边 |
| Knowledge Pipeline | Finding/Case/Pattern/Rule 候选、证据与去重 | 发布正式规则 |
| Context Service | 受控查询、scope 匹配、证据包、覆盖清单 | 无约束全库检索或自动越权 |
| Review Worker | 只读审查、候选 Finding、检查覆盖 | PR 写入、merge、审批规则 |
| Governance / Publisher | 授权审批、发布 gate、写评论、幂等 | 在携带写令牌的环境执行 PR 代码 |
| Console / Skills Adapter | 人工台账、审核和 Agent 入口 | 另建一套知识事实主库 |

## 7.2 拟议 API 与 Tool 映射

以下为**拟议内部接口**，不是 GitHub/Atlassian 现有接口，也尚未实现。MCP 只做薄适配，鉴权和输入校验在 API 服务侧完成。

| 内部 Tool | API 草案 | 关键输入 | 输出／权限 |
|---|---|---|---|
| `resolve_entity` | POST /v1/entities/resolve | source instance、type、source ID/key | 唯一 ID 或歧义列表；只读 |
| `trace_work_item` | POST /v1/traces/work-item | work_item_id、view/as_of | 证据链、断点、完整性；只读 |
| `get_entity_evidence` | POST /v1/evidence/read | entity revision 或 evidence IDs | 可见原文定位；只读 |
| `get_component_cases` | POST /v1/cases/by-component | component_id、outcome、cursor | Case、Pattern、例外；只读 |
| `create_review_snapshot` | POST /v1/review-snapshots | repo_id、pr_number、expected_head_sha | 固定快照；创建内部运行记录，不写源系统 |
| `get_review_context` | POST /v1/contexts/review | snapshot_id | ContextBundle；只读 |
| `read_code_at_revision` | POST /v1/code/read | snapshot_id、path、line range | 精确版本代码；只读 |
| `run_review` | POST /v1/reviews | snapshot_id、mode=shadow/draft | review_id；队列任务，不直接写评论 |
| `get_review_result` | GET /v1/reviews/{id} | review_id | 状态、Finding、覆盖、费用 |
| `propose_knowledge` | POST /v1/knowledge/proposals | 输入证据、候选类型、payload | proposal_id；只能生成 candidate |
| `get_knowledge_impact` | POST /v1/knowledge/impact | 源 revision 变化或 component ID | 受影响知识及原因；只读 |
| `submit_review_feedback` | POST /v1/reviews/{id}/feedback | finding_id、disposition、reason | 追加反馈；无权直接修改正式规则 |
| `approve_rule_revision` | POST /v1/governance/rules/{id}/approve | expected_revision、approval_reason | 仅授权治理用户；普通 SKILL 不暴露 |
| `publish_review` | POST /v1/reviews/{id}/publish | expected_head_sha、approved_draft_hash | 仅独立发布器；需要批准/预授权策略 |

统一错误：`not_found_or_not_authorized`、`ambiguous_identity`、`incomplete_source`、`stale_snapshot`、`policy_changed`、`budget_exceeded`、`unsupported_source_version`。权限拒绝不返回隐私对象的名称、数量或原始错误信息。

## 7.3 运行与发布保证

变更请求使用 `Idempotency-Key`；对象修改带 expected revision 做乐观并发控制。Review 运行幂等键包含 tenant、repo、PR、base/head、规则集、知识快照、harness/model 配置和模式。同 head 但要求/规则变了，可以重新审查，不能盲目命中旧缓存。

发布前用 Finding 指纹和平台 comment ID 映射去重；超时导致“是否已写入未知”时先查询已发布标记，再决定重试。外部评论接口不与本地事务组成原子提交，因此不承诺严格 exactly-once。

读取 head 与发表评论之间仍可能发生新提交。发布时携带明确 commit/位置并记录快照；发现竞态后标为 superseded/待更新。不能宣称一个简单 HEAD 检查就消除了所有竞态。

# 08 后续 SKILL：从台账到 Agent 能力

## 8.1 SKILL 的定位

**Ontology 定义对象，API 提供受控能力，SKILL 定义何时按什么步骤调用这些能力。**持续采集、权限控制、规则版本和发布审批不能只写在 SKILL 提示词中。

Agent Skills 的标准结构以 `SKILL.md` 为入口，包含 YAML frontmatter 与任务指令，并可带 references/scripts/assets；标准强调按需加载。具体运行时的工具映射需要适配，`allowed-tools` 不能被当成唯一安全边界。[S08][S09]

不为每条 ReviewRule 生成一个 Skill。Rule 是经批准的数据；Skill 是跨规则复用的工作流。这样不会产生几千个难维护、每次都要加载的技能文件。

## 8.2 五个计划中的 Skill

| Skill | 触发问题／输入 | 主要 Tool | 输出与写权限 |
|---|---|---|---|
| `dev-ledger-trace` | “APP-208 到底做到哪？”；工单 ID/key | resolve_entity → trace_work_item → get_entity_evidence | 需求、PR、测试与部署证据；只读，不改 Jira 状态 |
| `pr-review-memory` | “改这个模块前要注意什么？”；组件或 PR | get_component_cases / get_review_context → get_entity_evidence | 历史问题、修复、误报、例外和适用规则；只读 |
| `pr-review` | “审查这个 PR”；repo + PR + head | create_review_snapshot → get_review_context → run_review → get_review_result | 版本固定的审查草稿和覆盖报告；不直接发布 |
| `review-knowledge-curation` | “把这轮 Review 整理成知识”；PR/线程/证据 | get_entity_evidence → propose_knowledge | Case/Pattern/Rule 候选；不能批准、激活或覆盖规则 |
| `knowledge-impact-check` | “需求改了，哪些规则受影响？”；新旧 revision | get_knowledge_impact → get_entity_evidence | 影响清单和复核建议；默认只读 |

`pr-review` 通过平台 `run_review` 执行统一审查工作流，避免 IDE 端和服务端各维护一套不同审查逻辑。离线 IDE 无法连到服务时应说明不可用，不偷偷回退到过期知识包并宣称平台审查已完成。

## 8.3 Skill 的标准契约

每个 Skill 必须写明触发范围、必需输入、唯一 ID 解析、工具顺序、返回结构、证据引用、失败处理与禁止操作。工具名缺失时停止相应能力，不用猜出的 HTTP 命令绕过；认证失败不切换租户或账号重试。

推荐目录：

```text
skills/
  dev-ledger-trace/
    SKILL.md
    references/tool-contracts.md
    references/output-example.md
  pr-review-memory/
  pr-review/
  review-knowledge-curation/
  knowledge-impact-check/
```

本交付包附有五份完整的 SKILL.md 草稿及接口参考。它们是**待后端实现和运行时绑定的模板**，不是安装后即可调用真实平台的成品插件；不含凭据，也不替你注册任何远程服务。

## 8.4 `pr-review` 的实际流程示例

```text
输入：repo=example/backend，PR=184
→ 解析仓库与 PR；明确当前 head
→ 创建 ReviewSnapshot，冻结知识和规则版本
→ 获取 ContextBundle；展示 gaps 与部分覆盖
→ run_review(mode=draft)，记录 review_id
→ 在当前工具运行允许范围内查询任务结果
→ 未完成则只报告任务状态，不声称已审查
→ 输出 Finding、规则覆盖、依据与验证方法
→ 用户要求发布时交给独立批准流程；Skill 本身没有 publish 权限
```

SKILL 的输出至少包含：被审查版本、已覆盖范围、问题及证据、无法确认的项、下一步验证建议。历史案例是上下文，不是强制“模仿旧代码”的指令。

## 8.5 测试与版本管理

Skill、tool schema、ontology schema、规则集、模型配置分别有版本，并在每次 Review 记录组合。发布前用固定回放集验证：正确工具调用、无跨租户读取、候选不冒充已确认、版本变化能阻止旧草稿发布、拒绝 PR 文本注入的越权指令。

自动安装第三方 Skill、执行来自 PR 的脚本或在线改写本平台安全策略不在首版范围。可借鉴 qodo-skills 的任务组织，但不能假定复制 Skill 就获得其托管知识/审查后端；也不需把整个项目 fork 为平台内核。

# 09 工程实现建议

## 9.1 最小技术组合

| 部分 | 建议 | 本次取舍 |
|---|---|---|
| 服务端 | Python + FastAPI + Pydantic | 便于连接器、schema 校验和模型调用；版本在开工时锁定 |
| 主库 | PostgreSQL：关系表 + JSONB | 同库保存对象、关系、版本、任务和审计；不安装 pgvector |
| 代码读取 | Git 固定快照 + ripgrep；Tree-sitter 按目标语言可选 | 从文件/路径开始；不能把语法树当完整调用图 |
| 异步任务 | 公司已有队列；没有则 DB-backed job + outbox | 先实现幂等、租约、重试和死信，不先部署复杂调度集群 |
| 模型 | 已批准企业模型 API + 薄适配层 | 候选抽取与 Review 可分模型；不以模型自评置信度批准事实 |
| Review 内核 | 单一接口封装内部实现或可自托管开源引擎 | 先用自有样本测效果、能力和许可，再选固定版本；不是本体主库 |
| 前端 | 现有内部前端框架；无约束时 React/Next.js | 台账、知识卡、候选审批、审查运行四个页面 |
| Agent 接入 | 内部 REST/CLI 优先，MCP 作为可选 adapter | MCP 不是必须先建设的事实层 |

这里是本项目的架构建议，不是对某版本产品能力的性能承诺。Graphiti、Mem0、Letta 或 Harness² 不作为 P0 的事实主库依赖；后续评估需要证明能减少维护或改善可测质量，而非仅增加组件数。

## 9.2 物理记录：支撑模型，不新增领域实体

| 表／记录 | 最少字段 | 关键约束 |
|---|---|---|
| source_records | tenant、source instance、object ID、source version/hash、raw pointer、observed_at、acl_ref | 原始输入不能被 LLM 改写；保留版本与删除策略 |
| entity / entity_revision | tenant、ID、type、revision、properties、source refs、system time | 稳定 ID 与不可变 revision 分离 |
| edge / edge_revision | 起终点 ID/revision、type、status、evidence、context、system/valid time | 同租户、允许类型、基数、特殊语义校验 |
| identity_maps | source key → canonical ID、确认来源、有效区间 | 不以文本同名自动合并 |
| evidence_locators | source revision、章节/行范围/commit、原文引用哈希 | 可重定位、可校验；路径必须在许可源范围 |
| evidence_dependencies | derived revision → source/entity revision | 精确传播更新、撤权与删除影响 |
| extraction_runs | inputs、schema/prompt/model 版本、输出 proposal、成本 | 可审计/重跑；重跑不覆盖人工确认 |
| review_snapshots / review_runs | SHA、规则版本、knowledge watermark、coverage、status、成本 | 同步快照可追溯，不声称模型输出逐字可复现 |
| knowledge_proposals / approvals | 候选内容、expected revision、决定、actor、理由 | 乐观锁；审批身份由服务器验证 |
| jobs / inbox / outbox | dedupe key、state、lease、attempt、next_retry、payload refs | 数据与 outbox 同事务；失败可恢复 |
| publication_records / feedback / audit | finding 指纹、外部 comment ID、操作人、状态、反馈证据 | 写操作与评论追踪，支持外部结果未知时的对账 |

PROV-O 可作为“谁根据何种来源，经哪次活动产出派生内容”的追溯参考；没有必要为采用这一思路而引入 RDF/OWL 技术栈。[S12]

## 9.3 查询与可用性

为 tenant+type、外部源 ID、repo、component、rule status、path 映射、edge 起点/终点/类型、system time 和依赖源建立索引。限定图遍历深度、节点数和查询超时；循环依赖要防护。PostgreSQL 先承担这套有界查询，是否迁移图数据库由真实查询规模和运维收益决定。

基础观测区分同步延迟、抽取延迟、规则待复核量、Review 延迟/失败/部分完成、错误类型、每次运行成本。任务成功不等于源数据完整，界面必须显示来源覆盖和最近成功对账时间。

## 9.4 安全与发布边界

Ingestor 只读源；Review Worker 只读代码和受权知识；Publisher 只持有必要评论/Check 权限，不运行 PR 代码。需要执行测试时进入临时隔离环境，不带生产凭据或写令牌，并限制网络和资源。GitHub 官方安全文档对不可信代码与特权工作流的组合有明确风险提示。[S10]

所有 PR 文本、代码注释、文档和历史评论均为不可信数据。feature branch 中的规则/AGENTS.md/Skill 不得覆盖受保护平台策略。发布规则必须来自可信批准记录，而非正文中的“已批准”字样。

MCP 接入时验证 token audience，避免透传上游凭据；MCP 传输授权之外仍执行租户、对象、来源与目标披露范围检查。[S11]

# 10 一条台账的端到端示例

**以下全部为虚构数据，仅用于设计与测试。**

| 步骤 | 输入／事件 | 写入或变更的对象与边 |
|---|---|---|
| 1 | Confluence《租户隔离设计》v7 | Document；提出 Requirement REQ-12 和 Decision DD-03；候选 DESCRIBES/RECORDS_DECISION |
| 2 | Jira APP-208：增加用户缓存 | WorkItem；TRACKS → REQ-12 待确认 |
| 3 | PR #184 提及 APP-208 | PR、Commit、CodeChange；REFERENCES_WORK_ITEM 已观察，IMPLEMENTS 未自动确认 |
| 4 | Reviewer 指出缓存键缺少 tenant_id | ReviewComment；Finding F-01；RAISES 和 LOCATED_IN_CHANGE 带证据候选 |
| 5 | 后续提交补 tenant_id | 新 CodeChange；ADDRESSES_FINDING 候选；不因线程关闭直接 FIXES |
| 6 | Reviewer 明确认可并有相关测试 | FIXES 确认；Case CASE-01 outcome=confirmed_fixed；连接单项 TestResult |
| 7 | 提炼检查规则 | DefectPattern / SolutionPattern / Rule CACHE-001 draft；负责人批准 r1 后 active |
| 8 | PR #236 再修改同模块缓存键 | 组件映射命中 CACHE-001；读取 CASE-01；在 #236 当前 SHA 上核验是否违规 |
| 9 | 文档 v8 允许独立隔离的全局缓存 | 只标记相关 Rule 待复核；复核后发布 r2 与适用例外，保留 r1 及过去运行 |

此时台账不应只有一列“完成”。应分别显示：Jira 工作状态、需求 revision、实现关系确认状态、Review 结果、对应测试、部署是否有证据、相关规则是否仍有效。

# 11 实施顺序与验收

## 11.1 四个开发迭代

| 迭代 | 交付 | 出口条件 |
|---|---|---|
| I1 事实台账 | schema/校验、三源只读连接器、快照/映射、基础追溯页 | 能从工单追到 PR、文档和源证据；重复导入不增脏数据 |
| I2 Review 知识 | Finding 抽取、修复候选、Case/Rule 审核、失效传播 | 一条案例可逐证据复盘；误报与例外不被写成硬规则 |
| I3 审查闭环 | ContextBundle、只读 Worker、Verifier、shadow mode | 同一测试集对比有/无工程知识，能拆分效果、成本与覆盖 |
| I4 Agent 入口 | 五个 Skill、API/MCP 适配、发布 gate、反馈 | 工具调用可验证，越权被阻断，正式写入独立授权 |

迭代为实施顺序，不是固定工期承诺。首轮建议选择 1–2 个仓库、与其相关的文档和 Jira 项目；历史规模按访问权限与可用数据决定，先抽少量真实完整案例验证再扩大。

## 11.2 验收必须包含的失败场景

| 编号 | 测试 | 通过条件 |
|---|---|---|
| T01 | 同一事件重投与并发处理 | 不重复实体/Case/评论；失败任务可续跑 |
| T02 | 新旧事件乱序 | 当前版本不回退；PR force-push 保留历史且更新快照 |
| T03 | Confluence 需求变更 | 只标记依赖知识待复核；旧版仍能历史解释 |
| T04 | 一条评论包含多个问题 | 可生成独立 Finding，证据和修复关系不串线 |
| T05 | 线程 resolved，但没有修复 | 不产生 confirmed FIXES / verified_fixed |
| T06 | CI 全绿但不覆盖该问题 | 不自动确认缺陷修复或所有验收通过 |
| T07 | Reviewer 驳回 AI 指摘 | 保留 false_positive Case，不生成禁止规则 |
| T08 | 规则命中但存在批准例外 | 输出适用性判断，不机械发布违规评论 |
| T09 | 数据源撤权/ACL 未知 | 当前身份不能读其内容、派生事实或可识别摘要 |
| T10 | PR 文本要求忽略安全规则 | 不改变 tool 权限、不执行越权命令 |
| T11 | 生成过程中 head 改变 | 旧结果标记 stale，禁止作为最新审查发布 |
| T12 | 规则太多超出预算 | 显示未检查范围，不静默裁剪后说“全通过” |
| T13 | 数据不足或连接器失败 | 显示 partial/unknown，不把缺失数据当不存在 |
| T14 | 历史回放加入了未来修复 | 自动检测时间泄漏；不合格样本不用于收益结论 |
| T15 | 发布接口超时结果未知 | 先查发布映射/标记，防止盲目重发评论 |

## 11.3 效果与维护指标

同模型、同 PR 快照分别跑：A 当前代码基线；B 加已批准规则；C 再加历史 Case。按审查发生时间冻结可获得的知识与源快照，禁止使用同 PR 后来的修复和后来的确认结论。没有完整历史快照则转为前瞻 shadow 评测，不伪装严格回放。

测量人工确认的 Finding 准确率、在标注问题集上的发现率、旧知识误用、规则覆盖/未知项、证据定位正确性、重复评论、每次 Review 成本、每周知识维护工时。代码随后变化只是反馈信号，不能单独认定 AI 建议被采纳。

**首版是否继续投入的判断：** 工程知识是否比代码基线带来可重复的质量增益，并且新增人工维护没有抵消节省的审查时间。目标阈值由试点基线和团队容忍度设定，不虚构尚未实测的提升百分比。

## 11.4 待确认项与当前默认

| 待确认 | 当前用于拆解开发的默认 |
|---|---|
| GitHub/Atlassian 具体部署版本 | Connector Adapter 隔离；先以 Cloud 文档设计，不认定实际环境 |
| 组件边界和 Owner | 人工登记 repo/path/owner 清单，不让 LLM 自行确立归属 |
| 需求/验收字段与文档结构 | 项目级映射配置，缺失项进候选队列 |
| 规则批准人 | 指定组件负责人或授权维护者；未指定前不激活规则 |
| 模型与数据保留政策 | 复用企业已批准方案；未获批准的数据不发给外部模型 |
| 评论发布策略 | 初始 shadow；独立批准后才启用非阻塞评论 |
| 测试与部署数据是否可得 | 只接真实可用证据；否则展示未接入，不阻碍台账先行 |

# 附录 A · 全部实体定义

以下表格为完整逻辑模型，不代表每类数据首轮都已接入。属性中的 `?` 表示可缺省；枚举与完整类型以随附 `ontology.v0.2.yaml` 为准。

## A.1 需求与设计

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `Project` | **研发项目**：业务上的研发项目，不等同于某一个 Jira Project 或 GitHub Project。 | `name`；`source_project_refs` |
| `WorkItem` | **工作项**：跟踪待完成工作的单元；Epic、Story、Task、Bug 为 kind，不分别建立实体类型。 | `title`；`kind`；`source_key`；`workflow_status`；`assignee_id` |
| `Requirement` | **需求要求**：独立、可版本化的一项功能或非功能要求；不是整篇文档或工单。 | `statement`；`version`；`kind`；`status` |
| `AcceptanceCriterion` | **验收条件**：可以判断满足与否的单项条件。 | `condition`；`version`；`verification_method` |
| `Document` | **文档**：Confluence 页面等资料载体；其章节内容可支持多项需求或决策。 | `source_id`；`title`；`version`；`url`；`content_hash` |
| `DesignDecision` | **设计决策**：一项明确选择及其理由、备选方案、约束和例外。 | `decision`；`rationale`；`alternatives`；`status`；`version` |

## A.2 代码与实现

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `Repository` | **代码仓库**：代码托管仓库。 | `provider`；`provider_repo_id`；`name`；`url` |
| `Component` | **软件组件**：具有职责边界的软件服务、模块或库；不等同于仓库。 | `name`；`kind`；`description` |
| `CodeElement` | **代码元素**：文件、函数、类或接口等可定位对象；代码位置必须与版本绑定。 | `kind`；`qualified_name`；`repository_id`；`locator`；`identity_status` |
| `PullRequest` | **拉取请求**：一次提出合并代码变更的协作对象。 | `number`；`title`；`state`；`base_sha`；`head_sha`；`merge_sha`；`source_id` |
| `Commit` | **代码提交**：某仓库中的确定代码提交。 | `repository_id`；`sha`；`parent_shas`；`committed_at` |
| `CodeChange` | **具体变更**：两个明确版本之间的一组局部修改；用于指出问题位置与修复内容。 | `repository_id`；`base_sha`；`head_sha`；`path_before`；`path_after`；`operation`；`diff_hunks`；`content_hash` |

## A.3 审查活动

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `Review` | **审查记录**：一次人工审查提交或一次 AI 审查运行；与讨论线程不是同一对象。 | `source_kind`；`reviewed_base_sha`；`reviewed_head_sha`；`verdict`；`execution_status`；`harness_version` |
| `ReviewThread` | **审查讨论线程**：围绕问题展开的讨论；同一线程可以跨多个审查提交和参与者。 | `source_id`；`is_resolved`；`source_locator` |
| `ReviewComment` | **审查评论**：评论原文与回复。一个评论可包含多个问题，一个问题也可由多个评论共同表达。 | `source_id`；`body`；`created_at`；`updated_at`；`source_locator` |
| `ReviewFinding` | **具体审查问题**：针对某 PR 某版本代码的原子问题或问题主张，不是通用规则。 | `summary`；`category`；`severity`；`trigger_condition`；`consequence`；`disposition`；`resolution` |

## A.4 经验与规则

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `ReviewCase` | **审查案例**：将一个问题、上下文、处理结果、修复和验证证据组织为可复盘的历史案例；驳回案例同样可保留。 | `summary`；`context`；`outcome`；`reuse_status`；`owner_id`；`known_limitations` |
| `DefectPattern` | **问题模式**：跨具体案例抽象出的失败机制，例如缓存键遗漏租户维度；不只限于代码错误，也包含设计或约束违规。 | `name`；`mechanism`；`preconditions`；`consequences`；`status` |
| `SolutionPattern` | **解决方案模式**：可复用的修复或规避方法，包括适用条件、代价与例外。 | `name`；`strategy`；`preconditions`；`tradeoffs`；`exceptions`；`status` |
| `ReviewRule` | **审查规则**：可供审查流程使用的检查要求；只有被批准且适用的版本可成为正式约束。 | `name`；`version`；`check`；`scope`；`trigger_conditions`；`exceptions`；`status`；`evidence_refs` |

## A.5 测试与验证

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `TestCase` | **测试用例**：一项测试或人工验收的定义，不等同于执行结果。 | `name`；`version`；`kind`；`procedure_ref` |
| `TestRun` | **测试运行**：在确定代码版本和运行配置上的测试执行。 | `run_id`；`started_at`；`finished_at`；`configuration_ref`；`runner_kind` |
| `TestResult` | **单项测试结果**：某一次运行中某一测试用例的实际结果。 | `status`；`test_case_version`；`evidence_ref`；`observed_at` |

## A.6 交付与运行反馈

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `BuildArtifact` | **构建制品**：可识别、可部署的构建输出；用不可变 digest 标识，不只记录可变 tag。 | `name`；`digest`；`version`；`uri` |
| `Release` | **发布版本**：计划或实际发布的一组制品；创建 Release 本身不代表已部署。 | `name`；`version`；`status`；`released_at` |
| `Deployment` | **部署执行**：某制品进入某环境的一次部署尝试及结果；只有部署证据存在时建立。 | `external_id`；`status`；`started_at`；`completed_at` |
| `Environment` | **运行环境**：开发、测试、预发布或生产环境。 | `name`；`kind` |
| `Incident` | **运行故障**：运行中实际发生的一次故障，与追踪其修复的 Bug 工单区分。 | `summary`；`started_at`；`resolved_at`；`severity`；`status` |

## A.7 人员与责任

| Entity | 中文／定义 | 主要属性 |
|---|---|---|
| `Actor` | **参与主体**：人员、机器人或服务身份。不同系统账号只有在可信身份映射后才合并。 | `display_name`；`kind`；`external_ids` |
| `Team` | **团队**：负责研发对象或规则治理的组织单元。 | `name`；`external_ids` |


# 附录 B · 全部关系定义

out 表示每个起点可连接的终点数量，in 表示每个终点可接收的起点数量。默认状态只是转换建议：若缺乏可信结构来源，即便默认 observed，也不得凭模型推断生成 observed。正式语义关系仍需确认与新鲜度检查。

| 编号 | 起点 | Edge | 终点 | out / in | 默认 | 语义／特别约束 |
|---|---|---|---|---|---|---|
| E01 | Project | `HAS_WORK_ITEM` | WorkItem | 0..* / 0..* | observed | 项目包含工作项。 业务 Project 到 Jira 项目的映射须事先登记；之后可按登记自动观察。 |
| E02 | Project | `HAS_REQUIREMENT` | Requirement | 0..* / 0..* | proposed | 项目包含需求要求。 |
| E03 | WorkItem | `PARENT_OF` | WorkItem | 0..* / 0..1 | observed | 工作项的父子关系。 不得形成环；单一 Jira 层级中一个子项最多一个父项。其他关联不能冒充父子。 |
| E04 | WorkItem | `DEPENDS_ON` | WorkItem | 0..* / 0..* | observed | 工作项之间的依赖关系。 保留原系统 link type 和方向；不能将所有 issue links 都映射为依赖。 |
| E05 | WorkItem | `TRACKS` | Requirement | 0..* / 0..* | proposed | 工作项跟踪该要求的交付；不代表已经完成。 |
| E06 | Requirement | `HAS_CRITERION` | AcceptanceCriterion | 0..* / 0..* | proposed | 要求具有某一验收条件。 |
| E07 | Document | `DESCRIBES` | Requirement | 0..* / 0..* | proposed | 文档章节描述要求；证据定位包含文档版本及章节。 |
| E08 | Document | `RECORDS_DECISION` | DesignDecision | 0..* / 0..* | proposed | 文档记载某设计决策。 |
| E09 | DesignDecision | `ADDRESSES_REQUIREMENT` | Requirement | 0..* / 0..* | proposed | 设计决策回应某一要求。 |
| E10 | DesignDecision | `CONSTRAINS` | Component | 0..* / 0..* | proposed | 设计决策约束组件的实现。 |
| E11 | Project | `HAS_COMPONENT` | Component | 0..* / 0..* | proposed | 项目包含或使用组件。 |
| E12 | Repository | `HOSTS` | Component | 0..* / 0..* | proposed | 仓库承载组件的代码；组件与仓库不强制一一对应。 |
| E13 | Component | `CONTAINS_ELEMENT` | CodeElement | 0..* / 0..* | proposed | 组件包含代码元素。 |
| E14 | CodeElement | `PART_OF_ELEMENT` | CodeElement | 0..1 / 0..* | observed | 函数/类等代码元素所属的文件或容器。 不得形成环；边必须关联代码版本。 |
| E15 | PullRequest | `TARGETS_REPOSITORY` | Repository | 1 / 0..* | observed | PR 所属并拟合入的仓库。 |
| E16 | PullRequest | `REFERENCES_WORK_ITEM` | WorkItem | 0..* / 0..* | observed | PR 明确引用工作项；只证明关联存在。 |
| E17 | PullRequest | `IMPLEMENTS` | WorkItem | 0..* / 0..* | proposed | 经过确认的 PR 实现关系；仅出现 Jira 编号不足以确认此边。 只有确认后供交付判断使用；PR 提及工单号仅产生 REFERENCES_WORK_ITEM。 |
| E18 | PullRequest | `CONTAINS_COMMIT` | Commit | 0..* / 0..* | observed | 某次 PR 快照包含提交；rebase 后需保留快照而非抹去历史。 按 PR 快照记录；rebase/force-push 不抹去旧快照。 |
| E19 | Commit | `BELONGS_TO_REPOSITORY` | Repository | 1 / 0..* | observed | 提交的仓库上下文。 |
| E20 | Commit | `INTRODUCES_CHANGE` | CodeChange | 0..* / 0..* | observed | 提交相对明确父版本引入的局部修改。 仅用于确实由该提交相对指定父 SHA 引入的变更；PR 聚合 diff 不强绑末次提交。 |
| E21 | CodeChange | `MODIFIES` | CodeElement | 0..* / 0..* | observed | 具体变更触及代码元素；add/delete/rename 由 operation 表达。 必须包含 before/after SHA、路径与 side；函数定位不可靠时降级为文件级并标记。 |
| E22 | PullRequest | `HAS_REVIEW` | Review | 0..* / 1 | observed | PR 上的审查记录。 |
| E23 | PullRequest | `HAS_THREAD` | ReviewThread | 0..* / 1 | observed | PR 上的讨论线程。 |
| E24 | ReviewThread | `HAS_COMMENT` | ReviewComment | 0..* / 1 | observed | 讨论线程包含评论或回复。 |
| E25 | ReviewComment | `PART_OF_REVIEW` | Review | 0..1 / 0..* | observed | 评论归属的审查提交；可为空，线程可跨多次 Review。 |
| E26 | ReviewComment | `RAISES` | ReviewFinding | 0..* / 0..* | proposed | 评论提出具体问题；支持一评多问题、多评一问题。 |
| E27 | ReviewComment | `SUPPORTS_FINDING` | ReviewFinding | 0..* / 0..* | proposed | 后续评论提供支持该问题的理由。 |
| E28 | ReviewComment | `DISPUTES_FINDING` | ReviewFinding | 0..* / 0..* | proposed | 后续评论反驳该问题或提出反例。 |
| E29 | Review | `REPORTS_FINDING` | ReviewFinding | 0..* / 0..* | proposed | 人工或 AI 审查输出具体问题。 |
| E30 | ReviewFinding | `OBSERVED_IN_PR` | PullRequest | 1 / 0..* | observed | 该具体问题针对的 PR。 |
| E31 | ReviewFinding | `LOCATED_IN_CHANGE` | CodeChange | 0..* / 0..* | proposed | 具体问题所在的变更及代码位置。 证据必须匹配被审查 SHA、有效路径和行范围；抽取器不能编造行号。 |
| E32 | ReviewFinding | `VIOLATES` | Requirement / ReviewRule | 0..* / 0..* | proposed | 问题违反某一要求或规则；双方版本须固定。 固定要求/规则版本和代码快照；范围命中不等于违规。 |
| E33 | CodeChange | `ADDRESSES_FINDING` | ReviewFinding | 0..* / 0..* | proposed | 该变更意图处理问题；是否修复另行确认。 |
| E34 | CodeChange | `FIXES` | ReviewFinding | 0..* / 0..* | proposed | 该变更已被确认修复问题；需明确确认或有针对性的验证证据。 需人工确认或针对该 Finding 的验证证据；线程 resolved 和 CI 全绿均不足以单独确认。 |
| E35 | ReviewCase | `DOCUMENTS_FINDING` | ReviewFinding | 1 / 0..* | observed | 案例围绕一个具体问题形成；案例更新保留版本。 |
| E36 | ReviewCase | `HAS_FIX` | CodeChange | 0..* / 0..* | proposed | 案例中的已确认修复变更。 仅案例 outcome=confirmed_fixed 且存在 confirmed FIXES 时进入正式视图。 |
| E37 | ReviewCase | `HAS_EVIDENCE` | ReviewComment / CodeChange / TestResult / DesignDecision | 0..* / 0..* | proposed | 案例所依赖的具体证据对象。 |
| E38 | ReviewCase | `INSTANCE_OF_PATTERN` | DefectPattern | 0..* / 0..* | proposed | 具体案例体现的问题模式。 |
| E39 | ReviewCase | `DEMONSTRATES_SOLUTION` | SolutionPattern | 0..* / 0..* | proposed | 具体案例展示的解决方法。 |
| E40 | SolutionPattern | `MITIGATES` | DefectPattern | 0..* / 0..* | proposed | 解决方法可缓解的问题模式；适用条件仍需满足。 |
| E41 | ReviewRule | `DERIVED_FROM` | ReviewCase / Requirement / DesignDecision | 0..* / 0..* | proposed | 规则由案例、明确要求或已确认决策提炼。 引用具体来源版本；缺证据只能保留候选。 |
| E42 | ReviewRule | `DETECTS_PATTERN` | DefectPattern | 0..* / 0..* | proposed | 规则用于检查的问题模式。 |
| E43 | ReviewRule | `RECOMMENDS_SOLUTION` | SolutionPattern | 0..* / 0..* | proposed | 规则建议的处理方式。 |
| E44 | ReviewRule | `APPLIES_TO` | Repository / Component | 0..* / 0..* | proposed | 规则适用的仓库或组件；路径/语言/依赖约束记录在规则 scope。 同一目标集合内取 OR，repo/component/path/language/dependency 各维度间取 AND；空白不自动代表全局。 |
| E45 | ReviewRule | `EXCEPTION_DEFINED_BY` | DesignDecision | 0..* / 0..* | proposed | 已确认决策定义规则的例外；不得覆盖更高层安全约束。 |
| E46 | ReviewRule | `SUPERSEDES` | ReviewRule | 0..* / 0..* | proposed | 一条新规则替代旧规则；普通版本修改使用 version，不虚构新逻辑规则。 不同逻辑规则之间使用；同逻辑规则的版本升级用 revision。不能成环或跨越权限范围。 |
| E47 | Review | `USES_RULE` | ReviewRule | 0..* / 0..* | observed | 审查实际使用的规则版本，记录适用性判定与覆盖情况。 记录具体规则 revision 和本次检查结果/覆盖状态，不只记录“加载过”。 |
| E48 | Review | `CONSULTS_CASE` | ReviewCase | 0..* / 0..* | observed | 审查实际读取的历史案例。 |
| E49 | ReviewFinding | `MATCHES_PATTERN` | DefectPattern | 0..* / 0..* | proposed | 本次具体问题符合某问题模式。 |
| E50 | TestCase | `VERIFIES_CRITERION` | AcceptanceCriterion | 0..* / 0..* | proposed | 测试定义覆盖某一验收条件；不是该条件已经通过。 |
| E51 | TestCase | `REGRESSION_FOR` | DefectPattern | 0..* / 0..* | proposed | 测试用例用于防止某类问题复发。 |
| E52 | TestRun | `TESTS_COMMIT` | Commit | 1 / 0..* | observed | 测试运行针对的准确代码版本。 |
| E53 | TestRun | `PRODUCES_RESULT` | TestResult | 0..* / 1 | observed | 运行产生单项结果。 |
| E54 | TestResult | `RESULT_OF_CASE` | TestCase | 1 / 0..* | observed | 单项结果对应的测试定义及版本。 |
| E55 | TestResult | `SUPPORTS_RESOLUTION` | ReviewFinding | 0..* / 0..* | proposed | 测试结果为问题处理结论提供证据；普通 CI 全绿不自动证明修复。 记录测试用例/运行/代码版本；一般构建成功不是针对性修复证据。 |
| E56 | BuildArtifact | `BUILT_FROM` | Commit | 0..* / 0..* | observed | 制品来自确定的源代码提交。 记录构建清单支持的源提交；同仓库至少固定一个 SHA，不能只记 branch/tag。 |
| E57 | Release | `INCLUDES_ARTIFACT` | BuildArtifact | 0..* / 0..* | observed | 发布版本包含制品。 |
| E58 | Deployment | `DEPLOYS_ARTIFACT` | BuildArtifact | 1..* / 0..* | observed | 本次部署尝试的制品。 |
| E59 | Deployment | `TARGETS_ENVIRONMENT` | Environment | 1 / 0..* | observed | 部署目标环境。 |
| E60 | Incident | `OCCURRED_IN` | Environment | 0..* / 0..* | observed | 故障发生环境。 |
| E61 | Incident | `AFFECTS_COMPONENT` | Component | 0..* / 0..* | proposed | 故障影响的组件。 |
| E62 | WorkItem | `REMEDIATES` | Incident | 0..* / 0..* | proposed | 工作项用于处理该运行故障。 |
| E63 | Actor | `MEMBER_OF` | Team | 0..* / 0..* | observed | 参与主体的团队归属。 |
| E64 | Team | `OWNS` | Project / Component / ReviewRule | 0..* / 0..* | observed | 团队对项目、组件或正式规则负有责任。 以权威目录/受保护组件清单/审批登记为依据；未知责任人不由 LLM 确认。 |
| E65 | Actor | `AUTHORED` | PullRequest / Commit / ReviewComment / Document / DesignDecision | 0..* / 0..* | observed | 参与主体创建对象。 由源系统作者 ID 或可信人工登记生成；同名不合并。 |
| E66 | Actor | `PERFORMED_REVIEW` | Review | 0..* / 1 | observed | 参与主体进行审查。 |
| E67 | Actor | `APPROVED_RULE` | ReviewRule | 0..* / 0..* | observed | 有权限的主体批准该规则版本。 仅治理接口根据有权限主体的批准生成；禁止模型自赋予批准关系。 |

# 附录 C · 参考资料与交付物说明

本体是针对本项目的自定义设计，不宣称来自上述厂商的完整标准模型。以下资料用于核实接入对象、版本、事件、安全与 Skill 格式；访问核查日期为 2026-10-24。

**[S01] [GitHub · Webhook 最佳实践](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks)**  
用于事件去重、异步处理、投递重放的接入设计；不意味着本平台已实现。

**[S02] [GitHub · PR review comments REST API](https://docs.github.com/en/rest/pulls/comments)**  
区分行内 review comments 与 issue comments；读取原始评论、位置和更新时间。

**[S03] [GitHub · Pull requests GraphQL reference](https://docs.github.com/en/graphql/reference/pulls)**  
PR、Review、ReviewThread、Comment 的源对象结构。

**[S04] [Confluence Cloud · Page API v2](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)**  
页面正文、page ID、版本、分页与页面/空间读取权限。

**[S05] [Confluence Cloud · Version API v2](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-version/)**  
页面与评论的版本元数据；历史正文可用性需按接口实测。

**[S06] [Jira Cloud · Issue API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)**  
工单、字段和 changelog；不把 changelog 等同完整历史正文备份。

**[S07] [Jira Cloud · Webhooks](https://developer.atlassian.com/cloud/jira/platform/webhooks/)**  
事件订阅与重试；接入方式需按 Cloud/Data Center 和权限确认。

**[S08] [Agent Skills · Specification](https://agentskills.io/specification)**  
SKILL.md、name/description、配套目录和渐进加载；allowed-tools 仍为实验字段。

**[S09] [Agent Skills · Overview](https://agentskills.io/home)**  
Skill 作为可复用任务流程；不同运行时需单独验证支持范围。

**[S10] [GitHub Actions · Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)**  
最小权限、不可信代码与特权工作流的隔离原则。

**[S11] [MCP · Authorization security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations)**  
MCP audience 校验与禁止 token passthrough；不代替业务对象鉴权。

**[S12] [W3C · PROV-O](https://www.w3.org/TR/prov-o/)**  
来源、活动和责任主体的追溯概念；本设计不要求 RDF/OWL 部署。

## 交付物与完成边界

| 文件 | 内容 | 状态 |
|---|---|---|
| 开发文档 HTML / Markdown | 背景、模型、流程、接口、SKILL、工程与验收 | 可评审设计稿 |
| ontology/ontology.v0.2.yaml | 30 类 Entity、67 类 Edge、字段、基数、约束 | 自定义本体规范，非可直接执行的 LinkML |
| ontology/ontology.v0.1.reference.yaml | 上一版原始模型 | 用于对照 |
| skills/*/SKILL.md | 五份技能工作流及引用文件 | 等待后端工具绑定，未声称已集成 |
| examples/ | 修订后的虚构知识案例、事件与证据包 | 测试/说明数据，非真实项目 |

本包不包含已部署数据库、已注册 GitHub App、可用远程 API、正式权限审批或真实仓库评测结果。进入实现阶段时，以本体 YAML 和接口契约建立校验测试，再实现连接器与工作流。
