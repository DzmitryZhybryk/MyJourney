import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";

const BRAND = "MyJourney";

/**
 * Tab title for the current route.
 *
 * Without it the `<title>` from `index.html` is the same on every route: tabs and history
 * entries look identical and a screen reader does not announce where an SPA navigation led
 * (a route change is not a reload, so the title is the only "page changed" signal).
 *
 * Keys reuse the existing section copy so the tab title and the on-screen heading do not drift.
 * Renders `null`: it is an effect, not markup.
 */
export function DocumentTitle() {
  const { pathname } = useLocation();
  const { t, i18n } = useTranslation(["common", "auth", "journeys"]);

  useEffect(() => {
    const title = resolveTitle(pathname, t);
    // The landing carries a full title with the pitch, inner screens use "Section · Brand".
    document.title = title === null ? `${BRAND} — ${t("pageTitle.landing")}` : `${title} · ${BRAND}`;
    // i18n.language is a dependency: on a language switch `t` is the same function but the title
    // must be retranslated, otherwise the tab keeps the old language until the next navigation.
  }, [pathname, t, i18n.language]);

  return null;
}

/** Section title, or `null` for the landing (it has its own full title). */
function resolveTitle(pathname: string, t: (key: string) => string): string | null {
  if (pathname.startsWith("/login")) return t("auth:login.title");
  if (pathname.startsWith("/signup")) return t("auth:signup.title");
  if (pathname.startsWith("/home")) return t("pageTitle.home");
  if (pathname.startsWith("/journeys/add")) return t("journeys:addJourney.title");
  if (pathname.startsWith("/journeys")) return t("journeys:title");

  return null;
}
