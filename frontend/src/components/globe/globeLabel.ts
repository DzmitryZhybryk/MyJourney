/*
 * HTML city label for the globe (dot + name). The globe.gl HTML layer is used instead of 3D
 * labels: full Unicode (diacritics like "Reykjavík" render correctly, no "?"), and a text-shadow
 * keeps it bright and readable on a busy texture. Far-side occlusion comes from
 * `htmlElementVisibilityModifier` (applyLabelVisibility below).
 */

/** Without `name` the label is just a dot: the city name has not arrived yet. */
export function createGlobeLabel(name: string | undefined, id: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "globe-label";
  // Stable label key for the declutterer: names are not unique (same-named cities are legitimate),
  // so the key includes coordinates; textContent stays pure display.
  wrapper.dataset.labelId = id;
  // Start at zero: `applyLabelVisibility` immediately sets 1 for visible labels and the CSS
  // transition (globe-label.css) fades them in, so the user's real cities FADE IN on entering
  // /home instead of popping in over the curated ones. The fade depends on the active render
  // loop (globe.gl calls the modifier): the only screen with a pause (/journeys) is hidden there
  // too, so no label gets stuck at 0. If a "paused but visible" screen appears, labels will need
  // a different reveal.
  wrapper.style.opacity = "0";

  const dot = document.createElement("span");
  dot.className = "globe-label__dot";
  wrapper.append(dot);
  if (name === undefined) {
    return wrapper;
  }

  const label = document.createElement("span");
  label.className = "globe-label__name";
  label.textContent = name;

  wrapper.append(label);
  return wrapper;
}

/** Hides the label when its point is on the invisible (far) side of the globe. */
export function applyLabelVisibility(el: HTMLElement, isVisible: boolean): void {
  el.style.opacity = isVisible ? "1" : "0";
}

/**
 * Hides/shows ONLY the label text; the city dot always stays visible. This is the collision
 * declutterer's channel (a class on the wrapper, CSS hides `__name`); it does not overlap with
 * the occlusion above, which owns the wrapper's inline opacity.
 */
export function applyLabelDeclutter(wrapper: HTMLElement, isHidden: boolean): void {
  wrapper.classList.toggle("globe-label--decluttered", isHidden);
}
