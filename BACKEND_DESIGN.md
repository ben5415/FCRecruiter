# Backend Design — Modular Monolith

## 1. 架构结论

本项目采用：

> **模块化单体（Modular Monolith）+ 进程内 Agent 模块 + 可选后台 Worker**

第一版只有一个 FastAPI 应用、一个 PostgreSQL 数据库和一套代码仓库。AI 不单独部署成微服务，而是作为边界清晰的业务模块运行。

```text
React + TypeScript
        ↓ REST API
FastAPI Modular Monolith
  ├── Auth
  ├── Team
  ├── Player Catalog
  ├── Events
  ├── Recruitment
  ├── Knowledge
  └── Agent
        ↓
PostgreSQL
```

如果 Agent 任务变慢，可以启动一个使用同一代码库的 Worker：

```text
FastAPI ──提交任务──→ Queue ──→ Agent Worker
   ↑                              │
   └────────查询任务状态──────────┘
```

Worker 是部署方式的扩展，不是新的业务微服务。它复用相同的领域模型、工具和数据库。

## 2. 为什么不使用微服务

当前项目不具备拆分微服务的必要条件：

- 开发者人数少。
- 两周内需要快速迭代。
- 模块边界仍在探索。
- 当前没有独立扩缩容和可用性要求。
- 分布式事务、服务发现、网络错误和部署管理会掩盖 Agent 学习目标。

模块化单体仍然可以学习：

- 领域边界。
- 依赖倒置。
- 事件驱动。
- 异步任务。
- 缓存和幂等。
- 可观测性。
- 未来服务拆分。

## 3. 设计原则

### 3.1 业务数据属于业务模块

- Player 模块拥有球员查询和球员数据解释。
- Team 模块拥有阵容、阵型和球队状态。
- Recruitment 模块拥有引援需求、候选名单和 shortlist。
- Agent 模块不直接拥有球员、阵容和 shortlist。

### 3.2 Agent 通过 Tool 调用业务能力

Agent 不能自由执行 SQL，也不能直接修改业务表。它只能调用注册过的领域工具：

```text
get_current_squad
calculate_position_depth
search_players
get_player_profile
calculate_role_fit
retrieve_role_knowledge
```

这些 Tool 是业务 Application Service 的受控适配器，而不是通用插件系统。

### 3.3 结构化数据是事实来源

- 数据库保存球队、球员、事件和引援状态。
- Markdown 报告只是带时间和版本的生成结果。
- LLM 输出必须通过 schema 校验后才能保存。
- AI 不能直接覆盖球队的核心状态。

### 3.4 依赖方向固定

```text
API / UI Adapter
      ↓
Application Use Cases
      ↓
Domain
      ↑
Infrastructure Adapters
```

Domain 不依赖 FastAPI、SQLAlchemy、LangChain 或具体模型 SDK。

## 4. 推荐目录结构

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── shared/
│   │   ├── database.py
│   │   ├── errors.py
│   │   ├── pagination.py
│   │   └── observability.py
│   └── modules/
│       ├── auth/
│       │   ├── api.py
│       │   ├── application.py
│       │   ├── domain.py
│       │   └── repository.py
│       ├── team/
│       │   ├── api.py
│       │   ├── application.py
│       │   ├── domain.py
│       │   └── repository.py
│       ├── players/
│       │   ├── api.py
│       │   ├── application.py
│       │   ├── domain.py
│       │   └── repository.py
│       ├── events/
│       │   ├── api.py
│       │   ├── application.py
│       │   ├── domain.py
│       │   └── repository.py
│       ├── recruitment/
│       │   ├── api.py
│       │   ├── application.py
│       │   ├── domain.py
│       │   ├── scoring.py
│       │   └── repository.py
│       ├── knowledge/
│       │   ├── application.py
│       │   ├── ingestion.py
│       │   └── repository.py
│       └── agent/
│           ├── api.py
│           ├── application.py
│           ├── state.py
│           ├── graph.py
│           ├── tools.py
│           ├── prompts.py
│           ├── schemas.py
│           ├── model_gateway.py
│           └── repository.py
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
└── pyproject.toml
```

这是目标结构，不要求第一天创建所有空文件。只有实现模块时才创建对应目录和文件。

## 5. 模块职责

### 5.1 Auth

负责：

- 经理账号登录和登出。
- Session Cookie。
- 当前用户读取。
- 后续角色权限扩展点。

不负责球队业务逻辑。

### 5.2 Team

负责：

- 当前球队。
- 阵容和阵型。
- 阵容快照。
- 位置深度计算。
- 球队状态报告的业务输入。

### 5.3 Player Catalog

负责：

- 球员列表、详情、筛选、排序和分页。
- 俱乐部、联赛和国家关联查询。
- 数据来源和数据快照信息。
- 球员原始属性读取。

### 5.4 Events

负责：

- 训练、医疗、更衣室和招募事件。
- 事件时间线。
- 事件来源和创建者。
- 为球队状态报告提供结构化输入。

事件不可变。需要修正时新增更正事件，不静默覆盖历史。

### 5.5 Recruitment

负责：

- `RecruitmentBrief`。
- 硬约束与软偏好。
- Role Profile。
- Role Fit 确定性评分。
- 候选人搜索和排序。
- Shortlist 和经理备注。

最终 shortlist 决定属于经理，不属于 Agent。

### 5.6 Knowledge

负责：

- 阵型、角色和足球分析知识文档。
- 文档清洗、chunk、embedding 和版本。
- 带来源的检索结果。

精确球员属性不进入 RAG，应从 Player Catalog 查询。

### 5.7 Agent

负责：

- 足球领域意图解析。
- 有上限的 Planning。
- Tool Use 编排。
- Working Memory。
- 一次 Reflection。
- 结构化报告生成。
- 模型调用次数、Token、耗时和错误记录。

不负责：

- 通用 Tool Registry。
- 动态 Skill 加载。
- MCP Host。
- 任意代码或 Shell 执行。
- 自主创建 Agent。
- 身份认证和最终业务决策。

## 6. 模块通信方式

模块间优先通过 Application Service 调用：

```python
class SearchPlayers:
    def execute(self, query: PlayerSearchQuery) -> PlayerSearchResult:
        ...


