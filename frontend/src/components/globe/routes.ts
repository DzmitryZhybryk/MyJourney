/*
 * Canonical globe data: curated city sets and the routes between them. Arcs are drawn between
 * `from`/`to`; ONLY the end cities are labelled (`ROUTE_CITIES`).
 *
 * Drawing rule: 2 cities per continent, and an arc NEVER joins two cities of the same continent.
 * So every flight is intercontinental, arcs overlap, and the picture reads as lively chaos
 * rather than a tidy walk around the perimeter.
 *
 * The backbone is OPEN chains, not closed rings: a trip has a start and an end. Closing them
 * would give every city degree 2, and a graph with degree 2 everywhere is always a cycle, which
 * reads as a ring walk.
 *
 * The continent invariant holds BY CONSTRUCTION: each chain takes exactly one city per continent,
 * so neighbours are always on different continents. Hand-written BRIDGES between chains add
 * hub cities (degree 3) and stitch the two strands so the eye no longer splits the picture into
 * two threads. City degree ranges from 1 (chain end) to 3.
 *
 * A set is picked at random ONCE per module load, so it is stable across navigation (the
 * persistent globe lives between routes) and changes only on page refresh. The same set never
 * comes up twice in a row.
 */

import { CITIES, type City } from "./cities";

export type { City, GlobeCity } from "./cities";

export interface RouteArc {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  /** Initial phase of the running dash, [0,1). Shared by a synchronized group of arcs. */
  dashInitialGap: number;
}

interface Route {
  readonly from: City;
  readonly to: City;
}

export interface RouteSet {
  /** Backbone: chains with one city per continent. The order is the picture. */
  readonly chains: readonly (readonly City[])[];
  /**
   * Hand-written arcs over the backbone. The construction guarantee does NOT cover them, so each
   * pair's continents are written in a comment and checked by eye. All go BETWEEN chains: a bridge
   * inside one chain would close neighbours into a triangle.
   */
  readonly bridges: readonly Route[];
}

/*
 * Sets are hand-picked by the same rules. When ordering a chain keep arcs under ~110° of central
 * angle: longer arcs balloon in height and leave the sphere. Do not add a third arc into a city
 * if two others already converge nearby: such a bundle reads as a blot.
 */
export const ROUTE_SETS: readonly RouteSet[] = [
  {
    chains: [
      [CITIES.reykjavik, CITIES.newYork, CITIES.cusco, CITIES.capeTown, CITIES.delhi, CITIES.sydney],
      [CITIES.tokyo, CITIES.honolulu, CITIES.vancouver, CITIES.rio, CITIES.marrakesh, CITIES.istanbul],
    ],
    bridges: [
      { from: CITIES.tokyo, to: CITIES.sydney }, // Asia -> Oceania, western Pacific
      { from: CITIES.newYork, to: CITIES.marrakesh }, // N. America -> Africa, across the Atlantic
      { from: CITIES.istanbul, to: CITIES.delhi }, // Europe -> Asia
    ],
  },
  {
    chains: [
      [CITIES.stockholm, CITIES.cairo, CITIES.shanghai, CITIES.auckland, CITIES.buenosAires, CITIES.mexicoCity],
      [CITIES.sanFrancisco, CITIES.papeete, CITIES.bogota, CITIES.lisbon, CITIES.nairobi, CITIES.dubai],
    ],
    bridges: [
      { from: CITIES.dubai, to: CITIES.cairo }, // Asia -> Africa
      { from: CITIES.mexicoCity, to: CITIES.lisbon }, // N. America -> Europe, across the Atlantic
      { from: CITIES.shanghai, to: CITIES.sanFrancisco }, // Asia -> N. America, northern Pacific
    ],
  },
  {
    chains: [
      [CITIES.perth, CITIES.kathmandu, CITIES.dublin, CITIES.dakar, CITIES.quito, CITIES.chicago],
      [CITIES.rome, CITIES.zanzibar, CITIES.singapore, CITIES.suva, CITIES.santiago, CITIES.havana],
    ],
    bridges: [
      { from: CITIES.rome, to: CITIES.chicago }, // Europe -> N. America
      { from: CITIES.singapore, to: CITIES.perth }, // Asia -> Oceania
      { from: CITIES.havana, to: CITIES.dakar }, // N. America -> Africa, across the Atlantic
    ],
  },
  {
    chains: [
      [CITIES.edinburgh, CITIES.lagos, CITIES.saoPaulo, CITIES.montreal, CITIES.honolulu, CITIES.seoul],
      [CITIES.samarkand, CITIES.athens, CITIES.antananarivo, CITIES.wellington, CITIES.ushuaia, CITIES.losAngeles],
    ],
    bridges: [
      { from: CITIES.seoul, to: CITIES.losAngeles }, // Asia -> N. America, northern Pacific
      { from: CITIES.athens, to: CITIES.lagos }, // Europe -> Africa
      { from: CITIES.saoPaulo, to: CITIES.antananarivo }, // S. America -> Africa, southern Atlantic
    ],
  },
  {
    chains: [
      [CITIES.helsinki, CITIES.tunis, CITIES.bangkok, CITIES.brisbane, CITIES.lima, CITIES.anchorage],
      [CITIES.vladivostok, CITIES.apia, CITIES.miami, CITIES.rio, CITIES.maputo, CITIES.barcelona],
    ],
    bridges: [
      { from: CITIES.barcelona, to: CITIES.bangkok }, // Europe -> Asia
      { from: CITIES.anchorage, to: CITIES.vladivostok }, // N. America -> Asia, northern Pacific
      { from: CITIES.helsinki, to: CITIES.miami }, // Europe -> N. America, across the Atlantic
    ],
  },
];

