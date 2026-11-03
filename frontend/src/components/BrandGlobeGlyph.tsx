import type { CSSProperties } from "react";

interface BrandGlobeGlyphProps {
  className?: string;
  style?: CSSProperties;
}

/**
 * Globe glyph standing in for the "o" in MyJourney (graticule: outline + meridian + equator).
 * Vector, so it is crisp at any size with no CDN dependency.
 *
 * Outline on `currentColor`, no fill: the mark inherits the text colour, so the same markup works
 * in both headers. The consumer sets the size (em units of the word's font size).
 */
export function BrandGlobeGlyph({ className, style }: BrandGlobeGlyphProps) {
  return (
    <svg aria-hidden viewBox="0 0 100 100" className={className} style={style}>
      <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="6" />
      <ellipse cx="50" cy="50" rx="18" ry="46" fill="none" stroke="currentColor" strokeWidth="4" />
      <line x1="6" y1="50" x2="94" y2="50" stroke="currentColor" strokeWidth="4" />
    </svg>
  );
}
