# 两周 Agent-first MVP 开发日程

## 1. 项目定位

本项目的重点不是制作一个功能完整的球员电商网站，而是通过足球引援场景系统学习并展示：

- RAG：知识库构建、检索、重排、引用和效果评估。
- Tool Use：让 Agent 调用确定性的数据库查询与分析工具。
- Planning：把阵容诊断或引援任务拆成可执行步骤。
- Memory：区分会话记忆、俱乐部长期记忆和任务执行状态。
- Reflection：让独立的检查节点发现证据不足、冲突或越界建议。
- Multi-Agent：让有不同职责、工具和上下文的 Agent 协作。
- Agent 工程：状态持久化、可观测性、失败恢复、评估与迭代。

React Marketplace 是 Agent 的操作台和结果展示层；FastAPI 是业务与 Agent 的接口层。前后端交付流程需要完整，但不是两周内的主要技术深度。

## 2. 两周最终演示

用户以俱乐部身份登录后，可以：

1. 浏览、筛选、比较和收藏球员。
2. 发起一次“分析当前阵容”的后台任务。
3. 查看 Agent 的计划、工具调用、证据、推理状态和最终结论。
4. 选择阵型或战术目标，推演阵容弱点和位置缺口。
5. 输入预算、年龄、位置和风格约束，获得可解释的引援候选人。
6. 看到战术、球探、财务风险和 Critic Agent 的不同意见及最终综合结果。
7. 在下一次任务中复用俱乐部偏好和历史反馈。

## 3. 推荐的 Agent 方向

### 方向 A：阵容诊断与阵型推演 Agent（核心）

输入：俱乐部、目标阵型、比赛风格和赛季目标。

Agent 可以调用：

- `get_club_squad`
- `get_player_profile`
- `calculate_position_depth`
- `calculate_role_fit`
- `compare_formations`
- `retrieve_tactical_knowledge`

输出：位置深度、角色适配、阵容不平衡、关键球员依赖、替补缺口及不同阵型的利弊。

适合展示：Tool Use、Planning、RAG、状态图和 Reflection。

### 方向 B：约束条件下的智能引援 Agent（核心）

输入：阵容缺口、预算、工资、年龄、联赛、角色和风险偏好。

执行流程：

```text
理解需求
  → 生成结构化 RecruitmentBrief
  → SQL 硬条件过滤
  → 确定性评分与排序
  → RAG 检索角色/战术知识
  → Agent 解释适配性
  → Critic 检查证据和约束
  → 返回候选名单
```

适合展示：结构化输出、混合检索、Tool Use、Reflection 和人类反馈。

### 方向 C：多 Agent 招聘委员会（核心的扩展）

- Tactical Analyst：判断战术与角色适配。
- Scout Agent：寻找候选人并解释技术特点。
- Financial/Risk Agent：检查身价、工资、年龄和合同风险。
- Critic Agent：检查事实、遗漏、约束冲突和无证据结论。
- Recruitment Lead：汇总分歧并生成最终建议。

每个 Agent 必须拥有不同的工具或上下文范围，并返回固定 schema。不要仅用不同 system prompt 模拟多个角色。

### 方向 D：Shortlist Monitoring Agent（加分项）

当 shortlist、预算或阵容发生变化时，后台重新计算：

- 是否存在位置重复投资。
- 总转会费和工资是否超限。
- 某候选人是否被更合适的球员替代。
- 阵容年龄、身高或惯用脚是否失衡。

适合展示：事件驱动、消息队列、后台任务、缓存失效和通知。

### 方向 E：俱乐部 Recruitment Memory（加分项）

保存俱乐部明确确认的偏好和历史决策，例如“不接受 29 岁以上高价球员”。后续推荐可以引用这些记忆。

适合展示：长期 Memory、反馈学习和记忆冲突处理。

## 4. Agent 机制与项目模块映射

