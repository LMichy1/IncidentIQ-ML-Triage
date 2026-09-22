import { test, expect } from "@playwright/test";

/**
 * Real browser -> real backend -> real SQLite feedback workflow. No mocks.
 * Runs against the same webServer-managed instances as smoke.spec.ts.
 */

async function submitIncidentAndOpenDetail(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.fill("#title", "Login fails with a 401");
  await page.fill(
    "#description",
    "Users cannot sign in via SSO, seeing a 401 error on the auth service in production.",
  );
  await page.click('button[type="submit"]');
  await expect(page.getByText("Authentication Access")).toBeVisible({ timeout: 15_000 });

  const href = await page.locator('a:has-text("View full record")').getAttribute("href");
  if (!href) throw new Error("detail link not found");
  await page.goto(href);
  await expect(page.getByText("Human review")).toBeVisible();
  return href;
}

test.describe.serial("human review feedback workflow", () => {
  test("confirming the original prediction is recorded without changing it", async ({
    page,
  }) => {
    await submitIncidentAndOpenDetail(page);

    await page.fill("#fb-reviewer", "alex");
    await page.fill("#fb-note", "Looks correct.");
    await page.click('button[type="submit"]:has-text("Submit feedback")');

    await expect(page.getByText("Feedback saved")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Review history (1)")).toBeVisible();
    await expect(page.getByText("Confirmed the original prediction and priority as-is.")).toBeVisible();
    // The original prediction card is unaffected by a confirmation.
    await expect(page.getByText("Authentication Access")).toBeVisible();
  });

  test("a correction is recorded as new history, not an overwrite", async ({ page }) => {
    const href = await submitIncidentAndOpenDetail(page);

    await page.click("#fb-category");
    await page
      .locator('[role="listbox"]:visible')
      .last()
      .getByRole("option", { name: "Security Vulnerability", exact: true })
      .click();
    await page.click("#fb-priority");
    await page
      .locator('[role="listbox"]:visible')
      .last()
      .getByRole("option", { name: "P1", exact: true })
      .click();
    await page.fill("#fb-note", "Actually a security issue.");
    await page.click('button[type="submit"]:has-text("Submit feedback")');

    await expect(page.getByText("Review history (1)")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Corrected category to Security Vulnerability/)).toBeVisible();
    await expect(page.getByText(/Corrected priority to P1/)).toBeVisible();

    // The original prediction/priority shown at the top is still untouched.
    await expect(page.getByText("Authentication Access").first()).toBeVisible();

    // Real persistence, not local component state: reload and re-fetch.
    await page.goto(href);
    await expect(page.getByText("Review history (1)")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Corrected category to Security Vulnerability/)).toBeVisible();
  });

  test("history table shows a reviewed indicator after feedback", async ({ page }) => {
    await page.goto("/history", { waitUntil: "networkidle" });
    await expect(page.getByText("Reviewed").first()).toBeVisible({ timeout: 10_000 });
  });
});
