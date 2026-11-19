import type { CardPosition } from "./controlsPosition";

/** Rectangle in map area coordinates, px. */
export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface PlacementLayout {
  /** Map area size. */
  area: { width: number; height: number };
  /** Card size (without the tab). */
  card: { width: number; height: number };
  /** How far the tab sticks out above the card. */
  overhangTop: number;
  /** Navigation panel over the map; `null` if it is not over it (mobile layout). */
  panel: Box | null;
}

// Inset from the map area edges when there is no panel: the same as the panel's on the left.
const EDGE_GAP = 32;
// Gap between the card and the panel when the card sits beside it.
const PANEL_GAP = 16;

function overlaps(first: Box, second: Box): boolean {
  return (
    first.left < second.left + second.width &&
    second.left < first.left + first.width &&
    first.top < second.top + second.height &&
    second.top < first.top + first.height
  );
}

/**
 * Where the filter card ends up if it is asked to go to `wanted`.
 *
 * The frame the card travels in is aligned to the navigation panel: the card's left edge is no
 * further left than the panel's, its top (with the tab) no higher than the panel's top; on the
 * right and bottom the inset from the map area edge equals the panel's on the left. The card never
 * overlaps the panel: dragged there, it lands beside it, right of the panel or under it, whichever is closer.
 */
export function placeCard(wanted: CardPosition, { area, card, overhangTop, panel }: PlacementLayout): CardPosition {
  const edge = panel ? panel.left : EDGE_GAP;
  const minLeft = edge;
  const maxLeft = Math.max(area.width - edge - card.width, minLeft);
  const minTop = (panel ? panel.top : EDGE_GAP) + overhangTop;
  const maxTop = Math.max(area.height - edge - card.height, minTop);
  const clampIntoFrame = (position: CardPosition): CardPosition => ({
    left: Math.min(Math.max(position.left, minLeft), maxLeft),
    top: Math.min(Math.max(position.top, minTop), maxTop),
  });

  const placed = clampIntoFrame(wanted);
  const footprint = (position: CardPosition): Box => ({
    left: position.left,
    top: position.top - overhangTop,
    width: card.width,
    height: card.height + overhangTop,
  });
  if (!panel || !overlaps(footprint(placed), panel)) {
    return placed;
  }

  // Overlapping the panel: the nearer of two spots beside it that fits in the frame.
  const besidePanel = [
    { left: panel.left + panel.width + PANEL_GAP, top: placed.top },
    { left: placed.left, top: panel.top + panel.height + PANEL_GAP + overhangTop },
  ]
    .map(clampIntoFrame)
    .filter((position) => !overlaps(footprint(position), panel));
  const distance = (position: CardPosition) => Math.hypot(position.left - placed.left, position.top - placed.top);
  return besidePanel.sort((first, second) => distance(first) - distance(second))[0] ?? placed;
}
