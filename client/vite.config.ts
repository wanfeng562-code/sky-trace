import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { HttpsProxyAgent } from "https-proxy-agent";

export default defineConfig(({ mode }) => {
	// Load ALL env vars (no prefix filter) so HTTP_PROXY is accessible in Node context.
	const env = loadEnv(mode, process.cwd(), "");

	// Honour HTTP_PROXY from .env or the system environment.
	const localProxy = env.HTTP_PROXY || process.env.HTTP_PROXY || "";
	const agent = localProxy ? new HttpsProxyAgent(localProxy) : undefined;
	if (agent) {
		console.info(`[vite] tile proxy → ${localProxy}`);
	}

	return {
		plugins: [vue()],
		server: {
			port: 5173,
			// Map tile proxy: forwards browser requests to external tile CDNs through
			// the Vite dev server (Node.js picks up HTTP_PROXY / HTTPS_PROXY from the
			// environment, enabling traffic to route through a local proxy such as Clash).
			proxy: {
				// MapTiler Cloud
				"/maptiler-proxy": {
					target: "https://api.maptiler.com",
					rewrite: (path) => path.replace(/^\/maptiler-proxy/, ""),
					changeOrigin: true,
					secure: true,
					...(agent ? { agent } : {}),
				},
				// Stadia Maps
				"/stadia-proxy": {
					target: "https://tiles.stadiamaps.com",
					rewrite: (path) => path.replace(/^\/stadia-proxy/, ""),
					changeOrigin: true,
					secure: true,
					...(agent ? { agent } : {}),
				},
			},
		},
	};
});
