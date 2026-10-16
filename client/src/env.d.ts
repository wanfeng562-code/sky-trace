/// <reference types="vite/client" />
declare module "*.vue";
declare module "opencc-js/t2cn" {
    export function Converter(options: { from: "t" | "tw" | "hk"; to: "cn" }): (text: string) => string;
}
interface ImportMetaEnv {
    readonly VITE_APP_NAME: string;
    readonly VITE_API_BASE_URL: string;
    readonly VITE_BACKEND_ENABLED?: string;
    readonly VITE_WS_URL: string;
    readonly VITE_ENABLE_MOCK: string;
    readonly VITE_TIANDITU_KEY?: string;
    readonly VITE_MAP_APPROVAL_NUMBER?: string;
    readonly VITE_MAP_APPROVAL_VECTOR?: string;
    readonly VITE_MAP_APPROVAL_IMAGERY?: string;
    readonly VITE_MAP_APPROVAL_TERRAIN?: string;
    readonly VITE_MAP_DEFAULT_STYLE?: string;
    readonly VITE_MAP_INIT_LNG?: string;
    readonly VITE_MAP_INIT_LAT?: string;
    readonly VITE_MAP_INIT_ZOOM?: string;
}
interface ImportMeta { readonly env: ImportMetaEnv; }
