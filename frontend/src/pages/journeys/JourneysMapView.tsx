import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Button, Loader, Text } from "@mantine/core";

import { cityLabel, useCityNames } from "../../api/cityNames";
import { getJourneysMapOptions, type JourneysMapResponse } from "../../api/sdk";
import type { MapCountry } from "../../components/WorldMap";
import { GeoNamesAttribution } from "./GeoNamesAttribution";
import { JourneysLegendCard } from "./JourneysLegendCard";
import { MAP_TONE } from "./journeys-data";
import type { JourneysMapScene } from "./map/journeysMapScene";
// The shell loads the shared map lazily; importing it here ships it with this tab, without a
// second round trip after the tab renders.
import "./map/JourneysSharedMap";
import { usePublishMapScene } from "./map/usePublishMapScene";

// Stable "no countries" reference: `WorldMap` recomputes colouring by prop identity.
const NO_COUNTRIES: readonly MapCountry[] = [];

/**
 * Converts the map aggregate into the `WorldMap` model.
 *
 * The endpoint returns only visited countries (wishlist is a separate request), so the status is
 * set here. The frontend resolves the country name from the code; the backend does not send it.
 *
 * Module-level (not an inline arrow): Query memoizes the `select` result by function reference.
 */
function toMapCountries(response: JourneysMapResponse): readonly MapCountry[] {
  return response.countries.map((country) => ({
    id: country.countryCode,
    status: "visited",
    cities: country.cities.map((city) => ({
      id: city.cityId,
      lat: city.latitude,
      lng: city.longitude,
      years: city.years,
    })),
  }));
}

/**
 * "Journey map" sub-tab, the index route /journeys. Fetches the user's journey aggregate from
 * the backend and colours the shared world map; an empty set means a grey map (no journeys).
 * Loading/error show as an overlay over the map; the map itself shows immediately.
 */
export function JourneysMapView() {
  const { t } = useTranslation("journeys");
  const { t: tCommon } = useTranslation("common");
  // `staleTime: 0`: own freshness on top of the queryKey shared with the globe background. The map
  // tab is opened to see current journeys, so fetch on every mount.
  const { data, isPending, isError, isFetching, refetch } = useQuery({
    ...getJourneysMapOptions(),
    staleTime: 0,
    select: toMapCountries,
  });

  const countries = data ?? NO_COUNTRIES;
  const nameOf = useCityNames(countries.flatMap((country) => country.cities.map((city) => city.id)));
  const unknownLabel = tCommon("map.unknownCity");
  const namedCountries = useMemo(
    () =>
      countries.map((country) => ({
        ...country,
        cities: country.cities.map((city) => ({ ...city, name: cityLabel(nameOf(city.id), unknownLabel) })),
      })),
    [countries, nameOf, unknownLabel],
  );
  const scene = useMemo<JourneysMapScene>(
    () => ({ tabId: "journeys", countries: namedCountries, tone: MAP_TONE }),
    [namedCountries],
  );
  usePublishMapScene(scene);

  return (
    <>
      {isPending && (
        <output className="journeys-map-status">
          <Loader size="sm" color="gray" />
          <Text size="sm" c="var(--text-muted)">
            {t("map.loading")}
          </Text>
        </output>
      )}
      {isError && (
        <div className="journeys-map-status" role="alert">
          <Text size="sm" fw={500} c="var(--text-error)">
            {t("map.error")}
          </Text>
          {/* The alert stays on screen during a retry; the spinner lives in the button itself,
              otherwise the control would vanish together with the message. */}
          <Button size="xs" variant="subtle" color="gray" loading={isFetching} onClick={() => refetch()}>
            {t("map.retry")}
          </Button>
        </div>
      )}
      <JourneysLegendCard />
      <GeoNamesAttribution />
    </>
  );
}
