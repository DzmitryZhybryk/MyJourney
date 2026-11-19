import { useState } from "react";
import { useTranslation } from "react-i18next";

import { JourneysLegend } from "./JourneysLegend";
import { MAP_TONE } from "./journeys-data";
import { isLegendCollapsed, setLegendCollapsed } from "./legendStorage";

/**
 * Floating legend card in a corner of the map. Collapses/expands on a title click; the choice is
 * remembered (localStorage) and applied on later visits.
 */
export function JourneysLegendCard() {
  const { t } = useTranslation("journeys");
  const [collapsed, setCollapsed] = useState(isLegendCollapsed);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      setLegendCollapsed(next);
      return next;
    });
  };

  return (
    <aside className="journeys-legend-card journeys-card">
      <button
        type="button"
        className="journeys-legend-card__toggle"
        aria-expanded={!collapsed}
        onClick={toggle}
      >
        {t("legendLabel")}
        <span
          className={
            collapsed
              ? "journeys-legend-card__chevron"
              : "journeys-legend-card__chevron journeys-legend-card__chevron--open"
          }
          aria-hidden="true"
        />
      </button>

      {!collapsed && <JourneysLegend tone={MAP_TONE} />}
    </aside>
  );
}
