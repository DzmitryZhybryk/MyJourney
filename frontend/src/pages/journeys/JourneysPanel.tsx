import type { Ref } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";

import { SoonBadge } from "../../components/SoonBadge";

// Section sub-navigation (maps -> lists). The journey map item has end=true so /journeys is not
// highlighted on child routes. "Add" is separate below.
// `soon: true` marks an unimplemented section: the item renders inactive (not a link) with a
// "Soon" badge instead of linking to an empty route.
const NAV_ITEMS = [
  { key: "map", to: "/journeys", end: true, soon: false },
  { key: "movements", to: "/journeys/movements", end: false, soon: false },
  { key: "all", to: "/journeys/all", end: false, soon: false },
  { key: "wishlist", to: "/journeys/wishlist", end: false, soon: true },
] as const;

/**
 * Left side menu of the Journeys section: title and sub-navigation. The map legend is a separate
 * corner block (see JourneysMapView).
 */
interface JourneysPanelProps {
  /** Needed by the map so it does not hide under the panel what it shows initially. */
  ref?: Ref<HTMLElement>;
}

export function JourneysPanel({ ref }: JourneysPanelProps) {
  const { t } = useTranslation("journeys");

  return (
    <section ref={ref} className="journeys-panel journeys-card" aria-label={t("controls")}>
      <span className="journeys-panel__label">{t("title")}</span>

      <nav className="journeys-nav">
        {NAV_ITEMS.map((item) =>
          item.soon ? (
            <span
              key={item.key}
              className="journeys-nav__item journeys-nav__item--soon"
              aria-disabled="true"
              title={t("common:badge.comingSoon")}
            >
              {t(`nav.${item.key}`)}
              <SoonBadge />
            </span>
          ) : (
            <NavLink
              key={item.key}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? "journeys-nav__item journeys-nav__item--active" : "journeys-nav__item"
              }
            >
              {t(`nav.${item.key}`)}
            </NavLink>
          ),
        )}
        <NavLink
          to="/journeys/add"
          className={({ isActive }) =>
            isActive ? "journeys-nav__add journeys-nav__add--active" : "journeys-nav__add"
          }
        >
          {t("nav.add")}
        </NavLink>
        {/*
         * "Add place" (seas, mountains, ...) is a secondary action beside "Add journey" (cities).
         * Not implemented yet: a disabled button with a "Soon" badge.
         */}
        <button
          type="button"
          className="journeys-nav__add-place"
          disabled
          title={t("common:badge.comingSoon")}
        >
          {t("nav.addPlace")}
          <SoonBadge />
        </button>
      </nav>
    </section>
  );
}
