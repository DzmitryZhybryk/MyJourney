import { WORLD_ASPECT, WORLD_VIEW_BOX, clampView, type ViewBox } from "./worldProjection";

/** On-screen size of the map area, px. */
interface CanvasSize {
  width: number;
  height: number;
}

// Margin around the content, as a share of its size on each side.
const PADDING_RATIO = 0.15;
// Content narrower than this share of the world is not stretched: one short trip does not fill the screen.
const MIN_CONTENT_WIDTH_RATIO = 0.25;

/**
 * Picks a visible area so `bounds` (in canvas units) fit entirely into the part of the map area
 * that nothing covers.
 *
 * The map fits by height and extra width is cropped equally from both edges, so the visible
 * part is computed in pixels, not canvas fractions. `occludedLeft` is how many pixels on the
 * left are covered (by the navigation panel).
 */
export function fitView(bounds: ViewBox, canvas: CanvasSize, occludedLeft: number): ViewBox {
  const svgWidth = canvas.height * WORLD_ASPECT;
  // Offset from the map area's left edge to the SVG's left edge (negative if the SVG is wider).
  const svgOffset = (canvas.width - svgWidth) / 2;
  const areaLeft = Math.max(0, occludedLeft - svgOffset);
  const areaRight = Math.min(svgWidth, canvas.width - svgOffset);
  const areaWidth = areaRight - areaLeft;
  if (canvas.height <= 0 || areaWidth <= 0) {
    return WORLD_VIEW_BOX;
  }

  const contentWidth = Math.max(bounds.width * (1 + 2 * PADDING_RATIO), WORLD_VIEW_BOX.width * MIN_CONTENT_WIDTH_RATIO);
  const contentHeight = bounds.height * (1 + 2 * PADDING_RATIO);
  const unitsPerPx = Math.max(contentWidth / areaWidth, contentHeight / canvas.height);
  const width = unitsPerPx * svgWidth;
  if (width >= WORLD_VIEW_BOX.width) {
    return WORLD_VIEW_BOX;
  }

  // Center the content in the uncovered part; near the world edge the frame shifts inward.
  return clampView({
    x: bounds.x + bounds.width / 2 - ((areaLeft + areaRight) / 2) * unitsPerPx,
    y: bounds.y + bounds.height / 2 - (canvas.height / 2) * unitsPerPx,
    width,
    height: width / WORLD_ASPECT,
  });
}
