import { useTranslation } from "react-i18next";

import { AppHeader } from "../components/AppHeader";
import { useCurrentUser } from "../user/useCurrentUser";
import "./home.css";

/*
 * PLACEHOLDERS. The dashboard is not wired to the backend yet: the API returns no statistics,
 * recommendations or recent trips. The data is English on purpose: translating fictional numbers
 * and descriptions into two languages doubles work that goes away with the mock. The section
 * labels around them are real UI and go through i18n.
 */
const STAT_KEYS = ["countries", "cities", "streak"] as const;
const STAT_VALUES: Record<(typeof STAT_KEYS)[number], number> = {
  countries: 12,
  cities: 47,
  streak: 7,
};

const RECOMMENDED = {
  countries: [
    { name: "Norway", desc: "Fjords and aurora skies" },
    { name: "Vietnam", desc: "Street food and old temples" },
    { name: "Peru", desc: "Andean trails to Machu Picchu" },
  ],
  cities: [
    { name: "Kyoto", desc: "Zen gardens, quiet shrines" },
    { name: "Porto", desc: "Riverside wine and azulejos" },
    { name: "Reykjavik", desc: "Geothermal lagoons up north" },
  ],
} as const;

const RECENT = [
  { city: "Tokyo", date: "Mar 2026" },
  { city: "Lisbon", date: "Jan 2026" },
  { city: "Berlin", date: "Nov 2025" },
] as const;

/**
 * "Saturday · May 2026": the current date in the UI language. Built from parts (weekday +
 * standalone month + year) rather than one format: the single Russian Intl format would add
 * "г." after the year and decline the month ("мая" instead of "май").
 */
function formatGreetingDate(locale: string): string {
  const now = new Date();
  const weekday = new Intl.DateTimeFormat(locale, { weekday: "long" }).format(now);
  const month = new Intl.DateTimeFormat(locale, { month: "long" }).format(now);
  return `${weekday} · ${month} ${now.getFullYear()}`;
}

export function HomePage() {
  const { t, i18n } = useTranslation("common");
  const currentUser = useCurrentUser();

  return (
    <div className="app-shell home-shell" data-globe-passthrough>
      <AppHeader />

      <main className="home-main">
        {/* The date does not depend on the network and shows immediately; only the greeting line
            is gated on /me. While there is no profile (loading/error) an nbsp holds its place, so
            the name appears on a reserved line with no layout jump. */}
        <div className="home-greeting">
          <span className="home-greeting__hello">
            {currentUser.status === "ready"
              ? t("greeting", { name: currentUser.user.displayName })
              : " "}
          </span>
          <span className="home-greeting__date">{formatGreetingDate(i18n.language)}</span>
        </div>

        {/* Empty center slot where the app-global globe background visually sits (the root
            PersistentGlobeHost, framed by data-screen="home"). Holds the vertical rhythm greeting ->
            planet -> caption; it is transparent to both eyes and events, so gestures pass through
            to the planet (drag rotation, contract in persistent-globe.css). */}
        <div className="home-stage" aria-hidden data-globe-slot />

        <p className="home-aura">{t("home.aura")}</p>

        <aside className="home-recommend" aria-label={t("home.recommend.aria")}>
          <div className="home-recommend__head">
            <span className="home-recommend__title">{t("home.recommend.title")}</span>
            <span className="home-recommend__caption">{t("home.recommend.caption")}</span>
          </div>

          <div className="home-recommend__group">
            <span className="home-recommend__group-label">{t("home.recommend.countries")}</span>
            <ul className="home-recommend__list">
              {RECOMMENDED.countries.map((item) => (
                <li key={item.name} className="home-recommend__item">
                  <span className="home-recommend__name">{item.name}</span>
                  <span className="home-recommend__desc">{item.desc}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="home-recommend__group">
            <span className="home-recommend__group-label">{t("home.recommend.cities")}</span>
            <ul className="home-recommend__list">
              {RECOMMENDED.cities.map((item) => (
                <li key={item.name} className="home-recommend__item">
                  <span className="home-recommend__name">{item.name}</span>
                  <span className="home-recommend__desc">{item.desc}</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <aside className="home-right" aria-label={t("home.activity.aria")}>
          <div className="home-stats">
            <span className="home-stats__title">{t("home.stats.title")}</span>
            <ul className="home-stats__list">
              {STAT_KEYS.map((key) => (
                <li key={key} className="home-stat">
                  <span className="home-stat__name">{t(`home.stats.${key}`)}</span>
                  <span className="home-stat__meta">
                    {key === "streak"
                      ? t("home.stats.days", { count: STAT_VALUES[key] })
                      : t("home.stats.visited", { count: STAT_VALUES[key] })}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="home-recent">
            <span className="home-recent__title">{t("home.recent.title")}</span>
            <ul className="home-recent__list">
              {RECENT.map((entry) => (
                <li key={entry.city} className="home-recent__item">
                  <span className="home-recent__city">{entry.city}</span>
                  <span className="home-recent__date">{entry.date}</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </main>
    </div>
  );
}
