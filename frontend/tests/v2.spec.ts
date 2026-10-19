import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const inputs = JSON.parse(
  readFileSync(new URL("./v2-inputs.json", import.meta.url), "utf8"),
);
test("V2 method-specific Rt keeps its explicit model and exact-method gate", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Retention Prediction", exact: false })
    .click();
  await page.getByLabel("Retention SMILES").fill(inputs["report0259-rt"]);
  await page
    .getByRole("button", { name: "Load exact RepoRT0259 method" })
    .click();
  await page
    .getByRole("button", { name: "Predict retention", exact: true })
    .click();
  await expect(page.getByTestId("retention-result")).toContainText("min", {
    timeout: 30000,
  });
  await expect(
    page.getByText("Experimental model prediction", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "LC Mode & Column", exact: false })
    .click();
  await page.getByLabel("Column length (mm)", { exact: true }).fill("150");
  await page
    .getByRole("button", { name: "Retention Prediction", exact: false })
    .click();
  await page.getByLabel("Retention model").selectOption("report0259-rt");
  await page.getByLabel("Retention SMILES").fill(inputs["report0259-rt"]);
  await page
    .getByRole("button", { name: "Predict retention", exact: true })
    .click();
  await expect(page.getByTestId("retention-result")).toContainText("Withheld", {
    timeout: 30000,
  });
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width + 1,
      page.viewportSize()!.width,
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
    .getByRole("button", { name: "UV-Vis / DAD", exact: false })
    .click();
  await page
    .getByLabel("UV SMILES", { exact: true })
    .fill(inputs["pnnl-uv-shape"]);
  await page
    .getByRole("button", { name: "Analyze UV structure", exact: true })
    .click();
  await expect(page.getByTestId("uv-status")).toHaveText(
    "Experimental model prediction",
    { timeout: 30000 },
  );
  await expect(page.getByTestId("uv-chart").locator("canvas")).toBeVisible();
  await expect(page.getByAltText("UV molecular structure")).toBeVisible();
  await page
    .getByLabel("Import UV CSV")
    .setInputFiles({
      name: "observed.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(
        "wavelength_nm,intensity\n220,0.1\n250,0.8\n400,0.02\n",
      ),
    });
  await expect(
    page.getByText("observed.csv · Experimental · 3 points · absorbance"),
  ).toBeVisible();
  for (const name of [
    "Export UV CSV",
    "Export UV PNG",
    "Export UV SVG",
    "Export original data JSON",
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
  await page
    .getByRole("button", { name: "Analyze UV structure", exact: true })
    .click();
  await expect(page.getByTestId("uv-status")).toHaveText(
    "Qualitative screening",
    { timeout: 30000 },
  );
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width + 1,
      page.viewportSize()!.width,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