class AnalyseSquadDepth:
    def execute(self, team_id: int, formation: str) -> SquadDepthReport:
        ...
```

Agent Tool 只包装这些接口：

```python
def search_players_tool(args: SearchPlayersArgs) -> SearchPlayersResult:
    return search_players.execute(args.to_query())
```

禁止 Agent Tool 直接获得通用 SQLAlchemy Session 并自由查询数据库。

模块事件只用于不要求立即返回的副作用：

```text
TeamEventCreated
ShortlistChanged
RecruitmentBriefConfirmed
AgentRunCompleted
```

第一版可以在进程内同步处理事件。需要异步时，再将相同事件交给队列处理。

## 7. Agent 工作流

只实现一个固定的 `RecruitmentAnalysisGraph`：

```text
Receive Question
      ↓
Validate Football Intent
      ↓
Parse Structured Request
      ↓
Load Team Context
      ↓
Create Limited Plan
      ↓
Execute Registered Tools
      ↓
Retrieve Football Knowledge
      ↓
Draft Structured Report
      ↓
Deterministic Validation
      ↓
One-pass Reflection
      ↓
Return Report
```

硬限制：

```text
工作流数量          1
工具数量            ≤ 6
计划步骤            ≤ 6
Reflection          ≤ 1
候选球员上下文      ≤ 10
模型供应商          1
```

## 8. API 设计

### Auth

```http
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

### Team 与 Events

```http
GET  /api/team
GET  /api/team/squad
GET  /api/team/formations
GET  /api/team/status-report
POST /api/team/status-report/refresh
GET  /api/events
POST /api/events
```

### Players

```http
GET /api/players
GET /api/players/{player_id}
```

`GET /api/players` 支持：

```text
search, position, club_id, league_id,
min_age, max_age, max_value_eur,
min_overall, sort, order, page, page_size
```

### Recruitment

```http
POST  /api/recruitment/briefs
GET   /api/recruitment/briefs/{brief_id}
PATCH /api/recruitment/briefs/{brief_id}
POST  /api/recruitment/briefs/{brief_id}/confirm
GET   /api/recruitment/briefs/{brief_id}/candidates

GET    /api/shortlist
POST   /api/shortlist/players
DELETE /api/shortlist/players/{player_id}
```

### Agent

```http
POST /api/agent/runs
GET  /api/agent/runs/{run_id}
GET  /api/agent/runs/{run_id}/events
POST /api/agent/runs/{run_id}/confirm
POST /api/agent/runs/{run_id}/cancel
```

耗时任务返回：

```http
HTTP/1.1 202 Accepted
```

```json
{
  "run_id": "uuid",
  "status": "queued"
}
```

MVP 前端使用轮询，不需要 WebSocket。

## 9. 核心数据表

复用已有：

- `players`
- `clubs`
- `leagues`
- `countries`

新增：

```text
users
user_sessions
team_config
squad_snapshots
squad_members
team_events
team_status_reports
role_profiles
recruitment_briefs
recruitment_candidates
shortlist_items
knowledge_documents
knowledge_chunks
agent_runs
agent_events
agent_checkpoints
```

第一版按实际实现顺序创建表，不一次生成全部 migration。

### `agent_runs` 最小字段

```text
id
user_id
task_type
status
input_json
result_json
current_step
model_calls
input_tokens
output_tokens
started_at
completed_at
error_code
```

### `agent_events` 最小字段

```text
id
run_id
event_type
step_name
summary
metadata_json
created_at
```

