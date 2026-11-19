/**
 * Where the user dragged the movements map filter card; kept in localStorage and survives a
 * reload and leaving the tab. With nothing saved the card sits in the bottom-left corner.
 */

/** Card position from the top-left corner of the map area, px. */
export interface CardPosition {
  left: number;
  top: number;
}

const CONTROLS_POSITION_KEY = "journeys-movements-controls-position";

function isCardPosition(value: unknown): value is CardPosition {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const { left, top } = value as Record<string, unknown>;
  return typeof left === "number" && Number.isFinite(left) && typeof top === "number" && Number.isFinite(top);
}

/** Saved card position; `null` means not saved or corrupted. */
export function readControlsPosition(): CardPosition | null {
  try {
    const stored = localStorage.getItem(CONTROLS_POSITION_KEY);
    const parsed: unknown = stored === null ? null : JSON.parse(stored);
    return isCardPosition(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

/** Saves the card position; `null` forgets it and the card returns to the default corner. */
export function saveControlsPosition(position: CardPosition | null): void {
  try {
    if (position) {
      localStorage.setItem(CONTROLS_POSITION_KEY, JSON.stringify(position));
    } else {
      localStorage.removeItem(CONTROLS_POSITION_KEY);
    }
  } catch {
    // localStorage unavailable (private mode / disabled): the position is not persisted.
  }
}
