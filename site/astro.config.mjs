import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://techkazi.pages.dev",
  output: "static",
  vite: { build: { assetsInlineLimit: 0 } },
});
