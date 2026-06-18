import { getPeriodBounds, periodLabel, DashboardPeriod } from "../dashboardPeriod";function mockDate(isoDate: string) {
  jest.useFakeTimers();
  jest.setSystemTime(new Date(isoDate));
}

afterEach(() => {
  jest.useRealTimers();
});

describe('getPeriodBounds("this_month")', () => {
  it("mid-month", () => {
    mockDate("2024-06-15");
    expect(getPeriodBounds("this_month")).toEqual({ start: "2024-06-01", end: "2024-06-15" });
  });
  it("first day of month", () => {
    mockDate("2024-03-01");
    expect(getPeriodBounds("this_month")).toEqual({ start: "2024-03-01", end: "2024-03-01" });
  });
  it("last day of 31-day month", () => {
    mockDate("2024-01-31");
    expect(getPeriodBounds("this_month")).toEqual({ start: "2024-01-01", end: "2024-01-31" });
  });
  it("pads single-digit months", () => {
    mockDate("2024-09-07");
    expect(getPeriodBounds("this_month")).toEqual({ start: "2024-09-01", end: "2024-09-07" });
  });
  it("February in leap year", () => {
    mockDate("2024-02-29");
    expect(getPeriodBounds("this_month")).toEqual({ start: "2024-02-01", end: "2024-02-29" });
  });
  it("February in non-leap year", () => {
    mockDate("2023-02-14");
    expect(getPeriodBounds("this_month")).toEqual({ start: "2023-02-01", end: "2023-02-14" });
  });
});

describe('getPeriodBounds("last_month")', () => {
  it("mid-month", () => {
    mockDate("2024-06-15");
    expect(getPeriodBounds("last_month")).toEqual({ start: "2024-05-01", end: "2024-05-31" });
  });
  it("January crosses year boundary to December", () => {
    mockDate("2024-01-20");
    expect(getPeriodBounds("last_month")).toEqual({ start: "2023-12-01", end: "2023-12-31" });
  });
  it("February non-leap year (28 days)", () => {
    mockDate("2023-03-10");
    expect(getPeriodBounds("last_month")).toEqual({ start: "2023-02-01", end: "2023-02-28" });
  });
  it("February leap year (29 days)", () => {
    mockDate("2024-03-10");
    expect(getPeriodBounds("last_month")).toEqual({ start: "2024-02-01", end: "2024-02-29" });
  });
  it("called on first day of month", () => {
    mockDate("2024-08-01");
    expect(getPeriodBounds("last_month")).toEqual({ start: "2024-07-01", end: "2024-07-31" });
  });
  it("30-day previous month", () => {
    mockDate("2024-05-01");
    expect(getPeriodBounds("last_month")).toEqual({ start: "2024-04-01", end: "2024-04-30" });
  });
});

describe('getPeriodBounds("ytd")', () => {
  it("mid-year", () => {
    mockDate("2024-07-04");
    expect(getPeriodBounds("ytd")).toEqual({ start: "2024-01-01", end: "2024-07-04" });
  });
  it("January 1st – start equals end", () => {
    mockDate("2024-01-01");
    expect(getPeriodBounds("ytd")).toEqual({ start: "2024-01-01", end: "2024-01-01" });
  });
  it("December 31st – full year span", () => {
    mockDate("2024-12-31");
    expect(getPeriodBounds("ytd")).toEqual({ start: "2024-01-01", end: "2024-12-31" });
  });
});

describe("getPeriodBounds – return shape", () => {
  const periods: DashboardPeriod[] = ["this_month", "last_month", "ytd"];
  it.each(periods)('"%s" returns YYYY-MM-DD strings with start <= end', (period) => {
    mockDate("2024-09-18");
    const { start, end } = getPeriodBounds(period);
    expect(start).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(end).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(start <= end).toBe(true);
  });
});

describe("periodLabel", () => {
  it('returns "This Month"', () => expect(periodLabel("this_month")).toBe("This Month"));
  it('returns "Last Month"', () => expect(periodLabel("last_month")).toBe("Last Month"));
  it('returns "Year to Date"', () => expect(periodLabel("ytd")).toBe("Year to Date"));
  it("default branch returns This Month for unknown values", () => {
    expect(periodLabel("unknown" as DashboardPeriod)).toBe("This Month");
  });
});