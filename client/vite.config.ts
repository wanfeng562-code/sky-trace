import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
    plugins: [vue()],
    // Old public/geo boundary data is historical input, excluded from dev and production.
    publicDir: "public-app",
    server: { port: 5173 },
});
