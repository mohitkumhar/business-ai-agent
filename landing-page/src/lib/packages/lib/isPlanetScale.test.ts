import { beforeEach, describe, expect, it, mock } from "bun:test";

const envMock: { DATABASE_URL?: string } = {};

mock.module("@typebot.io/env", () => ({
  env: envMock,
}));

const { isPlaneteScale } = await import("./isPlanetScale");

describe("isPlaneteScale", () => {
  beforeEach(() => {
    delete envMock.DATABASE_URL;
  });

  it("returns true when the database URL contains the PlanetScale password marker", () => {
    envMock.DATABASE_URL =
      "mysql://username:pscale_pw_password@aws.connect.psdb.cloud/database";

    expect(isPlaneteScale()).toBe(true);
  });

  it("returns false when the database URL does not contain the PlanetScale password marker", () => {
    envMock.DATABASE_URL = "mysql://username:password@localhost/database";

    expect(isPlaneteScale()).toBe(false);
  });

  it("returns false for an empty database URL", () => {
    envMock.DATABASE_URL = "";

    expect(isPlaneteScale()).toBe(false);
  });

  it("returns undefined when the database URL is missing", () => {
    expect(isPlaneteScale()).toBeUndefined();
  });
});
