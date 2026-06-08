declare module "bun:test" {
  type TestCallback = () => unknown | Promise<unknown>;

  type Matchers = {
    not: Matchers;
    resolves: {
      toEqual: (expected: unknown) => void;
    };
    toBe: (expected: unknown) => void;
    toBeDefined: () => void;
    toBeUndefined: () => void;
    toContain: (expected: unknown) => void;
    toEqual: (expected: unknown) => void;
    toHaveLength: (expected: number) => void;
    toThrow: (expected?: unknown) => void;
  };

  export const beforeEach: (callback: TestCallback) => void;
  export const describe: (name: string, callback: TestCallback) => void;
  export const expect: (actual: unknown) => Matchers;
  export const it: (name: string, callback: TestCallback) => void;
  export const mock: {
    module: (
      moduleName: string,
      factory: () => Record<string, unknown>,
    ) => void;
  };
}
