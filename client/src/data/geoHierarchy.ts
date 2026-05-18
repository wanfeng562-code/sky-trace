import { COUNTRIES, type SubRegion } from "./countries";
import {
	NESTED_GEO_CN,
	NESTED_GEO_DE,
	NESTED_GEO_JP,
	NESTED_GEO_US,
	type GeoBBox,
	type GeoCity,
	type GeoDistrict,
} from "./geoNested";

export type { GeoBBox, GeoCity, GeoDistrict };

const NESTED_BY_COUNTRY: Record<string, Record<string, GeoCity[]>> = {
	CN: NESTED_GEO_CN,
	US: NESTED_GEO_US,
	JP: NESTED_GEO_JP,
	DE: NESTED_GEO_DE,
};

export function getCountryRegions(countryCode: string): SubRegion[] {
	return COUNTRIES.find((c) => c.code === countryCode)?.regions ?? [];
}

export function getCitiesForRegion(
	countryCode: string,
	regionCode: string,
): GeoCity[] {
	const nested = NESTED_BY_COUNTRY[countryCode]?.[regionCode];
	if (nested?.length) return nested;
	if (!hasNestedGeo(countryCode)) return [];
	const region = getCountryRegions(countryCode).find((r) => r.code === regionCode);
	if (!region) return [];
	return [
		{
			code: `${regionCode}-ALL`,
			nameZh: `全${region.nameZh}`,
			latMin: region.latMin,
			latMax: region.latMax,
			lonMin: region.lonMin,
			lonMax: region.lonMax,
			airports: region.airports,
		},
	];
}

export function getDistrictsForCity(
	countryCode: string,
	regionCode: string,
	cityCode: string,
): GeoDistrict[] {
	const city = getCitiesForRegion(countryCode, regionCode).find(
		(c) => c.code === cityCode,
	);
	return city?.districts ?? [];
}

export function hasNestedGeo(countryCode: string): boolean {
	return countryCode in NESTED_BY_COUNTRY;
}

export function maxGeoDepth(countryCode: string): number {
	if (!hasNestedGeo(countryCode)) return 2;
	const nested = NESTED_BY_COUNTRY[countryCode];
	for (const cities of Object.values(nested)) {
		for (const city of cities) {
			if (city.districts?.length) return 4;
		}
	}
	return 3;
}

/** 解析当前选中的最深级别 bbox（国 → 省 → 市 → 区） */
export function resolveGeoBBox(
	countryCode: string,
	regionCode: string | null,
	cityCode: string | null,
	districtCode: string | null,
): GeoBBox | null {
	const country = COUNTRIES.find((c) => c.code === countryCode);
	if (!country) return null;

	if (districtCode && regionCode && cityCode) {
		const district = getDistrictsForCity(
			countryCode,
			regionCode,
			cityCode,
		).find((d) => d.code === districtCode);
		if (district) return district;
	}

	if (cityCode && regionCode) {
		const city = getCitiesForRegion(countryCode, regionCode).find(
			(c) => c.code === cityCode,
		);
		if (city) return city;
	}

	if (regionCode) {
		const region = country.regions?.find((r) => r.code === regionCode);
		if (region) return region;
	}

	return country;
}
