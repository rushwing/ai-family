# 知微 Home Intelligence

面向家庭智能设备的本地优先数字孪生控制台。当前版本是可交互前端原型，设备状态为演示数据，尚未连接真实 MCP 服务。

## 已包含

- 可调整尺寸的 Widget 卡片 Dashboard 与 20 台设备登记
- 154㎡ 平层户型图二级视图
- 建筑 → 楼层 → 房间 → 设备的数据层级，预留 275㎡ 四层住宅扩展
- 家庭网络拓扑与设备能力视图
- 设备详情、快速控制和异步任务队列
- `read_home_status` 与 `dispatch_device_task` 两个 WebMCP 工具
- 针对手机、平板和桌面的 4 / 8 / 12 列响应式布局
- 面向 NAS 的 Docker Compose 部署入口

## 本地开发

需要 Node.js 22.13 或更高版本。

```bash
npm ci
npm run dev
```

默认开发地址由终端输出，通常为 `http://localhost:5173`。

## NAS 部署

在支持 Docker Compose 的 NAS 上执行：

```bash
docker compose up -d --build
```

启动后访问 `http://<NAS局域网IP>:3000`。

## 接入真实设备

下一阶段建议在树莓派 5 上提供统一的家庭智能中枢 API：

1. 每个设备适配器注册统一的设备描述、状态 Schema 和 MCP capabilities。
2. 前端通过中枢读取设备快照和订阅状态事件，不直接持有厂商凭证。
3. 所有控制请求先进入任务队列，再由策略引擎执行权限、安全和幂等检查。
4. Ontology 服务维护空间、设备、能力、成员、策略与任务之间的关系。
5. 对断网、离线设备和长任务使用事件流或轮询回执，前端只展示最终一致状态。

建议的 API 边界：

- `GET /api/twin/snapshot`：家庭数字孪生快照
- `GET /api/devices/:id`：设备详情与能力
- `POST /api/tasks`：创建异步任务
- `GET /api/tasks/:id`：查询任务状态
- `GET /api/events`：SSE 状态与任务事件流
- `GET /api/ontology`：读取家庭知识图谱

高风险动作（断开路由器电源、删除数据、门锁与安防控制等）应要求二次确认，并保留不可抵赖审计记录。
