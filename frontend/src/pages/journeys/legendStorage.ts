/**
 * The "map legend collapsed" flag lives in localStorage: the choice persists across sessions and
 * visits, so once collapsed the map keeps opening with a collapsed legend.
 */

const LEGEND_COLLAPSED_KEY = "journeys-legend-collapsed";

/** Whether the legend is collapsed, per the user's saved choice. */
export function isLegendCollapsed(): boolean {
  try {
    return localStorage.getItem(LEGEND_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

/** Saves the collapsed state (collapsed: write the flag, expanded: clear it). */
export function setLegendCollapsed(collapsed: boolean): void {
  try {
    if (collapsed) {
      localStorage.setItem(LEGEND_COLLAPSED_KEY, "1");
    } else {
      localStorage.removeItem(LEGEND_COLLAPSED_KEY);
    }
  } catch {
    // localStorage unavailable (private mode / disabled): the state is not persisted.
  }
}
