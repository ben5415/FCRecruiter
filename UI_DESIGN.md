# UI Design — Football Recruitment Agent MVP

## 0. 产品前提

本 Web 应用当前只服务一家俱乐部。未来可以扩展为多俱乐部、多租户系统，但 MVP 不实现。

系统未来可以包含经理、教练、球探、队医等不同职责账号；当前只实现一个经理账号。经理可以查看球队状态、提交或查看球队事件、分析阵容，并完成球员招募相关工作。

应用的长期方向是基于球队管理系统构建球队 Agent；当前版本只实现 Recruitment Agent。球员管理、职员管理、训练、医疗、预算和更衣室等模块只保留支撑引援分析所需的最小信息。

核心原则：

> AI 负责记录、整理、检索、分析和归纳，不负责替负责人做最终决定或评价。

AI 可以指出数据中的问题、候选人的特点、约束冲突和信息缺口，但最终引援优先级、候选人评价和 shortlist 决策由经理完成。

## 1. MVP 导航结构

```text
Login
  ↓
App Shell
  ├── Home / 球队主页
  ├── Squad / 阵容
  ├── Recruitment / 招募
  └── Shortlist / 候选名单
```

桌面端使用左侧导航栏；移动端可以折叠为顶部菜单。页面右上角显示当前账号和退出按钮。

推荐路由：

```text
/login
/
/squad
/recruitment
/shortlist
/players/:playerId
/recruitment/runs/:runId
```

## 2. 登录界面

### 功能

- 用户名或邮箱输入框。
- 密码输入框。
- 登录按钮。
- 登录中、登录失败和 Session 过期提示。

### 布局

```text
┌──────────────────────────────────────┐
│       Football Recruitment Hub       │
│                                      │
│  Username / Email                    │
│  [_______________________________]   │
│                                      │
│  Password                            │
│  [_______________________________]   │
│                                      │
│  [ Sign in ]                         │
└──────────────────────────────────────┘
```

MVP 不实现注册、忘记密码、邮箱验证和第三方登录。

## 3. 球队主页

主页回答两个问题：球队现在是什么状态，以及最近发生了什么。

### 3.1 球队现状

显示一份由 AI 整理的简短球队状态报告。报告可以综合：

- 当前阵容和阵型。
- 位置深度。
- 伤病事件。
- 训练事件。
- 更衣室事件。
- 最近由经理确认的招募重点。

报告旁显示：

- 上次更新时间。
- 使用了哪些类型的数据。
- 缺失或过期的数据提示。
- `更新报告` 按钮。
- `基于现状开始招募分析` 按钮。

报告是结构化事件和球队数据生成的结果快照，不作为球队状态的唯一数据源。即使内部生成 Markdown，也应保存对应时间、来源和版本。

### 3.2 球队事件

以时间线显示最近事件：

```text
Today      Main striker injured — estimated 3 weeks
Yesterday  High-intensity defensive training completed
3 days ago Dressing-room morale reported as stable
```

事件类型预留：

- `training`
- `medical`
- `dressing_room`
- `match`
- `recruitment`

当前版本可以使用预置或简单表单录入的事件，不实现完整训练、医疗和更衣室子系统。

### 页面草图

```text
┌────────────┬───────────────────────────────────────────┐
│ Home       │ Team Overview                Manager ▾    │
│ Squad      ├───────────────────────────────────────────┤
│ Recruitment│ Current Team Status        Updated 10:30 │
│ Shortlist  │                                           │
│            │ [AI 整理的简短状态报告]                  │
│            │                                           │
│            │ [Update] [Start Recruitment Analysis]     │
│            ├───────────────────────────────────────────┤
│            │ Recent Events                             │
│            │ ○ Medical event                           │
│            │ ○ Training event                          │
│            │ ○ Recruitment event                       │
└────────────┴───────────────────────────────────────────┘
```

## 4. 阵容界面

阵容页面用于理解现有人员，而不是管理全部球员事务。

### 4.1 阵型视图

- 显示当前使用阵型。
- 在球场图上显示首发球员。
- 点击球员打开简要信息面板。
- 显示每个位置的主要替补人数。
- 允许在预置阵型之间切换以进行简单推演。

MVP 可以只支持：

- 4-3-3
- 4-2-3-1

### 4.2 阵容列表

显示：

- 球员姓名。
- 年龄。
- 主要位置。
- Overall / Potential。
- 当前阵容角色。
- 简单状态信息。

支持按位置分组，不需要实现复杂的数据表自定义功能。

### 4.3 Agent 分析入口

页面提供有限的快捷问题：

- `当前阵容有什么问题？`
- `哪个位置的阵容深度最差？`
- `如果改踢 4-3-3，需要补强什么位置？`

分析结果显示为报告卡片：

```text
Finding
Defensive midfield depth is limited.

Evidence
- 1 natural defensive midfielder
- Backup role-fit score: 54/100
- Starter-to-backup overall gap: 11

Limitations
- Injury and form data are not available

[Create Recruitment Brief]
```

## 5. 招募界面

招募界面是 MVP 的核心页面，同时支持手动筛选和自然语言分析。

### 5.1 页面结构

