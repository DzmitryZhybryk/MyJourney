/*
 * Adapter from the user's cities to app-global globe points.
 *
 * The public (anonymous) zone feeds the globe curated `ROUTE_CITIES`; the authorized one feeds
 * real visited cities from journeys. TanStack Query owns the cache, request dedup and reset on
 * logout (`getJourneysGlobeOptions` + cache clearing in `AuthProvider`); only the pure
 * transformation stays here.
 */
import type { JourneysGlobeResponse } from "../../api/sdk";

/** A visited city without a name: the globe requests names from geo separately. */
export interface UserCityPoint {
  readonly id: string;
  readonly lat: number;
  readonly lng: number;
}

/**
 * Converts cities from the globe response into city points (id and coordinates). The backend
 * returns each city once.
 *
 * Query uses the function reference as the memoization key of `select`, so it is module-level:
 * an inline arrow would return a new array every render, and `react-globe.gl` compares
 * `htmlElementsData` by identity and would rebuild the whole label layer.
 */
export function citiesFromJourneysGlobe(response: JourneysGlobeResponse): readonly UserCityPoint[] {
  return response.cities.map((city) => ({ id: city.cityId, lat: city.latitude, lng: city.longitude }));
}
