# GLOSSARY — 术语表（唯一权威定义）

> 所有设计文档、ADR、REQ、代码注释必须使用本表术语。新增术语先入表、再使用；发现文档用词与本表冲突按 BUG 处理。
> 排序：按主题分组，组内按字母序。

## 1. 平台与角色

| 术语 | 英文 | 定义 |
|---|---|---|
| 家庭成员 | Family Member | 平台的最终用户，即一个家庭里的真实的人。每个成员对应 IdP 中的一个账号，是租户隔离的最小单位 |
| 租户 | Tenant | 本项目中租户 = 家庭成员（非"家庭"）。数据库 RLS、向量集合、文件桶均按 family_member_id 隔离 |
| 角色 | Role | RBAC 角色，v1 仅三种：`admin`（家长+运维）、`adult`（成年成员）、`kid`（未成年成员，强制经过 Compliance） |
| 通道 | Channel | 用户触达平台的入口形态：ChatUI（主通道）、Telegram（经 OpenClaw）、未来的 PWA 等 |
| 平台基座 | Platform Base | 所有 Agent 共享的基础设施集合：身份、数据库、向量库、消息总线、可观测性、网络层 |

## 2. 智能体体系

| 术语 | 英文 | 定义 |
|---|---|---|
| 智能体 | Agent | 一个有独立职责域、独立 LangGraph 图、独立 MCP 工具集的服务单元。v1 共 7 个领域 Agent + 3 个平台 Agent |
| 领域 Agent | Domain Agent | GoalAgent、StudyAgent、TravelAgent、StockAgent、ResearchAgent、KnowledgeAgent、DataAgent |
| 平台 Agent | Platform Agent | IntentRouter、Planner、Compliance——不直接面向业务，服务于编排与治理 |
| 意图路由器 | IntentRouter | 对用户输入做意图分类 + 风险分级（read / draft / write / high-risk），决定单 Agent 直达还是交给 Planner |
| 规划器 | Planner | 把复杂长程任务分解为 Agent 任务图（DAG），含 Plan Mode：先产出计划给用户确认，再执行 |
| Plan Mode | Plan Mode | Planner 的前置确认模式：复杂/写操作任务先生成可读的执行计划，用户批准后才进入执行（对标 Claude Code plan mode） |
| 合规审查 | Compliance | 双向 guardrail：输入侧做意图过滤与注入检测，输出侧做内容审查与 PII 处理；kid 角色强制全量经过 |
| ReAct | ReAct | Reason + Act 循环：LLM 推理→选工具→执行→观察→再推理。各 Agent 内部的基本执行范式 |
| 垂直切片 | Vertical Slice | 一条从 ChatUI 到数据层全链路打通的最小业务闭环。v1 的垂直切片 = GoalAgent |
| 长程任务 | Long-running Task | 跨多轮、多 Agent、可能跨天执行的任务（如"制定并跟踪一个月学习计划"）。依赖 Checkpointer 实现韧性 |

## 3. 编排与上下文

| 术语 | 英文 | 定义 |
|---|---|---|
| 编排图 | Graph | LangGraph 的 StateGraph 实例。每个 Agent 一张图；Planner 动态组装跨 Agent 任务图 |
| 检查点 | Checkpointer | LangGraph 状态持久化机制，本项目用 PostgreSQL checkpointer。进程重启/失败后可从断点恢复 |
| 上下文装配 | Context Assembly | 按固定配方组装 prompt 上下文：系统策略 + 用户角色 + 任务意图 + 检索证据 + 会话状态 + 工具结果 + 风险等级 + 输出 schema |
| 会话 | Session | 一次连续对话，以 thread_id 标识，绑定 family_member_id。状态存 Checkpointer，热数据缓存于 Redis |
| 策略引擎 | Policy Engine | 业务规则（儿童限制、工具白名单、配额）的结构化存放与判定服务。**规则不写进 prompt** |

## 4. 工具与集成

| 术语 | 英文 | 定义 |
|---|---|---|
| MCP | Model Context Protocol | Agent 与工具之间的标准协议。平台所有工具均以 MCP server 形式暴露 |
| MCP 服务器 | MCP Server | 一个领域 Agent 配套一个 FastMCP server（复用 goal-agent 的 36-tool 模式），承载该域全部工具 |
| MCP 网关 | MCP Gateway | 工具注册、按角色下发工具白名单、JWT 校验、调用审计的统一入口 |
| 工具 | Tool | MCP server 上的一个可调用函数。工具侧自行鉴权——"Agent 读到上下文 ≠ 用户拥有该权限" |
| 工具侧鉴权 | Tool-side AuthZ | 每次工具调用携带用户 JWT，由工具自己校验权限并以该用户身份访问数据，而非信任 Agent |
| Draft-First | Draft-First | 所有写操作（发消息、改日程、下单类）先产出草稿，用户确认后才执行。高风险操作不可自动执行 |
| 技能 | Skill | OpenClaw 侧的能力包（如 tutor、kids-coding）。与平台 Tool 的关系：Skill 是 OpenClaw 宿主内的实现形态，经 MCP 桥接后对平台呈现为 Tool |
| OpenClaw | OpenClaw | 自托管个人 Agent 宿主（MacMini 上运行），承担 web-search、日历同步、邮件收发等通道型能力，经 MCP 接入平台 |

