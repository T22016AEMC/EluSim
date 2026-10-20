import { curveExamples, test, expect } from "./fixtures";
test("real curve compounds resolve by ID; 5:3:2 area composition; gradient and ratio dataflow", async ({
  page,
}) => {
  // End-to-end workflow makes several separately bounded public API calls.
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await curveExamples(page);
  await expect(
    page.getByLabel("相對份數 Caffeine", { exact: true }),
  ).toHaveValue("3");
  await page.getByRole("button", { name: "由結構取得滯留參數" }).click();
  await expect(
    page.getByLabel("logKw Caffeine", { exact: true }),
  ).not.toHaveValue("", { timeout: 30000 });
  const resolved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("elusim-project")!),
  );
  expect(resolved.compounds.map((c: any) => c.parameter_origin)).toEqual([
    "literature",
    "literature",
    "literature",
  ]);
  const run = async () => {
    const response = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/simulate") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "執行模擬", exact: false })
      .first()
      .click();
    const r = await response;
    expect(r.ok()).toBeTruthy();
    return r.json();
  };
  const initial = await run();
  expect(initial.order).toHaveLength(3);
  expect(initial.peaks.map((p: any) => p.mixture_fraction)).toEqual([
    0.5, 0.3, 0.2,
  ]);
  expect(initial.peaks[0].peak_area).toBeCloseTo(0.5, 8);
  await page
    .getByRole("button", { name: "流動相與梯度", exact: false })
    .click();
  await page.getByLabel("時間（min） 節點 2", { exact: true }).fill("15");
  const changed = await run();
  expect(changed.peaks[0].rt_min).not.toBe(initial.peaks[0].rt_min);
  await page
    .getByRole("navigation", { name: "工作區" })
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await page.getByLabel("批次相對份數").fill("10:3:2");
  await page.getByRole("button", { name: "套用批次組成" }).click();
  const ratio = await run();
  expect(ratio.peaks[0].peak_area).toBeCloseTo(10 / 15, 8);
  expect(ratio.peaks.map((p: any) => p.rt_min)).toEqual(
    changed.peaks.map((p: any) => p.rt_min),
  );
  await page.getByRole("button", { name: "梯度最佳化", exact: false }).click();
  await page.getByLabel("梯度時間（min）：最小", { exact: true }).fill("8");
  await page.getByLabel("梯度時間（min）：最大", { exact: true }).fill("12");
  await page.getByLabel("梯度時間（min）：格數", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "產生分離度地圖", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "候選梯度", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page
    .getByRole("navigation", { name: "工作區" })
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await page.getByLabel("logKw Caffeine", { exact: true }).fill("1.234");
  await page.getByRole("button", { name: "由結構取得滯留參數" }).click();
  await expect(page.getByRole("狀態")).toHaveCount(0, { timeout: 30000 });
  await expect(page.getByLabel("logKw Caffeine", { exact: true })).toHaveValue(
    "1.234",
  );
  await page
    .getByRole("button", { name: "層析模式與管柱", exact: false })
    .click();
  await page.getByLabel("管柱溫度（°C）", { exact: true }).fill("30");
  await page
    .getByRole("navigation", { name: "工作區" })
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await expect(
    page.getByText("滯留條件有差異", { exact: false }).first(),
  ).toBeVisible();
  const incompatible = await run();
  expect(incompatible.order).toHaveLength(3);
  expect(incompatible.peaks.every((peak: any) => peak.warning)).toBeTruthy();
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(
      (w) => document.documentElement.scrollWidth <= w + 1,
      page.viewportSize()!.width,
    ),
  ).toBeTruthy();
});

import { readFileSync } from "node:fs";
const inputs = JSON.parse(
  readFileSync(new URL("./v2-inputs.json", import.meta.url), "utf8"),
);
test("automatic curve source fills a compound; manual edits remain protected", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "層析模式與管柱", exact: false })
    .click();
  await page.getByRole("button", { name: "套用模型來源條件" }).click();
  const compounds = () =>
    page
      .getByRole("navigation", { name: "工作區" })
      .getByRole("button", { name: "化合物", exact: false });
  await compounds().click();
  await page
    .getByLabel("化合物名稱", { exact: true })
    .fill("Heldout structure");
  await page
    .getByLabel("SMILES", { exact: true })
    .fill(inputs["lss-parameters"]);
  await page.getByRole("button", { name: "新增化合物", exact: true }).click();
  await expect(
    page.getByLabel("logKw Heldout structure", { exact: true }),
  ).not.toHaveValue("", { timeout: 30000 });
  await page
    .getByRole("button", { name: "滯留參數來源", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: "Heldout structure", exact: false }),
  ).toContainText("實測曲線");
  await expect(page.getByLabel("Retention model")).toHaveCount(0);
  const predicted = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("elusim-project")!).compounds.find(
      (c: any) => c.name === "Heldout structure",
    ),
  );
  expect(predicted.logkw).not.toBeNull();
  expect(predicted.parameter_origin).toBe("literature");
  await compounds().click();
  await page
    .getByLabel("logKw Heldout structure", { exact: true })
    .fill("1.234");
  await page
    .getByRole("button", { name: "滯留參數來源", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: "Heldout structure", exact: false }),
  ).toContainText("手動輸入");
  await compounds().click();
  await expect(
    page.getByLabel("logKw Heldout structure", { exact: true }),
  ).toHaveValue("1.234");
  expect(
    await page.evaluate(
      (w) => document.documentElement.scrollWidth <= w + 1,
      page.viewportSize()!.width,
    ),
  ).toBeTruthy();
});
