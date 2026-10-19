import { test, expect } from "@playwright/test";
test("real curve compounds resolve by ID; 5:3:2 area composition; gradient and ratio dataflow", async ({
  page,
}) => {
  // End-to-end workflow makes several separately bounded public API calls.
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Retention Prediction", exact: false })
    .click();
  await page
    .getByRole("button", { name: "Load three experimental curve compounds" })
    .click();
  await page
    .getByRole("navigation", { name: "Workspaces" })
    .getByRole("button", { name: "Compounds", exact: false })
    .click();
  await expect(
    page.getByLabel("Mixture parts Caffeine", { exact: true }),
  ).toHaveValue("3");
  await page
    .getByRole("button", { name: "Resolve retention from structures" })
    .click();
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
      .getByRole("button", { name: "Run simulation", exact: false })
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
    .getByRole("button", { name: "Mobile Phase & Gradient", exact: false })
    .click();
  await page.getByLabel("Time (min) node 2", { exact: true }).fill("15");
  const changed = await run();
  expect(changed.peaks[0].rt_min).not.toBe(initial.peaks[0].rt_min);
  await page
    .getByRole("navigation", { name: "Workspaces" })
    .getByRole("button", { name: "Compounds", exact: false })
    .click();
  await page.getByLabel("Batch relative parts").fill("10:3:2");
  await page.getByRole("button", { name: "Apply batch composition" }).click();
  const ratio = await run();
  expect(ratio.peaks[0].peak_area).toBeCloseTo(10 / 15, 8);
  expect(ratio.peaks.map((p: any) => p.rt_min)).toEqual(
    changed.peaks.map((p: any) => p.rt_min),
  );
  await page
    .getByRole("button", { name: "Gradient Optimization", exact: false })
    .click();
  await page.getByLabel("Gradient durations", { exact: true }).fill("8,12");
  await page
    .getByRole("button", { name: "Optimize gradient", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Candidate 1", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page
    .getByRole("navigation", { name: "Workspaces" })
    .getByRole("button", { name: "Compounds", exact: false })
    .click();
  await page.getByLabel("logKw Caffeine", { exact: true }).fill("1.234");
  await page
    .getByRole("button", { name: "Resolve retention from structures" })
    .click();
  await expect(page.getByRole("status")).toHaveCount(0, { timeout: 30000 });
  await expect(page.getByLabel("logKw Caffeine", { exact: true })).toHaveValue(
    "1.234",
  );
  await page
    .getByRole("button", { name: "LC Mode & Column", exact: false })
    .click();
  await page.getByLabel("Column temperature (°C)", { exact: true }).fill("30");
  await page
    .getByRole("navigation", { name: "Workspaces" })
    .getByRole("button", { name: "Compounds", exact: false })
    .click();
  await expect(
    page
      .getByText("Retention condition differences:", { exact: false })
      .first(),
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
test("scoped QSRR fills a heldout compound; manual edits remain protected", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Retention Prediction", exact: false })
    .click();
  await page
    .getByRole("button", { name: "Load scoped curve conditions" })
    .click();
  const compounds = () =>
    page
      .getByRole("navigation", { name: "Workspaces" })
      .getByRole("button", { name: "Compounds", exact: false });
  await compounds().click();
  await page
    .getByLabel("Compound name", { exact: true })
    .fill("Heldout structure");
  await page
    .getByLabel("SMILES", { exact: true })
    .fill(inputs["lss-parameters"]);
  await page.getByRole("button", { name: "Add compound", exact: true }).click();
  await expect(
    page.getByLabel("logKw Heldout structure", { exact: true }),
  ).not.toHaveValue("", { timeout: 30000 });
  await page
    .getByRole("button", { name: "Retention Prediction", exact: false })
    .click();
  await page
    .getByLabel("Retention compound")
    .selectOption({ label: "Heldout structure" });
  await page.getByLabel("Retention model").selectOption("lss-parameters");
  await page
    .getByRole("button", { name: "Predict retention", exact: true })
    .click();
  await expect(page.getByTestId("retention-result")).not.toContainText(
    "Withheld",
    { timeout: 30000 },
  );
  await expect(
    page.getByText("Experimental model prediction", { exact: true }),
  ).toBeVisible();
  const predicted = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("elusim-project")!).compounds.find(
      (c: any) => c.name === "Heldout structure",
    ),
  );
  expect(predicted.logkw).not.toBeNull();
  expect(
    predicted.retention_provenance.applicability.seen_in_training,
  ).toBeFalsy();
  expect(predicted.parameter_origin).toBe("prediction");
  await compounds().click();
  await page
    .getByLabel("logKw Heldout structure", { exact: true })
    .fill("1.234");
  await page
    .getByRole("button", { name: "Retention Prediction", exact: false })
    .click();
  await page
    .getByLabel("Retention compound")
    .selectOption({ label: "Heldout structure" });
  await page
    .getByRole("button", { name: "Predict retention", exact: true })
    .click();
  await expect(
    page.locator("p.warn").filter({ hasText: "Manual parameters preserved;" }),
  ).toBeVisible({ timeout: 30000 });
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
