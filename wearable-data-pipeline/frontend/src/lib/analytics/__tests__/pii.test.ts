import { describe, expect, it } from "vitest";
import { assertNoPiiKeys, redactPii } from "../pii";

describe("PII protection", () => {
  it("blocks payloads containing PII keys", () => {
    expect(() => assertNoPiiKeys({ email: "test@example.com" })).toThrow(
      /PII key blocked/
    );
  });

  it("redacts PII keys for logging", () => {
    const redacted = redactPii({ email: "test@example.com", nested: { phone: "123" } });
    expect(redacted).toEqual({ email: "[REDACTED]", nested: { phone: "[REDACTED]" } });
  });
});
