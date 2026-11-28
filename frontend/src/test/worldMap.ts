/** jsdom may store a colour in another notation (`#0c4` as `rgb(0, 204, 68)`): compare through it. */
function normalizeColor(color: string): string {
  const probe = document.createElement("div");
  probe.style.color = color;
  return probe.style.color;
}

/**
 * Country paths of a `WorldMap` drawn with `fill`. A path has no accessible name, so a country is
 * found by its fill, which the map sets per status from the tone.
 */
export function countriesWithFill(container: HTMLElement, fill: string): SVGPathElement[] {
  const wanted = normalizeColor(fill);
  return [...container.querySelectorAll<SVGPathElement>(".world-map__country")].filter(
    (path) => normalizeColor(path.style.fill) === wanted,
  );
}
