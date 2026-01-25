export function calculateBackoffMs(
  attempt: number,
  baseMs: number,
  maxMs: number
): number {
  const delay = baseMs * Math.pow(2, attempt);
  return Math.min(delay, maxMs);
}
