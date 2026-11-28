import { describe, expect, it } from "vitest";

import { yearLabelCenters } from "./yearLabelCenters";

// The slider is 300 px; label centers stay no closer than 48 px to each other and 24 px from the edges.
const WIDTH = 300;

describe("yearLabelCenters", () => {
  it("далёкие ручки — подписи ровно под ними", () => {
    expect(yearLabelCenters([60, 220], 1, WIDTH)).toEqual([60, 220]);
  });

  it("правую ручку ведут к левой — левая подпись на месте, правая упирается в неё", () => {
    expect(yearLabelCenters([100, 110], 1, WIDTH)).toEqual([100, 148]);
  });

  it("левую ручку ведут к правой — правая подпись на месте, левая упирается в неё", () => {
    expect(yearLabelCenters([190, 200], 0, WIDTH)).toEqual([152, 200]);
  });

  it("у края подпись прижимается к нему и не выходит за ползунок", () => {
    expect(yearLabelCenters([2, 298], 1, WIDTH)).toEqual([24, 276]);
  });

  it("у края двигаемой подписи уступить некуда — отходит стоящая", () => {
    // Both thumbs are at the right edge and the right one is dragged: it has nowhere to go right, so the left label moves left.
    expect(yearLabelCenters([290, 296], 1, WIDTH)).toEqual([228, 276]);
    // Both are at the left edge and the left one is dragged: it has nowhere to go left, so the right label moves right.
    expect(yearLabelCenters([4, 10], 0, WIDTH)).toEqual([24, 72]);
  });
});
