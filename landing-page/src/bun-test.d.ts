declare module "bun:test" {
  type TestCallback = () => unknown | Promise<unknown>;

  type Matchers = {
    not: Matchers;
    resolves: Matchers;
    rejects: Matchers;
    toBe: (expected: unknown) => void;
    toBeDefined: () => void;
    toBeUndefined: () => void;
    toContain: (expected: unknown) => void;
    toEqual: (expected: unknown) => void;
    toHaveLength: (expected: number) => void;
    toThrow: (expected?: unknown) => void;
    toBeInstanceOf: (expected: unknown) => void;
    toHaveBeenCalled: () => void;
    toHaveBeenCalledWith: (...args: unknown[]) => void;
    toHaveBeenCalledTimes: (times: number) => void;
  };

  export const beforeEach: (callback: TestCallback) => void;
  export const afterEach: (callback: TestCallback) => void;
  export const beforeAll: (callback: TestCallback) => void;
  export const afterAll: (callback: TestCallback) => void;
  export const describe: (name: string, callback: TestCallback) => void;
  export const expect: (actual: unknown) => Matchers;
  export const it: (name: string, callback: TestCallback) => void;
  export const test: (name: string, callback: TestCallback) => void;
  export interface Mock<T extends (...args: any[]) => any = (...args: any[]) => any> {
    (...args: Parameters<T>): ReturnType<T>;
    mock: {
      calls: Parameters<T>[];
    };
    mockClear: () => void;
    mockReset: () => void;
    mockResolvedValueOnce: (value: any) => Mock<T>;
    mockRejectedValueOnce: (value: any) => Mock<T>;
    mockImplementationOnce: (fn: T) => Mock<T>;
    mockReturnValueOnce: (value: ReturnType<T>) => Mock<T>;
  }

  export const mock: {
    <T extends (...args: any[]) => any>(fn?: T): Mock<T>;
    module: (
      moduleName: string,
      factory: () => Record<string, unknown>,
    ) => void;
  };
}