| 机制 | 项目中的实现 | 必须验证的问题 |
|---|---|---|
| Tool Use | SQL 查询、阵容深度、角色评分、预算校验工具 | 参数是否合法；工具失败是否可恢复 |
| RAG | 战术、阵型、位置角色和招聘原则知识库 | 是否召回正确内容；回答能否引用来源 |
| Planning | 先生成结构化步骤，再按状态图执行 | 是否跳步、重复调用或无限循环 |
| Working Memory | 单次任务的 brief、计划、工具结果和中间结论 | 上下文是否过长；状态能否恢复 |
| Long-term Memory | 俱乐部偏好、历史 shortlist 反馈和决策 | 谁写入；何时失效；是否和当前需求冲突 |
| Reflection | Critic 检查事实、预算、引用和结论 | 是否能真正修正结果，而不是重复措辞 |
| Multi-Agent | 战术、球探、风险、Critic 和 Lead | 职责是否独立；冲突如何汇总 |
| Human-in-the-loop | 用户确认 brief、选择候选人、接受或拒绝建议 | Agent 是否越过决策边界 |

## 5. 推荐架构

```text
React + TypeScript
  ├── Player Marketplace
  ├── Recruitment Workspace
  ├── Agent Run Timeline
  └── Evidence / Feedback UI
             ↓ REST + polling
FastAPI
  ├── Auth / Club tenant boundary
  ├── Player / Squad / Shortlist API
  ├── Agent Run API
  └── Tool permission boundary
             ↓
Agent Orchestrator（先作为模块化单体）
  ├── State / Planning
  ├── Tool Registry
  ├── RAG Retriever
  ├── Memory Store
  ├── Specialist Agents
  └── Reflection / Evaluation
        ↓          ↓             ↓
   PostgreSQL   Vector index   Redis
   业务数据      战术知识库      队列/缓存
```

两周内不要真正拆成多个部署服务。先用模块化单体保留清晰接口；只把耗时 Agent Run 放进 worker，体验一个真实的异步边界。这比创建多个空壳微服务更能体现分布式系统的核心问题。

### 建议的数据结构

- `agent_runs`：任务、状态、当前步骤、俱乐部、创建者和耗时。
- `agent_events`：计划、工具调用、工具结果、Reflection 和错误事件。
- `recruitment_briefs`：结构化引援约束。
- `knowledge_documents` / `knowledge_chunks`：来源、版本、metadata 和文本块。
- `club_memories`：俱乐部长期偏好、来源、置信度和有效期。
- `recommendation_feedback`：接受、拒绝、理由和用户修正。

敏感的内部推理文本不作为产品输出。界面只展示计划摘要、工具名称与参数摘要、证据、状态变化和可验证结论。

## 6. 每天约 5 小时的分配

- 30 分钟：回顾目标和设计当天实验。
- 3 小时：实现当天的单一核心机制。
- 1 小时：测试、Agent trace 分析和失败案例。
- 30 分钟：记录结论、提交代码、维护评估集。

每天至少保留一个可重复测试的示例任务。不要只凭一次“看起来不错”的模型输出判断完成。

---

## 第 1 周：单 Agent、工具和 RAG

### Day 1 — 需求分析、任务边界与评估集

目标：先定义 Agent 应解决什么，以及如何证明它有效。

- 写出阵容诊断和引援推荐两条用户旅程。
- 定义 `RecruitmentBrief`、`AgentRun` 和最终建议 schema。
- 准备 8–10 个固定评估问题，覆盖正常、无结果、冲突约束和越权请求。
- 为每个问题记录期望工具、硬约束和关键事实，不要求固定自然语言答案。
- 画出初始状态图：输入 → 计划 → 工具 → 汇总 → 检查 → 输出。

完成标准：不用模型也能说清每个测试案例应查询什么、不能违反什么。

### Day 2 — React/FastAPI 骨架与 Agent 可观测性

目标：建立完整但最小的前后端交付链路。

- 创建 React + TypeScript 和 FastAPI 项目。
- 添加俱乐部测试账号和最小 Session 登录。
- 添加 `/api/health`。
- 创建 `agent_runs`、`agent_events` 表和状态枚举。
- 前端建立 Recruitment Workspace 和 Run Timeline 占位页面。
- 允许前端创建 run 并轮询状态，不调用模型。

完成标准：一次假任务能经历 queued → running → completed，并在界面显示事件时间线。

### Day 3 — 确定性 Tool Layer

目标：先让 Agent 拥有可信、可测试的能力。

- 实现球员搜索、球员详情、俱乐部阵容、位置深度和预算过滤工具。
- 每个工具使用明确的输入/输出 schema。
- 对 club scope、排序字段、返回数量和异常进行限制。
- 独立测试每个工具，不经过 LLM。
- 在 `agent_events` 中记录工具名、耗时、结果摘要和错误。

