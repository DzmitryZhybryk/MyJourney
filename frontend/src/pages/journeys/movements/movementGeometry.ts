import { greatCirclePoint } from "../../../components/globe/route";
import { ANTIMERIDIAN_JUMP, projectToScreen } from "../../../components/worldProjection";

/** Flat map canvas point: `[x, y]`. */
type ScreenPoint = readonly [number, number];

/**
 * Route arc on the canvas. Usually one piece; an arc across the antimeridian is cut into two,
 * otherwise its tail would stretch across the whole map.
 */
export type ArcPieces = readonly (readonly ScreenPoint[])[];

interface Coordinates {
  latitude: number;
  longitude: number;
}

// A great-circle arc is drawn as a polyline: with this many segments no kinks show even across half the world.
const ARC_SEGMENTS = 48;

/** Projects the great-circle arc between two cities onto the map canvas. */
export function projectArc(origin: Coordinates, destination: Coordinates): ArcPieces {
  const pieces: ScreenPoint[][] = [];
  let prevLng: number | null = null;
  for (let step = 0; step <= ARC_SEGMENTS; step += 1) {
    const { lat, lng } = greatCirclePoint(
      origin.latitude,
      origin.longitude,
      destination.latitude,
      destination.longitude,
      step / ARC_SEGMENTS,
    );
    if (prevLng === null || Math.abs(lng - prevLng) > ANTIMERIDIAN_JUMP) {
      pieces.push([]);
    }

    pieces[pieces.length - 1].push(projectToScreen(lng, lat));
    prevLng = lng;
  }

  return pieces;
}

/** SVG path of an arc piece. */
export function piecePath(piece: readonly ScreenPoint[]): string {
  return piece.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");
}

/** An arc piece split for fading at the world edge. */
export interface EdgeFadeSplit {
  /** Solid part of the piece, in drawing order; empty if the whole piece is shorter than the fade. */
  solid: readonly ScreenPoint[];
  /** Fading tail at the edge, in drawing order. */
  fade: readonly ScreenPoint[];
  /** Opacity gradient axis: from where the tail starts fading to the edge itself. */
  fadeAxis: readonly [ScreenPoint, ScreenPoint];
}

/**
 * Splits an arc piece into a solid part and a tail of `length` along the arc at the end that left
 * the world edge (`edge` says which end of the piece lies on it; `length` is in canvas units).
 * The gradient goes on the tail only: a linear gradient over the whole piece would fade the arc
 * along the tail's direction, not its length, and an arc turning after the edge would vanish.
 */
export function splitEdgeFade(piece: readonly ScreenPoint[], edge: "start" | "end", length: number): EdgeFadeSplit {
  // Walk from the edge inward until the fade length is covered.
  const fromEdge = edge === "end" ? [...piece].reverse() : [...piece];
  const fade: ScreenPoint[] = [fromEdge[0]];
  let travelled = 0;
  let index = 1;
  for (; index < fromEdge.length; index += 1) {
    const [prevX, prevY] = fromEdge[index - 1];
    const [x, y] = fromEdge[index];
    const step = Math.hypot(x - prevX, y - prevY);
    if (travelled + step >= length) {
      // The fade start point is inside this segment, at the needed distance from the edge.
      const ratio = step === 0 ? 0 : (length - travelled) / step;
      fade.push([prevX + (x - prevX) * ratio, prevY + (y - prevY) * ratio]);
      break;
    }

    travelled += step;
    fade.push(fromEdge[index]);
  }

  const inner = fade[fade.length - 1];
  const rest = fromEdge.slice(index);
  // The fade ended exactly at a vertex: it is already first in the rest, no need to add it twice.
  const isSplitAtVertex = rest.length > 0 && rest[0][0] === inner[0] && rest[0][1] === inner[1];
  const solidFromEdge = rest.length === 0 || isSplitAtVertex ? rest : [inner, ...rest];
  const inDrawingOrder = (points: ScreenPoint[]) => (edge === "end" ? points.reverse() : points);

  return { solid: inDrawingOrder(solidFromEdge), fade: inDrawingOrder(fade), fadeAxis: [inner, fromEdge[0]] };
}
