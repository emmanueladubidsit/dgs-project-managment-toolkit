import { describe, expect, it, vi } from "vitest";
import { addDays, formatDate, parseDate, relativeDue, toISODate } from "./format";

describe("dates", () => {
  it("parses ISO dates as local dates (no UTC off-by-one)", () => {
    const d = parseDate("2026-03-01");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 2, 1]);
    expect(toISODate(d)).toBe("2026-03-01");
  });
  it("adds days across month boundaries", () => {
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });
  it("formats in British English", () => {
    expect(formatDate("2026-11-21")).toBe("21 Nov 2026");
    expect(formatDate(null)).toBe("—");
  });
  it("describes deadlines relative to today", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 21, 10));
    expect(relativeDue("2026-11-21")).toBe("Due today");
    expect(relativeDue("2026-11-22")).toBe("Due tomorrow");
    expect(relativeDue("2026-11-20")).toBe("1 day overdue");
    expect(relativeDue("2026-11-18")).toBe("3 days overdue");
    expect(relativeDue(null)).toBeNull();
    vi.useRealTimers();
  });
});
