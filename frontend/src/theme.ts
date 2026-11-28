import { createTheme, type MantineColorsTuple } from "@mantine/core";

const slate: MantineColorsTuple = [
  "#f8fafc",
  "#f1f5f9",
  "#e2e8f0",
  "#cbd5e1",
  "#94a3b8",
  "#64748b",
  "#475569",
  "#334155",
  "#1e293b",
  "#0f172a",
];

// Accent: golden-hour terracotta. Main shade (--sun #e8935c) is shade 6 (primaryShade), the dark
// one (--sun-deep #cf6a3a) is shade 7 (hover of filled buttons).
const sun: MantineColorsTuple = [
  "#fdf4ed",
  "#f7e4d3",
  "#eecaa7",
  "#e6b17d",
  "#e19a5c",
  "#dd8f4e",
  "#e8935c",
  "#cf6a3a",
  "#ad5620",
  "#8c4310",
];

/*
 * Do NOT duplicate font stacks as literals: use the CSS variables declared in `index.css`.
 * `:root` is the single source of truth.
 */
const bodyFont = "var(--font-body)";
const displayFont = "var(--font-display)";

export const theme = createTheme({
  primaryColor: "sun",
  primaryShade: 6,
  colors: { slate, sun },
  /*
   * Mantine picks the label colour on accent-filled buttons. The accent `#e8935c` is light
   * (luminance 0.388 vs threshold 0.179), so a white label gave 2.4:1, below AA; with
   * `autoContrast` a dark label is used: 7.2:1.
   *
   * `black` is overridden on purpose: autoContrast uses `theme.black`, and pure #000 on terracotta
   * is harsher than the designed `--on-sun`. Same value as the token, so Mantine and CSS agree.
   */
  autoContrast: true,
  black: "#2a1608",
  fontFamily: bodyFont,
  headings: { fontFamily: displayFont, fontWeight: "600" },
  defaultRadius: "md",
  radius: {
    xs: "4px",
    sm: "8px",
    md: "10px",
    lg: "16px",
    xl: "20px",
  },
  cursorType: "pointer",
});
