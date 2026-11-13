import { describe, expect, it } from "vitest";

import enCommon from "../../locales/en/common.json";
import ruCommon from "../../locales/ru/common.json";
import { CITIES } from "./cities";

const CITY_IDS = Object.keys(CITIES).sort();

describe("пул городов глобуса", () => {
  it("id города совпадает с его ключом в CITIES — по нему ищется перевод", () => {
    const mismatched = Object.entries(CITIES).filter(([key, city]) => city.id !== key);

    expect(mismatched).toEqual([]);
  });

  it.each([
    { language: "en", cities: enCommon.globe.cities },
    { language: "ru", cities: ruCommon.globe.cities },
  ])("$language: перевод есть ровно у каждого города пула, без пустых и лишних", ({ cities }) => {
    expect(Object.keys(cities).sort()).toEqual(CITY_IDS);
    expect(Object.values(cities).filter((name) => name.trim() === "")).toEqual([]);
  });
});
