import { Text } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useParams } from "react-router";

import { useCityNames } from "../../../api/cityNames";
import { getJourneyYearsOptions, zTransportTypeEnum, type JourneyFeedEntry, type TransportTypeEnum } from "../../../api/sdk";
import { YearRangeSlider } from "../movements/YearRangeSlider";
import { JourneyCard } from "./JourneyCard";
import { ALL_JOURNEYS_PATH } from "./journeyCardPath";
import { JourneyFeed, type FeedStatus } from "./JourneyFeed";
import { TransportChips } from "./TransportChips";
import { useFeedMapScene } from "./useFeedMapScene";
import { useFeedReturn } from "./useFeedReturn";
import { fitYearRange, type YearRange } from "./yearRange";
import "./all-journeys.css";

const NO_JOURNEYS: readonly JourneyFeedEntry[] = [];

// Same breakpoint as the layout in all-journeys.css: narrower means a full-width column with no room for the map.
const DESKTOP_QUERY = "(min-width: 62em)";

/**
 * "All journeys" sub-tab, route /journeys/all: a feed of journeys by year with year and
 * transport filters; /journeys/all/<id> shows that journey's card in place of the column.
 *
 * The year scale runs from the user's first to last year, ignoring filters: it must not shrink
 * from its own selection. Thumbs at the scale edges mean all years, no filter. Behind the column
 * the shared map shows muted land with the active journey's arc (desktop only).
 *
 * The card takes its journey from the loaded feed (there is no request for one journey). The feed
 * stays mounted under the card, so filters, loaded pages and scroll survive. Until the journey is
 * found the feed shows its own loading or error; if the loaded feed has no such journey (a reload
 * past the first page, a stale link), the address falls back to the list. Once found, the card
 * keeps its journey even if a refetch drops it from the filtered feed.
 */
export function AllJourneysView() {
  const { t } = useTranslation("journeys");
  const { journeyId } = useParams<{ journeyId?: string }>();
  const years = useQuery({ ...getJourneyYearsOptions(), staleTime: Infinity });
  const [yearRange, setYearRange] = useState<YearRange | null>(null);
  const [transportTypes, setTransportTypes] = useState<readonly TransportTypeEnum[]>(zTransportTypeEnum.options);
  const yearList = years.data?.years ?? [];
  const firstYear = yearList.at(0);
  const lastYear = yearList.at(-1);
  const shownYearRange = useMemo(
    () => fitYearRange(yearRange, firstYear, lastYear),
    [yearRange, firstYear, lastYear],
  );
  // The slider compares the window by reference, so do not recreate "all years" every render.
  const yearWindow = useMemo<YearRange>(
    () => shownYearRange ?? [firstYear ?? 0, lastYear ?? 0],
    [shownYearRange, firstYear, lastYear],
  );
  const isDesktop = useMediaQuery(DESKTOP_QUERY, false, { getInitialValueInEffect: false });
  const hasTransport = transportTypes.length > 0;
  const columnRef = useRef<HTMLDivElement>(null);
  const feedRef = useRef<HTMLElement>(null);
  const [loadedJourneys, setLoadedJourneys] = useState<readonly JourneyFeedEntry[]>(NO_JOURNEYS);
  // "pending" until the feed reports, so the first render cannot fall back to the list.
  const [feedStatus, setFeedStatus] = useState<FeedStatus>("pending");
  const [activeJourney, setActiveJourney] = useState<JourneyFeedEntry | null>(null);

  // The card's journey: the feed's latest entry while it has one, the last known entry otherwise.
  const [cardEntry, setCardEntry] = useState<JourneyFeedEntry | null>(null);
  const feedEntry = journeyId === undefined ? null : (loadedJourneys.find((entry) => entry.journeyId === journeyId) ?? null);
  if (feedEntry !== null && feedEntry !== cardEntry) {
    setCardEntry(feedEntry);
  } else if (journeyId === undefined && cardEntry !== null) {
    setCardEntry(null);
  }
  const cardJourney = cardEntry !== null && cardEntry.journeyId === journeyId ? cardEntry : null;
  const isCardMissing = journeyId !== undefined && cardJourney === null && feedStatus === "loaded";
  useFeedReturn(feedRef, cardJourney?.journeyId ?? null, isDesktop);

  // The card's journey may have left the filtered feed; the map still needs its cities.
  const mapJourneys = useMemo(
    () => (cardJourney === null || loadedJourneys.includes(cardJourney) ? loadedJourneys : [...loadedJourneys, cardJourney]),
    [cardJourney, loadedJourneys],
  );
  // The same city set as the feed and the map, so the card shares their names request.
  const nameOf = useCityNames(mapJourneys.flatMap((journey) => [journey.origin.cityId, journey.destination.cityId]));
  // Narrow screens have no map: the column is full width.
  useFeedMapScene({
    journeys: hasTransport ? mapJourneys : NO_JOURNEYS,
    activeJourney: cardJourney ?? (hasTransport ? activeJourney : null),
    occluderRef: columnRef,
    isEnabled: isDesktop,
  });

  return (
    <div className="all-journeys">
      {/* Beside the feed, not instead of it: the list address is the same route, so the feed stays
          mounted and its requests in flight are not dropped. */}
      {isCardMissing && <Navigate to={ALL_JOURNEYS_PATH} replace />}
      <div ref={columnRef} className="all-journeys__column">
        {cardJourney !== null && <JourneyCard key={cardJourney.journeyId} journey={cardJourney} nameOf={nameOf} />}
        <section
          className="all-journeys__filters journeys-card"
          aria-label={t("all.filters")}
          hidden={journeyId !== undefined}
        >
          <h1 className="all-journeys__title">{t("nav.all")}</h1>
          {/* A single year leaves nothing to choose, so no scale. */}
          {firstYear !== undefined && lastYear !== undefined && firstYear < lastYear && (
            <fieldset className="all-journeys__years">
              <legend className="all-journeys__filter-label">{t("all.years")}</legend>
              <YearRangeSlider
                firstYear={firstYear}
                lastYear={lastYear}
                window={yearWindow}
                onWindowChange={([from, to]) => setYearRange(from === firstYear && to === lastYear ? null : [from, to])}
                fromLabel={t("movements.yearFrom")}
                toLabel={t("movements.yearTo")}
              />
            </fieldset>
          )}
          <TransportChips transportTypes={transportTypes} onTransportTypesChange={setTransportTypes} />
        </section>

        <section
          ref={feedRef}
          className="all-journeys__feed journeys-card"
          aria-label={t("all.feed")}
          tabIndex={-1}
          hidden={cardJourney !== null}
        >
          {hasTransport ? (
            <JourneyFeed
              yearRange={shownYearRange}
              transportTypes={transportTypes}
              hasJourneys={yearList.length > 0}
              isHidden={cardJourney !== null}
              onJourneysChange={setLoadedJourneys}
              onStatusChange={setFeedStatus}
              onActiveJourneyChange={setActiveJourney}
            />
          ) : (
            <output className="all-journeys__status">
              <Text size="sm" c="var(--text-muted)">
                {t("movements.noTransport")}
              </Text>
            </output>
          )}
        </section>
      </div>
    </div>
  );
}
