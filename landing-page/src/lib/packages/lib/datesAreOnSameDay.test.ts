import { describe, expect, it } from "bun:test";
import { datesAreOnSameDay } from "./datesAreOnSameDay";

describe("datesAreOnSameDay", () => {
  it("returns true for the exact same date and time", () => {
    const date1 = new Date("2023-10-15T12:00:00Z");
    const date2 = new Date("2023-10-15T12:00:00Z");
    expect(datesAreOnSameDay(date1, date2)).toBe(true);
  });

  it("returns true for different times on the same day", () => {
    const date1 = new Date("2023-10-15T01:00:00Z");
    const date2 = new Date("2023-10-15T23:59:59Z");
    expect(datesAreOnSameDay(date1, date2)).toBe(true);
  });

  it("returns false for different days", () => {
    const date1 = new Date("2023-10-15T12:00:00Z");
    const date2 = new Date("2023-10-16T12:00:00Z");
    expect(datesAreOnSameDay(date1, date2)).toBe(false);
  });

  it("returns false for same day and month but different years", () => {
    const date1 = new Date("2023-10-15T12:00:00Z");
    const date2 = new Date("2024-10-15T12:00:00Z");
    expect(datesAreOnSameDay(date1, date2)).toBe(false);
  });

  it("returns false for same day and year but different months", () => {
    const date1 = new Date("2023-10-15T12:00:00Z");
    const date2 = new Date("2023-11-15T12:00:00Z");
    expect(datesAreOnSameDay(date1, date2)).toBe(false);
  });

  it("handles midnight boundaries correctly", () => {
    // 2023-10-15 00:00:00
    const startOfDay = new Date(2023, 9, 15, 0, 0, 0);
    // 2023-10-15 23:59:59.999
    const endOfDay = new Date(2023, 9, 15, 23, 59, 59, 999);
    // 2023-10-16 00:00:00
    const startOfNextDay = new Date(2023, 9, 16, 0, 0, 0);

    expect(datesAreOnSameDay(startOfDay, endOfDay)).toBe(true);
    expect(datesAreOnSameDay(endOfDay, startOfNextDay)).toBe(false);
  });
});
