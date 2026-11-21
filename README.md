# FCRecruiter

面向足球俱乐部的 **Player Marketplace + Embedded Recruitment Agent**。

## 项目简介

FCRecruiter 将球员市场与招募决策支持放在同一个工作流中。用户可以浏览、搜索和筛选球员，查看球队阵容与战术，并在关键决策点请求 Recruitment Agent 生成带有证据、假设、不确定性和权衡说明的招募报告。

项目遵循以下边界：

- Backend 负责筛选、排序、权限、租户隔离和工作流状态等确定性逻辑；
- Agent Service 负责解释、综合分析和推荐辅助，不替代用户做最终决定；
- Agent 只能通过受控的 Backend API 读取业务数据，不能绕过权限直接访问业务数据库；
- 业务数据与 Agent 的对话、知识向量和运行记录分别存储，便于独立演进。

当前主要能力包括：

- 球员 Marketplace、搜索、筛选、分页和详情；
- 阵容、球队事件与战术管理；
- 多租户账号、角色权限和服务端 Session；
- 基于 LangChain + DeepSeek 的结构化招募分析；
- 基于 Ollama `bge-m3` + pgvector 的足球知识检索；
- Agent Memory、版本注册、运行观测与离线评测。

## 架构图

```mermaid
flowchart LR
    User[俱乐部用户] -->|浏览器| Frontend[React + TypeScript<br/>Vite Frontend]
    Frontend -->|/api<br/>Session + CSRF| Backend[FastAPI Backend<br/>确定性业务逻辑]

    Backend -->|SQLAlchemy| BusinessDB[(PostgreSQL<br/>业务数据库)]
    Backend -->|受控的招募请求| Agent[FastAPI Agent Service<br/>解释与推荐辅助]
    Agent -->|内部只读工具 API<br/>Tenant + User Context| Backend

    Agent -->|Memory / Knowledge / Runs| AgentDB[(PostgreSQL + pgvector<br/>Agent 数据库)]
    Agent -->|Chat Completion| DeepSeek[DeepSeek API]
    Agent -->|Embedding| Ollama[Ollama<br/>bge-m3]
```

Backend 与 Agent Service 使用同一个 `AGENT_SERVICE_TOKEN` 进行服务间认证。Agent 调用 Backend 时会携带租户和用户上下文，由 Backend 重新验证身份与权限。

## 前置依赖清单

### 必需依赖

| 依赖 | 建议版本 | 用途 |
| --- | --- | --- |
| Git | 2.x | 获取和管理代码 |
| Python | 3.11+，推荐 3.12 | Backend、Agent Service、脚本和迁移 |
| Node.js | 20+ | 构建和运行 React 前端 |
| npm | 10+ | 安装前端依赖 |
| PostgreSQL | 15+ | 业务数据库和 Agent 数据库 |
| pgvector | 与 PostgreSQL 版本匹配 | Agent 知识向量存储与相似度检索 |
| GNU Make | 4.x | 执行项目统一命令 |

PostgreSQL 服务器必须能安装以下扩展：

- `unaccent`：球员姓名模糊搜索；
- `vector`：Agent 知识向量存储与检索。

建议创建两个独立数据库，避免业务迁移与 Agent 迁移互相影响：

```sql
CREATE DATABASE fc26;
CREATE DATABASE fc26_agent;
```

### Agent 功能依赖

完整使用 Recruitment Agent 还需要：

| 依赖 | 是否必需 | 用途 |
| --- | --- | --- |
| DeepSeek API Key | 招募分析必需 | 生成结构化 Recruitment Report |
| Ollama | 默认 Embedding 方案必需 | 在本机运行向量模型 |
| `bge-m3` 模型 | 默认配置必需 | 生成 1024 维知识向量 |

安装 Ollama 后拉取默认模型：

```bash
ollama pull bge-m3
```

如果改用兼容 HTTP API 的 Embedding Provider，可以不运行 Ollama，但需要同步配置 Provider、模型名称和向量维度。

### 环境变量

在项目根目录创建 `.env`。下面只展示变量名和本地开发示例；不要提交真实密码、共享密钥或 API Key。

```dotenv
# Backend
APP_ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fc26
FRONTEND_ORIGIN=http://localhost:5173
SESSION_COOKIE_NAME=recruitment_session
SESSION_LIFETIME_HOURS=24
COOKIE_SECURE=false

# Backend <-> Agent Service
AGENT_SERVICE_URL=http://127.0.0.1:8001
BUSINESS_BACKEND_URL=http://127.0.0.1:8000/api
AGENT_SERVICE_TOKEN=replace_with_a_long_random_value

# Agent database
AGENT_ENVIRONMENT=development
AGENT_DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fc26_agent

# Recruitment model
DEEPSEEK_API_KEY=replace_with_your_api_key
DEEPSEEK_MODEL=deepseek-chat

# Default embedding provider
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSIONS=1024
```

