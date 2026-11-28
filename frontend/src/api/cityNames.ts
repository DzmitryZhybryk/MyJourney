import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { toApiLanguage } from "../i18n/apiLanguage";
import { resolveCities, type LanguageEnum } from "./sdk";

// The backend accepts at most 1000 ids per request, so larger lists are split into chunks.
const RESOLVE_CHUNK_SIZE = 1000;

/**
 * City name to display:
 * - string: the name in the UI language;
 * - `null`: geo answered but does not know the city (show an "unknown city" label);
 * - `undefined`: still loading (or the request failed), show nothing.
 */
export type CityName = string | null | undefined;

export type CityNameLookup = (cityId: string) => CityName;

/**
 * Label for a city. A city geo does not know gets `unknownLabel` (otherwise it would vanish
 * from the map silently); while names load there is no label.
 */
export function cityLabel(name: CityName, unknownLabel: string): string | undefined {
  return name === null ? unknownLabel : name;
}

interface ResolvedNames {
  requested: ReadonlySet<string>;
  names: ReadonlyMap<string, string>;
}

const NOTHING_LOADED: CityNameLookup = () => undefined;

async function fetchCityNames(cityIds: readonly string[], language: LanguageEnum, signal: AbortSignal): Promise<ResolvedNames> {
  const chunks: string[][] = [];
  for (let start = 0; start < cityIds.length; start += RESOLVE_CHUNK_SIZE) {
    chunks.push(cityIds.slice(start, start + RESOLVE_CHUNK_SIZE));
  }

  const responses = await Promise.all(
    chunks.map((chunk) => resolveCities({ body: { cityIds: chunk, language }, signal, throwOnError: true })),
  );
  const names = new Map<string, string>();
  for (const response of responses) {
    for (const item of response.items) {
      names.set(item.cityId, item.name);
    }
  }

  return { requested: new Set(cityIds), names };
}

/**
 * City names in the UI language, for the map and globe, where journeys store only city ids.
 *
 * Id order and duplicates do not matter: the list is normalized, so the map and globe share one
 * request and one cache. Names never change, so the cache is permanent, and previous names stay
 * on screen while names for a newly added journey load.
 *
 * Returns an `id -> name` lookup (see `CityName`).
 */
export function useCityNames(cityIds: Iterable<string>): CityNameLookup {
  const { i18n } = useTranslation();
  const language = toApiLanguage(i18n.language);

  const idsKey = [...new Set(cityIds)].sort().join(",");
  const normalizedIds = useMemo(() => (idsKey ? idsKey.split(",") : []), [idsKey]);

  const { data } = useQuery({
    queryKey: ["cityNames", language, normalizedIds],
    queryFn: ({ signal }) => fetchCityNames(normalizedIds, language, signal),
    enabled: normalizedIds.length > 0,
    staleTime: Infinity,
    placeholderData: keepPreviousData,
  });

  return useMemo<CityNameLookup>(() => {
    if (!data) {
      return NOTHING_LOADED;
    }

    // keepPreviousData may hold results that never asked about a new id: its name is still
    // loading, not "unknown".
    return (cityId) => data.names.get(cityId) ?? (data.requested.has(cityId) ? null : undefined);
  }, [data]);
}
