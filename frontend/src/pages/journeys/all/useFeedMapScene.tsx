import { useCallback, useMemo, useState, type RefObject } from "react";
import { useTranslation } from "react-i18next";

import { cityLabel, useCityNames } from "../../../api/cityNames";
import type { JourneyFeedEntry } from "../../../api/sdk";
import type { MapCountry } from "../../../components/WorldMap";
import { projectToScreen, WORLD_VIEW_BOX, type ViewBox } from "../../../components/worldProjection";
import { MAP_TONE } from "../journeys-data";
import type { JourneysMapScene } from "../map/journeysMapScene";
import { usePublishMapScene } from "../map/usePublishMapScene";
import { ArrowMarker } from "../movements/ArrowMarker";
import { connectionBounds } from "../movements/connectionBounds";
import { layOutCityLabels } from "../movements/labelPlacement";
import { piecePath, projectArc } from "../movements/movementGeometry";

const NO_COUNTRIES: readonly MapCountry[] = [];
// Sizes in canvas units at the whole-world view.
const DOT_RADIUS = 2.6;
const LINE_WIDTH = 1.8;
const ARROW_SIZE = 7;
// One arc at a time on this map, so one marker id; the leaving layer fades with the same shape.
const ARROW_MARKER_ID = "feed-arc-arrow";
const LABEL_FONT_SIZE = 8;
// Label offset from the dot edge, clearance from the arc, halo stroke behind the text.
const LABEL_GAP = 2;
const LABEL_CLEARANCE = 1.2;
const LABEL_HALO_WIDTH = 2.4;

interface FeedMapSceneOptions {
  /** Loaded feed journeys: before the first hover the frame covers all of them. */
  journeys: readonly JourneyFeedEntry[];
  /** Journey whose arc to show; `null` means a map without an arc. */
  activeJourney: JourneyFeedEntry | null;
  /** Feed column over the map: the frame fits into the part it does not cover. */
  occluderRef: RefObject<HTMLElement | null>;
  /** `false` (narrow screen, the column is full width): the feed has no map. */
  isEnabled: boolean;
}

/**
 * Publishes the feed's scene on the shared map: muted land behind the column, visible through it,
 * and the arc of the journey the user is on (hovered, focused, edited or dragged) with city names
 * at the ends. The map is background and not clickable.
 *
 * The frame glides to the hovered journey and stays on it after the cursor leaves the feed, so the
 * map does not jump back and forth. Before the first hover the frame covers all loaded journeys.
 * The arc is redrawn for each new journey, keyed by its id.
 */
export function useFeedMapScene({ journeys, activeJourney, occluderRef, isEnabled }: FeedMapSceneOptions): void {
  const { t } = useTranslation("common");
  const [framedJourney, setFramedJourney] = useState<JourneyFeedEntry | null>(null);
  if (activeJourney !== null && activeJourney !== framedJourney) {
    setFramedJourney(activeJourney);
  }

  // Same city set as the feed: names come from its request, no new one per hover.
  const nameOf = useCityNames(journeys.flatMap((journey) => [journey.origin.cityId, journey.destination.cityId]));
  const unknownLabel = t("map.unknownCity");

  const fitBounds = useMemo(() => {
    const framed = framedJourney ? [framedJourney] : journeys;
    return connectionBounds(framed.map((journey) => projectArc(journey.origin, journey.destination)));
  }, [framedJourney, journeys]);
  const arc = useMemo(
    () => (activeJourney ? projectArc(activeJourney.origin, activeJourney.destination) : null),
    [activeJourney],
  );

  const overlay = useCallback(
    (view: ViewBox) => {
      if (!activeJourney || !arc) {
        return null;
      }

      const unitScale = view.width / WORLD_VIEW_BOX.width;
      const ends = [activeJourney.origin, activeJourney.destination].map((city) => {
        const [x, y] = projectToScreen(city.longitude, city.latitude);
        return { cityId: city.cityId, x, y };
      });
      // A journey from a city to itself is one dot and one label.
      const cities = ends[0].cityId === ends[1].cityId ? [ends[0]] : ends;
      const labels = layOutCityLabels(
        cities.flatMap((city) => {
          const label = cityLabel(nameOf(city.cityId), unknownLabel);
          return label ? [{ ...city, label, routeCount: 1 }] : [];
        }),
        [arc],
        {
          fontSize: LABEL_FONT_SIZE * unitScale,
          gap: (DOT_RADIUS + LABEL_GAP) * unitScale,
          dotRadius: DOT_RADIUS * unitScale,
          clearance: LABEL_CLEARANCE * unitScale,
        },
      );

      return (
        <g key={activeJourney.journeyId} className="feed-arc">
          <defs>
            <ArrowMarker id={ARROW_MARKER_ID} size={ARROW_SIZE * unitScale} className="feed-arc__arrow" />
          </defs>
          {arc.map((piece, pieceIndex) => (
            <path
              key={`${piece[0][0]},${piece[0][1]}`}
              className="feed-arc__line"
              d={piecePath(piece)}
              pathLength={1}
              strokeWidth={LINE_WIDTH * unitScale}
              // An arc across the world edge is several pieces: only the last one ends at the destination.
              markerEnd={pieceIndex === arc.length - 1 ? `url(#${ARROW_MARKER_ID})` : undefined}
            />
          ))}
          {cities.map((city) => (
            <circle key={city.cityId} className="feed-arc__dot" cx={city.x} cy={city.y} r={DOT_RADIUS * unitScale} />
          ))}
          {labels.map((label) => (
            <text
              key={label.cityId}
              className="feed-arc__label"
              x={label.x}
              y={label.y}
              textAnchor={label.anchor}
              fontSize={LABEL_FONT_SIZE * unitScale}
              strokeWidth={LABEL_HALO_WIDTH * unitScale}
              dominantBaseline="central"
            >
              {label.label}
            </text>
          ))}
        </g>
      );
    },
    [activeJourney, arc, nameOf, unknownLabel],
  );

  const scene = useMemo<JourneysMapScene | null>(
    () =>
      isEnabled
        ? {
            tabId: "feed",
            countries: NO_COUNTRIES,
            tone: MAP_TONE,
            fitBounds,
            occluderRef,
            shouldFadeUnderOccluder: false,
            isFitAnimated: true,
            isInteractive: false,
            isLandMuted: true,
            isDecorative: true,
            overlay,
          }
        : null,
    [isEnabled, fitBounds, occluderRef, overlay],
  );
  usePublishMapScene(scene);
}
