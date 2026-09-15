# FCRecruiter：30 天实现与吃透计划

> 周期：30 天  
> 默认投入：每天 60 分钟  
> 建议上限：每天 75 分钟  
> 绝对上限：每天 120 分钟，到点必须停止，不以“马上就好”为理由延长

## 1. 30 天后的目标

30 天后，不追求把 FCRecruiter 做成完整产品，而是完成一个能够运行、演示、测试和讲解的 Agent 应用闭环：

```text
用户在 Web 页面提出足球引援问题
  → Backend 验证用户与租户
  → Agent Service 找到当前 Agent Definition
  → 加载 Thread Memory
  → AgentRunner 调用模型和类型化 Tool
  → Backend 安全查询阵容、战术、伤病和候选球员
  → 返回带依据的结构化招募报告
  → 保存消息、执行轨迹和基础指标
  → 前端展示报告与证据
```

同时达到以下“吃透”标准：

- 能不看文档画出前端、Backend、Agent Service 和两个数据库之间的调用图。
- 能解释一次登录请求、一次球员分页请求和一次 Agent 请求分别经过哪些组件。
- 能解释 Agent Loop、Tool Calling、结构化输出、超时和降级。
- 能解释为什么模型不能访问数据库、不能生成 SQL、不能决定租户身份。
- 能解释 Thread、Message、滚动摘要、上下文裁剪和乐观锁。
- 能解释 Agent Definition 为什么需要版本化，以及旧 Thread 为什么固定旧版本。
- 能运行迁移和测试，并独立定位至少一类 API、数据库或模型调用问题。
- 能用 5～8 分钟完成项目介绍，并回答常见追问。

## 2. 明确不做的内容

一个月只有约 30 小时，以下内容不进入本月主线：

- Multi-Agent 协作和复杂 Planning。
- 通用 Skill 市场、插件系统或 OpenClaw 式平台。
- 微服务注册中心、Kafka、Redis 集群和分布式事务。
- 自动执行转会、修改业务数据或其他高风险写 Tool。
- 完整生产级 OAuth、mTLS、Kubernetes 和云部署体系。
- 大规模知识库、复杂 Graph RAG 和微调模型。
- 完整的 Agent 管理后台和可视化工作流编辑器。

如果主线提前完成，可以加入一个最小 pgvector 知识检索 Tool；不得因此推迟核心闭环。

## 3. 每天的固定时间盒

推荐每天严格按以下结构执行：

| 时间 | 内容 |
|---|---|
| 0～5 分钟 | 写下今天唯一的交付目标，运行现有测试确认起点 |
| 5～20 分钟 | 阅读当天涉及的少量源码，画调用关系或写出自己的解释 |
| 20～50 分钟 | 只实现一个小模块或一个测试闭环 |
| 50～60 分钟 | 运行测试，记录结果、问题和明天第一步 |

如果当天状态较好，可以继续到 75 分钟，但不自动扩大任务。

### 强制停止规则

达到 60 分钟时先做一次停止判断：

1. 功能已完成：立即提交当天结果，不追加新功能。
2. 功能未完成但代码可运行：写 TODO，明天继续。
3. 测试失败：保存错误信息和最小复现，不临时重写架构。
4. 达到 90 分钟：只允许恢复到可运行状态或补记录。
5. 达到 120 分钟：无条件停止，不继续搜索、不继续重构。

当天没有完成不允许通过第二天加倍时长补偿。计划顺延或砍掉可选项。

## 4. 每天的完成记录模板

每天在开发日志中只写以下内容，控制在 5 分钟内：

```text
Day N
今天交付：
我现在能解释：
测试结果：
仍不理解：
明天打开项目后的第一步：
实际用时：__ 分钟
```

## 5. 第一周：重新建立全局理解

本周目标：能画出系统架构，理解已有业务系统和 Agent Runtime，不急着增加新功能。

### Day 1：建立项目地图

目标：知道每个目录解决什么问题。

- 阅读 `README.md`、`DETAILED_DESIGN.md`。
- 浏览 `frontend/src`、`backend/app`、`agent_service/app` 的目录。
- 手画一张 Browser → Backend → Agent Service → Database 图。
- 运行 `make test`，记录测试数量和警告。

