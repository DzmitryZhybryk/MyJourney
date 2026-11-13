import { describe, expect, it } from "vitest";

import type { JourneysFeedResponse } from "../../../api/sdk";
import { makeFeedJourney as journey } from "../../../test/feedJourney";
import { feedQueryOptions, filterFeedPages, groupFeedByYear, isFeedFullyLoaded } from "./feedQuery";

describe("feedQueryOptions", () => {
  it("один и тот же набор транспорта в любом порядке даёт один ключ", () => {
    const first = feedQueryOptions({ yearRange: null, transportTypes: ["water", "air"] });
    const second = feedQueryOptions({ yearRange: null, transportTypes: ["air", "water"] });

    expect(first.queryKey).toEqual(second.queryKey);
    expect(first.queryKey[0].query).toEqual({ transportType: ["air", "water"] });
  });

  it("все виды транспорта и без диапазона — запрос без фильтров", () => {
    const options = feedQueryOptions({ yearRange: null, transportTypes: ["land", "air", "water"] });

    expect(options.queryKey[0].query).toEqual({});
  });

  it("диапазон лет уходит границами yearFrom/yearTo", () => {
    const options = feedQueryOptions({ yearRange: [2017, 2020], transportTypes: ["land", "air", "water"] });

    expect(options.queryKey[0].query).toEqual({ yearFrom: 2017, yearTo: 2020 });
  });

  it("следующая порция — по курсору ответа, без курсора порций больше нет", () => {
    const { getNextPageParam } = feedQueryOptions({ yearRange: null, transportTypes: ["air"] });

    expect(getNextPageParam({ items: [], nextCursor: "next" })).toBe("next");
    expect(getNextPageParam({ items: [], nextCursor: null })).toBeUndefined();
  });
});

describe("filterFeedPages", () => {
  const pages: JourneysFeedResponse[] = [
    { items: [journey("a", 2021), { ...journey("b", 2021), transportType: "water" }], nextCursor: "c1" },
    { items: [journey("c", 2019), journey("d", 2017)], nextCursor: null },
  ];
  const idsOf = (filtered: JourneysFeedResponse[]) => filtered.flatMap((page) => page.items.map((item) => item.journeyId));

  it("оставляет строки диапазона лет включительно, в порядке ленты", () => {
    const filtered = filterFeedPages(pages, { yearRange: [2019, 2021], transportTypes: ["land", "air", "water"] });

    expect(idsOf(filtered)).toEqual(["a", "b", "c"]);
  });

  it("оставляет только выбранный транспорт", () => {
    const filtered = filterFeedPages(pages, { yearRange: null, transportTypes: ["water"] });

    expect(idsOf(filtered)).toEqual(["b"]);
  });

  it("у выборки нет курсоров — догружать её нечем", () => {
    const filtered = filterFeedPages(pages, { yearRange: null, transportTypes: ["land", "air", "water"] });

    expect(filtered.map((page) => page.nextCursor)).toEqual([null, null]);
  });
});

describe("isFeedFullyLoaded", () => {
  it("лента загружена до конца, когда у последней порции нет курсора", () => {
    expect(isFeedFullyLoaded([{ items: [], nextCursor: "c1" }, { items: [], nextCursor: null }])).toBe(true);
  });

  it("есть следующая порция, порций нет или ленты нет в кэше — не до конца", () => {
    expect(isFeedFullyLoaded([{ items: [], nextCursor: "c1" }])).toBe(false);
    expect(isFeedFullyLoaded([])).toBe(false);
    expect(isFeedFullyLoaded(undefined)).toBe(false);
  });
});

describe("groupFeedByYear", () => {
  it("раскладывает строки по годам в порядке ленты, сохраняя порядок внутри года", () => {
    const pages: JourneysFeedResponse[] = [
      { items: [journey("a", 2021), journey("b", 2021)], nextCursor: "c1" },
      { items: [journey("c", 2021), journey("d", 2019)], nextCursor: null },
    ];

    expect(groupFeedByYear(pages)).toEqual([
      { year: 2021, journeys: [journey("a", 2021), journey("b", 2021), journey("c", 2021)] },
      { year: 2019, journeys: [journey("d", 2019)] },
    ]);
  });

  it("поездка, попавшая в две порции, показывается один раз — там, где встретилась первой", () => {
    const pages: JourneysFeedResponse[] = [
      { items: [journey("a", 2021), journey("b", 2021)], nextCursor: "c1" },
      { items: [journey("b", 2021), journey("c", 2019)], nextCursor: null },
    ];

    const groups = groupFeedByYear(pages);

    expect(groups.flatMap((group) => group.journeys.map((item) => item.journeyId))).toEqual(["a", "b", "c"]);
  });

  it("без порций групп нет", () => {
    expect(groupFeedByYear([])).toEqual([]);
  });
});
