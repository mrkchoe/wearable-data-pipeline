import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";

export const EVENT_SCHEMA_VERSION = "1.0.0" as const;

export enum EventName {
  PageView = "page_view",
  Identify = "identify",
  ConnectDeviceStarted = "connect_device_started",
  ConnectDeviceSucceeded = "connect_device_succeeded",
  ConnectDeviceFailed = "connect_device_failed",
  SyncRequested = "sync_requested",
  SyncCompleted = "sync_completed",
  SyncFailed = "sync_failed",
  MetricViewed = "metric_viewed",
  GoalCreated = "goal_created",
  ExportClicked = "export_clicked",
  UiError = "ui_error",
  ApiError = "api_error",
  PerfLcp = "perf_lcp",
  PerfApiLatency = "perf_api_latency"
}

const EnvironmentSchema = z.enum(["local", "dev", "staging", "prod"]);
const VendorSchema = z.enum([
  "fitbit",
  "apple_health",
  "garmin",
  "oura",
  "whoop",
  "other"
]);
const MetricTypeSchema = z.enum([
  "steps",
  "sleep",
  "calories",
  "distance",
  "active_minutes"
]);
const DateRangeSchema = z.enum(["day", "week", "month", "custom"]);
const SyncStatusSchema = z.enum(["requested", "in_progress", "completed", "failed"]);

const BaseEventSchema = z
  .object({
    event_id: z.string().uuid(),
    schema_version: z.literal(EVENT_SCHEMA_VERSION),
    client_ts: z.string().datetime(),
    user_id: z.string().optional(),
    anonymous_id: z.string().optional(),
    session_id: z.string(),
    device_id: z.string().nullable(),
    page: z.string(),
    referrer: z.string().nullable(),
    app_version: z.string(),
    environment: EnvironmentSchema,
    source: z.literal("web"),
    correlation_id: z.string().uuid()
  })
  .strict();

const PageViewSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.PageView),
  page_title: z.string(),
  entry_point: z.string()
}).strict();

const IdentifySchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.Identify),
  user_status: z.enum(["known", "merged", "anonymous"])
}).strict();

const ConnectDeviceStartedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.ConnectDeviceStarted),
  vendor: VendorSchema
}).strict();

const ConnectDeviceSucceededSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.ConnectDeviceSucceeded),
  vendor: VendorSchema,
  device_model: z.string()
}).strict();

const ConnectDeviceFailedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.ConnectDeviceFailed),
  vendor: VendorSchema,
  error_code: z.string(),
  error_message: z.string()
}).strict();

const SyncRequestedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.SyncRequested),
  vendor: VendorSchema,
  date_range: DateRangeSchema,
  sync_status: SyncStatusSchema
}).strict();

const SyncCompletedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.SyncCompleted),
  vendor: VendorSchema,
  date_range: DateRangeSchema,
  sync_status: SyncStatusSchema,
  records_synced: z.number().int().nonnegative()
}).strict();

const SyncFailedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.SyncFailed),
  vendor: VendorSchema,
  date_range: DateRangeSchema,
  sync_status: SyncStatusSchema,
  error_code: z.string(),
  error_message: z.string()
}).strict();

const MetricViewedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.MetricViewed),
  metric_type: MetricTypeSchema,
  date_range: DateRangeSchema,
  vendor: VendorSchema
}).strict();

const GoalCreatedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.GoalCreated),
  metric_type: MetricTypeSchema,
  target_value: z.number().nonnegative(),
  target_unit: z.string(),
  date_range: DateRangeSchema
}).strict();

const ExportClickedSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.ExportClicked),
  export_format: z.enum(["csv", "json"]),
  date_range: DateRangeSchema,
  vendor: VendorSchema
}).strict();

const UiErrorSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.UiError),
  component: z.string(),
  error_code: z.string(),
  error_message: z.string(),
  severity: z.enum(["info", "warning", "error"])
}).strict();

const ApiErrorSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.ApiError),
  endpoint: z.string(),
  status_code: z.number().int().nonnegative(),
  error_code: z.string(),
  error_message: z.string()
}).strict();

const PerfLcpSchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.PerfLcp),
  lcp_ms: z.number().nonnegative(),
  page_type: z.string()
}).strict();

const PerfApiLatencySchema = BaseEventSchema.extend({
  event_name: z.literal(EventName.PerfApiLatency),
  api_latency_ms: z.number().nonnegative(),
  endpoint: z.string(),
  status_code: z.number().int().nonnegative()
}).strict();

export const EventSchema = z.discriminatedUnion("event_name", [
  PageViewSchema,
  IdentifySchema,
  ConnectDeviceStartedSchema,
  ConnectDeviceSucceededSchema,
  ConnectDeviceFailedSchema,
  SyncRequestedSchema,
  SyncCompletedSchema,
  SyncFailedSchema,
  MetricViewedSchema,
  GoalCreatedSchema,
  ExportClickedSchema,
  UiErrorSchema,
  ApiErrorSchema,
  PerfLcpSchema,
  PerfApiLatencySchema
]).refine((data) => Boolean(data.user_id || data.anonymous_id), {
  message: "user_id or anonymous_id must be set"
});

export type AnalyticsEvent = z.infer<typeof EventSchema>;

export const BaseEventSchemaJson = zodToJsonSchema(BaseEventSchema, "BaseEvent");
export const EventSchemaJson = zodToJsonSchema(EventSchema, "AnalyticsEvent");
