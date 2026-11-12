import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const alias = {
  "@": fileURLToPath(new URL("./src", import.meta.url)),
  // The real package throws outside React Server Components; tests run handlers directly in Node.
  "server-only": fileURLToPath(new URL("./tests/server-only-stub.ts", import.meta.url)),
};

export default defineConfig({
  resolve: { alias },
  test: {
    projects: [
      {
        // Real-backend integration: needs the local Postgres (54329) and engine (8787); see docs/PHASE7C_QA_REPORT.md.
        resolve: { alias },
        test: {
          name: "api",
          environment: "node",
          include: ["tests/*.test.ts"],
          setupFiles: ["tests/setup.ts"],
          testTimeout: 60_000,
          hookTimeout: 60_000,
          fileParallelism: false,
        },
      },
      {
        // Isolated component tests in jsdom; only the HTTP boundary (fetch) and Next navigation are mocked.
        resolve: { alias },
        esbuild: { jsx: "automatic" },
        test: {
          name: "ui",
          environment: "jsdom",
          include: ["tests/ui/**/*.test.{ts,tsx}"],
          setupFiles: ["tests/ui/setup.ts"],
          testTimeout: 20_000,
        },
      },
    ],
  },
});