验收：能用两分钟解释为什么业务 Backend 和 Agent Service 分开。

### Day 2：吃透前端到 Backend 的普通请求

目标：理解不含 Agent 的一次数据展示。

- 从球员 Marketplace 页面找到发请求的位置。
- 顺着 URL 找到 Backend router、Pydantic Schema、Repository 和 SQLAlchemy Model。
- 写出“点击页面后数据如何出现”的 8～12 步流程。

验收：能指出分页发生在前端还是数据库，并解释为什么。

### Day 3：吃透登录、角色和租户

目标：区分认证、鉴权与租户隔离。

- 阅读 Backend 的 auth dependencies、User/Tenant/UserSession。
- 跟踪 Cookie Session 如何变成 `current_user`。
- 找一个租户隔离查询和一个角色权限判断。

验收：能解释“已登录”为什么不等于“有权访问所有数据”。

### Day 4：吃透 AgentRunner

目标：自己讲清 Agent Loop。

- 阅读 `runtime/runner.py`、`model_adapter.py`、`tools.py`。
- 画出 Model → Tool → ToolMessage → Model 的循环。
- 对照测试跟踪一次“调用 Tool 后生成报告”的执行。

验收：能解释 step 和 tool call 为什么是两个预算。

### Day 5：吃透类型化 Tool 链路

目标：理解模型如何安全读取业务数据。

- 阅读 `AGENT_TOOLS_BACKEND_API_DESIGN.html`。
- 跟踪 `search_players` 从 Tool Schema 到 Backend 查询的完整路径。
- 写下至少四个安全边界。

验收：能回答“为什么不让模型直接生成 SELECT SQL”。

### Day 6：吃透 Memory 与 Registry

目标：区分三种版本。

- 阅读 `AGENT_MEMORY_REGISTRY_DESIGN.html`。
- 阅读 Memory/Registry 模型和测试。
- 自己解释 `thread.revision`、`summary.version`、`agent_version`。

验收：能解释为什么启用 Agent v2 后旧 Thread 不应自动切换。

### Day 7：第一周复盘，不写新功能

目标：暴露理解断点。

- 不看源码画完整架构图。
- 用录音或口述做一次 5 分钟项目介绍。
- 记录讲不清楚的三个问题。
- 整理下一周实现所需接口，不编码。

验收：产出一页架构图和三个明确问题。

## 6. 第二周：完成 Agent 后端调用闭环

本周目标：实现一个真正可调用的招募分析 API，不做前端。

### Day 8：设计 ConversationService

目标：只定义编排职责和类型接口。

- 写出请求、响应 Schema。
- 明确顺序：验证身份、解析 Thread、加载固定 Agent 版本、构建 Memory、调用 Runner、保存结果。
- 明确失败时哪些内容应该保存。

验收：接口和时序确定，但当天不实现全部逻辑。

### Day 9：实现 ConversationService 骨架

目标：把依赖注入和主要流程搭起来。

- 创建 Service 类。
- 注入 Registry、Memory、ContextBuilder、Runner Factory。
- 暂时使用 Fake Runner 或 Fake Model。

验收：一个 Service 单元测试能够走通无 Tool 的假回答。

### Day 10：接入 Thread 与历史上下文

目标：第二轮问题能够看到第一轮历史。

- 创建或读取 Thread。
- 用 `MemoryContextBuilder` 构建 `history_messages`。
- 将历史传给 `AgentRunner.run()`。

验收：Fake Model 测试断言第二轮收到上一轮消息。

### Day 11：明确消息保存与并发策略

目标：处理 revision，而不是忽略并发。

- 保存用户消息和 Agent 最终回答。
- 发生 revision 冲突时返回明确的 409 或业务错误。
- 不实现静默无限重试。

验收：正常追加和过期 revision 两个测试通过。

### Day 12：接入真实 LangChain 模型

目标：完成最小真实模型调用。

- 在配置中读取模型名和 API Key 环境变量。
- 创建 LangChain Chat Model 和 `LangChainModelAdapter`。
- 用一个极简问题验证结构化输出。

验收：真实调用成功一次；日志和 Git 中没有密钥。

