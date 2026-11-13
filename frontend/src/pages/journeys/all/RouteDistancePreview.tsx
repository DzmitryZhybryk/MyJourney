import { useQuery } from "@tanstack/react-query";

import { estimateJourneyDistanceOptions, type CitySearchItem, type JourneyFeedEntry } from "../../../api/sdk";

interface RouteDistancePreviewProps {
  /** The journey as the feed has it: its pair needs no request, its distance is already known. */
  journey: JourneyFeedEntry;
  origin: CitySearchItem | null;
  destination: CitySearchItem | null;
  distanceFormat: Intl.NumberFormat;
}

/**
 * Distance value of the journey card's pair; the card labels it.
 *
 * The pair of the feed's journey shows its distance without a request; another pair asks the
 * backend for an estimate. An incomplete or invalid pair, or a failed request, shows a dash; while a
 * new pair is being calculated the dash is dimmed and `aria-busy`. No previous number is kept:
 * editing a city field already clears the pick (`CityAutocomplete` emits `null` on typing), so
 * every new pair starts from the dash anyway.
 */
export function RouteDistancePreview({ journey, origin, destination, distanceFormat }: RouteDistancePreviewProps) {
  const isSavedPair = origin?.cityId === journey.origin.cityId && destination?.cityId === journey.destination.cityId;
  const isPairValid = Boolean(origin && destination && origin.cityId !== destination.cityId);
  const distanceQuery = useQuery({
    ...estimateJourneyDistanceOptions({
      query: { originCityId: origin?.cityId ?? "", destinationCityId: destination?.cityId ?? "" },
    }),
    enabled: isPairValid && !isSavedPair,
    // The distance of a pair never changes.
    staleTime: Infinity,
  });

  // `undefined` = the new pair is still being calculated; `null` = nothing to show.
  let settledKm: number | null | undefined;
  if (isSavedPair) {
    settledKm = journey.distanceKm;
  } else if (!isPairValid || distanceQuery.isError) {
    settledKm = null;
  } else {
    settledKm = distanceQuery.data?.distanceKm;
  }

  const isRecalculating = settledKm === undefined;
  const shownKm = settledKm ?? null;

  return (
    <span
      className={
        isRecalculating ? "journey-card__distance journey-card__distance--recalculating" : "journey-card__distance"
      }
      aria-live="polite"
      aria-busy={isRecalculating}
    >
      {shownKm === null ? "—" : distanceFormat.format(shownKm)}
    </span>
  );
}