```text
┌────────────┬───────────────────────────────────────────┐
│ Filters    │ Recruitment Assistant                     │
│            │ [描述你需要寻找的球员……             ][→]│
│ Position   │ Suggestions:                              │
│ Age        │ · 找一个年轻的拖后组织核心               │
│ Value      │ · 根据当前阵容建议优先补强位置             │
│ Wage       ├───────────────────────────────────────────┤
│ League     │ Parsed Recruitment Brief                  │
│ Foot       │ [结构化、可编辑的筛选条件]                │
│ Role       │ [Confirm and Search]                      │
│            ├───────────────────────────────────────────┤
│            │ Player Card  Player Card  Player Card     │
│            │ Player Card  Player Card  Player Card     │
└────────────┴───────────────────────────────────────────┘
```

### 5.2 手动筛选

MVP 筛选条件：

- 姓名。
- 位置。
- 年龄范围。
- 身价上限。
- 工资上限。
- 俱乐部。
- 联赛。
- 惯用脚。
- Overall / Potential。
- 球员角色。

筛选、排序和分页由确定性代码执行，不交给 LLM。

### 5.3 自然语言输入

输入框不是开放式通用聊天入口，其提示文案为：

> 描述你的阵容问题或需要寻找的球员。

示例：

> 找一个 24 岁以下、4000 万以内、适合拖后组织核心的后腰。

系统处理流程：

```text
自然语言输入
  → 足球领域和意图检查
  → 生成结构化 Recruitment Brief
  → 用户确认或修改条件
  → 执行球员搜索和角色评分
  → 生成带证据的结果说明
```

系统必须先展示结构化条件，不允许模型直接绕过条件生成候选人。

### 5.4 Recruitment Brief

展示并允许编辑：

- 目标位置。
- 目标角色。
- 年龄范围。
- 转会费和工资限制。
- 硬约束。
- 软偏好。
- 是否结合当前阵容分析。

硬约束与软偏好必须使用不同视觉样式。

### 5.5 球员卡片

每张卡只显示最重要的信息：

- 头像、姓名和年龄。
- 俱乐部、联赛和位置。
- Overall / Potential。
- 身价和工资。
- Role Fit 分数。
- 2–3 个主要优势。
- 数据不足或主要风险提示。
- `查看详情`、`比较`、`加入 Shortlist`。

Role Fit 必须显示为派生评分，不能伪装成原始数据库字段。

## 6. 球员详情

详情页分为：

- Overview。
- Technical。
- Mental。
- Physical。
- Position Ratings。
- Contract。
- Recruitment Analysis。

Recruitment Analysis 显示：

- 与当前 Recruitment Brief 的适配情况。
- 满足和未满足的条件。
- 主要优势。
- 风险和数据缺口。
- 引用的球员数据和知识来源。

AI 解释与原始事实使用不同样式，避免把模型判断当成数据库事实。

## 7. Shortlist 界面

显示经理主动加入的候选球员。

支持：

- 查看候选人。
- 删除候选人。
- 添加经理备注。
- 选择 2–3 人进行比较。
- 发起一次 shortlist 分析。

Shortlist 分析可以整理：

- 候选人角色是否重复。
- 各候选人主要差异。
- 是否违反已确认的预算或年龄条件。
- 当前数据中仍缺少什么。

AI 不自动删除、排序或批准候选人；如提供排序，必须展示排序依据并允许经理忽略。

## 8. Agent 执行过程

普通用户不需要看到内部思维链。界面只展示可审计、可理解的执行摘要：

```text
✓ Parsed recruitment request
✓ Loaded current squad
✓ Analysed position depth
✓ Retrieved role knowledge
✓ Searched 18,405 players
✓ Reviewed 8 candidates
```

点击展开后可以看到：

- 计划摘要。
- 工具名称。
- 工具参数摘要。
- 数据来源。
- 执行耗时。
- 错误或 fallback。
- Critic 检查结果。

不显示隐藏的 chain-of-thought 或模型内部推理文本。

## 9. 通用页面状态

所有主要页面都需要设计：

- Loading。
- Empty。
- Error。
- Partial data。
- Agent timeout。
- Model unavailable。
- No matching players。

当模型不可用时，手动筛选、数据库查询、确定性评分和阵容基础分析仍然可用。

## 10. MVP 视觉原则

- 使用专业足球管理界面的信息密度，不模仿通用聊天应用。
- 关键结论必须同时展示证据和限制。
- 原始事实、派生评分和 AI 解释使用不同标签。
- 高风险不只依靠红绿颜色，还要有文字和图标。
- 首先适配桌面端；保证平板可用，手机端只要求基础浏览。
- 动画和复杂图表不是 MVP 必需项。

建议标签：

```text
[DATA]       原始数据
[CALCULATED] 确定性计算
[AI INSIGHT] AI 整理或解释
[LIMITATION] 数据限制
```

## 11. 当前版本不实现

- 多俱乐部租户。
- 教练、球探和队医的完整独立界面。
- 完整训练、医疗、更衣室和比赛管理。
- 自动转会、报价或合同谈判。
- 通用聊天助手。
- 动态 Skill 或插件界面。
- MCP 管理界面。
- 通用 Agent Workflow Designer。
- 无限 Planning、Reflection 或 Agent 自主执行。

## 12. MVP 验收流程

```text
经理登录
→ 查看球队现状
→ 打开阵容并发起问题分析
→ 系统识别一个阵容缺口
→ 经理创建并确认 Recruitment Brief
→ 系统搜索并展示候选球员
→ 经理查看推荐证据和限制
→ 经理将球员加入 Shortlist
→ 比较候选人并自行做出决定
```

完成标准：上述流程可以在一个浏览器 Session 中完整演示；模型失败时，系统仍可完成手动筛选和查看球员数据。