### Day 13：让真实模型调用一个业务 Tool

目标：跑通 Agent Service → Backend → Database。

- 优先使用 `get_squad`，不要一次测试四个 Tool。
- 检查服务密钥、tenant/user Header 和 Backend 权限。
- 保存 Tool 轨迹。

验收：模型读取当前球队阵容并生成合法报告。

### Day 14：增加招募分析 HTTP API

目标：让前端未来只需调用一个稳定入口。

- 新增例如 `POST /recruitment/analyse`。
- 请求包含 question、可选 thread_id、expected_revision。
- 返回 thread_id、revision、结构化报告和受控运行元数据。

验收：HTTPX 集成测试使用 Fake Model 完整通过。

## 7. 第三周：前端入口、滚动摘要和可观测性

本周目标：形成可演示 Web 闭环，同时理解 Memory 与运行轨迹。

### Day 15：设计最小 Agent 前端

目标：先决定页面，不编码复杂 UI。

- 在阵容或 Marketplace 页面选择一个嵌入入口。
- 只设计问题输入、加载状态、错误状态和报告区域。
- 不做通用聊天工作台。

验收：一张简单线框图和前端响应类型。

### Day 16：实现前端 API Client

目标：前端能调用招募分析 API。

- 增加 TypeScript 请求和响应类型。
- 复用现有认证与错误处理方式。
- 使用 Mock 或 Fake API 数据验证。

验收：组件能展示固定的 RecruitmentReport。

### Day 17：实现提问与加载/错误状态

目标：用户能发出问题且不会重复提交。

- 输入问题、提交按钮、loading、错误提示。
- 保存返回的 thread_id 和 revision。
- 不做 Markdown 编辑器或流式输出。

验收：浏览器中完成一次真实请求。

### Day 18：结构化展示推荐结果

目标：报告不是一大段聊天文本。

- 展示 summary、needs、candidates、assumptions、uncertainty。
- Evidence 至少显示 source_type、source_id、description。
- 降级结果有明确提示。

验收：正常、空候选和降级三种状态都能显示。

### Day 19：实现 LangChainSummaryGenerator

目标：为已有滚动摘要机制接入真实模型。

- Summary Prompt 明确要求保留用户约束、已否决候选和未解决问题。
- 设置独立超时和最大摘要长度。
- 使用 Fake Model 测试摘要输入结构。

验收：能够生成并保存 summary v1。

### Day 20：自动触发滚动摘要

目标：长对话不会无限增长。

- 在成功保存一轮消息后检查是否需要摘要。
- 摘要失败不应让已完成的回答失败。
- 记录 summary version 和 summarized-through sequence。

验收：构造长对话后，上下文变成“摘要 + 最近消息”。

### Day 21：记录最小运行观测数据

目标：能够回答 Agent 为什么慢、调用了什么。

- 为每次 Run 保存 run_id、thread_id、agent_version。
- 保存 step_count、tool_call_count、degraded、error_code、总延迟。
- Token 如果模型能返回 usage 就记录，否则允许为空。

验收：完成一次请求后能查询到运行记录。

## 8. 第四周：评测、加固与项目表达

本周目标：少加功能，多做验证、解释和交付。

### Day 22：建立最小评测集

目标：不凭感觉判断 Agent 效果。

- 写 8～10 个固定足球问题。
- 覆盖阵容、战术、伤病、候选筛选和越界问题。
- 为每题标记期望使用的 Tool 和关键事实。

验收：评测数据可以重复运行。

### Day 23：实现规则评测

目标：先用确定性指标，不急着 LLM-as-judge。

- 检查 Tool 选择是否正确。
- 检查报告 Schema、Evidence、候选是否来自 Tool 结果。
- 检查越界问题是否拒答或降级。

验收：输出每条 case 和总体通过率。

### Day 24：做一次失败注入

目标：理解降级机制是否真实有效。

- 分别模拟模型超时、Tool 超时、Backend 403、非法结构化输出。
- 检查 API 状态、degraded 标志、error_code 和前端提示。

验收：至少四类失败行为可预测、可解释。

### Day 25：检查安全与数据边界

目标：证明模型无法越权，而不只是声称安全。

