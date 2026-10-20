import { test, expect, type Page } from "./fixtures";

/** Enter three structures through the unchanged compound workflow. */
async function structures(page: Page) {
  await page.goto("/");
  for (const [name, smiles] of [
    ["Map ethanol", "CCO"],
    ["Map ether", "COCOC"],
    ["Map caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"],
  ]) {
    await page.getByLabel("化合物名稱", { exact: true }).fill(name);
    await page.getByLabel("SMILES", { exact: true }).fill(smiles);
    const response = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/retention/estimate") &&
        response
          .request()
          .postDataJSON()
          .method.compounds.some((compound: any) => compound.name === name),
    );
    await page.getByRole("button", { name: "新增化合物", exact: true }).click();
    expect((await response).ok()).toBeTruthy();
    await expect(
      page.getByLabel("logKw " + name, { exact: true }),
    ).not.toHaveValue("");
  }
}

/** Generate the map using real API calculations and return its output. */
async function map(page: Page) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "梯度最佳化", exact: false })
    .click();
  const response = page.waitForResponse((response) =>
    response.url().endsWith("/api/optimize/map"),
  );
  await page
    .getByRole("button", { name: "產生分離度地圖", exact: true })
    .click();
  const http = await response;
  expect(http.ok()).toBeTruthy();
  await expect(page.getByTestId("optimizer-candidates")).toBeVisible();
  return http.json();
}

/** Read a browser-generated export. */
async function exported(page: Page, label: string) {
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: label, exact: true }).click();
  const file = await pending;
  const { readFile } = await import("node:fs/promises");
  return readFile((await file.path())!, "utf8");
}

/** Confirm an apply action and wait for the resulting actual chromatogram. */
async function apply(page: Page, action: () => Promise<unknown>) {
  page.once("dialog", (dialog) => dialog.accept());
  const pending = page.waitForResponse((response) =>
    response.url().endsWith("/api/simulate"),
  );
  await action();
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  const result = await response.json();
  expect(result.solver).toBe("analytic");
  expect(result.peaks.some((peak: any) => peak.rt_min != null)).toBeTruthy();
  await expect(
    page.getByTestId("chromatogram").locator("canvas"),
  ).toBeVisible();
  return result;
}

test("three SMILES, resolution cell, candidate/Pareto apply, and CSV exports", async ({
  page,
}) => {
  test.setTimeout(240000);
  await structures(page);
  const result = await map(page);
  expect(result.axes.start_percent[0]).toBe(0);
  expect(result.axes.end_percent.at(-1)).toBe(100);
  expect(result.top_candidates.length).toBe(10);
  expect(await exported(page, "匯出地圖 CSV")).toContain('"critical_pair"');
  expect(await exported(page, "匯出候選 CSV")).toContain('"max_rel_sigma"');
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  // Exercise the actual ECharts heatmap click using its category grid geometry.
  const surface = page.getByTestId("resolution-map");
  await surface.scrollIntoViewIfNeeded();
  const countX = result.axes.gradient_time_min.length;
  const countY = result.axes.end_percent.length;
  const rectangle = await surface.boundingBox();
  const endIndex = result.min_rs[0].findIndex((row: any[]) =>
    row.some((value) => value != null),
  );
  const timeIndex = result.min_rs[0][endIndex].findIndex(
    (value: any) => value != null,
  );
  const x = 80 + ((rectangle!.width - 110) * (timeIndex + 0.5)) / countX;
  const y = 25 + ((380 - 125) * (countY - endIndex - 0.5)) / countY;
  const first = await apply(page, () => surface.click({ position: { x, y } }));
  expect(first.input.gradient[0].b_percent).toBe(0);
  await map(page);
  await apply(page, () =>
    page.getByRole("button", { name: "套用候選梯度 1", exact: true }).click(),
  );
  await map(page);
  await page.getByText("鍵盤選取非支配候選", { exact: true }).click();
  await apply(page, () =>
    page.getByRole("button", { name: "套用非支配候選 1", exact: true }).click(),
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
});

test("multi-segment search, JSON export, apply and cancellation", async ({
  page,
}) => {
  test.setTimeout(150000);
  await page.goto("/");
  await page
    .getByRole("button", { name: "載入示範混合物", exact: true })
    .click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "梯度最佳化", exact: false })
    .click();
  await page.getByLabel("搜尋時間上限（秒）", { exact: true }).fill("0.1");
  const pending = page.waitForResponse((response) =>
    response.url().endsWith("/api/optimize/multisegment"),
  );
  await page.getByLabel("最短段落時間（min）", { exact: true }).fill("0.75");
  await page
    .getByRole("button", {
      name: "多段梯度最佳化",
      exact: true,
    })
    .click();
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  const result = await response.json();
  const ramps = result.gradient.slice(0, 3);
  expect(
    ramps
      .slice(1)
      .every(
        (node: any, index: number) =>
          node.time_min - ramps[index].time_min >= 0.75 - 1e-9,
      ),
  ).toBeTruthy();
  expect(
    result.gradient.every(
      (node: any, index: number) =>
        index === 0 || node.b_percent >= result.gradient[index - 1].b_percent,
    ),
  ).toBeTruthy();
  await expect(page.getByTestId("multisegment-result")).toBeVisible();
  const file = JSON.parse(await exported(page, "匯出多段梯度 JSON"));
  expect(file.gradient).toEqual(result.gradient);
  await apply(page, () =>
    page.getByRole("button", { name: "套用多段梯度結果", exact: true }).click(),
  );
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "梯度最佳化", exact: false })
    .click();
  await page
    .getByRole("button", {
      name: "多段梯度最佳化",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("button", { name: "取消搜尋", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "取消搜尋", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("搜尋已取消");
  await expect(page.getByTestId("multisegment-result")).toHaveCount(0);
});
