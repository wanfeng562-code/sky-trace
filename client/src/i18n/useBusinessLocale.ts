import { computed } from "vue";
import { useLocaleStore } from "./index";

export function useBusinessLocale() {
    const locale = useLocaleStore();
    return { ui: computed(() => locale.t.business) };
}
