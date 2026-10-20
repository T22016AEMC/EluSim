import { test as base, expect, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { compatibleMethod } from "../src/ModelConditions";

export { expect, type Page };

const budgetFile = resolve(
  import.meta.dirname,
  "../test-results/api-post-times.json",
);
let reservations = Promise.resolve();

/** Pace real POSTs below the production 30/minute limit across project workers. */
async function reservePost(): Promise<void> {
  const reservation = reservations.then(async () => {
    mkdirSync(dirname(budgetFile), { recursive: true });
    let timestamps: number[] = [];
    try {
      timestamps = JSON.parse(readFileSync(budgetFile, "utf8"));
    } catch {
      timestamps = [];
    }
    let now = Date.now();
    timestamps = timestamps.filter((timestamp) => now - timestamp < 61000);
    if (timestamps.length >= 25) {
      await new Promise((resolve) =>
        setTimeout(resolve, Math.max(0, timestamps[0] + 61000 - now)),
      );
      now = Date.now();
      timestamps = timestamps.filter((timestamp) => now - timestamp < 61000);
    }
    timestamps.push(now);
    writeFileSync(budgetFile, JSON.stringify(timestamps), "utf8");
  });
  reservations = reservation.catch(() => {});
  return reservation;
}

/** Forward genuine requests unchanged; never replace scientific API responses. */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route("**/api/**", async (route) => {
      if (route.request().method() === "POST") await reservePost();
      if (page.isClosed() || route.request().failure()) return;
      try {
        await route.continue();
      } catch (error) {
        if (!page.isClosed() && !route.request().failure()) throw error;
      }
    });
    await use(page);
  },
});

/** Load the existing curve examples as browser-local test input, not a source picker. */
export async function curveExamples(page: Page) {
  const response = await page.request.get("/api/retention/database");
  const database = await response.json();
  const conditions = await (
    await page.request.get("/api/retention/conditions")
  ).json();
  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("elusim-project")!),
  );
  const fixture = { ...stored, ...compatibleMethod(stored, conditions) };
  await page.evaluate(
    async ({ examples, stored }) => {
      stored.compounds = examples.map((example: any, index: number) => ({
        id: "curve-" + index,
        name: ["Anthranilic acid", "Caffeine", "Diethyl malonate"][index],
        smiles: example.smiles,
        kind: "small_molecule",
        logkw: null,
        s: null,
        source: "insufficient_data",
        parameter_origin: "prediction",
        mixture_parts: [5, 3, 2][index],
        response_factor: 1,
      }));
      localStorage.setItem("elusim-project", JSON.stringify(stored));
    },
    { examples: database.examples, stored: fixture },
  );
  await page.reload();
}
