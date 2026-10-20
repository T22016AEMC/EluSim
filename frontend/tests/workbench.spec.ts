import { test, expect } from "./fixtures";
test("RDKit, multi-node gradient, simulation, optimization and refresh", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "載入示範混合物", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "化合物", exact: true }),
  ).toBeVisible();
  await page.getByLabel("化合物名稱", { exact: true }).fill("caffeine");
  await page.getByRole("button", { name: "計算 RDKit 分子描述子" }).click();
  await expect(page.getByText("C8H10N4O2", { exact: true })).toBeVisible({
    timeout: 30000,
  });
  // Keep the default three synthetic parameterized compounds as the science fixture.
  await page
    .getByRole("button", { name: "流動相與梯度", exact: false })
    .click();
  await page.getByLabel("ACN（%） 節點 2", { exact: true }).fill("85");
  await page.getByLabel("時間（min） 節點 2", { exact: true }).fill("12");
  await page
    .getByRole("button", { name: "執行模擬", exact: false })
    .first()
    .click();
  await expect(page.getByRole("heading", { name: "模擬層析圖" })).toBeVisible({
    timeout: 45000,
  });
  await expect(
    page.getByTestId("chromatogram").locator("canvas"),
  ).toBeVisible();
  await expect(page.getByText("3 / 3", { exact: true })).toBeVisible();
  await page.getByLabel("疊加前次結果").check();
  await page.getByTestId("chromatogram").hover();
  await page.mouse.wheel(0, -120);
  await page.getByRole("button", { name: "梯度最佳化", exact: false }).click();
  await page.getByLabel("梯度時間（min）：最小", { exact: true }).fill("8");
  await page.getByLabel("梯度時間（min）：最大", { exact: true }).fill("12");
  await page.getByLabel("梯度時間（min）：格數", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "產生分離度地圖", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "候選梯度" })).toBeVisible({
    timeout: 45000,
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "套用候選梯度 1", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "模擬層析圖" })).toBeVisible({
    timeout: 45000,
  });
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
    page.getByRole("heading", { name: "化合物", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("logKw 示範化合物 1")).toHaveValue("2");
  expect(errors).toEqual([]);
});
test("unsupported modes never produce fictitious predictions", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "載入示範混合物", exact: true })
    .click();
  await page
    .getByRole("button", { name: "層析模式與管柱", exact: false })
    .click();
  await page
    .getByRole("button", { name: "親水作用層析（HILIC）", exact: false })
    .click();
  await page
    .getByRole("button", { name: "執行模擬", exact: false })
    .first()
    .click();
  await expect(page.getByTestId("chromatogram")).toHaveCount(0);
  await expect(page.getByText("0 / 3", { exact: true })).toBeVisible({
    timeout: 45000,
  });
  await expect(
    page
      .getByText(
        "HILIC：尚未啟用獨立定量模型。",
      )
      .first(),
  ).toBeVisible();
});
