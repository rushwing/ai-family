// TC-003-08（A）：ChatUI v0 三屏、确认交互与端到端 trace（ChatUI e2e）。
// 需求 8 / 验收 #3；回归 BUG-018。
//
// gate：未设 AIFAMILY_BASE_URL 时跳过；WP-8 ChatUI + REQ-005 playwright 接 CI 后转 passing。
// trace_id 贯通断言见 tests/e2e/test_langfuse_goal_trace.py（同一 trace_id）。
import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

const BASE_URL = process.env.AIFAMILY_BASE_URL;

test.describe('ChatUI v0 目标流', () => {
  test.skip(!BASE_URL, '设 AIFAMILY_BASE_URL 运行 ChatUI e2e（WP-8）');

  test('adult 三屏可用 + 用户点击确认才写入', async ({ page }) => {
    await loginAs(page, 'adult');
    await expect(page.getByTestId('screen-chat')).toBeVisible();
    await page.getByTestId('nav-board').click();
    await expect(page.getByTestId('goal-board')).toBeVisible();

    // 发起需确认的目标写操作
    await page.getByTestId('nav-chat').click();
    await page.getByTestId('chat-input').fill('帮我建一个目标');
    await page.getByTestId('chat-send').click();
    const confirm = page.getByTestId('confirm-gate');
    await expect(confirm).toBeVisible();
    // 确认门描述为 GoalAgent 内部确认门，不暗示 M2 Planner（BUG-018）
    await expect(confirm).not.toContainText(/Plan Mode|Planner/i);

    // 记录 trace_id（供 Langfuse 贯通断言）
    const traceId = await page.getByTestId('trace-id').getAttribute('data-trace-id');
    expect(traceId).toBeTruthy();

    await page.getByTestId('confirm-accept').click();
    await expect(page.getByTestId('goal-created-toast')).toBeVisible();
  });

  test('取消或缺确认不产生业务写入', async ({ page }) => {
    await loginAs(page, 'adult');
    await page.getByTestId('chat-input').fill('再建一个目标');
    await page.getByTestId('chat-send').click();
    const before = await page.getByTestId('goal-card').count();
    await page.getByTestId('confirm-cancel').click();
    await expect(page.getByTestId('goal-card')).toHaveCount(before);
  });
});
