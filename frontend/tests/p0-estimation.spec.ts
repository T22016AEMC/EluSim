import { test, expect } from "./fixtures";
import { readFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { demo, type Config } from "../src/types";

const caffeine = "Cn1cnc2c1c(=O)n(C)c(=O)n2C";
const database = JSON.parse(
  readFileSync(
    new URL("../../data/retention/curves.json", import.meta.url),
    "utf8",
  ),
);

/** Seed only browser-local project state for UI behavior checks. */
async function seed(page: import("@playwright/test").Page, config: Config) {
  await page.addInitScript(
    (project) =>
      localStorage.setItem("elusim-project", JSON.stringify(project)),
    config,
  );
  await page.goto("/");
}

/** Add a structure on Compounds and wait for its real estimate response. */
async function addStructure(
  page: import("@playwright/test").Page,
  name: string,
  smiles: string,
) {
  await page.getByLabel("化合物名稱", { exact: true }).fill(name);
  await page.getByLabel("SMILES", { exact: true }).fill(smiles);
  const response = page.waitForResponse(
    (result) =>
      result.url().endsWith("/api/retention/estimate") &&
      result
        .request()
        .postDataJSON()
        .method.compounds.some((compound: any) => compound.name === name),
  );
  await page.getByRole("button", { name: "新增化合物", exact: true }).click();
  const estimate = await (await response).json();
  await expect(
    page.getByLabel("logKw " + name, { exact: true }),
  ).not.toHaveValue("");
  return estimate;
}

/** Read a browser download without modifying its original values. */
async function downloadCsv(
  page: import("@playwright/test").Page,
  button: string,
) {
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: button, exact: true }).click();
  const file = await pending;
  return readFile((await file.path())!, "utf8");
}

test("default method: caffeine and a non-database SMILES auto-fill, edit, simulate and export without workspace switching", async ({
  page,
}) => {
  test.setTimeout(180000);
  await page.clock.install({ time: new Date("2026-10-20T00:00:00Z") });
  await page.goto("/");
  const first = await addStructure(page, "Auto caffeine", caffeine);
  expect(first.tier).toBe("A");
  const unknown = await addStructure(page, "Auto ether", "COCOC");
  expect(
    database.some(
      (row: any) => row.smiles === unknown.features.canonical_smiles,
    ),
  ).toBeFalsy();
  expect(["B", "C"]).toContain(unknown.tier);
  const requested: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/api/retention/estimate"))
      requested.push(request.postDataJSON().smiles);
  });
  const updated = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/retention/estimate") &&
      response.request().postDataJSON().smiles === "COCCOC",
  );
  // Keep both edits inside the debounce window regardless of host scheduling.
  await page.clock.pauseAt(new Date("2026-10-20T01:00:00Z"));
  await page
    .getByLabel("已存 SMILES Auto ether", { exact: true })
    .fill("COCOCC");
  await page
    .getByLabel("已存 SMILES Auto ether", { exact: true })
    .fill("COCCOC");
  await page.clock.runFor(599);
  expect(requested).toEqual([]);
  await page.clock.runFor(1);
  await page.clock.resume();
  expect((await updated).ok()).toBeTruthy();
  expect(requested).not.toContain("COCOCC");
  await expect(
    page.getByRole("button", { name: "執行模擬", exact: false }).first(),
  ).toBeEnabled();
  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("elusim-project")!),
  );
  expect(stored.column).toEqual(demo.column);
  expect(stored.mobile).toEqual(demo.mobile);
  expect(stored.gradient).toEqual(demo.gradient);
  const parameters = await downloadCsv(page, "匯出參數 CSV");
  expect(parameters.split("\r\n")[0]).toBe(
    "id,name,smiles,canonical_smiles,logkw,s,tier,tier_label,parameter_source,model_version,warnings,crippen_logp,tpsa,hbd,aromatic_rings,mw",
  );
  expect(parameters).toContain("Auto caffeine");
  const response = page.waitForResponse((result) =>
    result.url().endsWith("/api/simulate"),
  );
  await page
    .getByRole("button", { name: "執行模擬", exact: false })
    .first()
    .click();
  const result = await (await response).json();
  for (const name of ["Auto caffeine", "Auto ether"]) {
    const peak = result.peaks.find((item: any) => item.name === name);
    expect(peak.rt_min).not.toBeNull();
    expect(
      Math.max(...result.traces.find((trace: any) => trace.id === peak.id).y),
    ).toBeGreaterThan(0);
    expect(peak.k_e).toBeGreaterThan(0);
    expect(peak.compression_factor).toBeGreaterThan(0);
  }
  await expect(
    page.getByTestId("chromatogram").locator("canvas"),
  ).toBeVisible();
  const peaks = await downloadCsv(page, "匯出峰表 CSV");
  expect(peaks.split("\r\n")[0]).toBe(
    "id,name,tier,tier_label,rt_min,k_e,phi_outlet,sigma_min,compression_factor,fwhm_min,rs_to_next",
  );
  expect(peaks).toContain("Auto caffeine");
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width + 1,
      page.viewportSize()!.width,
    ),
  ).toBeTruthy();
});

