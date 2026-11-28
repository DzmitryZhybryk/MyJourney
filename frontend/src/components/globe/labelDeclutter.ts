/*
 * Globe label declutter: decides whose labels fit, in pure screen coordinates with no DOM and no
 * knowledge of globe.gl (the integration collects rects and applies the result, see GlobeCanvas).
 *
 * Rules:
 *  - a label closer to the disk center wins: near the limb the projection squeezes distances and
 *    text there is unreadable anyway, so it yields; ties break by key for a stable order;
 *  - hysteresis: a hidden label returns only with extra clearance (SHOW_CLEARANCE_PX), otherwise
 *    it would flicker every rotation frame at the overlap boundary.
 */

/**
 * Screen rectangle of a label; `id` is a stable unique label key (a city name will not do:
 * same-named cities are legitimate).
 */
export interface LabelBox {
  readonly id: string;
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

/** Globe disk center in the same screen coordinates as `LabelBox`. */
export interface DiskCenter {
  readonly x: number;
  readonly y: number;
}

/** Extra clearance (px) a hidden label needs to return: hysteresis against flicker. */
export const SHOW_CLEARANCE_PX = 8;

/** Squared distance from the label rectangle's center to the disk center. */
function distanceSqToCenter(box: LabelBox, center: DiskCenter): number {
  const dx = box.left + box.width / 2 - center.x;
  const dy = box.top + box.height / 2 - center.y;
  return dx * dx + dy * dy;
}

/** Whether the rectangles intersect when each is inflated by `gap` on every side. */
export function boxesIntersect(a: LabelBox, b: LabelBox, gap: number): boolean {
  return (
    a.left < b.left + b.width + gap &&
    b.left < a.left + a.width + gap &&
    a.top < b.top + b.height + gap &&
    b.top < a.top + a.height + gap
  );
}

/**
 * Whether the candidate conflicts with any already accepted label (`gap` px of clearance
 * required; 0 means just no overlap).
 *
 * The linear scan is the one place to replace with a spatial grid once there are hundreds of
 * cities; the signature stays the same.
 */
function hasConflict(box: LabelBox, accepted: readonly LabelBox[], gap: number): boolean {
  return accepted.some((other) => boxesIntersect(box, other, gap));
}

/**
 * Decides which labels to hide in the current frame; returns their keys.
 *
 * Greedy selection in priority order (closer to the disk center first, ties by key): a label gets
 * space if it does not conflict with already accepted ones. A label hidden last frame needs
 * `SHOW_CLEARANCE_PX` of clearance, a visible one only no overlap (`previouslyHidden` carries
 * that hysteresis). Zero-size rectangles (label not rendered yet) are filtered by the caller.
 */
export function resolveLabelVisibility(
  boxes: readonly LabelBox[],
  center: DiskCenter,
  previouslyHidden: ReadonlySet<string>,
): ReadonlySet<string> {
  const byPriority = boxes
    .map((box) => ({ box, distanceSq: distanceSqToCenter(box, center) }))
    .sort((a, b) => a.distanceSq - b.distanceSq || (a.box.id < b.box.id ? -1 : 1))
    .map((entry) => entry.box);

  const accepted: LabelBox[] = [];
  const hidden = new Set<string>();
  for (const box of byPriority) {
    const requiredGap = previouslyHidden.has(box.id) ? SHOW_CLEARANCE_PX : 0;
    if (hasConflict(box, accepted, requiredGap)) {
      hidden.add(box.id);
    } else {
      accepted.push(box);
    }
  }

  return hidden;
}
