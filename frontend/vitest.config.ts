import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Resolved by the Next compiler rather than installed, so Vitest cannot find it.
      // Stubbed so server modules are unit-testable; the guard itself is build-time.
      "server-only": path.resolve(__dirname, "./test/server-only-stub.ts"),
    },
  },
});
