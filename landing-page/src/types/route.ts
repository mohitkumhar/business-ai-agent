/**
 * Concrete shape passed to TanStack Router's route.update().
 * Replaces the implicit `any` cast emitted by routeTree.gen.ts.
 */
export interface RouteUpdateOptions {
  id: string;
  path: string;
  getParentRoute: () => unknown;
}