# 知微 Handover

## 交付状态

本次 Handover 把原先独立的 `Family-Intelligence/family-digital-twin` 前端原型纳入 `ai-family` modular monorepo，并补齐产品、需求和项目治理上下文。

当前状态：

- 前端原型可本地运行和构建；Compose 入口只用于本机评审，不是 NAS 生产部署；
- 设备总览、网络拓扑、场景与流程、任务队列等主要页面已形成；
- 设备、地址、户型位置和状态全部使用虚构 fixture；设备交互使用前端异步动画；
- 尚未接入真实设备、家庭中枢 API、MCP Gateway 或事件流；
- GitHub Project 尚未物化，配置契约已落在 `.github/project-management/home-intelligence.yaml`；
- Harness 已新增 `REQ-011` 记录本次 Handover，等待人类评审。

已发布原型：<https://zhiwei-home-intelligence.ruoxu-wang720739.chatgpt.site/>

## 本次包含

- `apps/home-intelligence-web/`：当前 Web 原型的完整已跟踪源码；
- `PRD.md`：产品范围、设备交互、场景、队列、治理与非功能要求；
- `requirements.xlsx`：6 个 Roadmap、18 个 Epic、68 个 Story、12 个示例 Task；
- `roadmap.yaml`：供 Agent 快速读取的层级索引；
- `ARCHITECTURE.md`：与 ai-family 的集成边界；
- `PROJECT_MANAGEMENT.md`：GitHub Project 与 Harness 的职责和同步方向；
- `.github/project-management/home-intelligence.yaml`：字段、视图、Milestone 和状态映射的声明式配置；
- `harness/tasks/features/REQ-011.md`：本次交接的正式 Harness 记录。

## 不包含

- 厂商账号、Token、家庭网络密码或设备密钥；
- `node_modules`、`.next`、`dist`、Wrangler 本地状态等构建产物；
- 真实 MCP Server、设备适配器和任务消费者；
- 生产数据库迁移和真实家庭设备状态；
- 已创建的 GitHub Project、Issue 或 Milestone。外部对象应在本 PR 合并后按配置物化，避免评审前产生双写状态。

## 本地运行

```bash
cd apps/home-intelligence-web
npm ci
npm run dev
```

构建与静态检查：

```bash
npm run lint
npm run build
```

本机容器演示：

```bash
cd apps/home-intelligence-web
docker compose up -d --build
```

默认入口为 `http://127.0.0.1:3000`。该入口使用无鉴权的 Wrangler 开发服务器，只能评审虚构数据，不得暴露到局域网或公网。生产 NAS 运行入口、鉴权、healthcheck、非 root 和最小化镜像由 `ZW-ST-1801` 后续实现。

## 公共演示数据

公共仓库只保留虚构的多房间住宅与通用设备类别，用于验证 Device Profile、控件和接入边界。真实家庭 inventory、局域网地址、成员终端、精确户型和设备坐标必须放在被忽略的私有配置中，不得提交到代码、文档、截图或需求表。

## 集成顺序

1. 冻结 Device Profile、Task、Event 三个基础契约；
2. 提供家庭状态快照和事件订阅 API；
3. 接入普通队列与优先队列，先打通灯、窗帘、插座、NAS 指标和中枢指标；
4. 用 MCP Gateway 下发按成员、角色和设备过滤后的能力；
5. 把观影模式做成第一个端到端场景；
6. 再引入自然语言建流、Planner 和长程工作流。

## 已知风险

- 部分厂商设备没有稳定局域网写接口，必须明确标注只读或实验性能力；
- 窗帘运动百分比只能以停止后的真实上报为准；
- 路由器重启和关键插座断电会导致中枢暂时失联，不能按普通开关处理；
- Agent 计划必须经过工具侧鉴权，复杂写操作必须人工 Review；
- Excel 是二进制文件；CI 使用 OpenXML 校验字段、枚举、层级、依赖和导入视图，评审时同时检查 `roadmap.yaml` 和 PRD。

## 接手检查

- [ ] 阅读 PRD、Architecture 和 Project Management；
- [ ] 在目标 Node 版本执行 `npm ci`、lint 和 build；
- [ ] 确认 Web 原型没有包含家庭密钥；
- [ ] 评审 `REQ-011` 的 scope 与 `tc_policy`；
- [ ] 合并后创建 GitHub Project、Milestone 和镜像 Issue；
- [ ] 从 P0 Story 中选择首批 Ready 项，逐项创建 REQ，不批量跳过 Harness 门禁。
