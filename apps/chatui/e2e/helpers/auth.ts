// ChatUI e2e 登录助手（code+PKCE）。WP-8/REQ-005 接 IdP 后实现真实登录流。
import { Page } from '@playwright/test';

export type Role = 'admin' | 'adult' | 'kid';

const USERS: Record<Role, string> = {
  admin: 'best_pal',
  adult: 'go_getter',
  kid: 'kid',
};

/** 以指定角色经 Keycloak code+PKCE 登录 ChatUI。 */
export async function loginAs(page: Page, role: Role): Promise<void> {
  const base = process.env.AIFAMILY_BASE_URL!;
  await page.goto(`${base}/login`);
  await page.getByTestId('username').fill(USERS[role]);
  await page.getByTestId('password').fill(process.env.AIFAMILY_TEST_PASSWORD ?? '');
  await page.getByTestId('login-submit').click();
  await page.waitForURL(`${base}/**`);
}