可以用下面的命令生成服务间共享密钥：

```bash
openssl rand -hex 32
```

生产环境必须将 `FRONTEND_ORIGIN` 设置为真实站点地址，并在 HTTPS 下设置 `COOKIE_SECURE=true`。如果使用 Docker，服务之间的 URL 需要改为 Compose 服务名，不能使用 `localhost`。

## 一键启动步骤

### 1. 首次初始化

安装 Python 与前端依赖：

```bash
make setup
```

确认两个 PostgreSQL 数据库已经创建且 `.env` 已填写，然后导入仓库自带的 FC26 数据。该命令会重建业务库中的 `countries`、`leagues`、`clubs` 和 `players` 表，只应在初始化或明确需要重新导入数据时执行：

```bash
PYTHONPATH=backend .venv/bin/python scripts/normalize_players.py --apply
```

启用 `unaccent` 并执行 Backend 迁移：

```bash
make setup-db
```

执行 Agent Service 迁移；迁移会在 Agent 数据库中启用 `vector` 扩展：

```bash
make migrate-agent
```

创建第一个俱乐部租户和经理账号。以下示例使用 `club-id=11`，命令执行时会交互式询问初始密码：

```bash
make tenant ARGS='create --name Arsenal --slug arsenal --club-id 11 --manager-username manager'
```

### 2. 日常一键启动

确保 PostgreSQL 和 Ollama 已运行，然后在项目根目录执行：

```bash
make dev
```

服务地址：

| 服务 | 地址 |
| --- | --- |
| Web App | <http://localhost:5173> |
| Backend API Docs | <http://localhost:8000/docs> |
| Agent Service API Docs | <http://localhost:8001/docs> |
| Backend Health | <http://localhost:8000/api/health> |
| Agent Health | <http://localhost:8001/health> |

停止服务时按 `Ctrl+C`。运行测试和前端生产构建：

```bash
make test
make build
```

> Docker/Compose 部署配置尚未加入当前仓库，因此目前没有可用的 `docker compose up` 命令。加入容器配置后，应在这里补充真正的从零一键部署入口。

## 演示区

> 待补充：这是没有在线 Demo 时最重要的展示区域。

<!--
建议后续至少加入以下内容：
1. Marketplace 搜索与筛选 GIF；
2. 球员详情和招募分析 GIF；
3. 阵容、战术与证据链截图；
4. 2～3 分钟本地演示视频链接；
5. 演示账号、演示数据和重置方式说明。
-->

## FAQ

### 为什么需要两个数据库？

业务数据库保存球员、球队、租户、用户、事件和战术；Agent 数据库保存对话、摘要、知识向量、运行轨迹和评测结果。两者生命周期不同，分开存储可以避免 AI 实验或迁移影响核心业务数据，也可以避免两套 Alembic 版本表发生冲突。

### 为什么 `make migrate` 报 `clubs` 或 `players` 表不存在？

当前 Backend 迁移以已经导入的 FC26 基础表为前提。首次初始化时必须先运行：

```bash
PYTHONPATH=backend .venv/bin/python scripts/normalize_players.py --apply
```

然后再运行 `make setup-db`。不要在已有业务数据的环境里盲目重复执行导入命令，因为它会重建四张基础数据表。

### 为什么 Agent 数据库迁移提示 `type "vector" does not exist`？

这表示 PostgreSQL 服务器没有安装 pgvector，或者当前数据库用户没有创建扩展的权限。先安装与 PostgreSQL 版本匹配的 pgvector，再重新执行：

```bash
make migrate-agent
```

Python 的 `pgvector` 包不能替代 PostgreSQL 服务端扩展。

### 为什么招募分析返回 503？

依次检查：

1. Agent Service 的 `/health` 是否可访问；
2. Backend 与 Agent 是否配置了完全相同的 `AGENT_SERVICE_TOKEN`；
3. `DEEPSEEK_API_KEY` 是否存在且有效；
4. `BUSINESS_BACKEND_URL` 和 `AGENT_SERVICE_URL` 是否指向正确地址；
5. Agent 数据库迁移是否完成。

### 为什么知识检索或导入返回 503？

默认配置依赖 Ollama。确认 Ollama 正在运行，并检查模型是否存在：

```bash
ollama list
```

列表中应包含 `bge-m3`，且 `OLLAMA_BASE_URL` 应能从 Agent Service 所在环境访问。

### 为什么前端能打开，但 API 请求失败？

本地开发时，Vite 会把 `/api` 代理到 `http://localhost:8000`。请确认 Backend 已在 8000 端口运行。跨域部署时还要检查 `FRONTEND_ORIGIN` 是否与浏览器实际访问的协议、域名和端口完全一致。

### 可以把 `.env` 提交到 Git 吗？

不可以。仓库已经忽略 `.env`，真实数据库密码、模型 API Key 和服务间共享密钥只能通过本地环境、部署平台 Secret 或专用密钥管理服务提供。