不保存或展示模型隐藏思维链。只保存计划摘要、工具调用、可验证结果、状态变化和错误。

## 10. 同步与异步执行

### 第一阶段

简单请求同步执行：

- 球员列表。
- 球员详情。
- 手动筛选。
- 确定性角色评分。

Agent 分析也可以先同步实现，设置明确超时。

### 第二阶段

只有确认出现以下问题时才加入 Worker：

- 请求经常超过反向代理超时。
- 用户需要关闭页面后继续任务。
- 需要可靠重试。
- 多个模型调用明显阻塞 API worker。

加入 Worker 后仍保持：

- 同一代码库。
- 同一模块结构。
- 同一数据库。
- 同一个 `RecruitmentAnalysisGraph`。

可以使用 Redis 和成熟任务队列，不自己实现调度器。

## 11. AI 成本与失败控制

每个 Agent Run 必须设置：

- 最大模型调用次数。
- 最大工具调用次数。
- 最大输入和输出 Token。
- 总超时。
- 单次 Tool 超时。
- 最大候选人数。
- 最多一次 Reflection。

降级策略：

```text
模型不可用
→ 返回确定性阵容分析和候选排序
→ 标记“AI explanation unavailable”
→ 不影响手动筛选和 shortlist
```

缓存对象优先选择：

- Role Profile。
- 球员对角色的适配评分。
- 同一阵容快照的位置深度。
- 稳定的知识检索结果。

没有实际性能问题前不引入 Redis；第一版可以使用数据库或进程内短期缓存。

## 12. 安全边界

- 密码使用安全哈希，不保存明文。
- 浏览器认证使用 HttpOnly Session Cookie。
- 写请求处理 CSRF。
- Agent 输入先经过足球领域和 schema 验证。
- Agent 只能调用白名单工具。
- Tool 参数再次验证，不能信任模型输出。
- 模型不能决定用户权限。
- Prompt 和知识文档视为不可信输入。
- `.env` 不提交到版本库。
- 日志不记录密码、Cookie、完整模型密钥或敏感输入。

## 13. 测试策略

### Unit Tests

- 位置深度。
- Role Fit 评分。
- Recruitment Brief 验证。
- Agent 状态转换。
- Tool 参数校验。

### Integration Tests

- API 与 PostgreSQL。
- Agent Tool 与 Application Service。
- 知识检索及来源。
- 登录和权限。

### Agent Evals

- 是否选择正确 Tool。
- 是否满足硬约束。
- 是否引用真实球员数据。
- RAG 是否命中预期知识。
- 无证据时是否承认不足。
- 是否在调用和 Token 上限内结束。
- Reflection 是否修正了真实问题。

模型调用在普通单元测试中使用 fake gateway；少量 eval 才调用真实模型。

## 14. 未来扩展与拆分条件

模块化单体应先纵向扩展模块。只有满足明确条件才考虑拆服务。

### 可以继续留在单体

- 新增教练、球探和队医账号。
- 增加事件类型。
- 增加更多足球 Tool。
- 增加第二个固定 Agent 工作流。
- 增加后台 Worker。
- 增加 Redis 缓存。

### 可能拆分 AI 服务的条件

- AI workload 需要独立扩缩容。
- Agent Worker 与 API 的资源需求显著不同。
- AI 发布频率和故障边界需要与核心业务分离。
- 多个独立产品共同使用相同 AI 能力。
- 团队已经有人分别负责核心业务和 AI 平台。

拆分时保留现有 Agent Application 接口，将进程内调用替换成内部 API 或消息协议，而不是重写领域逻辑。

## 15. MVP 实现顺序

1. 建立 FastAPI、数据库连接和模块目录。
2. 实现 Player Catalog 的只读 API。
3. 实现 Team 和 Squad 的最小模型。
4. 实现确定性阵容深度与角色评分。
5. 实现 Recruitment Brief 和候选人查询。
6. 将业务能力包装成固定 Agent Tools。
7. 实现单一 `RecruitmentAnalysisGraph`。
8. 加入小型 RAG 知识库。
9. 加入一次 Reflection 和运行记录。
10. 性能确有需要时再增加 Worker。

## 16. 架构守则

开发过程中持续使用以下判断：

> 这是完成足球引援流程所需的模块，还是为了未来任意 Agent 而创建的平台？

如果答案是后者，则不在当前项目中实现。

允许：

- `RecruitmentAnalysisGraph`
- `PlayerSearchTool`
- `RoleKnowledgeRetriever`
- `RecruitmentRunRepository`

不允许：

- `UniversalAgentRuntime`
- `DynamicSkillLoader`
- `GenericWorkflowEngine`
- `MCPServerManager`
- `PluginMarketplace`

模块化单体的目标不是暂时把微服务放在同一目录，而是用最少的运行时复杂度保持真正清晰的业务边界。