- 测试额外 `sql` 参数被拒绝。
- 测试错误 tenant/user 组合。
- 测试未注册 Tool 和未授权 Tool。
- 检查日志不打印服务密钥和数据库 URL。

验收：相关安全测试全部通过。

### Day 26：检查数据库与迁移

目标：能独立解释并重建数据结构。

- 查看业务 DB 和 Agent DB 的 Alembic current。
- 从空测试数据库执行迁移。
- 画出 Agent Definition、Thread、Message、Summary、Run 的关系。

验收：能够解释为什么 Agent 数据不和业务数据混在一个数据库。

### Day 27：整理代码，不扩大架构

目标：消除影响理解的明显问题。

- 删除死代码和重复命名。
- 补关键模块 docstring 和少量中文注释。
- 检查配置、异常名称和目录职责是否一致。

验收：`make test` 和前端 build 通过；不做无关重写。

### Day 28：完成项目运行文档

目标：陌生人可以按文档启动项目。

- 更新依赖安装、环境变量、两个数据库迁移和三个服务启动方法。
- 增加一个完整 Agent 演示请求。
- 写清当前限制，不宣称未实现功能。

验收：根据 README 从启动到演示不需要猜步骤。

### Day 29：准备项目讲解与面试问答

目标：把“写过”转换成“讲得清”。

- 准备 30 秒、2 分钟和 8 分钟三个版本的介绍。
- 回答为什么选 LangChain、为什么自定义 Runner、为什么分离 Agent Service。
- 回答 Tool 安全、Memory 一致性、版本注册和观测设计。

验收：不看源码完成一次 8 分钟录音讲解。

### Day 30：完整验收与冻结范围

目标：形成一个稳定可演示版本。

- 从登录开始演示阵容、战术、事件、Marketplace 和 Agent 分析。
- 运行 Backend 测试、Agent 测试和前端 build。
- 运行最小评测集并保存结果。
- 标记已完成、已知限制和下一阶段候选任务。

验收：完成最终演示；当天不再添加功能。

## 9. 每周里程碑

| 时间 | 必须得到的结果 |
|---|---|
| Day 7 | 能完整画图并解释现有系统 |
| Day 14 | 后端 Agent 分析 API 闭环跑通 |
| Day 21 | Web 可提问，Memory 与基础观测可用 |
| Day 30 | 测试、评测、文档、演示和项目表达完成 |

如果某周延期，优先保留顺序是：

```text
可运行闭环
  > 租户与 Tool 安全
  > 测试和错误降级
  > Memory
  > 观测与规则评测
  > RAG
  > UI 美化
```

## 10. 最终验收清单

### 产品闭环

- [ ] 用户可以从 Web 发起一个足球招募问题。
- [ ] Agent 能读取当前租户阵容、战术、伤病并筛选外部球员。
- [ ] 页面展示结构化报告、依据、假设和不确定性。
- [ ] 第二轮问题能够使用第一轮上下文。

### 工程能力

- [ ] Backend 是权限与业务数据的可信执行边界。
- [ ] 模型不能提交 SQL、租户 ID 或任意 Tool 参数。
- [ ] Agent 有步骤、Tool 次数、模型超时和 Tool 超时限制。
- [ ] Thread revision 冲突不会被静默覆盖。
- [ ] Agent Definition 支持版本注册、启用、禁用和发现。
- [ ] 至少记录运行延迟、Tool 轨迹和降级原因。

### 质量与表达

- [ ] Backend、Agent Service 测试和前端 build 全部通过。
- [ ] 至少 8 条固定评测 case 可以重复运行。
- [ ] README 能让其他人启动并演示项目。
- [ ] 能完成 8 分钟项目讲解并回答关键设计取舍。

## 11. 可选项进入条件

只有以下条件全部满足，才允许加入最小 pgvector RAG：

- Day 21 之前已经跑通 Web Agent 闭环。
- 多轮 Memory、租户隔离和错误降级已有测试。
- 每天实际用时没有超过 120 分钟。
- RAG 只增加一个 `search_football_knowledge` Tool 和少量文档。

否则把 RAG 放到下一个月。完成一个边界清楚、能够解释和验证的 Agent 系统，比堆叠更多名词更重要。
