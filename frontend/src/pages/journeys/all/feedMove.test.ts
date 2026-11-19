import { describe, expect, it } from "vitest";

import type { JourneysFeedResponse } from "../../../api/sdk";
import { makeFeedJourney as journey } from "../../../test/feedJourney";
import { feedSortingStrategy, moveJourneyInPages, resolveMoveTarget, yearHeaderShift } from "./feedMove";

const FEED = [journey("a", 2021), journey("b", 2021), journey("c", 2019), journey("d", 2019)];

describe("resolveMoveTarget", () => {
  it("строку тянули вниз — встаёт после той, на которую бросили, и берёт её год", () => {
    expect(resolveMoveTarget(FEED, "a", "c")).toEqual({ neighborJourneyId: "c", placement: "after", traveledYear: 2019 });
  });

  it("строку тянули вверх — встаёт перед той, на которую бросили", () => {
    expect(resolveMoveTarget(FEED, "d", "b")).toEqual({ neighborJourneyId: "b", placement: "before", traveledYear: 2021 });
  });

  it("бросили на своё место или на неизвестную строку — переноса нет", () => {
    expect(resolveMoveTarget(FEED, "b", "b")).toBeNull();
    expect(resolveMoveTarget(FEED, "b", "zzz")).toBeNull();
    expect(resolveMoveTarget(FEED, "zzz", "b")).toBeNull();
  });
});

describe("moveJourneyInPages", () => {
  const pages: JourneysFeedResponse[] = [
    { items: [journey("a", 2021), journey("b", 2021)], nextCursor: "c1" },
    { items: [journey("c", 2019), journey("d", 2019)], nextCursor: null },
  ];

  it("после соседа из другой порции: строка уходит из своей порции и встаёт за соседом с его годом", () => {
    const moved = moveJourneyInPages(pages, "a", { neighborJourneyId: "c", placement: "after", traveledYear: 2019 });

    expect(moved.map((page) => page.items.map((item) => [item.journeyId, item.traveledYear]))).toEqual([
      [["b", 2021]],
      [
        ["c", 2019],
        ["a", 2019],
        ["d", 2019],
      ],
    ]);
    expect(moved.map((page) => page.nextCursor)).toEqual(["c1", null]);
  });

  it("перед соседом: строка встаёт непосредственно перед ним", () => {
    const moved = moveJourneyInPages(pages, "d", { neighborJourneyId: "a", placement: "before", traveledYear: 2021 });

    expect(moved[0].items.map((item) => item.journeyId)).toEqual(["d", "a", "b"]);
    expect(moved[1].items.map((item) => item.journeyId)).toEqual(["c"]);
  });

  it("соседа или строки нет в загруженных порциях — порции не меняются", () => {
    const withoutNeighbor = moveJourneyInPages(pages, "a", { neighborJourneyId: "zzz", placement: "after", traveledYear: 2019 });
    const withoutJourney = moveJourneyInPages(pages, "zzz", { neighborJourneyId: "c", placement: "after", traveledYear: 2019 });

    expect(withoutNeighbor).toEqual(pages);
    expect(withoutJourney).toEqual(pages);
  });
});

describe("feedSortingStrategy", () => {
  // FEED rows are 44 px each, flush; between b (2021) and c (2019) is a 56 px year heading.
  const ROW = 44;
  const rects = [0, 44, 144, 188].map((top) => ({ top, left: 0, width: 600, height: ROW, right: 600, bottom: top + ROW }));
  const shiftsFor = (activeIndex: number, overIndex: number) =>
    rects.map((_, index) =>
      feedSortingStrategy({ activeIndex, overIndex, index, rects, activeNodeRect: rects[activeIndex] })?.y ?? 0,
    );

  it("строку из 2019 держат над последней строкой 2021 — строки уступают ровно её высоту, без заголовка", () => {
    expect(shiftsFor(2, 1)).toEqual([0, ROW, 0, 0]);
  });

  it("строку тянут вниз через границу года — строки до цели поднимаются на её высоту", () => {
    expect(shiftsFor(0, 2)).toEqual([0, -ROW, -ROW, 0]);
  });

  it("строку держат над своим местом — ничего не сдвигается", () => {
    expect(shiftsFor(1, 1)).toEqual([0, 0, 0, 0]);
  });
});

describe("yearHeaderShift", () => {
  const ROW = 44;
  // In FEED the year 2021 starts at row 0, the year 2019 at row 2.
  const shiftOf2019 = (activeIndex: number, overIndex: number) =>
    yearHeaderShift({ activeIndex, overIndex, firstRowIndex: 2, height: ROW });

  it("строку из 2019 несут вверх в 2021 — заголовок 2019 опускается вместе со строками", () => {
    expect(shiftOf2019(2, 1)).toBe(ROW);
  });

  it("строку из 2021 несут вниз в 2019 — заголовок 2019 поднимается вместе со строками", () => {
    expect(shiftOf2019(0, 2)).toBe(-ROW);
  });

  it("строку держат над первой строкой года снизу — заголовок на месте, строка встанет под ним", () => {
    expect(shiftOf2019(3, 2)).toBe(0);
  });

  it("перенос не пересекает заголовок или строки нет в ленте — заголовок на месте", () => {
    expect(shiftOf2019(0, 1)).toBe(0);
    expect(yearHeaderShift({ activeIndex: 2, overIndex: 1, firstRowIndex: 0, height: ROW })).toBe(0);
    expect(shiftOf2019(-1, 1)).toBe(0);
    expect(shiftOf2019(2, -1)).toBe(0);
  });
});
