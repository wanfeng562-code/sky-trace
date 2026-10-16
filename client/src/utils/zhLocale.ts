/** Local OpenCC conversion; preserves simplified Chinese and Latin names. */
import { Converter } from "opencc-js/t2cn";

const convert = Converter({ from: "t", to: "cn" });
const HAN = /[\u3400-\u9fff]/;

export function containsTraditionalChinese(text: string): boolean {
	return !!text && HAN.test(text) && convert(text) !== text;
}

export function toSimplifiedChinese(text: string): string {
	return text && HAN.test(text) ? convert(text) : text;
}
