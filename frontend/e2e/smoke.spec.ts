import { test, expect, type Page } from "@playwright/test";

/**
 * Real browser -> real Next.js app -> real FastAPI backend -> real trained
 * artifact -> real SQLite. No mocked responses. Requires the M1 model
 * artifact to exist (see playwright.config.ts and ../ml/README).
 */

async function selectOption(page: Page, triggerSelector: string, optionText: string) {
  await page.click(triggerSelector);
  const listbox = page.locator('[role="listbox"]:visible').last();
  await listbox.getByRole("option", { name: optionText, exact: true }).click();
}

test.describe.serial("incident submission -> prediction -> history flow", () => {
  test("home page surfaces the synthetic-model disclosure", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.getByText("Synthetic demonstration model")).toBeVisible();
  });

  test("submitting a clear-signal incident returns a real, correct prediction", async ({
    page,
  }) => {
    await page.goto("/");
    await page.fill("#title", "Login fails with a 401");
    await page.fill(
      "#description",
      "Users cannot sign in via SSO, seeing a 401 error on the auth service in production.",
    );
    await selectOption(page, "#impact", "High");
    await selectOption(page, "#urgency", "High");
    await page.click('button[type="submit"]');

    await expect(page.getByText("Authentication Access")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/^P[1-4]$/)).toBeVisible();
    await expect(page.getByText("Not a calibrated confidence score")).toBeVisible();
  });

  test("an ambiguous incident with no impact/urgency is flagged for review with undetermined priority", async ({
    page,
  }) => {
    await page.goto("/");
    await page.fill("#title", "System issue reported by support");
    await page.fill(
      "#description",
      "Users report an issue affecting multiple customers, needs investigation, was flagged by monitoring.",
    );
    await page.click('button[type="submit"]');

    await expect(page.getByText("Flagged for human review", { exact: true })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("Undetermined — needs review")).toBeVisible();
  });

  test("client-side validation blocks a too-short title before hitting the API", async ({
    page,
  }) => {
    await page.goto("/");
    await page.fill("#title", "a");
    await page.fill("#description", "short");
    await page.click('button[type="submit"]');
    await expect(page.getByText("Title must be at least 3 characters.")).toBeVisible();
  });

  test("history page lists the incidents just submitted, persisted in SQLite", async ({
    page,
  }) => {
    await page.goto("/history");
    // >= 2, not ==2: the backend/DB is shared across spec files in this
    // config, so other suites (e.g. feedback.spec.ts) may have already
    // added their own incidents. This test only needs to confirm ITS two
    // submissions above actually persisted, not that it's the only writer.
    // expect.poll (not a one-shot count) because the client-side fetch to
    // /api/v1/incidents happens after networkidle already resolved.
    await expect
      .poll(() => page.locator("table tbody tr").count(), { timeout: 15_000 })
      .toBeGreaterThanOrEqual(2);
  });

  test("clicking into history opens the real persisted record", async ({ page }) => {
    await page.goto("/history", { waitUntil: "networkidle" });
    await page.locator("table tbody tr a").first().click();
    await page.waitForURL(/\/incidents\//);
    await expect(page.getByText("Advisory priority")).toBeVisible({ timeout: 15_000 });
  });

  test("an unknown incident id shows a real 404-backed error state", async ({ page }) => {
    await page.goto("/incidents/does-not-exist", { waitUntil: "networkidle" });
    await expect(page.getByText("No incident found with this ID.")).toBeVisible();
  });
});
