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
- **env-gated 用例的两段式评审（human-001 裁决，2026-06-20）**：当 TC 的被测组件/受控依赖尚未落地（测试先行，缺服务/缺模块即 `skip`）时——
  - `tc_impl_review` **只审「代码名副其实」**：测试在其 env/模块就绪后会真正断言所声明的安全/功能属性（扫描对象正确、断言关系成立、契约/角色/枚举与系统真值一致、fixture/seed 合法、无伪造输入或假绿），缺环境时干净 skip。此阶段**不要求真跑通过**。
  - **「真跑实证」正式归入 `req_impl_review`**：req_impl 落地组件后，相应 `skip` 必须转 `passing` 才能签 T13；env-gated 用例的实际执行证据在此闭环。
  - 适用前提：用例顶层以 `importorskip`/`skipif` gating，不把缺测试支撑伪装成通过。评审打回应针对「代码不名副其实」，而非「当前环境跑不起来」。
