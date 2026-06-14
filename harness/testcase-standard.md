# Test Case Standard（TC 规范）

## 1. 文件位置与命名

- 路径：`harness/tasks/test-cases/TC-NNN-SS.md`
- `NNN` = 关联 REQ 编号；`SS` = 该 REQ 下用例序号（01 起）

## 2. Frontmatter

```yaml
---
tc_id: TC-003-01
linked_req: REQ-003
title: "一句话用例标题"
status: draft        # draft | reviewed | implemented | passing | failing
level: integration   # unit | integration | e2e | eval
owner: claude-code-001
automated: true      # false 时必须写手工执行步骤
---
```

## 3. 正文结构

```markdown
## 前置条件
## 步骤（编号列表，每步一个动作）
## 期望结果（与 REQ 验收标准一一对应）
## 实现位置（自动化用例的测试代码路径；eval 用例的数据集路径）
```

## 4. 特殊约定（AI 平台项目）

- **eval 级用例**：针对 Agent 行为质量（意图分类准确率、检索召回、工具调用正确性、儿童内容拦截率），
  用例需指明 golden dataset 路径与通过阈值，例如 `意图分类在 golden-50 数据集上准确率 ≥ 90%`
- **回归约定**：severity 为 high/critical 的 BUG 关闭前必须新增对应 TC，并回填 BUG 与 REQ 的 `test_case_ref`
- 自动化测试栈：后端 pytest（沿用 goal-agent：SQLite in-memory / PG testcontainer），前端 vitest/playwright，eval 用 Langfuse datasets
