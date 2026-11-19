import { useTranslation } from "react-i18next";

/** CC BY 4.0 licence condition: credit the source wherever GeoNames city names are shown. */
export function GeoNamesAttribution() {
  const { t } = useTranslation("journeys");

  return (
    <p className="journeys-map-attribution">
      {t("map.attribution")}{" "}
      <a href="https://www.geonames.org" target="_blank" rel="noreferrer">
        GeoNames
      </a>
      ,{" "}
      <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">
        CC BY 4.0
      </a>
    </p>
  );
}
