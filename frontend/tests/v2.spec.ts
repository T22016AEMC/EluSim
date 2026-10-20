import { test, expect } from "./fixtures";
import { readFileSync } from "node:fs";
const inputs = JSON.parse(
  readFileSync(new URL("./v2-inputs.json", import.meta.url), "utf8"),
);
test("V2 method-specific model remains in the read-only library", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "滯留參數來源", exact: false })
    .click();
  await expect(page.getByLabel("Retention model")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Predict retention", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "模型與管柱資料庫", exact: false })
    .click();
  await expect(page.getByText(/RepoRT0259/).last()).toBeVisible();
  const response = await page.request.get("/api/models");
  expect(response.ok()).toBeTruthy();
  expect(
    (await response.json()).models.some(
      (model: any) => model.model_id === "report0259-rt",
    ),
  ).toBeTruthy();
});

test("V2 experimental full UV spectrum, imports, exports and qualitative abstention", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "UV-Vis／DAD 光譜", exact: false })
    .click();
  await page
    .getByLabel("UV SMILES", { exact: true })
    .fill(inputs["pnnl-uv-shape"]);
  await page.getByRole("button", { name: "分析 UV 結構", exact: true }).click();
  await expect(page.getByTestId("uv-status")).toHaveText("實驗性模型預測", {
    timeout: 30000,
  });
  await expect(page.getByTestId("uv-chart").locator("canvas")).toBeVisible();
  await expect(page.getByAltText("UV 分子結構")).toBeVisible();
  await page.getByLabel("匯入 UV CSV").setInputFiles({
    name: "observed.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "wavelength_nm,intensity\n220,0.1\n250,0.8\n400,0.02\n",
    ),
  });
  await expect(
    page.getByText("observed.csv · 實驗資料 · 3 個資料點 ·吸光度"),
  ).toBeVisible();
  for (const name of [
    "匯出 UV CSV",
    "匯出 UV PNG",
    "匯出 UV SVG",
    "匯出原始資料 JSON",
  ]) {
    const event = page.waitForEvent("download");
    await page.getByRole("button", { name, exact: true }).click();
    await event;
  }
  await page.screenshot({
    path: "../artifacts/" + info.project.name + "-v2-uv.png",
    fullPage: true,
  });
  await page.getByLabel("UV SMILES", { exact: true }).fill("CCCC");
  await page.getByRole("button", { name: "分析 UV 結構", exact: true }).click();
  await expect(page.getByTestId("uv-status")).toHaveText("定性篩選", {
    timeout: 30000,
  });
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width + 1,
      page.viewportSize()!.width,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
