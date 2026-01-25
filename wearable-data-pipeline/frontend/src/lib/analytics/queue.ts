import type { AnalyticsEvent } from "../../types/events";

export type QueuedEvent = AnalyticsEvent & {
  attempts: number;
  next_attempt_at: number;
  created_at: number;
};

export type QueueStore = {
  enqueue(event: QueuedEvent): Promise<void>;
  has(eventId: string): Promise<boolean>;
  peekBatch(limit: number, now: number, maxAttempts: number): Promise<QueuedEvent[]>;
  markSent(eventIds: string[]): Promise<void>;
  incrementAttempts(
    eventId: string,
    attempts: number,
    nextAttemptAt: number
  ): Promise<void>;
  count(): Promise<number>;
};

const DB_NAME = "analytics_queue";
const STORE_NAME = "events";
const LOCAL_STORAGE_KEY = "analytics_queue_v1";

function isIndexedDbAvailable(): boolean {
  return typeof indexedDB !== "undefined";
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "event_id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getAllEvents(db: IDBDatabase): Promise<QueuedEvent[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => resolve((request.result as QueuedEvent[]) ?? []);
    request.onerror = () => reject(request.error);
  });
}

async function getEvent(db: IDBDatabase, eventId: string): Promise<QueuedEvent | undefined> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(eventId);
    request.onsuccess = () => resolve(request.result as QueuedEvent | undefined);
    request.onerror = () => reject(request.error);
  });
}

async function putEvent(db: IDBDatabase, event: QueuedEvent): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const request = store.put(event);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function deleteEvent(db: IDBDatabase, eventId: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const request = store.delete(eventId);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

function readLocalEvents(): QueuedEvent[] {
  const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as QueuedEvent[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeLocalEvents(events: QueuedEvent[]): void {
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(events));
}

function createLocalStorageQueue(): QueueStore {
  return {
    async enqueue(event) {
      const events = readLocalEvents();
      if (events.some((item) => item.event_id === event.event_id)) {
        return;
      }
      events.push(event);
      writeLocalEvents(events);
    },
    async has(eventId) {
      return readLocalEvents().some((item) => item.event_id === eventId);
    },
    async peekBatch(limit, now, maxAttempts) {
      return readLocalEvents()
        .filter((event) => event.attempts < maxAttempts && event.next_attempt_at <= now)
        .sort((a, b) => a.created_at - b.created_at)
        .slice(0, limit);
    },
    async markSent(eventIds) {
      const remaining = readLocalEvents().filter(
        (event) => !eventIds.includes(event.event_id)
      );
      writeLocalEvents(remaining);
    },
    async incrementAttempts(eventId, attempts, nextAttemptAt) {
      const events = readLocalEvents().map((event) =>
        event.event_id === eventId
          ? { ...event, attempts, next_attempt_at: nextAttemptAt }
          : event
      );
      writeLocalEvents(events);
    },
    async count() {
      return readLocalEvents().length;
    }
  };
}

function createIndexedDbQueue(db: IDBDatabase): QueueStore {
  return {
    async enqueue(event) {
      await putEvent(db, event);
    },
    async has(eventId) {
      const found = await getEvent(db, eventId);
      return Boolean(found);
    },
    async peekBatch(limit, now, maxAttempts) {
      const events = await getAllEvents(db);
      return events
        .filter((event) => event.attempts < maxAttempts && event.next_attempt_at <= now)
        .sort((a, b) => a.created_at - b.created_at)
        .slice(0, limit);
    },
    async markSent(eventIds) {
      await Promise.all(eventIds.map((eventId) => deleteEvent(db, eventId)));
    },
    async incrementAttempts(eventId, attempts, nextAttemptAt) {
      const existing = await getEvent(db, eventId);
      if (!existing) return;
      await putEvent(db, {
        ...existing,
        attempts,
        next_attempt_at: nextAttemptAt
      });
    },
    async count() {
      const events = await getAllEvents(db);
      return events.length;
    }
  };
}

export async function createQueueStore(): Promise<QueueStore> {
  if (!isIndexedDbAvailable()) {
    return createLocalStorageQueue();
  }

  try {
    const db = await openDb();
    return createIndexedDbQueue(db);
  } catch {
    return createLocalStorageQueue();
  }
}
