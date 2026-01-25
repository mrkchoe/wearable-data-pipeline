import { expect, test } from "@playwright/test";

test("main flow emits analytics events", async ({ page }) => {
  const receivedEvents: string[] = [];

  await page.route("**/analytics", async (route) => {
    const body = route.request().postDataJSON() as { events?: Array<{ event_name: string }> };
    if (body?.events) {
      body.events.forEach((eventItem) => receivedEvents.push(eventItem.event_name));
    }
    await route.fulfill({ status: 200, body: JSON.stringify({ ok: true }) });
  });

  await page.goto("/");

  await page.getByRole("button", { name: "Identify user" }).click();
  await page.getByRole("button", { name: "Connect device" }).click();
  await page.getByRole("button", { name: "Sync" }).click();
  await page.getByRole("button", { name: "View metric" }).click();
  await page.getByRole("button", { name: "Create goal" }).click();
  await page.getByRole("button", { name: "Export" }).click();
  await page.getByRole("button", { name: "Trigger UI error" }).click();

  await page.waitForTimeout(6000);

  expect(receivedEvents).toContain("page_view");
  expect(receivedEvents).toContain("connect_device_started");
  expect(receivedEvents).toContain("sync_requested");
  expect(receivedEvents).toContain("metric_viewed");
  expect(receivedEvents).toContain("goal_created");
  expect(receivedEvents).toContain("export_clicked");
  expect(receivedEvents).toContain("ui_error");
});
