import type { WorldMapTone } from "../../components/WorldMap";

/*
 * Map status palette on the night surface.
 *
 * The key rule is about AREA, not hue: a country fill covers half the screen, so it is muted. Pure
 * `--sun` (#e8935c) stays for small elements (buttons, active states); flooding continents with it
 * stops it being an accent. Visited is therefore a deep terracotta: clearly lighter than land,
 * clearly quieter than buttons.
 *
 * Statuses are separated by palette meaning: visited is warm and "lit"; wishlist is periwinkle,
 * the palette's "cold distance". The pair differs in both hue and lightness, so it reads under
 * colour blindness (the earlier emerald/amber converged to one yellow-brown in deuteranopia).
 *
 * Values are literals, not `var(--...)`: the colours go into SVG `fill`/`stroke` attributes where
 * CSS variables do not work.
 */
export const MAP_TONE: WorldMapTone = {
  land: "#2b3147", // land rises above the night but stays background
  border: "#3d4560", // outline one step lighter than land
  visited: "#b2703f", // muted terracotta: quieter than buttons, lighter than land
  wishlist: "#5b6ea6", // muted periwinkle: "cold distance"
  cityDot: "#f4ede2", // a light dot reads on both land and a visited country
};
