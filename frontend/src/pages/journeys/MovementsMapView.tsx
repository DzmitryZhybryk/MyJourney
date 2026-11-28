import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOutletContext } from "react-router";
import { Button, Loader, Text } from "@mantine/core";

import { cityLabel, useCityNames } from "../../api/cityNames";
import { zTransportTypeEnum, type MovementsMapResponse, type TransportTypeEnum } from "../../api/sdk";
import type { MapCountry } from "../../components/WorldMap";
import { WORLD_VIEW_BOX, type ViewBox } from "../../components/worldProjection";
import { GeoNamesAttribution } from "./GeoNamesAttribution";
import { MAP_TONE } from "./journeys-data";
import type { JourneysOutletContext } from "./JourneysLayout";
import type { JourneysMapScene } from "./map/journeysMapScene";
// The shell loads the shared map lazily; importing it here ships it with this tab.
import "./map/JourneysSharedMap";
import { usePublishMapScene } from "./map/usePublishMapScene";
import { connectionBounds } from "./movements/connectionBounds";
import { MovementConnections, type ProjectedConnection } from "./movements/MovementConnections";
import { MovementsControls, type YearWindow } from "./movements/MovementsControls";
import { projectArc } from "./movements/movementGeometry";
import { movementsQueryOptions } from "./movements/movementsQuery";

// Stable "empty" references: `WorldMap` and the arrow layer recompute by prop identity.
const NO_COUNTRIES: readonly MapCountry[] = [];
const NO_CONNECTIONS: readonly ProjectedConnection[] = [];

interface MovementsData {
  firstYear: number | null;
  lastYear: number | null;
  connections: readonly ProjectedConnection[];
}

/**
 * Projects the route arcs once per response.
 *
 * Module-level (not an inline arrow): Query memoizes the `select` result by function reference.
 */
function toMovementsData(response: MovementsMapResponse): MovementsData {
  return {
    firstYear: response.firstYear,
    lastYear: response.lastYear,
    connections: response.connections.map((connection) => ({
      key: `${connection.origin.cityId}>${connection.destination.cityId}`,
      origin: connection.origin,
      destination: connection.destination,
      years: connection.years,
      arc: projectArc(connection.origin, connection.destination),
    })),
  };
}

/**
 * "Movements map" sub-tab, route /journeys/movements: where the user travelled, an arrow per
 * route, with city names. Routes are filtered by a year window and transport types.
 *
 * The year window applies on the client, by the years each route carries, so lines change as the
 * slider is dragged, with no requests. Transport goes through a request: while a new set loads,
 * the previous routes stay on the map. The year scale, map frame and city names come from all
 * journeys, unfiltered, so the frame does not jump. Countries are one colour, no tooltips.
 */
export function MovementsMapView() {
  const { t } = useTranslation("journeys");
  const { t: tCommon } = useTranslation("common");
  const { panelRef } = useOutletContext<JourneysOutletContext>();

  const all = useQuery({ ...movementsQueryOptions(), select: toMovementsData });
  const firstYear = all.data?.firstYear ?? null;
  const lastYear = all.data?.lastYear ?? null;
  const allConnections = all.data?.connections ?? NO_CONNECTIONS;

  // The year window is unset until the user touches the slider; then it means all years.
  const [selectedWindow, setSelectedWindow] = useState<YearWindow | null>(null);
  const [transportTypes, setTransportTypes] = useState<readonly TransportTypeEnum[]>(zTransportTypeEnum.options);
  const hasTransport = transportTypes.length > 0;
  const window = useMemo<YearWindow | null>(
    () => selectedWindow ?? (firstYear !== null && lastYear !== null ? [firstYear, lastYear] : null),
    [selectedWindow, firstYear, lastYear],
  );

  // All transport types share the key of the unfiltered request, so no second request is sent.
  const shown = useQuery({
    ...movementsQueryOptions(transportTypes),
    select: toMovementsData,
    placeholderData: keepPreviousData,
    enabled: hasTransport,
  });
  const shownConnections = shown.data?.connections;
  // A route is visible if at least one of its journeys falls in the year window.
  const connections = useMemo(() => {
    if (!hasTransport || !shownConnections || !window) {
      return NO_CONNECTIONS;
    }

    const [from, to] = window;
    return shownConnections.filter((connection) => connection.years.some((year) => year >= from && year <= to));
  }, [hasTransport, shownConnections, window]);

  const fitBounds = useMemo(
    () => connectionBounds(allConnections.map((connection) => connection.arc)),
    [allConnections],
  );
  const nameOf = useCityNames(
    allConnections.flatMap((connection) => [connection.origin.cityId, connection.destination.cityId]),
  );
  const unknownLabel = tCommon("map.unknownCity");
  const labelOf = useCallback((cityId: string) => cityLabel(nameOf(cityId), unknownLabel), [nameOf, unknownLabel]);

  const overlay = useCallback(
    (view: ViewBox) => (
      <MovementConnections
        connections={connections}
        unitScale={view.width / WORLD_VIEW_BOX.width}
        labelOf={labelOf}
      />
    ),
    [connections, labelOf],
  );
  const scene = useMemo<JourneysMapScene>(
    () => ({
      tabId: "movements",
      countries: NO_COUNTRIES,
      tone: MAP_TONE,
      fitBounds,
      occluderRef: panelRef,
      isInteractive: false,
      overlay,
    }),
    [fitBounds, panelRef, overlay],
  );
  usePublishMapScene(scene);

  const isError = all.isError || (hasTransport && shown.isError);
  const retry = () => {
    void all.refetch();
    if (hasTransport) {
      void shown.refetch();
    }
  };

  return (
    <>
      {all.isPending && (
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
          <Button
            size="xs"
            variant="subtle"
            color="gray"
            loading={all.isFetching || shown.isFetching}
            onClick={retry}
          >
            {t("map.retry")}
          </Button>
        </div>
      )}
      {all.isSuccess && allConnections.length === 0 && (
        <output className="journeys-map-status">
          <Text size="sm" c="var(--text-muted)">
            {t("movements.empty")}
          </Text>
        </output>
      )}
      {firstYear !== null && lastYear !== null && window && (
        <MovementsControls
          firstYear={firstYear}
          lastYear={lastYear}
          window={window}
          onWindowChange={setSelectedWindow}
          transportTypes={transportTypes}
          onTransportTypesChange={setTransportTypes}
          panelRef={panelRef}
        />
      )}
      <GeoNamesAttribution />
    </>
  );
}