/** Arcs of a set: chains (city i -> city i+1, not closed) plus bridges. */
export function routesOf(routeSet: RouteSet): readonly Route[] {
  return [
    ...routeSet.chains.flatMap((chain) =>
      chain.slice(0, -1).map((from, index) => ({ from, to: chain[index + 1] })),
    ),
    ...routeSet.bridges,
  ];
}

/*
 * The running-dash phase belongs not to an arc but to a GROUP of synchronized arcs. Arcs sharing
 * a departure city (leave together) and arcs sharing an arrival city (arrive together) join one
 * group: equal phases make the dash move identically along the normalized length, so the same
 * equality gives both a synchronized departure and a synchronized arrival.
 *
 * Equality is transitive, so groups are equivalence classes computed by union-find, not a manual
 * list: an arc like `NY->Marrakesh` joins departures from New York with arrivals in Marrakesh into
 * one class. Add an arc and the groups rebuild themselves. Phases are spread evenly between
 * groups, otherwise the globe would pulse in unison.
 */
function synchronizedPhases(routes: readonly Route[]): number[] {
  const parent = routes.map((_, index) => index);

  const find = (index: number): number => {
    let root = index;
    while (parent[root] !== root) {
      root = parent[root];
    }

    return root;
  };

  const union = (a: number, b: number): void => {
    parent[find(b)] = find(a);
  };

  const firstDepartureFrom = new Map<City, number>();
  const firstArrivalTo = new Map<City, number>();
  routes.forEach((route, index) => {
    const sameDeparture = firstDepartureFrom.get(route.from);
    if (sameDeparture === undefined) {
      firstDepartureFrom.set(route.from, index);
    } else {
      union(sameDeparture, index);
    }

    const sameArrival = firstArrivalTo.get(route.to);
    if (sameArrival === undefined) {
      firstArrivalTo.set(route.to, index);
    } else {
      union(sameArrival, index);
    }
  });

  const groups = routes.map((_, index) => find(index));
  const distinct = Array.from(new Set(groups));

  return groups.map((group) => distinct.indexOf(group) / distinct.length);
}

const LAST_SET_STORAGE_KEY = "myjourney.globe.route-set";

function readLastPickedIndex(): number | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.sessionStorage.getItem(LAST_SET_STORAGE_KEY);
    return raw === null ? null : Number.parseInt(raw, 10);
  } catch {
    // Safari private mode blocks storage access: just do not remember the previous set.
    return null;
  }
}

function rememberPickedIndex(index: number): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.setItem(LAST_SET_STORAGE_KEY, String(index));
  } catch {
    // Write unavailable: the only consequence is that a set may repeat back to back.
    return;
  }
}

/**
 * A random set different from the one shown on the previous load. The previous index lives in
 * sessionStorage, which lasts as long as the tab: "refresh the page, see a different world".
 */
function pickRouteSet(): RouteSet {
  const previous = readLastPickedIndex();
  const allIndexes = ROUTE_SETS.map((_, index) => index);
  const candidates = allIndexes.filter((index) => index !== previous);
  const pool = candidates.length > 0 ? candidates : allIndexes;
  const picked = pool[Math.floor(Math.random() * pool.length)];

  rememberPickedIndex(picked);
  return ROUTE_SETS[picked];
}

const ROUTES: readonly Route[] = routesOf(pickRouteSet());
const DASH_PHASES: readonly number[] = synchronizedPhases(ROUTES);

/** Arcs for globe.gl `arcsData`. */
export const ROUTE_ARCS: readonly RouteArc[] = ROUTES.map((route, index) => ({
  startLat: route.from.lat,
  startLng: route.from.lng,
  endLat: route.to.lat,
  endLng: route.to.lng,
  dashInitialGap: DASH_PHASES[index],
}));

/** Unique route end cities; these are labelled on the globe. */
export const ROUTE_CITIES: readonly City[] = Array.from(
  new Map(
    ROUTES.flatMap((route) => [
      [route.from.id, route.from],
      [route.to.id, route.to],
    ]),
  ).values(),
);
