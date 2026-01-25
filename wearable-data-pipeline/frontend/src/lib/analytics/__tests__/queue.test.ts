import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { createQueueStore } from "../queue";
import { EventName } from "../../../types/events";

const baseEvent = {
  event_id: "test-event-1",
  schema_version: "1.0.0",
  client_ts: new Date().toISOString(),
  user_id: "user-1",
  anonymous_id: undefined,
  session_id: "session-1",
  device_id: null,
  page: "/",
  referrer: null,
  app_version: "0.1.0",
  environment: "local",
  source: "web",
  correlation_id: "corr-1"
};

describe("queue store", () => {
  it("persists and retrieves events", async () => {
    const queue = await createQueueStore();
    await queue.enqueue({
      ...baseEvent,
      event_name: EventName.PageView,
      page_title: "Dashboard",
      entry_point: "direct",
      attempts: 0,
      next_attempt_at: Date.now(),
      created_at: Date.now()
    });

    const batch = await queue.peekBatch(10, Date.now(), 5);
    expect(batch).toHaveLength(1);
    expect(batch[0].event_id).toBe("test-event-1");
  });
});
