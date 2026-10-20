import { test, expect } from "./fixtures";
import { t } from "../src/i18n/zh-TW";

/** Exercise optional inputs and output columns using the existing demo only. */
test("desktop optional mixer efficiency and pressure controls", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: t("Load demo mixture"), exact: true }).click();
  await page.getByRole("navigation").getByRole("button", {
    name: t("LC Mode & Column"), exact: false,
  }).click();
  await page.getByLabel(t("efficiency_model"), { exact: true }).selectOption("van_deemter");
  await expect(page.getByLabel(t("computed_plates"), { exact: true })).toBeDisabled();
  await page.getByLabel(t("vd_a"), { exact: true }).fill("1.1");
  await page.getByLabel(t("diffusion"), { exact: true }).fill("1");
  await page.getByLabel(t("flow_resistance"), { exact: true }).fill("500");
  await expect(page.getByText(t("reference_pending"), { exact: true })).toBeVisible();
  await page.getByRole("navigation").getByRole("button", {
    name: t("Mobile Phase & Gradient"), exact: false,
  }).click();
  await page.getByLabel(t("mixer_ml"), { exact: true }).fill("0.02");
  await page.getByLabel(t("system_pressure"), { exact: true }).fill("5");
  await expect(page.getByText(t("mixer_help"), { exact: true })).toBeVisible();
  await page.getByRole("button", { name: t("Run simulation"), exact: false }).first().click();
  await expect(page.getByTestId("chromatogram").locator("canvas")).toBeVisible({ timeout: 45000 });
  await expect(page.locator("thead th").filter({ hasText: t("plates_used") })).toBeVisible();
  await expect(page.getByText(t("max_pressure"), { exact: true })).toBeVisible();
  await page.getByLabel(t("pressure_limit"), { exact: true }).fill("1");
  await page.getByRole("button", { name: t("Run simulation"), exact: false }).first().click();
  await expect(page.getByText(/最高壓力.*超過上限/).first()).toBeVisible({ timeout: 45000 });
  const result = await page.locator("main").innerText();
  expect(result).not.toMatch(/色譜|保留時間|色譜柱|分辨率|校準|優化/);
});
