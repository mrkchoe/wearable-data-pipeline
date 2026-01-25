import { describe, expect, it } from "vitest";
import { EventName, EventSchema, EVENT_SCHEMA_VERSION } from "../../../types/events";

const baseEvent = {
  event_id: "7cf57d5f-1a1e-4be6-9c66-7edb7c2b7a11",
  schema_version: EVENT_SCHEMA_VERSION,
  client_ts: new Date().toISOString(),
  user_id: "user-1",
  session_id: "session-1",
  device_id: null,
  page: "/",
  referrer: null,
  app_version: "0.1.0",
  environment: "local",
  source: "web",
  correlation_id: "5f42d7e9-b7d1-4a02-a6a3-8aa2b7cd4134"
};

describe("event schema", () => {
  it("accepts valid events", () => {
    const event = EventSchema.parse({
      ...baseEvent,
      event_name: EventName.PageView,
      page_title: "Dashboard",
      entry_point: "direct"
    });

    expect(event.event_name).toBe(EventName.PageView);
  });

  it("rejects events without user or anonymous id", () => {
    expect(() =>
      EventSchema.parse({
        ...baseEvent,
        user_id: undefined,
        anonymous_id: undefined,
        event_name: EventName.PageView,
        page_title: "Dashboard",
        entry_point: "direct"
      })
    ).toThrow(/user_id or anonymous_id/);
  });
});