## 5. 数据与检索

| 术语 | 英文 | 定义 |
|---|---|---|
| RLS | Row-Level Security | PostgreSQL 行级安全策略。所有业务表带 family_member_id 列并启用 RLS，连接会话设置 `app.current_member` |
| pgvector | pgvector | PostgreSQL 向量扩展，v1 的向量检索底座（决策见 ADR-004） |
| 混合检索 | Hybrid Search | 向量相似度 + 全文检索（PG FTS + 中文分词）加权融合，用于学习资料问答 |
| 知识图谱 | Knowledge Graph | Neo4j 中的家庭本体：成员—目标—学习主题—地点—投资标的等实体与关系（ADR-005） |
| 本体 | Ontology | 知识图谱的 schema 层：实体类型、关系类型、属性的受控定义。由 KnowledgeAgent 维护 |
| 摄取管线 | Ingestion Pipeline | 学习资料（pdf/html/md/excel）→ 解析 → 分块 → 嵌入 → 入 pgvector/Neo4j 的异步流水线，经 RabbitMQ 调度 |
| 嵌入 | Embedding | 文本向量化。v1 经 LLM 网关调用 API 嵌入模型，预留 MacMini 本地嵌入选项 |

## 6. 安全与治理

| 术语 | 英文 | 定义 |
|---|---|---|
| IdP | Identity Provider | OIDC 身份提供方（选型见 ADR-008），家庭成员账号、角色、组的唯一来源 |
| 身份链 | Identity Chain | CF Access → IdP OIDC → ChatUI 会话 → JWT → LangGraph → MCP 工具 → PG RLS 的端到端身份透传路径 |
| 零公网端口 | Zero Open Port | 所有自托管节点不向公网开放任何入站端口；节点间走 Tailscale，对外只有 Cloudflare Tunnel 出站连接 |
| 审计追踪 | Audit Trail | 每次 prompt、工具调用、检索、输出均落库，带 trace_id + family_member_id，不可变更 |
| 全链路追踪 | Tracing | Langfuse 记录每个请求的完整执行树（LLM 调用、token、延迟、成本），与审计表通过 trace_id 关联 |
| PII | Personally Identifiable Information | 个人敏感信息。进入 LLM 上下文前检测，对外输出前脱敏 |
| 提示注入 | Prompt Injection | 用户上传内容中夹带指令的攻击。检索内容一律按"数据"而非"指令"处理，注入检测在 Compliance 输入侧 |

## 7. 工程方法（harness）

| 术语 | 英文 | 定义 |
|---|---|---|
| Harness | Harness Engineering | 以文件化 REQ/TC/BUG/ADR 驱动人机协作开发的工程方法（承自 OpenStock 仓库约定） |
| REQ | Requirement | 需求单 `harness/tasks/features/REQ-NNN.md`，带 frontmatter 与生命周期状态机 |
| TC | Test Case | 测试用例 `TC-NNN-SS.md`，NNN 关联 REQ 编号 |
| BUG | Bug | 缺陷单 `BUG-NNN.md`，五类：req_bug / tc_bug / impl_bug / ci_bug / user_bug |
| ADR | Architecture Decision Record | 架构决策记录 `docs/adr/ADR-NNN-*.md`：背景、选项 pros/cons、决策、代价、重审触发条件 |
| 验收标准 | Acceptance Criteria | "一句话、现在时态、可验证"。例：`kid 用户请求被拒资源时收到引导性回复且审计表新增一条记录` |
| 渐进式披露 | Progressive Disclosure | 文档按 L0→L3 分层组织，读者按需深入；任何文档不假设读者已读全部文档 |
| 三色笔记 | Three-color Notes | 设计文档的富文本风格：蓝=事实/引用，绿=决策/结论，橙/红=风险/警告（HTML 呈现） |

## 8. 里程碑代号

| 代号 | 内容 |
|---|---|
| M0 | 架构设计稿 v1 + 外部评审闭环（当前阶段） |
| M1 | 平台基座最小集 + GoalAgent 垂直切片上线 |
| M2 | IntentRouter + Planner + ResearchAgent + Compliance v0 |
| M3 | KnowledgeAgent（摄取管线/图谱）+ StudyAgent |
| M4 | TravelAgent + DataAgent + StockAgent |
| M5 | docker-compose → K3s 迁移 + 容灾演练 |
