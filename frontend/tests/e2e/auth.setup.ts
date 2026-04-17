import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test as setup } from "@playwright/test";

import { getFixture } from "./fixture";

const authFile = path.resolve(__dirname, "../../playwright/.auth/admin.json");

setup("authenticate admin", async ({ page }) => {
  const fixture = getFixture();

  mkdirSync(path.dirname(authFile), { recursive: true });

  await page.goto("/login");
  await page.getByLabel("Email").fill(fixture.admin_email);
  await page.getByLabel("Password").fill(fixture.admin_password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.waitForURL(/\/projects(?:\/)?$/);
  await expect(page).toHaveURL(/\/projects(?:\/)?$/);

  await page.context().storageState({ path: authFile });
});
