# FCRecruiter

> 把足球经理类游戏中“看阵容、定需求、找球员、做判断”的漫长过程，变成一个可解释的招募决策闭环。

FCRecruiter 是一个面向足球游戏玩家和普通球迷的智能阵容分析与引援辅助 Web 应用。它不是替玩家自动买人的 AI，也不是套着足球外壳的通用聊天机器人；它首先是一个可以浏览球员、管理球队上下文和查看候选人的 Player Marketplace，Agent 则作为分析层嵌入招募流程。

项目当前使用 FC26 球员数据构建可运行原型，重点验证一个产品假设：如果系统能够把阵容、战术、伤病和球员数据组合成可解释的补强建议，玩家是否能更快地形成合理的候选范围，同时保留足球经理游戏最重要的乐趣——自己做决定。

## 为什么做这个项目

足球经理类游戏的转会市场很有吸引力，因为玩家需要像真实的足球管理者一样观察阵容、定义需求、搜集信息并承担选择结果。但随着球员数量和属性维度增加，乐趣也很容易变成重复劳动。

一次看似简单的“找个新中场”，通常包含一连串隐性任务：

1. 判断球队真正缺少的是人数、即战力，还是某种战术能力；
2. 把模糊需求转换成位置、年龄、能力、潜力和预算条件；
3. 在大量球员页面之间反复切换和比较；
4. 判断某个高评分球员是否真的适合当前阵型和打法；
5. 在阵容深度、伤病、成长空间和短期成绩之间权衡。

游戏提供了丰富数据，但数据本身不会自动变成结论。尤其对不熟悉战术和数据分析的玩家而言，真正困难的不是“找不到球员”，而是无法快速回答：

- 我的阵容究竟哪里有问题？
- 转会窗口应该优先补强哪个位置？
- 我应该搜索什么类型的球员？
- 这名球员为什么适合，风险又在哪里？
- AI 的建议依据了什么，我能不能相信？

FCRecruiter 希望减少这部分信息整理成本，而不是跳过选择过程。

## 它与足球经理类游戏有什么关系

FCRecruiter 借鉴了 Football Manager、EA Sports FC 生涯模式等游戏中的俱乐部管理循环，并将其中最耗时的招募环节重新组织为一条更短、更清晰的工作流。

| 足球经理类游戏中的玩法 | FCRecruiter 中的对应体验 |
| --- | --- |
| 查看一线队与位置深度 | Squad 页面汇总当前球队阵容 |
| 设置阵型、风格和球员职责 | Tactics 页面保存阵型、打法与战术备注 |
| 查看伤病、训练和更衣室动态 | Events 页面记录影响招募判断的球队事件 |
| 使用球探中心或球员搜索器 | Marketplace 搜索、筛选和分页浏览球员 |
| 召开招募会议、确定补强方向 | Agent 综合球队上下文生成阵容诊断和补强建议 |
| 阅读球探报告 | 球员详情页生成优势、风险和战术适配分析 |
| 比较候选并决定是否继续考察 | 用户检查 Evidence 后自行决定下一步 |

两者的关系是“玩法抽象与辅助”，不是存档插件或游戏修改器：

- 当前版本不会读取或修改 Football Manager、EA Sports FC 等游戏存档；
- 不模拟比赛、谈判、报价、合同或转会执行；
- 不声称预测真实转会成功率；
- 项目使用独立数据模型，未来可以接入其他合法的足球数据源；
- 所有商标归各自权利人所有，本项目与相关游戏厂商不存在官方关联。

## 玩家痛点与产品回应

| 玩家痛点 | 常见后果 | FCRecruiter 的设计回应 |
| --- | --- | --- |
| 知道球队“不太对”，但说不清问题 | 凭印象买人，忽略位置深度和伤病 | 汇总阵容、战术和事件，生成结构化阵容诊断 |
| 球员太多、属性太多 | 反复翻页，筛选条件频繁试错 | 把补强方向转成可执行的市场筛选条件 |
| 难以把孤立属性映射为战术作用 | 只看总评或潜力，买到不适配的球员 | 对比候选、现有阵容与战术，解释具体作用和风险 |
| 推荐只给结论，不给理由 | 玩家无法核验，也难以建立信任 | 展示数据 Evidence、知识来源、假设和不确定性 |
| AI 工具需要写 Prompt、配置工具 | 分析门槛比游戏本身还高 | 在“生成补强建议”和“招募分析”等节点直接触发 |
| AI 不稳定或服务暂时不可用 | 整个产品无法继续使用 | Marketplace、阵容和详情等基础体验不依赖模型 |

## 核心体验

```mermaid
flowchart LR
    A[准备进入转会窗口] --> B[查看阵容、战术与伤病]
    B --> C[进入球员市场]
    C --> D[生成球队补强建议]
    D --> E[查看诊断、筛选条件与 Evidence]
    E --> F[确认或调整筛选条件]
    F --> G[浏览确定性候选列表]
    G --> H[打开感兴趣的球员]
    H --> I[生成单球员适配分析]
    I --> J{玩家作出决定}
    J -->|继续考察| G
    J -->|暂不考虑| C
```

