/*
 * City pool for the route sets (`routes.ts`). Cities are grouped by continent: a set takes
 * exactly 2 per continent, so the grouping is a working selection tool, not decoration.
 *
 * A city's continent is not a reference tag but part of the drawing rule: an arc never joins two
 * cities of the same continent. Honolulu, Papeete and Apia are Oceania (Polynesia) by geography;
 * they hold the middle of the Pacific, otherwise that face of the planet is empty.
 *
 * No names here: the label in the UI language comes from translations by `id`
 * (`common:globe.cities.<id>`); `id` equals the key in `CITIES`.
 */

export type Continent =
  | "africa"
  | "asia"
  | "europe"
  | "northAmerica"
  | "oceania"
  | "southAmerica";

/**
 * Minimal contract of a globe point: coordinates and, if known, a name. This is exactly what
 * `GlobeCanvas` reads for labels (`htmlElementsData`). The user's real cities (from journeys)
 * and translated curated `City` values are converted to it before drawing.
 */
export interface GlobeCity {
  /** Absent while the city name loads: the point is drawn without a label. */
  readonly name?: string;
  readonly lat: number;
  readonly lng: number;
}

export interface City {
  readonly id: string;
  readonly lat: number;
  readonly lng: number;
  readonly continent: Continent;
}

export const CITIES = {
  // --- North America ---
  newYork: { id: "newYork", lat: 40.7128, lng: -74.006, continent: "northAmerica" },
  vancouver: { id: "vancouver", lat: 49.2827, lng: -123.1207, continent: "northAmerica" },
  sanFrancisco: { id: "sanFrancisco", lat: 37.7749, lng: -122.4194, continent: "northAmerica" },
  mexicoCity: { id: "mexicoCity", lat: 19.4326, lng: -99.1332, continent: "northAmerica" },
  chicago: { id: "chicago", lat: 41.8781, lng: -87.6298, continent: "northAmerica" },
  havana: { id: "havana", lat: 23.1136, lng: -82.3666, continent: "northAmerica" },
  montreal: { id: "montreal", lat: 45.5019, lng: -73.5674, continent: "northAmerica" },
  losAngeles: { id: "losAngeles", lat: 34.0522, lng: -118.2437, continent: "northAmerica" },
  anchorage: { id: "anchorage", lat: 61.2181, lng: -149.9003, continent: "northAmerica" },
  miami: { id: "miami", lat: 25.7617, lng: -80.1918, continent: "northAmerica" },

  // --- South America ---
  cusco: { id: "cusco", lat: -13.532, lng: -71.9675, continent: "southAmerica" },
  rio: { id: "rio", lat: -22.9068, lng: -43.1729, continent: "southAmerica" },
  buenosAires: { id: "buenosAires", lat: -34.6037, lng: -58.3816, continent: "southAmerica" },
  bogota: { id: "bogota", lat: 4.711, lng: -74.0721, continent: "southAmerica" },
  quito: { id: "quito", lat: -0.1807, lng: -78.4678, continent: "southAmerica" },
  santiago: { id: "santiago", lat: -33.4489, lng: -70.6693, continent: "southAmerica" },
  saoPaulo: { id: "saoPaulo", lat: -23.5505, lng: -46.6333, continent: "southAmerica" },
  ushuaia: { id: "ushuaia", lat: -54.8019, lng: -68.303, continent: "southAmerica" },
  lima: { id: "lima", lat: -12.0464, lng: -77.0428, continent: "southAmerica" },

  // --- Europe ---
  reykjavik: { id: "reykjavik", lat: 64.1466, lng: -21.9426, continent: "europe" },
  istanbul: { id: "istanbul", lat: 41.0082, lng: 28.9784, continent: "europe" },
  lisbon: { id: "lisbon", lat: 38.7223, lng: -9.1393, continent: "europe" },
  stockholm: { id: "stockholm", lat: 59.3293, lng: 18.0686, continent: "europe" },
  dublin: { id: "dublin", lat: 53.3498, lng: -6.2603, continent: "europe" },
  rome: { id: "rome", lat: 41.9028, lng: 12.4964, continent: "europe" },
  edinburgh: { id: "edinburgh", lat: 55.9533, lng: -3.1883, continent: "europe" },
  athens: { id: "athens", lat: 37.9838, lng: 23.7275, continent: "europe" },
  helsinki: { id: "helsinki", lat: 60.1699, lng: 24.9384, continent: "europe" },
  barcelona: { id: "barcelona", lat: 41.3874, lng: 2.1686, continent: "europe" },

  // --- Africa ---
  marrakesh: { id: "marrakesh", lat: 31.6295, lng: -7.9811, continent: "africa" },
  capeTown: { id: "capeTown", lat: -33.9249, lng: 18.4241, continent: "africa" },
  cairo: { id: "cairo", lat: 30.0444, lng: 31.2357, continent: "africa" },
  nairobi: { id: "nairobi", lat: -1.2921, lng: 36.8219, continent: "africa" },
  dakar: { id: "dakar", lat: 14.7167, lng: -17.4677, continent: "africa" },
  zanzibar: { id: "zanzibar", lat: -6.1659, lng: 39.2026, continent: "africa" },
  lagos: { id: "lagos", lat: 6.5244, lng: 3.3792, continent: "africa" },
  antananarivo: { id: "antananarivo", lat: -18.8792, lng: 47.5079, continent: "africa" },
  tunis: { id: "tunis", lat: 36.8065, lng: 10.1815, continent: "africa" },
  maputo: { id: "maputo", lat: -25.9692, lng: 32.5732, continent: "africa" },

  // --- Asia ---
  delhi: { id: "delhi", lat: 28.6139, lng: 77.209, continent: "asia" },
  tokyo: { id: "tokyo", lat: 35.6762, lng: 139.6503, continent: "asia" },
  shanghai: { id: "shanghai", lat: 31.2304, lng: 121.4737, continent: "asia" },
  dubai: { id: "dubai", lat: 25.2048, lng: 55.2708, continent: "asia" },
  kathmandu: { id: "kathmandu", lat: 27.7172, lng: 85.324, continent: "asia" },
  singapore: { id: "singapore", lat: 1.3521, lng: 103.8198, continent: "asia" },
  seoul: { id: "seoul", lat: 37.5665, lng: 126.978, continent: "asia" },
  samarkand: { id: "samarkand", lat: 39.627, lng: 66.975, continent: "asia" },
  bangkok: { id: "bangkok", lat: 13.7563, lng: 100.5018, continent: "asia" },
  vladivostok: { id: "vladivostok", lat: 43.1332, lng: 131.9113, continent: "asia" },

  // --- Oceania ---
  sydney: { id: "sydney", lat: -33.8688, lng: 151.2093, continent: "oceania" },
  honolulu: { id: "honolulu", lat: 21.3069, lng: -157.8583, continent: "oceania" },
  auckland: { id: "auckland", lat: -36.8485, lng: 174.7633, continent: "oceania" },
  papeete: { id: "papeete", lat: -17.5516, lng: -149.5585, continent: "oceania" },
  perth: { id: "perth", lat: -31.9523, lng: 115.8613, continent: "oceania" },
  suva: { id: "suva", lat: -18.1416, lng: 178.4419, continent: "oceania" },
  wellington: { id: "wellington", lat: -41.2866, lng: 174.7756, continent: "oceania" },
  brisbane: { id: "brisbane", lat: -27.4698, lng: 153.0251, continent: "oceania" },
  apia: { id: "apia", lat: -13.8333, lng: -171.7667, continent: "oceania" },
} satisfies Record<string, City>;
