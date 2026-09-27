# 知微 Home Intelligence Web

面向家庭智能设备的本地优先数字孪生控制台。当前目录只包含可交互前端原型，所有设备、地址、房间、状态和户型位置均为虚构演示数据；它尚未连接真实 MCP 服务或终端设备。

## 原型范围

- 按房间组织的可调整 Widget Dashboard；
- 虚构示例住宅的户型图二级视图；
- 家庭网络拓扑、设备详情、场景编排和异步任务队列；
- 空调、灯、窗帘、卷帘、鱼缸、插座、路由器等标准化控件；
- 手机、折叠屏、平板和桌面的响应式布局；
- 浏览器内 WebMCP 演示工具，只能对固定白名单能力创建本地 mock 队列项。

原型行为不是生产设备控制契约。权威交互、任务状态和安全边界见 `docs/product/home-intelligence/PRD.md` 与 `ARCHITECTURE.md`。

## 本地开发

需要 Node.js 22.13 或更高版本。

```bash
npm ci
npm run dev
```

默认地址由终端输出，通常为 `http://localhost:5173`。

## 本机容器演示

Compose 入口使用 Wrangler 的本地开发服务器，没有生产鉴权、健康检查或最小化运行时。它仅用于在本机评审虚构数据，默认只绑定 `127.0.0.1`；不得暴露到家庭局域网或公网。

```bash
docker compose up --build
```

启动后访问 `http://127.0.0.1:3000`。生产部署必须另行实现鉴权、生产运行入口、healthcheck、非 root 用户、资源限制和密钥注入，并由独立 REQ 验收。

## 真实 inventory

真实家庭 inventory 不进入公共仓库。若本地开发需要私有数据，放入以下任一忽略目录：

- `apps/home-intelligence-web/fixtures/private/`
- `docs/product/home-intelligence/private/`

不要在源代码、截图、PR 描述或需求表中提交真实型号、局域网地址、成员终端、精确户型和设备坐标。

## 后端接入边界

前端最终只访问家庭中枢 API，不保存厂商凭证：状态来自数字孪生快照与事件流，控制请求进入任务队列，并由身份、策略、风险确认、幂等和审计机制治理。详细边界见产品架构文档。
