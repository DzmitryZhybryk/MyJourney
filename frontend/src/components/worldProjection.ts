import { clamp } from "./globe/route";

/*
 * Flat world map projection: geographic coordinates -> SVG canvas coordinates, plus the visible
 * canvas area (zoom and pan). Shared by all flat maps so countries and what is drawn over them line up.
 */

// --- Equal Earth projection (Šavrič, Patterson, Jenny, 2018) ----------------
// Equal-area: shows true "how much was covered" without inflating the poles.
const A1 = 1.340264;
const A2 = -0.081106;
const A3 = 0.000893;
const A4 = 0.003796;
const M = Math.sqrt(3) / 2;
const DEG2RAD = Math.PI / 180;

function project(lng: number, lat: number): [number, number] {
  const lambda = lng * DEG2RAD;
  const phi = lat * DEG2RAD;
  const theta = Math.asin(M * Math.sin(phi));
  const t2 = theta * theta;
  const t6 = t2 * t2 * t2;
  const x =
    (2 * Math.sqrt(3) * lambda * Math.cos(theta)) /
    (3 * (A1 + 3 * A2 * t2 + 7 * A3 * t6 + 9 * A4 * t6 * t2));
  const y = theta * (A1 + A2 * t2 + A3 * t6 + A4 * t6 * t2);
  return [x, y];
}

// Canvas size is derived from the projection's real bounds, not eyeballed.
const VIEW_WIDTH = 1000;
const X_MAX = project(180, 0)[0];
const Y_MAX = project(0, 90)[1];
const VIEW_HEIGHT = Math.round((VIEW_WIDTH * Y_MAX) / X_MAX);

/**
 * If neighbouring points of a line jump across the antimeridian (Russia, Fiji, a Pacific
 * flight), the path must be broken, otherwise a horizontal stripe is drawn across the map.
 */
export const ANTIMERIDIAN_JUMP = 180;

/** Visible canvas area, in canvas coordinates. */
export interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** The whole world. */
export const WORLD_VIEW_BOX: ViewBox = { x: 0, y: 0, width: VIEW_WIDTH, height: VIEW_HEIGHT };

/** World aspect ratio: the visible area always keeps it; the map fits by height and crops width. */
export const WORLD_ASPECT = VIEW_WIDTH / VIEW_HEIGHT;

// Maximum zoom is 8x.
const MAX_ZOOM = 8;
const MIN_VIEW_WIDTH = VIEW_WIDTH / MAX_ZOOM;

/** Whether the whole map is visible (not zoomed in). */
export function isWorldView(view: ViewBox): boolean {
  return view.width >= VIEW_WIDTH;
}

/** Whether two areas are the same by value. */
export function isSameView(left: ViewBox, right: ViewBox): boolean {
  return left.x === right.x && left.y === right.y && left.width === right.width && left.height === right.height;
}

/** Clamps the area to a valid one: world aspect, zoom from the whole world to 8x, inside the world. */
export function clampView(view: ViewBox): ViewBox {
  // The world height is rounded, so width / WORLD_ASPECT would give 487.00000000000006; return
  // the exact constant for the whole world instead of recomputing.
  if (view.width >= VIEW_WIDTH) {
    return WORLD_VIEW_BOX;
  }

  const width = Math.max(view.width, MIN_VIEW_WIDTH);
  const height = width / WORLD_ASPECT;
  return {
    x: clamp(view.x, 0, VIEW_WIDTH - width),
    y: clamp(view.y, 0, VIEW_HEIGHT - height),
    width,
    height,
  };
}

/**
 * Zooms the area by `factor` (below one zooms out). The canvas point `(anchorX, anchorY)` stays
 * at the same screen position, so the map scales around the cursor.
 */
export function zoomView(view: ViewBox, factor: number, anchorX: number, anchorY: number): ViewBox {
  const width = clamp(view.width / factor, MIN_VIEW_WIDTH, VIEW_WIDTH);
  const ratio = width / view.width;
  return clampView({
    x: anchorX - (anchorX - view.x) * ratio,
    y: anchorY - (anchorY - view.y) * ratio,
    width,
    height: width / WORLD_ASPECT,
  });
}

/** Shifts the area by `(dx, dy)` canvas units. */
export function panView(view: ViewBox, dx: number, dy: number): ViewBox {
  return clampView({ ...view, x: view.x + dx, y: view.y + dy });
}

/** Converts longitude and latitude to canvas coordinates (x right, y down). */
export function projectToScreen(lng: number, lat: number): [number, number] {
  const [x, y] = project(lng, lat);
  return [((x + X_MAX) / (2 * X_MAX)) * VIEW_WIDTH, ((Y_MAX - y) / (2 * Y_MAX)) * VIEW_HEIGHT];
}
