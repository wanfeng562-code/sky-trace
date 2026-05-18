/**
 * 轻量繁体 → 简体转换（地名/机场常用字），配合 persistentCache 持久化结果。
 */

const TRAD_SIMP_PAIRS =
	"臺台灣湾島岛縣县區区東东車车電电國国際际廣广場场門门馬马長长風风氣气華华寧宁實实陽阳陰阴遠远邊边達达連连進进過过運运開开關关鐵铁飛飞機机場场廠厂業业务務网络體体術术醫医学学園园藝艺术術乐乐觀观視视聽听聲声話话語语說说讀读書书寫写畫画圖图層层標标准確确證证據据報报導导師师專专业貨货幣币價价買买賣卖費费稅税銀银錢钱財财產产資资貸贷債债險险億亿萬万與与為为從从來来個个們们這这那那里裏里麼么嗎吗歲岁時間间時时点線线網网絡络內内處处務务辦办廳厅館馆樓楼层環环境境溫温濕湿壓压測测預预報报雲云霧雾颱台風风灣湾漢汉语轉转换簡简体繁繁體旧臺台灣湾香香港澳澳门廈厦门滬沪穗穗深深圳蘇苏浙浙閩闽贛赣魯鲁遼辽吉吉黑黑晉晋冀冀豫豫鄂鄂湘湘桂桂瓊琼黔黔滇滇藏藏疆疆寧宁夏夏內内蒙蒙隸隶鄉乡鎮镇嶼屿峰峰巒峦嶺岭峽峡江河湖海龍龙鳳凤鳥鸟魚鱼龜龟貝贝見见觀观覺觉視视聽听聲声話话語语說说讀读書书寫写畫画圖图標标準准確确證证據据報报導导師师專专業业貨货幣币價价買买賣卖費费稅税銀银錢钱財财產产資资貸贷債债險险億亿萬万與与為为從从來来個个們们這这那那里裏里麼么歲岁時間间時时点線线內内處处務务辦办廳厅館馆樓楼层環环境境溫温濕湿壓压測测預预報报雲云霧雾颱台風风漢汉语轉转换簡简体舊旧廈厦滬沪蘇苏閩闽贛赣魯鲁遼辽晉晋豫豫瓊琼黔黔滇滇藏藏疆疆寧宁內内蒙蒙隸隶鄉乡鎮镇嶼屿巒峦嶺岭峽峡";

const TRAD_TO_SIMP = new Map<string, string>();
for (let i = 0; i < TRAD_SIMP_PAIRS.length; i += 2) {
	const trad = TRAD_SIMP_PAIRS[i];
	const simp = TRAD_SIMP_PAIRS[i + 1];
	if (trad && simp) TRAD_TO_SIMP.set(trad, simp);
}

const TRADITIONAL_HINT = /[\u4e00-\u9fff]/;

export function containsTraditionalChinese(text: string): boolean {
	for (const ch of text) {
		if (TRAD_TO_SIMP.has(ch) && ch !== TRAD_TO_SIMP.get(ch)) return true;
	}
	return false;
}

export function toSimplifiedChinese(text: string): string {
	if (!text || !TRADITIONAL_HINT.test(text)) return text;
	let out = "";
	for (const ch of text) {
		out += TRAD_TO_SIMP.get(ch) ?? ch;
	}
	return out;
}