完成标准：评估集中的事实问题可以完全由工具回答，且跨俱乐部私有数据不可访问。

### Day 4 — RAG 知识库管道

目标：构建可追溯的战术知识库，而不是只调用向量搜索。

- 选择少量合法、可引用的阵型和位置角色资料。
- 实现加载、清洗、chunk、metadata 和版本标识。
- 为每个 chunk 保存来源、标题、章节和更新时间。
- 建立 embedding 与向量索引；优先使用 PostgreSQL/pgvector，减少基础设施数量。
- 编写可重复执行且不会重复写入的 ingestion 脚本。

完成标准：给定阵型或角色问题，可以返回相关 chunk 及其来源。

### Day 5 — Retrieval、引用和 RAG 评估

目标：验证“检索正确”，而不只是“回答流畅”。

- 实现 metadata filter、top-k 和可选重排。
- 将结构化球员事实与知识库文本分开，禁止用向量库替代精确 SQL。
- 要求答案中的战术结论引用 chunk ID 或来源。
- 为评估问题标注期望命中文档。
- 记录 hit rate、无关召回和无答案处理。
- 对 chunk 大小、top-k 做一次小型对比实验。

完成标准：RAG 回答可追溯，缺乏证据时明确返回“不足以判断”。

### Day 6 — Tool-calling 单 Agent

目标：完成第一个真实 Agent loop。

- 将 Tool Registry 接入模型。
- 限制最大迭代次数、每次工具结果长度和总超时。
- 使用结构化最终输出。
- 处理错误参数、空结果、重复工具调用和模型不可用。
- 在 Timeline 中展示可审计事件，而不是内部思维链。
- 用 Day 1 评估集回归。

完成标准：Agent 可以自主选择正确工具完成简单阵容或引援查询，并且不会无限循环。

### Day 7 — Planning 与可恢复状态

目标：从自由循环升级为显式工作流。

- 让 Planner 输出有上限的结构化步骤。
- 用状态图实现 plan → execute → observe → revise → finish。
- 将状态 checkpoint 持久化到数据库。
- 支持某一步失败后重试，并区分可重试与不可重试错误。
- 在执行硬成本操作前预留 human approval 节点。
- 回顾第一周评估结果并修复最高频失败模式。

完成标准：中断一个任务后能够从已保存状态继续，而不是从头重新执行。

---

## 第 2 周：Memory、Reflection、多 Agent 与工程化

### Day 8 — Memory 设计与实现

目标：明确不同记忆的生命周期和写入规则。

- Working memory：保存在单次 `agent_run` 状态中。
- Long-term memory：只保存用户确认的俱乐部偏好和反馈。
- 为长期记忆增加来源、创建者、置信度、有效期和删除能力。
- 建立 memory retrieval tool，不把所有历史记录塞入 prompt。
- 实现一条冲突策略：当前明确需求优先于历史偏好。
- 测试 Club A 的记忆不会出现在 Club B 的任务中。

完成标准：用户确认一个偏好后，新任务可以引用它，并说明记忆来源。

### Day 9 — Reflection 与质量守门

目标：让 Reflection 执行检查和修正，而不是重复生成答案。

- 定义检查表：硬约束、事实一致性、引用、预算、候选数量和不确定性。
- 先用确定性 validator 检查结构和数值约束。
- 再由 Critic 检查证据是否支持结论以及是否遗漏明显风险。
- 限制最多一次修订，避免 reflection loop。
- 保存初稿、批评结果和修订后的结构化差异。
- 对比有无 Reflection 的评估结果、延迟和 token 成本。

完成标准：至少准备两个 Critic 能发现并实际修正的问题案例。

### Day 10 — 智能引援推荐完整闭环

目标：完成核心 Agent 场景之一。

- 前端创建结构化 Recruitment Brief 表单。
- 确定性过滤年龄、位置、预算、工资和联赛条件。
- 用角色适配分数排序候选人。
- 使用 RAG 为角色适配与风险解释提供知识依据。
- 让用户接受、拒绝或修正建议，并保存 feedback。
- 在结果页展示候选人、证据、风险和不同假设下的变化。

完成标准：输入同一 brief 可以重复得到满足硬约束的候选集合，解释包含真实数据和引用。

### Day 11 — 阵容诊断与阵型推演

