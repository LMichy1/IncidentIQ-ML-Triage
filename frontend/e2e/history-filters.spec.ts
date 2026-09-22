import { test, expect } from "@playwright/test";

/**
 * Real browser -> real backend -> real SQLite review-status filtering.
 * Shares one backend/database with smoke.spec.ts and feedback.spec.ts (per
 * playwright.config.ts), so assertions key off specific incident titles
 * this file creates rather than exact counts.
 */

const CLEAR_SIGNAL_TITLE = "Filter-test clear-signal incident";
const PENDING_TITLE = "Filter-test pending-review incident";
const REVIEWED_TITLE = "Filter-test reviewed incident";

async function submitIncident(page: import("@playwright/test").Page, title: string, description: string) {
  await page.goto("/");
  await page.fill("#title", title);
  await page.fill("#description", description);
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Advisory priority", { timeout: 15_000 });
  const href = await page.locator('a:has-text("View full record")').getAttribute("href");
  if (!href) throw new Error("detail link not found after submission");
  return href;
}

test.describe.serial("incident history review-status filters", () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();

    await submitIncident(
      page,
      CLEAR_SIGNAL_TITLE,
      "Users cannot sign in via SSO, seeing a 401 error on the auth service in production.",
    );

    await submitIncident(
      page,
      PENDING_TITLE,
      "Users report an issue affecting multiple customers, needs investigation, was flagged by monitoring.",
    );

    const reviewedHref = await submitIncident(
      page,
      REVIEWED_TITLE,
      "Users report an issue affecting multiple customers, needs investigation, was flagged by monitoring.",
    );
    await page.goto(reviewedHref);
    await page.click('button[type="submit"]:has-text("Submit feedback")');
    await expect(page.getByText("Feedback saved")).toBeVisible({ timeout: 10_000 });

    await page.close();
  });

  test("'All' shows every incident regardless of review state", async ({ page }) => {
    await page.goto("/history", { waitUntil: "networkidle" });
    await expect(page.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText(CLEAR_SIGNAL_TITLE)).toBeVisible();
    await expect(page.getByText(PENDING_TITLE)).toBeVisible();
    await expect(page.getByText(REVIEWED_TITLE)).toBeVisible();
  });

  test("'Pending review' excludes both non-flagged and already-reviewed incidents", async ({ page }) => {
    await page.goto("/history", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Pending review" }).click();
    await expect(page.getByRole("button", { name: "Pending review" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await expect(page.getByText(PENDING_TITLE)).toBeVisible();
    await expect(page.getByText(CLEAR_SIGNAL_TITLE)).not.toBeVisible();
    await expect(page.getByText(REVIEWED_TITLE)).not.toBeVisible();
  });

  test("'Reviewed' only shows incidents with feedback", async ({ page }) => {
    await page.goto("/history", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Reviewed", exact: true }).click();
    await expect(page.getByRole("button", { name: "Reviewed", exact: true })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await expect(page.getByText(REVIEWED_TITLE)).toBeVisible();
    await expect(page.getByText(CLEAR_SIGNAL_TITLE)).not.toBeVisible();
    await expect(page.getByText(PENDING_TITLE)).not.toBeVisible();
  });

  test("switching filters resets to the first page and the filter is retained in subsequent requests", async ({
    page,
  }) => {
    await page.goto("/history", { waitUntil: "networkidle" });

    const requestPromise = page.waitForRequest((req) =>
      req.url().includes("/api/v1/incidents") && req.url().includes("review_status=pending_review"),
    );
    await page.getByRole("button", { name: "Pending review" }).click();
    const request = await requestPromise;
    expect(request.url()).toContain("offset=0");
    expect(request.url()).toContain("review_status=pending_review");
  });

  test("a filter with no matches shows a filter-specific empty state, not the generic one", async ({
    page,
  }) => {
    // The real backend always has at least one "reviewed" incident from
    // this file's own setup, so a genuinely empty real response can't be
    // relied on here — intercept just this one request to deterministically
    // exercise the frontend's empty-state rendering for a specific filter,
    // without touching how any other test talks to the real backend.
    await page.route("**/api/v1/incidents?*review_status=reviewed*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, limit: 10, offset: 0, review_status: "reviewed" }),
      }),
    );

    await page.goto("/history", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Reviewed", exact: true }).click();

    await expect(page.getByText("No incidents have been reviewed yet.")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText("No incidents submitted yet.")).not.toBeVisible();
  });
});