test("generic tier, method refresh and re-estimate all preserve M and D", async ({
  page,
}) => {
  test.setTimeout(180000);
  const config = structuredClone(demo);
  config.compounds = [
    {
      ...config.compounds[0],
      id: "manual",
      name: "Manual",
      kind: "small_molecule",
      smiles: caffeine,
      parameter_tier: "M",
      parameter_origin: "manual",
    },
    {
      ...config.compounds[1],
      id: "calibration",
      name: "Calibration",
      kind: "small_molecule",
      smiles: caffeine,
      parameter_tier: "D",
      parameter_origin: "calibration",
      source: "calibrated",
    },
  ];
  await seed(page, config);
  const estimate = await addStructure(page, "Generic ion", "[Na+]");
  expect(estimate.tier).toBe("C");
  await expect(
    page
      .locator("article")
      .filter({ has: page.getByLabel("已存 SMILES Generic ion") })
      .getByTestId(/^tier-/),
  ).toContainText("通用估算");
  const response = page.waitForResponse((result) =>
    result.url().endsWith("/api/simulate"),
  );
  await page
    .getByRole("button", { name: "執行模擬", exact: false })
    .first()
    .click();
  const simulated = await (await response).json();
  expect(
    simulated.peaks.find((peak: any) => peak.name === "Generic ion")
      .parameter_tier,
  ).toBe("C");
  await expect(page.getByTestId("chromatogram")).toHaveAttribute(
    "aria-label",
    /Generic ion.*通用估算/,
  );
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await page.getByLabel("logKw Generic ion", { exact: true }).fill("1.234");
  await page.getByLabel("S Generic ion", { exact: true }).fill("3.2");
  await page.getByLabel("已存 SMILES Generic ion", { exact: true }).fill("CCO");
  await addStructure(page, "Refresh", "COCOC");
  await page
    .getByRole("button", { name: "流動相與梯度", exact: false })
    .click();
  const refreshed = page.waitForResponse(
    (result) =>
      result.url().endsWith("/api/retention/estimate") &&
      result.request().postDataJSON().method.mobile.b === "MeOH",
  );
  await page
    .getByRole("combobox", { name: "B 液（有機溶劑）", exact: true })
    .selectOption("MeOH");
  expect(
    (await (await refreshed).json()).condition_differences.some(
      (difference: string) => difference.includes("B 液"),
    ),
  ).toBeTruthy();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await expect(
    page.getByRole("button", { name: "重新估算所有自動來源" }),
  ).toBeEnabled();
  const recomputed = page.waitForResponse((result) =>
    result.url().endsWith("/api/retention/estimate"),
  );
  await page.getByRole("button", { name: "重新估算所有自動來源" }).click();
  expect((await recomputed).ok()).toBeTruthy();
  await expect(
    page.getByRole("button", { name: "執行模擬", exact: false }).first(),
  ).toBeEnabled();
  await expect(page.getByLabel("logKw Manual", { exact: true })).toHaveValue(
    "2",
  );
  await expect(
    page.getByLabel("logKw Calibration", { exact: true }),
  ).toHaveValue("2.5");
  await expect(
    page.getByLabel("logKw Generic ion", { exact: true }),
  ).toHaveValue("1.234");
  const manual = page
    .locator("article")
    .filter({ has: page.getByLabel("已存 SMILES Manual", { exact: true }) });
  const explicit = page.waitForResponse(
    (result) =>
      result.url().endsWith("/api/retention/estimate") &&
      result.request().postDataJSON().smiles === caffeine,
  );
  await manual.getByRole("button", { name: "重新估算", exact: true }).click();
  expect((await (await explicit).json()).tier).toBe("A");
  await expect(page.getByTestId("tier-manual")).toHaveText("實測曲線");
  await expect(page.getByTestId("tier-calibration")).toContainText("實驗校正");
});

test("a delayed real estimate cannot overwrite parameters manually edited while it was running", async ({
  page,
}) => {
  test.setTimeout(120000);
  let release!: () => void;
  let reached!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const fetched = new Promise<void>((resolve) => {
    reached = resolve;
  });
  await page.route("**/api/retention/estimate", async (route) => {
    const response = await route.fetch();
    reached();
    await gate;
    await route.fulfill({ response });
  });
  await page.goto("/");
  await page.getByLabel("化合物名稱", { exact: true }).fill("Concurrent edit");
  await page.getByLabel("SMILES", { exact: true }).fill("CCO");
  await page.getByRole("button", { name: "新增化合物", exact: true }).click();
  await fetched;
  await page.getByLabel("logKw Concurrent edit", { exact: true }).fill("1.7");
  await page.getByLabel("S Concurrent edit", { exact: true }).fill("3.2");
  release();
  await expect(
    page.getByRole("button", { name: "執行模擬", exact: false }).first(),
  ).toBeEnabled();
  await expect(
    page.getByLabel("logKw Concurrent edit", { exact: true }),
  ).toHaveValue("1.7");
  const saved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("elusim-project")!).compounds.find(
      (compound: any) => compound.name === "Concurrent edit",
    ),
  );
  expect(saved.parameter_tier).toBe("M");
  expect(saved.s).toBe(3.2);
});
