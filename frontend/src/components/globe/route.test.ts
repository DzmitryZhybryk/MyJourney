import { describe, expect, it } from "vitest";

import type { CitySearchItem } from "../../api/sdk";
import {
  altitudeForSeparation,
  apexScale,
  arcAltitude,
  buildTrail,
  CAMERA_MAX_ALTITUDE,
  CAMERA_MIN_ALTITUDE,
  clamp,
  greatCirclePoint,
  isRealCity,
  routeCameraPov,
  type GlobeRoute,
} from "./route";

// Minsk as a "real" city from autocomplete; coordinates are overridden per case.
function makeCity(overrides: Partial<CitySearchItem> = {}): CitySearchItem {
  return {
    cityId: "1",
    name: "Minsk",
    countryCode: "BY",
    latitude: 53.9,
    longitude: 27.56,
    population: 2_000_000,
    ...overrides,
  };
}

describe("greatCirclePoint", () => {
  it("при t=0 возвращает старт", () => {
    const point = greatCirclePoint(0, 0, 0, 90, 0);
    expect(point.lat).toBeCloseTo(0);
    expect(point.lng).toBeCloseTo(0);
  });

  it("при t=1 возвращает финиш", () => {
    const point = greatCirclePoint(0, 0, 0, 90, 1);
    expect(point.lat).toBeCloseTo(0);
    expect(point.lng).toBeCloseTo(90);
  });

  it("при t=0.5 попадает в середину дуги экватора", () => {
    // The great circle (0,0)->(0,90) along the equator: the midpoint is (0, 45).
    const point = greatCirclePoint(0, 0, 0, 90, 0.5);
    expect(point.lat).toBeCloseTo(0);
    expect(point.lng).toBeCloseTo(45);
  });

  it("возвращает старт для вырожденной дуги (совпадающие точки)", () => {
    const point = greatCirclePoint(55, 37, 55, 37, 0.5);
    expect(point.lat).toBeCloseTo(55);
    expect(point.lng).toBeCloseTo(37);
  });
});

describe("arcAltitude", () => {
  it("равна 0 на концах маршрута", () => {
    expect(arcAltitude(0, 0.14)).toBeCloseTo(0);
    expect(arcAltitude(1, 0.14)).toBeCloseTo(0);
  });

  it("достигает апекса в середине", () => {
    expect(arcAltitude(0.5, 0.14)).toBeCloseTo(0.14);
  });
});

describe("clamp", () => {
  it("возвращает значение внутри диапазона без изменений", () => {
    expect(clamp(5, 0, 10)).toBe(5);
  });

  it("подрезает снизу", () => {
    expect(clamp(-3, 0, 10)).toBe(0);
  });

  it("подрезает сверху", () => {
    expect(clamp(42, 0, 10)).toBe(10);
  });
});

describe("altitudeForSeparation", () => {
  it("отдаёт дальний предел при нулевом расстоянии", () => {
    expect(altitudeForSeparation(0)).toBe(CAMERA_MAX_ALTITUDE);
  });

  it("держит результат в пределах [MIN, MAX]", () => {
    for (const separation of [0.01, 0.1, 0.5, 1, 2, 3]) {
      const altitude = altitudeForSeparation(separation);
      expect(altitude).toBeGreaterThanOrEqual(CAMERA_MIN_ALTITUDE);
      expect(altitude).toBeLessThanOrEqual(CAMERA_MAX_ALTITUDE);
    }
  });

  it("монотонна: дальше города → выше камера", () => {
    expect(altitudeForSeparation(0.05)).toBeLessThan(altitudeForSeparation(0.3));
  });
});

describe("apexScale", () => {
  it("равен 0 при нулевом расстоянии", () => {
    expect(apexScale(0)).toBe(0);
  });

  it("насыщается в 1 на длинных маршрутах", () => {
    expect(apexScale(Math.PI)).toBe(1);
  });

  it("растёт с расстоянием и не превышает 1", () => {
    expect(apexScale(0.1)).toBeLessThan(apexScale(0.5));
    expect(apexScale(0.5)).toBeLessThanOrEqual(1);
  });
});

