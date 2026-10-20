import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90000,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: "../artifacts/browser-tests.json" }],
  ],
  use: {
    baseURL: process.env.ELUSIM_BASE_URL || "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
  ],
});
