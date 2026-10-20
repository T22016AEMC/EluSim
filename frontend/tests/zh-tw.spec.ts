import { test, expect } from "./fixtures";
import { t } from "../src/i18n/zh-TW";

/** Visit every workspace and report presentation leftovers only. */
test("desktop empty project, explicit demo and all-workspace text inventory", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".compound-grid article")).toHaveCount(0);
  for (const tab of [
    "Compounds",
    "LC Mode & Column",
    "Mobile Phase & Gradient",
    "Chromatogram Simulation",
    "Gradient Optimization",
    "Experimental Calibration",
    "Model & Column Library",
    "Retention Prediction",
    "UV-Vis / DAD",
  ]) {
    await page
      .getByRole("navigation")
      .getByRole("button", { name: t(tab), exact: false })
      .click();
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(
      /色譜|保留時間|色譜柱|柱子|分辨率|理論塔板數|駐留體積|死體積|進樣量|校準|優化|仿真|默認|導出|導入|軟件|信息/,
    );
    const properNames = [
      "Agilent Eclipse Plus C18",
      "Waters, ACQUITY UPLC BEH C18",
    ];
    const preserved = properNames.filter((name) => text.includes(name));
    const translatedText = properNames.reduce(
      (value, name) => value.replaceAll(name, ""),
      text,
    );
    const english =
      translatedText.match(
        /\b[A-Za-z][A-Za-z-]*(?: [A-Za-z][A-Za-z-]*){2,}/g,
      ) ?? [];
    console.log("PRESERVED PRODUCT NAMES", tab, JSON.stringify(preserved));
    console.log("ENGLISH INVENTORY", tab, JSON.stringify(english));
    expect(english).toEqual([]);
  }
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await page
    .getByRole("button", { name: t("Load demo mixture"), exact: true })
    .click();
  await expect(page.locator(".compound-grid article")).toHaveCount(3);
  await expect(
    page.getByLabel("logKw 示範化合物 1", { exact: true }),
  ).toHaveValue("2");
  await expect(page.getByLabel("Workflow", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Parameter source", { exact: true }),
  ).toHaveCount(0);
});

/** Check naming, exports and solvent labels without judging prediction values. */
test("desktop automatic names, live rename, source descriptions and solvent labels", async ({
  page,
}) => {
  test.setTimeout(180000);
  await page.goto("/");
  for (const [index, smiles] of ["CCO", "COCOC"].entries()) {
    await page.getByLabel("SMILES", { exact: true }).fill(smiles);
    await page.getByRole("button", { name: "新增化合物", exact: true }).click();
    await expect(
      page.getByLabel("logKw 化合物 " + (index + 1), { exact: true }),
    ).not.toHaveValue("", { timeout: 30000 });
  }
  const names = page.locator(".compound-grid .section-head input");
  await expect(names.nth(0)).toHaveValue("化合物 1");
  await expect(names.nth(1)).toHaveValue("化合物 2");
  await expect(page.locator(".source-badge").first()).toHaveText(
    /實測曲線|模型預測|通用估算/,
  );
  await page
    .getByRole("button", { name: "執行模擬", exact: false })
    .first()
    .click();
  await expect(page.getByTestId("chromatogram")).toBeVisible({
    timeout: 45000,
  });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await names.nth(0).fill("M-I");
  await names.nth(1).fill("PGMEA");
  const pending = page.waitForEvent("download");
  await page
    .getByRole("button", { name: t("Export parameter CSV"), exact: true })
    .click();
  const file = await pending;
  expect(file.suggestedFilename()).toBe("EluSim_參數.csv");
  const { readFile } = await import("node:fs/promises");
  const csv = await readFile((await file.path())!, "utf8");
  expect(csv.split("\r\n")[0]).toContain("tier,tier_label");
  expect(csv).toContain('"M-I"');
  expect(csv).toContain('"PGMEA"');
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "層析模擬", exact: false })
    .click();
  await expect(page.getByTestId("chromatogram")).toHaveAttribute(
    "aria-label",
    /M-I.*PGMEA/,
  );
  await expect(page.getByTestId("chromatogram")).not.toHaveAttribute(
    "aria-label",
    /\[[ABCDM]\]/,
  );
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "流動相與梯度", exact: false })
    .click();
  await page
    .getByRole("combobox", { name: "B 液（有機溶劑）", exact: true })
    .selectOption("MeOH");
  await expect(
    page.getByLabel("MeOH（%） 節點 1", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "梯度最佳化", exact: false })
    .click();
  await expect(
    page.getByLabel("起始 MeOH（%）：最小", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("結束 MeOH（%）：最大", { exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("combination-count")).toContainText("組");
  await page.getByRole("button", { name: "重設", exact: true }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "化合物", exact: false })
    .click();
  await expect(page.locator(".compound-grid article")).toHaveCount(0);
});