describe("buildTrail", () => {
  it("начинается у старта на нулевой высоте", () => {
    const trail = buildTrail(0, 0, 0, 90, 0.14, 1);
    const first = trail[0];
    expect(first.lat).toBeCloseTo(0);
    expect(first.lng).toBeCloseTo(0);
    expect(first.alt).toBeCloseTo(0);
  });

  it("при полном прогрессе доводит голову до финиша", () => {
    const trail = buildTrail(0, 0, 0, 90, 0.14, 1);
    const last = trail[trail.length - 1];
    expect(last.lng).toBeCloseTo(90);
  });

  it("поднимает след над поверхностью в середине маршрута", () => {
    const trail = buildTrail(0, 0, 0, 90, 0.14, 1);
    const maxAltitude = Math.max(...trail.map((point) => point.alt));
    expect(maxAltitude).toBeGreaterThan(0);
    expect(maxAltitude).toBeLessThanOrEqual(0.14 + 1e-9);
  });

  it("обрезает след по прогрессу — голова на середине, не на финише", () => {
    // progress=0.5 along the equator (0,0)->(0,90): the head is at (0, 45).
    const trail = buildTrail(0, 0, 0, 90, 0.14, 0.5);
    const last = trail[trail.length - 1];
    expect(last.lng).toBeCloseTo(45);
  });
});

describe("isRealCity", () => {
  it("false для null", () => {
    expect(isRealCity(null)).toBe(false);
  });

  it("false для города с нулевыми координатами", () => {
    expect(isRealCity(makeCity({ latitude: 0, longitude: 0 }))).toBe(false);
  });

  it("true для города с реальными координатами", () => {
    expect(isRealCity(makeCity({ latitude: 53.9, longitude: 27.56 }))).toBe(true);
  });

  it("true если хотя бы одна координата ненулевая", () => {
    expect(isRealCity(makeCity({ latitude: 0, longitude: 27.56 }))).toBe(true);
  });
});

describe("routeCameraPov", () => {
  const MINSK = makeCity();
  const VILNIUS = makeCity({ cityId: "2", name: "Vilnius", countryCode: "LT", latitude: 54.69, longitude: 25.28 });
  const TOKYO = makeCity({ cityId: "3", name: "Tokyo", countryCode: "JP", latitude: 35.68, longitude: 139.69 });

  function makeRoute(origin: CitySearchItem | null, destination: CitySearchItem | null): GlobeRoute {
    return { origin, destination, transportType: "air", originLabel: "", destinationLabel: "" };
  }

  it("без формы — нейтральный вид на дальнем зуме, центр подтянут к экватору", () => {
    // The neutral latitude 20° at far zoom gives 40% to the equator: 20 x 0.6.
    expect(routeCameraPov(null)).toEqual({ lat: 12, lng: 0, altitude: CAMERA_MAX_ALTITUDE });
  });

  it("пустая форма смотрит туда же, куда и отсутствие формы", () => {
    expect(routeCameraPov(makeRoute(null, null))).toEqual(routeCameraPov(null));
  });

  it("выбран только город отправления — камера на нём, на дальнем зуме", () => {
    const pov = routeCameraPov(makeRoute(MINSK, null));

    expect(pov.lng).toBeCloseTo(MINSK.longitude);
    expect(pov.lat).toBeCloseTo(MINSK.latitude * 0.6);
    expect(pov.altitude).toBe(CAMERA_MAX_ALTITUDE);
  });

  it("выбран только город назначения — камера на нём", () => {
    const pov = routeCameraPov(makeRoute(null, TOKYO));

    expect(pov.lng).toBeCloseTo(TOKYO.longitude);
    expect(pov.lat).toBeCloseTo(TOKYO.latitude * 0.6);
  });

  it("город без координат не считается выбранным — камера идёт на реальный конец", () => {
    const pov = routeCameraPov(makeRoute(makeCity({ latitude: 0, longitude: 0 }), TOKYO));

    expect(pov.lng).toBeCloseTo(TOKYO.longitude);
  });

  it("два города — камера на середине пути", () => {
    const pov = routeCameraPov(makeRoute(MINSK, VILNIUS));

    expect(pov.lng).toBeGreaterThan(VILNIUS.longitude);
    expect(pov.lng).toBeLessThan(MINSK.longitude);
  });

  it("ближе города — ближе камера, но не ближе нижнего предела", () => {
    const near = routeCameraPov(makeRoute(MINSK, VILNIUS));
    const far = routeCameraPov(makeRoute(MINSK, TOKYO));

    expect(near.altitude).toBeLessThan(far.altitude);
    expect(near.altitude).toBeGreaterThanOrEqual(CAMERA_MIN_ALTITUDE);
  });

  it("на ближнем зуме центр почти не тянется к экватору — города остаются в кадре", () => {
    const pov = routeCameraPov(makeRoute(MINSK, VILNIUS));
    const middleLat = greatCirclePoint(MINSK.latitude, MINSK.longitude, VILNIUS.latitude, VILNIUS.longitude, 0.5).lat;

    expect(pov.lat / middleLat).toBeGreaterThan(0.9);
  });
});
