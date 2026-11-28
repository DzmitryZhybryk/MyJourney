import { boxesIntersect, type LabelBox } from "../../../components/globe/labelDeclutter";
import type { ArcPieces } from "./movementGeometry";

/** A city on the canvas that needs a label. */
export interface LabelledCity {
  cityId: string;
  x: number;
  y: number;
  label: string;
  /** How many routes pass through the city: labels of busy cities are laid out first. */
  routeCount: number;
}

/** Label sizes in canvas units at the current zoom. */
export interface LabelMetrics {
  fontSize: number;
  /** Offset of the label from the dot center. */
  gap: number;
  dotRadius: number;
  /** Clearance the label keeps from lines and other labels. */
  clearance: number;
}

/** A label that got a position: `anchor` is the text alignment relative to `x`. */
export interface PlacedLabel {
  cityId: string;
  label: string;
  x: number;
  y: number;
  anchor: "start" | "middle" | "end";
}

type Point = readonly [number, number];

// Text width is estimated, not measured: jsdom has neither canvas.measureText nor
// getComputedTextLength. The ratio has headroom so wide Cyrillic letters do not exceed the estimate.
const CHAR_WIDTH_RATIO = 0.62;
const LINE_HEIGHT_RATIO = 1.25;
// Diagonal positions sit closer to the dot, otherwise the label "drifts away" from it.
const DIAGONAL_GAP_RATIO = 0.7;

// Where a label may go, in order of preference: to the right is the most natural to read.
const CANDIDATE_DIRECTIONS: readonly (readonly [number, number])[] = [
  [1, 0],
  [-1, 0],
  [1, -1],
  [1, 1],
  [-1, -1],
  [-1, 1],
  [0, -1],
  [0, 1],
];

/** Whether a segment crosses a rectangle (Liang-Barsky clipping). */
function segmentHitsBox(start: Point, end: Point, box: LabelBox): boolean {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const edges: readonly (readonly [number, number])[] = [
    [-dx, start[0] - box.left],
    [dx, box.left + box.width - start[0]],
    [-dy, start[1] - box.top],
    [dy, box.top + box.height - start[1]],
  ];
  let enter = 0;
  let exit = 1;
  for (const [direction, distance] of edges) {
    if (direction === 0) {
      if (distance < 0) {
        return false;
      }

      continue;
    }

    const t = distance / direction;
    if (direction < 0) {
      enter = Math.max(enter, t);
    } else {
      exit = Math.min(exit, t);
    }

    if (enter > exit) {
      return false;
    }
  }

  return true;
}

function inflate(box: LabelBox, by: number): LabelBox {
  return { ...box, left: box.left - by, top: box.top - by, width: box.width + 2 * by, height: box.height + 2 * by };
}

/**
 * Lays out city labels so they overlap neither each other, nor city dots, nor arcs with arrows.
 *
 * Greedy, in priority order (more routes first, ties by id so the layout does not jump): a label
 * takes the first position around its dot that touches nothing. If there is none, the first that
 * touches no other labels or dots (crossing a line is allowed). If there is none either, the label
 * is hidden: zooming in will make room for it.
 */
export function layOutCityLabels(
  cities: readonly LabelledCity[],
  arcs: readonly ArcPieces[],
  metrics: LabelMetrics,
): readonly PlacedLabel[] {
  const segments: [Point, Point][] = [];
  for (const pieces of arcs) {
    for (const piece of pieces) {
      for (let index = 1; index < piece.length; index += 1) {
        segments.push([piece[index - 1], piece[index]]);
      }
    }
  }

  const dots: LabelBox[] = cities.map((city) => ({
    id: city.cityId,
    left: city.x - metrics.dotRadius,
    top: city.y - metrics.dotRadius,
    width: 2 * metrics.dotRadius,
    height: 2 * metrics.dotRadius,
  }));

  const byPriority = [...cities].sort(
    (left, right) => right.routeCount - left.routeCount || (left.cityId < right.cityId ? -1 : 1),
  );

  const acceptedBoxes: LabelBox[] = [];
  const placed: PlacedLabel[] = [];
  for (const city of byPriority) {
    const width = city.label.length * metrics.fontSize * CHAR_WIDTH_RATIO;
    const height = metrics.fontSize * LINE_HEIGHT_RATIO;
    const candidates = CANDIDATE_DIRECTIONS.map(([dx, dy]) => {
      const gap = dx !== 0 && dy !== 0 ? metrics.gap * DIAGONAL_GAP_RATIO : metrics.gap;
      const left = dx > 0 ? city.x + gap : dx < 0 ? city.x - gap - width : city.x - width / 2;
      const top = dy > 0 ? city.y + gap : dy < 0 ? city.y - gap - height : city.y - height / 2;
      const box: LabelBox = { id: city.cityId, left, top, width, height };
      const anchor: PlacedLabel["anchor"] = dx > 0 ? "start" : dx < 0 ? "end" : "middle";
      const x = dx > 0 ? left : dx < 0 ? left + width : left + width / 2;
      return { box, label: { cityId: city.cityId, label: city.label, x, y: top + height / 2, anchor } };
    });

    const touchesLabelsOrDots = (box: LabelBox) =>
      acceptedBoxes.some((other) => boxesIntersect(box, other, metrics.clearance)) ||
      dots.some((dot) => dot.id !== city.cityId && boxesIntersect(box, dot, 0));
    const touchesLines = (box: LabelBox) => {
      const padded = inflate(box, metrics.clearance);
      return segments.some(([start, end]) => segmentHitsBox(start, end, padded));
    };

    const chosen =
      candidates.find(({ box }) => !touchesLabelsOrDots(box) && !touchesLines(box)) ??
      candidates.find(({ box }) => !touchesLabelsOrDots(box));
    if (chosen) {
      acceptedBoxes.push(chosen.box);
      placed.push(chosen.label);
    }
  }

  return placed;
}
