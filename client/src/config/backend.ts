/** Production may intentionally run as a map-only site while its server is retired. */
export const BACKEND_ENABLED = (import.meta.env.VITE_BACKEND_ENABLED ?? (import.meta.env.PROD ? "false" : "true")) !== "false";
