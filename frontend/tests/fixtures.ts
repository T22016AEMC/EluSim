import { test as base, expect, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

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
