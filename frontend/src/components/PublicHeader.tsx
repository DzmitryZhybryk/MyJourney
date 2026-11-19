import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import { BrandMark } from "./BrandMark";
import { LanguageSwitcher } from "./LanguageSwitcher";
import "./public-header.css";

/**
 * Public zone header (landing + login/signup). Mounted once in `PublicLayout`, so it survives
 * navigation together with the globe and is not redrawn going landing -> form.
 *
 * The active pill comes from the route: "Sign up" on `/signup`, "Log in" on `/login`, and on the
 * landing "Sign up" by default as the primary action.
 */
export function PublicHeader() {
  const { t } = useTranslation("landing");
  const { pathname } = useLocation();
  const isLogin = pathname.startsWith("/login");

  return (
    <header className="public-header">
      <BrandMark to="/" />
      <nav className="public-header__nav" aria-label={t("nav.label")}>
        <LanguageSwitcher className="public-header__lang" />
        <div className="public-header__pills">
          <Link
            to="/signup"
            className={isLogin ? "public-header__pill" : "public-header__pill is-active"}
          >
            {t("nav.signup")}
          </Link>
          <Link
            to="/login"
            className={isLogin ? "public-header__pill is-active" : "public-header__pill"}
          >
            {t("nav.login")}
          </Link>
        </div>
      </nav>
    </header>
  );
}
