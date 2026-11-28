import { describe, expect, it } from "vitest";

import { fitYearRange } from "./yearRange";

describe("fitYearRange", () => {
  it("выбор внутри шкалы остаётся как есть", () => {
    expect(fitYearRange([2017, 2019], 2015, 2021)).toEqual([2017, 2019]);
  });

  it("выбор, частично вышедший за шкалу, обрезается по её краям", () => {
    expect(fitYearRange([2013, 2016], 2015, 2021)).toEqual([2015, 2016]);
    expect(fitYearRange([2020, 2024], 2015, 2021)).toEqual([2020, 2021]);
  });

  it("выбор целиком за шкалой или во всю шкалу — все годы", () => {
    expect(fitYearRange([2010, 2012], 2015, 2021)).toBeNull();
    expect(fitYearRange([2023, 2024], 2015, 2021)).toBeNull();
    expect(fitYearRange([2013, 2024], 2015, 2021)).toBeNull();
  });

  it("шкалы нет или в ней один год — все годы: ползунка нет, и снять выбор нечем", () => {
    expect(fitYearRange([2019, 2019], 2019, 2019)).toBeNull();
    expect(fitYearRange([2019, 2019], undefined, undefined)).toBeNull();
  });

  it("ничего не выбрано — все годы", () => {
    expect(fitYearRange(null, 2015, 2021)).toBeNull();
  });
});
