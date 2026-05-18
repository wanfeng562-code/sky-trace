import { computed, ref } from "vue";
import { defineStore } from "pinia";
import enUS from "./locales/en-US";
import zhCN from "./locales/zh-CN";

export type AppLocale = "zh-CN" | "en-US";

export interface LocaleOption {
	id: AppLocale;
	label: string;
	/** 界面文案是否已完整翻译 */
	uiReady: boolean;
}

export const LOCALE_OPTIONS: LocaleOption[] = [
	{ id: "zh-CN", label: "简体中文", uiReady: true },
	{ id: "en-US", label: "English", uiReady: true },
];

const messages: Record<AppLocale, typeof zhCN> = {
	"zh-CN": zhCN,
	"en-US": enUS,
};

const STORAGE_KEY = "skytrace.locale";

function readStoredLocale(): AppLocale {
	try {
		const v = localStorage.getItem(STORAGE_KEY);
		if (v === "zh-CN" || v === "en-US") return v;
	} catch {
		/* ignore */
	}
	return "zh-CN";
}

export const useLocaleStore = defineStore("locale", () => {
	const locale = ref<AppLocale>(readStoredLocale());

	function setLocale(next: AppLocale) {
		const opt = LOCALE_OPTIONS.find((o) => o.id === next);
		if (!opt?.uiReady) return;
		locale.value = next;
		try {
			localStorage.setItem(STORAGE_KEY, next);
		} catch {
			/* ignore */
		}
		document.documentElement.lang = next === "zh-CN" ? "zh-CN" : "en";
	}

	// init document lang
	document.documentElement.lang = locale.value === "zh-CN" ? "zh-CN" : "en";

	const t = computed(() => messages[locale.value]);

	return { locale, setLocale, t };
});

/** 点路径取文案，如 t('nav.map') */
export function translate(
	dict: typeof zhCN,
	path: string,
	params?: Record<string, string>,
): string {
	const parts = path.split(".");
	let cur: unknown = dict;
	for (const p of parts) {
		if (cur == null || typeof cur !== "object") return path;
		cur = (cur as Record<string, unknown>)[p];
	}
	let text = typeof cur === "string" ? cur : path;
	if (params) {
		for (const [k, v] of Object.entries(params)) {
			text = text.replace(`{${k}}`, v);
		}
	}
	return text;
}