这条流程的终点不是“AI 给出唯一答案”，而是玩家得到一个有依据、可调整的候选决策。

### 场景一：我应该先补强哪里？

玩家准备进入转会窗口，但还没有明确目标。系统读取当前阵容、阵型、打法、伤病以及俱乐部知识，先用确定性逻辑统计位置深度和候选约束，再由 Agent 解释：

- 当前阵容最明显的结构问题；
- 应该优先补强的位置与原因；
- 适合转化为搜索条件的年龄、能力和位置要求；
- 结论依赖的事实、假设以及缺失信息。

玩家可以接受、修改或完全忽略这些条件，然后继续使用普通 Marketplace。

### 场景二：这名球员适合我的球队吗？

玩家已经发现一名候选球员，希望判断是否值得继续考察。系统会把候选人与同位置队友、当前战术和球队事件放在一起分析，而不是简单复述球员属性或给出一个虚假的精确分数。

结果重点回答：他能解决什么问题、可能扮演什么角色、相对现有球员有什么变化、主要风险是什么，以及当前数据还不能证明什么。

## 设计思路

### 1. Marketplace first，Agent embedded

玩家首先看到的是熟悉的球员市场和俱乐部管理界面，而不是一个空白聊天框。AI 只出现在需要综合判断的节点，不要求用户学习 Prompt，也不会处理与足球招募无关的开放式任务。

### 2. 确定性代码与 AI 明确分工

| 交给普通代码 | 交给 AI |
| --- | --- |
| 登录、权限和租户隔离 | 汇总多类球队上下文 |
| 搜索、筛选、排序和分页 | 解释阵容结构问题 |
| 数值计算和能力等级换算 | 归纳补强需求 |
| 候选存在性与硬条件校验 | 说明候选与战术的关系 |
| 工具参数、调用次数和超时限制 | 用玩家能理解的语言解释风险与取舍 |

模型输出始终被当作不可信输入：结构化结果必须经过校验，失败时返回可识别的降级结果，不能影响普通球员浏览。

### 3. Evidence，而不是“AI 说了算”

招募建议应该暴露它使用的球员数据、球队上下文和知识片段，同时区分已知事实、模型推断、关键假设和信息缺口。产品追求的是可解释判断，不是把主观建议包装成精确概率。

### 4. 人保留最终决定权

Agent 可以帮助缩小范围和解释取舍，但不会自动签约、出售球员或调整阵容。玩家可以修改筛选条件、忽略建议，也可以在 AI 不可用时继续手动完成整个搜索流程。

### 5. 面向多数据源，而不是绑定 FC 数据

FC26 CSV 是当前原型的数据起点，不是产品领域模型的永久边界。球员、球队、联赛和事件等核心概念保持相对独立，未来可以在遵守授权和数据协议的前提下适配其他足球数据提供方。

## 当前状态

FCRecruiter 目前是一个可运行的产品与技术原型，已经打通以下核心路径：

- 多租户登录、角色权限和球队隔离；
- 球员 Marketplace、搜索、筛选、分页和详情；
- 当前阵容、战术和球队事件管理；
- 球队补强建议与单球员招募适配分析；
- 租户足球知识库与 pgvector 检索；
- Agent Memory、运行轨迹、基础评测和异常降级。

仍需要通过后续迭代和用户测试验证或补齐：

- 建议筛选条件完整落地，而不只是应用部分字段；
- shortlist 和 2～3 名候选球员的并排比较；
- 更清晰的 Evidence 展示和用户反馈入口；
- 招募建议是否确实减少了玩家形成候选范围的时间；
- Docker 化部署、持续集成和生产环境运维配置。

## 演示区

> 演示素材待补充。没有在线 Demo 时，这里将用于展示完整的玩家操作路径。

<!--
建议依次加入：
1. 从阵容与战术进入 Marketplace 的截图；
2. 生成球队补强建议并应用筛选条件的 GIF；
3. 打开球员详情并生成适配分析的 GIF；
4. 展开 Evidence、假设与不确定性的截图；
5. 2～3 分钟本地演示视频和演示账号说明。
-->

## 本地运行

### 前置依赖

| 依赖 | 建议版本 | 用途 |
| --- | --- | --- |
| Python | 3.11+，推荐 3.12 | Backend、Agent Service 和数据脚本 |
| Node.js / npm | Node.js 20+、npm 10+ | React 前端 |
| PostgreSQL | 15+ | 业务数据库和 Agent 数据库 |
| pgvector | 与 PostgreSQL 匹配 | Agent 知识向量检索 |
| Ollama + `bge-m3` | 默认 Embedding 方案需要 | 生成 1024 维知识向量 |
| DeepSeek API Key | 招募分析需要 | 生成结构化分析报告 |
| GNU Make | 4.x | 统一开发命令 |

