import type { ViewBox } from "../../../components/worldProjection";
import type { ArcPieces } from "./movementGeometry";

/**
 * Canvas rectangle containing all arcs; the map is fitted to it.
 *
 * `null` means nothing to fit: no routes, or some arc crosses the antimeridian and lies at both
 * map edges at once; the map then shows the whole world.
 */
export function connectionBounds(arcs: readonly ArcPieces[]): ViewBox | null {
  if (arcs.length === 0 || arcs.some((pieces) => pieces.length > 1)) {
    return null;
  }

  // A loop, not Math.min(...points): thousands of arcs have more points than a function accepts as arguments.
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const [x, y] of arcs.flatMap((pieces) => pieces.flat())) {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }

  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}
