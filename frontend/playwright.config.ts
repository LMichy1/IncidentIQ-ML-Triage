import { defineConfig } from "@playwright/test";

/**
 * Real browser-to-API integration tests. Requires the M1 model artifact to
 * exist (ml/artifacts/incident_category_classifier/0.1.0/) — see
 * ../ml/README and ../backend/README. Both servers are started here so
 * `npm run test:e2e` is self-contained given that artifact.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  // Turbopack dev cold-compiles each route on first request (~15-20s for
  // the first page in this project) — generous enough to cover that
  // without masking a genuine hang.
  expect: { timeout: 25_000 },
  use: {
    baseURL: "http://localhost:3100",
    navigationTimeout: 30_000,
  },
  webServer: [
    {
      command: "uv run uvicorn app.main:app --port 8100",
      cwd: "../backend",
      url: "http://localhost:8100/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { INCIDENTIQ_DB_PATH: "./e2e-test.sqlite3" },
    },
    {
      command: "npm run dev -- --port 3100",
      url: "http://localhost:3100",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { NEXT_PUBLIC_API_BASE_URL: "http://localhost:8100" },
    },
  ],
});
