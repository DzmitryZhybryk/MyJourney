import { clamp } from "../../../components/globe/route";

// Year label centers are no closer than this, otherwise they would overlap; half of it is the
// label's inset from the slider edge. A year is 4 monospace 13px characters plus button padding, px.
const LABEL_SPACING_PX = 48;

/** Slider thumb: 0 is the left one, 1 the right. */
export type ThumbIndex = 0 | 1;

/**
 * Horizontal centers of the year labels (px from the slider's left edge).
 *
 * Normally exactly under their thumbs. When thumbs get closer than `LABEL_SPACING_PX`, the label
 * of the stationary one stays put, and the label of the one being moved does not come closer:
 * it holds that distance from its neighbour. No label leaves the slider edges; at the very edge,
 * where there is nowhere to yield, the already stationary label moves aside.
 */
export function yearLabelCenters(
  thumbs: readonly [number, number],
  movingThumb: ThumbIndex,
  sliderWidth: number,
): [number, number] {
  const half = LABEL_SPACING_PX / 2;
  const maxCenter = Math.max(sliderWidth - half, half);
  const centers: [number, number] = [clamp(thumbs[0], half, maxCenter), clamp(thumbs[1], half, maxCenter)];
  if (centers[1] - centers[0] >= LABEL_SPACING_PX) {
    return centers;
  }

  if (movingThumb === 1) {
    centers[1] = centers[0] + LABEL_SPACING_PX;
  } else {
    centers[0] = centers[1] - LABEL_SPACING_PX;
  }

  if (centers[1] > maxCenter) {
    centers[1] = maxCenter;
    centers[0] = maxCenter - LABEL_SPACING_PX;
  } else if (centers[0] < half) {
    centers[0] = half;
    centers[1] = half + LABEL_SPACING_PX;
  }

  return centers;
}
