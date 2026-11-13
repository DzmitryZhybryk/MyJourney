import { describe, expect, it } from "vitest";

import { getMovementsMapQueryKey } from "../../../api/sdk";
import { movementsQueryOptions } from "./movementsQuery";

describe("movementsQueryOptions", () => {
  it("без фильтра транспорта — запрос без параметров", () => {
    expect(movementsQueryOptions().queryKey).toEqual(getMovementsMapQueryKey({ query: {} }));
  });

  it("одинаковый набор транспорта в любом порядке даёт один ключ", () => {
    expect(movementsQueryOptions(["water", "air"]).queryKey).toEqual(movementsQueryOptions(["air", "water"]).queryKey);
    expect(movementsQueryOptions(["water", "air"]).queryKey).toEqual(
      getMovementsMapQueryKey({ query: { transportType: ["air", "water"] } }),
    );
  });

  it("выбраны все виды транспорта — то же, что без фильтра", () => {
    expect(movementsQueryOptions(["land", "air", "water"]).queryKey).toEqual(movementsQueryOptions().queryKey);
  });

  it("ответ не устаревает сам — его сбрасывает добавление поездки", () => {
    expect(movementsQueryOptions().staleTime).toBe(Infinity);
  });
});
