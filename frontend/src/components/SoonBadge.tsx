import { useTranslation } from "react-i18next";

import "./soon-badge.css";

/**
 * Compact "Soon" pill for unimplemented, disabled navigation items and actions. Text comes from
 * the `common` namespace (single source, follows the language), so the badge works in the header
 * and the section panel without the caller's namespace.
 */
export function SoonBadge() {
  const { t } = useTranslation("common");

  return <span className="soon-badge">{t("badge.soon")}</span>;
}
