# apps/ —— CLIENT 层

面向用户/通道的入口（ADR-013 / [docs/design/07](../docs/design/07-repo-strategy.html) §5）。

- `chatui/` —— NextJS Web 入口（Pi5 ingress 发布；scope 锚点见 [docs/design/prototypes/chatui-v0.html](../docs/design/prototypes/chatui-v0.html)，REQ-003）
- `channels/` —— Telegram / Web 等通道适配器（Agent 不直连渠道，统一经 `notify.out`，ADR-006）

> M1：chatui v0 三屏随 REQ-003 落地；目录在切片实现 PR 中填充。
