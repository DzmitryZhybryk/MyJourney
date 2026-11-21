import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";

import { AppHeader } from "../components/AppHeader";
import { ADMIN_SECTIONS } from "./adminSections";
import "./admin-layout.css";

/** Admin shell: the app header, the section menu on the left, the chosen section on the right. */
export function AdminLayout() {
  const { t } = useTranslation("admin");

  return (
    <div className="app-shell">
      <AppHeader />

      <div className="admin-layout">
        <nav className="admin-nav" aria-label={t("title")}>
          <span className="admin-nav__title">{t("title")}</span>
          {ADMIN_SECTIONS.map((section) => (
            <NavLink
              key={section.key}
              to={section.path}
              className={({ isActive }) => (isActive ? "admin-nav__link admin-nav__link--active" : "admin-nav__link")}
            >
              {t(`sections.${section.key}`)}
            </NavLink>
          ))}
        </nav>

        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
