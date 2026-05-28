import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { resolve } from "path";
import { defineConfig } from "vite";
import viteTsConfigPaths from "vite-tsconfig-paths";
import contentCollections from "./content-collection-vite-plugin";

const tanstackStartTarget =
  process.env.TANSTACK_START_TARGET === "node-server" ? "node-server" : "vercel";

export default defineConfig({
  resolve: {
    alias: {
      $magicBackgrounds: resolve("./src/assets/magicBackgrounds"),
      "@typebot.io/billing": resolve("./src/lib/packages/billing"),
      "@typebot.io/conditions": resolve("./src/lib/packages/conditions"),
      "@typebot.io/config": resolve("./src/lib/packages/config"),
      "@typebot.io/emails": resolve("./src/lib/packages/emails"),
      "@typebot.io/env": resolve("./src/lib/packages/env"),
      "@typebot.io/lib": resolve("./src/lib/packages/lib"),
      "@typebot.io/prisma": resolve("./src/lib/packages/prisma"),
      "@typebot.io/react": resolve("./src/lib/packages/react"),
      "@typebot.io/schemas": resolve("./src/lib/packages/schemas"),
      "@typebot.io/settings": resolve("./src/lib/packages/settings"),
      "@typebot.io/telemetry": resolve("./src/lib/packages/telemetry"),
      "@typebot.io/templates": resolve("./src/lib/packages/templates"),
      "@typebot.io/ui": resolve("./src/lib/packages/ui"),
      "@typebot.io/user": resolve("./src/lib/packages/user"),
      "@typebot.io/workspaces": resolve("./src/lib/packages/workspaces"),
      // https://github.com/prisma/prisma/issues/12504
      ".prisma/client/index-browser":
        "../../node_modules/.prisma/client/index-browser.js",
    },
  },
  plugins: [
    tailwindcss(),
    viteTsConfigPaths({
      skip: (dir) => dir === "opensrc",
    }),
    contentCollections(),
    tanstackStart({
      target: tanstackStartTarget,
    }),
  ],
});
