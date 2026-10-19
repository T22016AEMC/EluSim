import { test, expect } from "./fixtures";
test("RDKit, multi-node gradient, simulation, optimization and refresh", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Compounds", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Compound name", { exact: true }).fill("caffeine");
  await page
    .getByRole("button", { name: "Calculate RDKit descriptors" })
    .click();
  await expect(page.getByText("C8H10N4O2", { exact: true })).toBeVisible({
    timeout: 30000,
  });
  // Keep the default three synthetic parameterized compounds as the science fixture.
  await page
    .getByRole("button", { name: "Mobile Phase & Gradient", exact: false })
    .click();
  await page.getByLabel("B (%) node 2", { exact: true }).fill("85");
  await page.getByLabel("Time (min) node 2", { exact: true }).fill("12");
  await page
    .getByRole("button", { name: "Run simulation", exact: false })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Simulated Chromatogram" }),
  ).toBeVisible({ timeout: 45000 });
  await expect(
    page.getByTestId("chromatogram").locator("canvas"),
  ).toBeVisible();
  await expect(page.getByText("3 / 3", { exact: true })).toBeVisible();
  await page.getByLabel("Overlay previous run").check();
  await page.getByTestId("chromatogram").hover();
  await page.mouse.wheel(0, -120);
  await page
    .getByRole("button", { name: "Gradient Optimization", exact: false })
    .click();
  await page.getByLabel("Gradient time (min) min", { exact: true }).fill("8");
  await page.getByLabel("Gradient time (min) max", { exact: true }).fill("12");
  await page.getByLabel("Gradient time (min) steps", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Generate resolution map", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Top candidates" }),
  ).toBeVisible({ timeout: 45000 });
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Apply candidate 1", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Simulated Chromatogram" }),
  ).toBeVisible({ timeout: 45000 });
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width + 1,
      page.viewportSize()!.width,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../artifacts/" + info.project.name + "-workbench.png",
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Compounds", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("logKw Synthetic A")).toHaveValue("2");
  expect(errors).toEqual([]);
});
test("unsupported modes never produce fictitious predictions", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "LC Mode & Column", exact: false })
    .click();
  await page.getByRole("button", { name: "HILIC", exact: false }).click();
  await page
    .getByRole("button", { name: "Run simulation", exact: false })
    .first()
    .click();
  await expect(page.getByTestId("chromatogram")).toHaveCount(0);
  await expect(page.getByText("0 / 3", { exact: true })).toBeVisible({
    timeout: 45000,
  });
  await expect(
    page.getByText("HILIC: independent quantitative model not enabled").first(),
  ).toBeVisible();
});
