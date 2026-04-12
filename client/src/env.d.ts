/// <reference types="vite/client" />

declare module "*.vue";

interface ImportMetaEnv {
	readonly VITE_APP_NAME: string;
	readonly VITE_API_BASE_URL: string;
	readonly VITE_WS_URL: string;
	readonly VITE_MAP_PROVIDER: string;
	readonly VITE_ENABLE_MOCK: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
