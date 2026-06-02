import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // `set-state-in-effect` ships as an error via eslint-plugin-react-hooks v7.
      // The dashboard's data-fetching components intentionally call setLoading(true)
      // at the start of their fetch effects; treat this as a warning (consistent with
      // the other react-hooks/next advisories here) instead of failing CI.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
