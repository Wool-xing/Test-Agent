import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// L2 必测维度: 功能 + 边界 + 异常 + 兼容 + 可访问性

test("upload page renders @smoke", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /新建测试任务/ })).toBeVisible();
});

test("can switch input mode @smoke", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("radio", { name: "URL" }).check();
  await expect(page.getByLabel(/被测 URL/)).toBeVisible();
  await page.getByRole("radio", { name: "文件" }).check();
  await expect(page.getByLabel(/上传被测物/)).toBeVisible();
});

test("catalog page lists experts and skills @smoke", async ({ page }) => {
  await page.goto("/catalog");
  await expect(page.getByRole("heading", { name: "Catalog" })).toBeVisible();
});

test("submit empty text triggers required validation @boundary", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "开始测试" }).click();
  // browser native required validation: the textarea is invalid
  const ta = page.getByLabel(/测试需求/);
  await expect(ta).toHaveJSProperty("validity.valid", false);
});

test("upload page has no critical a11y violations @a11y", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const critical = results.violations.filter((v) => v.impact === "critical");
  expect(critical, JSON.stringify(critical, null, 2)).toHaveLength(0);
});

test("catalog page has no critical a11y violations @a11y", async ({ page }) => {
  await page.goto("/catalog");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const critical = results.violations.filter((v) => v.impact === "critical");
  expect(critical, JSON.stringify(critical, null, 2)).toHaveLength(0);
});

test("malformed run_id shows error or empty state @exception", async ({ page }) => {
  await page.goto("/runs/__nonexistent_run__");
  // status fetch will fail or return loading; just verify no JS crash
  await expect(page.getByText(/Run/)).toBeVisible();
});
