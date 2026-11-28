import { Link } from "react-router";

import { BrandGlobeGlyph } from "./BrandGlobeGlyph";
import "./brand-mark.css";

const BRAND = "MyJourney";

interface BrandMarkProps {
  /**
   * Where the mark links. Differs by zone: `/home` in the app (a logged-in user at the root gets
   * a redirect, an extra hop via their own logo), `/` in the public zone.
   */
  to: string;
}

/**
 * MyJourney brand mark, one for both zones.
 *
 * Built on a plain `<Link>`, not Mantine `Text`: the mark also lives on the landing, where
 * nothing else uses Mantine.
 */
export function BrandMark({ to }: BrandMarkProps) {
  return (
    <Link
      to={to}
      className="brand-mark"
      // Without a label the mark is read as "MyJurney": the globe glyph between "MyJ" and
      // "urney" is hidden from screen readers and the text pieces get glued together.
      aria-label={BRAND}
    >
      MyJ
      <BrandGlobeGlyph className="brand-mark__globe" />
      urney
    </Link>
  );
}
