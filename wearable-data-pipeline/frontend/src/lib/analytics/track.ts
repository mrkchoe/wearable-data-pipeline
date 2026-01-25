import { EventSchema, EventName, EVENT_SCHEMA_VERSION } from "../../types/events";
import type { AnalyticsEvent } from "../../types/events";
import { calculateBackoffMs } from "./backoff";
import { assertNoPiiKeys, redactPii } from "./pii";
import { createQueueStore, type QueueStore, type QueuedEvent } from "./queue";

type AnalyticsConfig = {
  endpoint: string;
  appVersion: string;
  env: "local" | "dev" | "staging" | "prod";
  batchSize: number;
  flushIntervalMs: number;
  maxAttempts: number;
  backoffBaseMs: number;
  backoffMaxMs: number;
};

const DEFAULT_CONFIG: Omit<AnalyticsConfig, "endpoint" | "appVersion" | "env"> = {
  batchSize: 10,
  flushIntervalMs: 5000,
  maxAttempts: 5,
  backoffBaseMs: 1000,
  backoffMaxMs: 30000
};

let config: AnalyticsConfig | null = null;
let queueStore: QueueStore | null = null;
let initialized = false;
let initPromise: Promise<void> | null = null;
let flushTimer: number | null = null;
let inFlight = false;

let userId: string | null = null;
let deviceId: string | null = null;
let anonymousId: string | null = null;
let sessionId: string | null = null;

const ANON_ID_KEY = "analytics_anon_id";
const USER_ID_KEY = "analytics_user_id";
const DEVICE_ID_KEY = "analytics_device_id";
const SESSION_ID_KEY = "analytics_session_id";

function createUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `uuid-${Math.random().toString(16).slice(2)}-${Date.now()}`;
}

function getOrCreateStorageItem(key: string, storage: Storage): string {
  const existing = storage.getItem(key);
  if (existing) {
    return existing;
  }
  const value = createUuid();
  storage.setItem(key, value);
  return value;
}

function resolveAnonymousId(): string {
  if (anonymousId) return anonymousId;
  anonymousId = getOrCreateStorageItem(ANON_ID_KEY, localStorage);
  return anonymousId;
}

function resolveSessionId(): string {
  if (sessionId) return sessionId;
  sessionId = getOrCreateStorageItem(SESSION_ID_KEY, sessionStorage);
  return sessionId;
}

function resolveUserId(): string | null {
  if (userId) return userId;
  userId = localStorage.getItem(USER_ID_KEY);
  return userId;
}

function resolveDeviceId(): string | null {
  if (deviceId) return deviceId;
  deviceId = localStorage.getItem(DEVICE_ID_KEY);
  return deviceId;
}

async function ensureInitialized(): Promise<void> {
  if (initialized) return;
  if (initPromise) return initPromise;
  throw new Error("Analytics SDK not initialized");
}

export function initAnalytics(options: {
  endpoint: string;
  appVersion: string;
  env: "local" | "dev" | "staging" | "prod";
}): void {
  if (initialized || initPromise) {
    return;
  }

  config = {
    endpoint: options.endpoint,
    appVersion: options.appVersion,
    env: options.env,
    ...DEFAULT_CONFIG
  };

  initPromise = (async () => {
    queueStore = await createQueueStore();
    resolveAnonymousId();
    resolveSessionId();
    resolveUserId();
    resolveDeviceId();
    initialized = true;

    flushTimer = window.setInterval(() => {
      void flushQueue();
    }, config.flushIntervalMs);

    void flushQueue();
  })();
}

export function identify(nextUserId: string): void {
  userId = nextUserId;
  localStorage.setItem(USER_ID_KEY, nextUserId);
}

export function setDevice(nextDeviceId: string): void {
  deviceId = nextDeviceId;
  localStorage.setItem(DEVICE_ID_KEY, nextDeviceId);
}

function buildBaseEvent(): Omit<AnalyticsEvent, "event_name"> {
  const resolvedUserId = resolveUserId();
  const resolvedAnonymousId = resolveAnonymousId();
  const resolvedSessionId = resolveSessionId();
  const resolvedDeviceId = resolveDeviceId();

  return {
    event_id: createUuid(),
    schema_version: EVENT_SCHEMA_VERSION,
    client_ts: new Date().toISOString(),
    user_id: resolvedUserId ?? undefined,
    anonymous_id: resolvedUserId ? undefined : resolvedAnonymousId,
    session_id: resolvedSessionId,
    device_id: resolvedDeviceId ?? null,
    page: typeof window !== "undefined" ? window.location.pathname : "unknown",
    referrer: typeof document !== "undefined" ? document.referrer || null : null,
    app_version: config?.appVersion ?? "unknown",
    environment: config?.env ?? "local",
    source: "web",
    correlation_id: createUuid()
  };
}

export async function track(
  eventName: EventName,
  payload: Record<string, unknown>
): Promise<void> {
  await ensureInitialized();
  if (!queueStore || !config) {
    return;
  }

  assertNoPiiKeys(payload);

  const event = EventSchema.parse({
    ...buildBaseEvent(),
    event_name: eventName,
    ...payload
  });

  const queuedEvent: QueuedEvent = {
    ...event,
    attempts: 0,
    next_attempt_at: Date.now(),
    created_at: Date.now()
  };

  const exists = await queueStore.has(queuedEvent.event_id);
  if (exists) {
    return;
  }

  await queueStore.enqueue(queuedEvent);

  const queueSize = await queueStore.count();
  if (queueSize >= config.batchSize) {
    void flushQueue();
  }
}

async function flushQueue(): Promise<void> {
  if (!queueStore || !config || inFlight) {
    return;
  }

  inFlight = true;
  try {
    const batch = await queueStore.peekBatch(
      config.batchSize,
      Date.now(),
      config.maxAttempts
    );

    if (batch.length === 0) {
      return;
    }

    const batchCorrelationId = createUuid();

    const response = await fetch(config.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-Id": batchCorrelationId
      },
      body: JSON.stringify({
        events: batch
      })
    });

    if (response.ok) {
      await queueStore.markSent(batch.map((eventItem) => eventItem.event_id));
      return;
    }

    await handleSendFailure(batch);
  } catch (error) {
    const safeError = redactPii(error);
    console.error("Analytics send failed", safeError);
    await handleSendFailure(
      queueStore ? await queueStore.peekBatch(config.batchSize, Date.now(), config.maxAttempts) : []
    );
  } finally {
    inFlight = false;
  }
}

async function handleSendFailure(batch: QueuedEvent[]): Promise<void> {
  if (!queueStore || !config) return;

  await Promise.all(
    batch.map(async (eventItem) => {
      const attempts = eventItem.attempts + 1;
      const backoffMs = calculateBackoffMs(
        attempts,
        config.backoffBaseMs,
        config.backoffMaxMs
      );
      const nextAttemptAt = Date.now() + backoffMs;
      await queueStore.incrementAttempts(eventItem.event_id, attempts, nextAttemptAt);
    })
  );
}