目标：完成第二个核心 Agent 场景。

- 实现阵容深度与角色覆盖的确定性分析。
- 支持至少两个阵型，例如 4-3-3 与 4-2-3-1。
- 输出每个位置的首选、替补、缺口和适配分数。
- 允许替换或加入一名候选球员后重新计算。
- Agent 解释阵型切换的收益、风险和关键假设。
- 前端用阵型图、差异表和 Insight Card 展示结果。

完成标准：推演结果随阵型或候选球员变化，并能解释变化来自哪些数据。

### Day 12 — Multi-Agent 招聘委员会

目标：用真实职责边界展示多 Agent 协作。

- Tactical Analyst 只访问阵型、角色和球员能力工具。
- Scout Agent 负责候选搜索和技术特点。
- Financial/Risk Agent 负责预算、工资、年龄和合同约束。
- Critic 检查三方输出与原始证据。
- Recruitment Lead 汇总共识、分歧和最终建议。
- 并行执行相互独立的 Specialist，并限制总调用次数。
- 与 Day 10 单 Agent 结果对比质量、延迟和成本。

完成标准：界面能够显示各 Specialist 的结构化意见和真实分歧，而不只是五段相似文本。

### Day 13 — 消息队列、缓存与后台 Agent

目标：适量体验分布式系统问题，不扩张为完整微服务项目。

- 将 Agent Run 从 FastAPI 请求进程移到 worker。
- 使用 Redis 支持任务队列或状态通知，并缓存高频只读查询。
- API 返回 `202 Accepted + run_id`，前端轮询任务状态。
- 为任务设计幂等键，避免重复提交产生两次结果。
- 设置超时、有限重试和失败状态。
- 修改 shortlist 或 club memory 时使相关缓存失效。
- 记录 correlation ID，串联 API、worker 和 Agent events。

完成标准：停止并重启 worker 后，任务不会无声丢失；重复请求不会产生重复副作用。

### Day 14 — 评估、需求验收与迭代演示

目标：用证据展示 Agent 架构，而不是只演示一次成功回答。

- 运行全部固定评估案例。
- 统计工具选择正确率、约束违反数、引用命中、任务成功率、延迟和模型成本。
- 演示一个失败案例以及 Reflection 或 fallback 如何处理。
- 用两个俱乐部账号检查数据和 Memory 隔离。
- 更新 README：需求、架构、Agent 状态图、数据流、启动方式和限制。
- 将未完成或低质量功能记录为 backlog，不在最后一天扩大范围。
- 准备 8 分钟演示：问题 → 计划 → 工具 → 多 Agent → 检查 → 反馈 → Memory。

完成标准：能够解释每个 Agent 机制为什么存在、保存什么状态、如何失败以及如何被评估。

## 7. 两周内的技术取舍

### 必须深入

- Tool schema 与权限边界。
- RAG 数据质量、引用和评估。
- 显式 Agent state 与有限状态图。
- Memory 生命周期与租户隔离。
- Reflection 的确定性检查与有限修订。
- Multi-Agent 的职责和工具隔离。
- Trace、错误处理和评估集。

### 只需体验

- React Marketplace 的视觉完善。
- 微服务拆分。
- Redis 缓存策略。
- 消息队列的重试和幂等。
- 容器化和部署。

### 暂不实现

- 自主无限循环 Agent。
- Agent 自动修改数据库核心数据。
- 模型自行决定身份认证或租户权限。
- 大规模爬虫和未经确认的数据源。
- Kubernetes、服务网格和复杂事件总线。
- 为了展示而创建多个没有独立职责的 Agent。

## 8. 时间不足时的裁剪顺序

1. 取消 Shortlist Monitoring Agent。
2. Redis 只用于任务队列，不做复杂缓存。
3. 阵型只支持两个固定模板。
4. Multi-Agent 只保留 Tactical、Risk、Critic 和 Lead。
5. Marketplace 只保留姓名、位置、俱乐部和身价筛选。

不能裁剪：固定评估集、工具测试、RAG 引用、俱乐部隔离、Agent 最大迭代限制和失败处理。

## 9. 每日学习与交付记录

每天结束时追加：

```text
日期：
今天研究的 Agent 机制：
实现的最小实验：
成功案例：
失败案例：
评估结果：
架构上的新认识：
明日第一步：
```
