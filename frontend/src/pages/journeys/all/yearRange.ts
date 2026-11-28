/** Feed year range `[from, to]`, both bounds inclusive; `null` means all years. */
export type YearRange = readonly [from: number, to: number];

/**
 * Selected years fitted into the current scale.
 *
 * The scale changes after editing and deleting journeys, and a selection that fell outside it
 * cannot be cleared without the slider.
 *
 * Returns `null` (all years) when nothing is selected, the selection covers the whole scale or
 * fell entirely outside it, there is no scale, or it holds a single year (then there is no slider).
 */
export function fitYearRange(
  yearRange: YearRange | null,
  firstYear: number | undefined,
  lastYear: number | undefined,
): YearRange | null {
  if (yearRange === null || firstYear === undefined || lastYear === undefined || firstYear === lastYear) {
    return null;
  }

  const from = Math.max(yearRange[0], firstYear);
  const to = Math.min(yearRange[1], lastYear);
  if (from > to || (from === firstYear && to === lastYear)) {
    return null;
  }

  return [from, to];
}
