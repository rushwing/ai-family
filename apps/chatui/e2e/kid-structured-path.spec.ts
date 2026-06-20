// TC-003-07（A）：kid 结构化只路径与越界转家长（ChatUI e2e）。
// 需求 7 / 验收 #1·#6；回归 BUG-012。
//
// gate：未设 AIFAMILY_BASE_URL 时跳过；WP-8 ChatUI + REQ-005 playwright 接 CI 后转 passing。
import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

const BASE_URL = process.env.AIFAMILY_BASE_URL;

test.describe('kid 结构化只路径', () => {
  test.skip(!BASE_URL, '设 AIFAMILY_BASE_URL 运行 ChatUI e2e（WP-8）');

  test('kid 只读自有目标并可走 Draft-First 打卡', async ({ page }) => {
    await loginAs(page, 'kid');
    await expect(page.getByTestId('goal-board')).toBeVisible();
    // 仅呈现结构化入口；无自由对话/创建/批准入口
    await expect(page.getByTestId('free-chat-input')).toHaveCount(0);
    await expect(page.getByTestId('create-goal')).toHaveCount(0);
    await expect(page.getByTestId('approve-plan')).toHaveCount(0);

    await page.getByTestId('checkin-draft-first').first().click();
    await page.getByTestId('checkin-confirm').click();
    await expect(page.getByTestId('praise-message')).toBeVisible();
  });

  test('kid 越界请求被拒并引导转家长', async ({ page }) => {
    await loginAs(page, 'kid');
    // 直接访问成人目标 URL → 被拦截，无跨成员数据
    await page.goto(`${BASE_URL}/goals?owner=adult`);
    await expect(page.getByTestId('goal-card')).toHaveCount(0);
    await expect(page.getByTestId('redirect-to-parent')).toBeVisible();
  });

  test('kid 看不到 M2 Planner/Plan Mode 表述', async ({ page }) => {
    await loginAs(page, 'kid');
    await expect(page.locator('body')).not.toContainText(/Plan Mode|Planner/i);
  });
});
