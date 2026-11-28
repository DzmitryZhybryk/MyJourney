/*
 * Builds country borders for flat maps: data/world-countries.geo.json (the source, not in the
 * bundle) -> src/data/world-countries.topo.json (what WorldMap imports). The result is committed;
 * CI rebuilds it and fails if it diverges from the source.
 *
 * TopoJSON stores a shared border of neighbours once, and coordinates as integer grid steps with
 * deltas instead of six-digit fractions. Outlines are not simplified; quantization only merges
 * neighbouring points that fall into one grid step, so a ring loses a point or two and a point
 * shifts by no more than half a step.
 *
 * Run: make generate-world
 */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { topology } from "topojson-server";

const SOURCE = fileURLToPath(new URL("../data/world-countries.geo.json", import.meta.url));
const TARGET = fileURLToPath(new URL("../src/data/world-countries.topo.json", import.meta.url));

// The key under which countries sit in the topology's `objects`; WorldMap reads the same one.
const COUNTRIES_OBJECT = "countries";

/*
 * Number of grid steps per axis. The map canvas is 1000 units per 360° of longitude; at maximum zoom
 * (8x) on a 1920 px screen a canvas unit is about 15 px. A grid of 1e5 steps is 0.0036°, about
 * 0.15 px even up close; 1e4 would give about 1.5 px and outlines would turn into stairs at 8x.
 */
const QUANTIZATION = 100_000;

const source = JSON.parse(readFileSync(SOURCE, "utf8")) as FeatureCollection<Polygon | MultiPolygon>;
const world = topology({ [COUNTRIES_OBJECT]: source }, QUANTIZATION);
writeFileSync(TARGET, `${JSON.stringify(world)}\n`);
