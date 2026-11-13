import { describe, expect, it } from "vitest";

import { citiesFromJourneysGlobe } from "./userCities";

const MOSCOW_ID = "11111111-1111-4111-8111-111111111111";
const LONDON_ID = "22222222-2222-4222-8222-222222222222";

describe("citiesFromJourneysGlobe", () => {
  it("переводит города глобуса в точки с id города и координатами", () => {
    const response = {
      cities: [
        { cityId: MOSCOW_ID, latitude: 55.75, longitude: 37.62 },
        { cityId: LONDON_ID, latitude: 51.5, longitude: -0.12 },
      ],
    };

    expect(citiesFromJourneysGlobe(response)).toEqual([
      { id: MOSCOW_ID, lat: 55.75, lng: 37.62 },
      { id: LONDON_ID, lat: 51.5, lng: -0.12 },
    ]);
  });

  it("пустой ответ даёт пустой список", () => {
    expect(citiesFromJourneysGlobe({ cities: [] })).toEqual([]);
  });
});
