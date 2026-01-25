const BLOCKED_KEYS = new Set([
  "email",
  "phone",
  "name",
  "first_name",
  "last_name",
  "full_name"
]);

export function assertNoPiiKeys(input: unknown): void {
  if (!input || typeof input !== "object") {
    return;
  }

  const stack: Array<{ path: string; value: unknown }> = [
    { path: "", value: input }
  ];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) continue;
    const { path, value } = current;
    if (!value || typeof value !== "object") {
      continue;
    }

    for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
      const normalized = key.toLowerCase();
      if (BLOCKED_KEYS.has(normalized) || normalized.includes("email") || normalized.includes("phone")) {
        const location = path ? `${path}.${key}` : key;
        throw new Error(`PII key blocked: ${location}`);
      }

      if (child && typeof child === "object") {
        stack.push({
          path: path ? `${path}.${key}` : key,
          value: child
        });
      }
    }
  }
}

export function redactPii(input: unknown): unknown {
  if (!input || typeof input !== "object") {
    return input;
  }

  if (Array.isArray(input)) {
    return input.map((item) => redactPii(item));
  }

  const output: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    const normalized = key.toLowerCase();
    if (BLOCKED_KEYS.has(normalized) || normalized.includes("email") || normalized.includes("phone")) {
      output[key] = "[REDACTED]";
      continue;
    }
    output[key] = redactPii(value);
  }

  return output;
}