PostgreSQL 还需要支持 `unaccent` 扩展。建议分别创建 `fc26` 业务数据库和 `fc26_agent` Agent 数据库。

### 环境变量

在项目根目录创建 `.env`，不要提交真实密码、共享密钥或 API Key：

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fc26
AGENT_DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fc26_agent

FRONTEND_ORIGIN=http://localhost:5173
AGENT_SERVICE_URL=http://127.0.0.1:8001
BUSINESS_BACKEND_URL=http://127.0.0.1:8000/api
AGENT_SERVICE_TOKEN=replace_with_a_long_random_value

DEEPSEEK_API_KEY=replace_with_your_api_key
DEEPSEEK_MODEL=deepseek-chat

EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSIONS=1024
```

### 首次初始化

```bash
# 安装 Python 与前端依赖
make setup

# 拉取默认 Embedding 模型
ollama pull bge-m3

# 首次导入 FC26 基础数据。该命令会重建四张基础数据表，不要在生产数据上重复执行
PYTHONPATH=backend .venv/bin/python scripts/normalize_players.py --apply

# 启用数据库扩展并执行两套迁移
make setup-db
make migrate-agent

# 创建第一个俱乐部和经理账号；执行时会询问初始密码
make tenant ARGS='create --name Arsenal --slug arsenal --club-id 11 --manager-username manager'
```

### 一键启动开发环境

确保 PostgreSQL 和 Ollama 已运行，然后执行：

```bash
make dev
```

| 服务 | 地址 |
| --- | --- |
| Web App | <http://localhost:5173> |
| Backend API Docs | <http://localhost:8000/docs> |
| Agent Service API Docs | <http://localhost:8001/docs> |

测试与前端生产构建：

```bash
make test
make build
```

> 当前仓库尚未加入 Docker/Compose 配置，因此暂时没有可用的 `docker compose up` 命令。

## 技术实现概览

技术实现服务于上面的产品边界：React + TypeScript 提供 Marketplace 与俱乐部工作流；FastAPI Backend 负责业务数据、权限和确定性规则；独立 Agent Service 使用 LangChain Tool Calling、Pydantic 结构化校验和 pgvector 知识检索生成招募解释。

Agent 不直接连接业务数据库，也不能生成并执行 SQL。它只能通过经过鉴权和租户隔离的内部 API 获取完成当前任务所需的数据。

主要技术栈：`React / TypeScript / FastAPI / PostgreSQL / pgvector / LangChain / Pydantic / Ollama / DeepSeek`

更完整的产品和技术说明：

- [用户场景与产品需求分析](design/PRODUCT_DISCOVERY.md)
- [MVP 产品规划](design/MVP_PRODUCT_PLAN.md)
- [详细设计](design/DETAILED_DESIGN.md)
- [项目简介](design/PROJECT_INTRODUCTION.md)

## FAQ

### 这是 Football Manager 或 EA Sports FC 的插件吗？

不是。FCRecruiter 借鉴足球经理类游戏的招募玩法，但当前不会读取或修改任何游戏存档，也不与相关厂商存在官方关系。

### Agent 会替玩家决定买谁吗？

不会。Agent 负责整理上下文、解释适配性和提示风险；筛选条件可以修改，建议可以忽略，最终决定始终由玩家完成。

### 为什么不直接给每名球员一个“适配分”？

单一分数容易隐藏战术前提、阵容差异和数据缺口，也会制造不必要的精确感。FCRecruiter 更关注球员能解决什么问题、存在哪些取舍，以及结论基于哪些 Evidence。

### AI 不可用时还能使用吗？

可以。登录、球员浏览、搜索、筛选、阵容和详情等核心功能由普通代码提供。模型或 Embedding 服务异常只会影响分析能力，不应阻断 Marketplace。

### 为什么使用两个数据库？

业务数据库保存球员、球队、租户、用户、事件和战术；Agent 数据库保存对话、知识向量、运行轨迹和评测结果。分开存储可以避免 AI 实验和迁移影响核心业务数据。

### 首次迁移为什么提示 `clubs` 或 `players` 不存在？

当前 Backend 迁移依赖已经导入的 FC26 基础表。首次初始化必须先运行：

```bash
PYTHONPATH=backend .venv/bin/python scripts/normalize_players.py --apply
```

然后再执行 `make setup-db`。该导入命令会重建基础表，不应在已有生产数据的环境中随意重复执行。

### 为什么知识检索提示 `vector` 不存在或返回 503？

确认 PostgreSQL 已安装服务端 pgvector 扩展、`make migrate-agent` 已成功完成、Ollama 正在运行且已经拉取 `bge-m3`。Python 的 `pgvector` 包不能替代 PostgreSQL 服务端扩展。
