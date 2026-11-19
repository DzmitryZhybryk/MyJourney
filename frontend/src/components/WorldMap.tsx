import {
  useCallback,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { useTranslation } from "react-i18next";
import type { Feature, MultiPolygon, Polygon, Position } from "geojson";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";

import worldTopology from "../data/world-countries.topo.json";
import { fitView } from "./fitView";
import { prefersReducedMotion } from "./reducedMotion";
import { useMapZoom } from "./useMapZoom";
import { useViewTransition, type ViewFlight } from "./useViewTransition";
import {
  ANTIMERIDIAN_JUMP,
  WORLD_VIEW_BOX,
  isSameView,
  isWorldView,
  projectToScreen,
  type ViewBox,
} from "./worldProjection";
import "./world-map.css";

/*
 * Flat world map in plain SVG, no external libraries. Country = <path>, fill depends on status
 * (visited / wishlist / not visited), cities are small dots at their coordinates. The hovered
 * country darkens and a tooltip shows its name and, for visited ones, cities with visit years.
 * The map is zoomed and panned by gestures (see useMapZoom); a custom overlay layer can be drawn
 * over the countries in canvas coordinates.
 */

// --- Parsing geo data into SVG paths (once, at module import) ------------
type CountryGeometry = Polygon | MultiPolygon;

interface CountryProperties {
  name: string;
}

type CountryFeature = Feature<CountryGeometry, CountryProperties> & { id: string };

type WorldTopology = Topology<{ countries: GeometryCollection<CountryProperties> }>;

function ringToPath(ring: readonly Position[]): string {
  const segments: string[] = [];
  let prevLng: number | null = null;
  for (const [lng, lat] of ring) {
    const [x, y] = projectToScreen(lng, lat);
    const command =
      prevLng === null || Math.abs(lng - prevLng) > ANTIMERIDIAN_JUMP ? "M" : "L";
    segments.push(`${command}${x.toFixed(1)} ${y.toFixed(1)}`);
    prevLng = lng;
  }

  return segments.length > 0 ? `${segments.join("")}Z` : "";
}

function geometryToPath(geometry: CountryGeometry): string {
  if (geometry.type === "Polygon") {
    return geometry.coordinates.map(ringToPath).join("");
  }

  return geometry.coordinates.flatMap((polygon) => polygon.map(ringToPath)).join("");
}

interface CountryShape {
  id: string;
  name: string;
  path: string;
}

// scripts/build-world-topology.ts builds the topology from country polygons that each have a
// string id and a name, so the features unpacked back are CountryFeature.
const WORLD = worldTopology as unknown as WorldTopology;
const COUNTRY_FEATURES = feature(WORLD, WORLD.objects.countries).features as readonly CountryFeature[];

const COUNTRY_SHAPES: readonly CountryShape[] = COUNTRY_FEATURES.map((country) => ({
  id: country.id,
  name: country.properties.name,
  path: geometryToPath(country.geometry),
}));

const COUNTRY_NAMES: ReadonlyMap<string, string> = new Map(
  COUNTRY_SHAPES.map((shape) => [shape.id, shape.name]),
);

// --- Component public API ---------------------------------------------
export type CountryStatus = "visited" | "wishlist";

export interface MapCity {
  /** City id in geo. */
  id: string;
  /** Name in the UI language; absent while names are loading. */
  name?: string;
  lat: number;
  lng: number;
  years: readonly number[];
}

export interface MapCountry {
  id: string;
  status: CountryStatus;
  cities: readonly MapCity[];
}

export interface WorldMapTone {
  /** Fill of a not-visited country. */
  land: string;
  /** Border colour. */
  border: string;
  /** Fill of a visited country. */
  visited: string;
  /** Fill of a wishlist country (no cities). */
  wishlist: string;
  /** City dot colour. */
  cityDot: string;
}

interface WorldMapProps {
  countries: readonly MapCountry[];
  tone: WorldMapTone;
  className?: string;
  /**
   * Layer over the countries, in canvas coordinates (see `projectToScreen`). Receives the current
   * visible area so labels and icons do not grow with the map when zoomed.
   */
  overlay?: (view: ViewBox) => ReactNode;
  /** What to show initially (canvas units); without it the map opens on the whole world. */
  fitBounds?: ViewBox | null;
  /**
   * Element over the left part of the map (a panel): the initial view fits into the uncovered
   * part and the map fades toward its edge so lines do not pop out from under it.
   */
  occluderRef?: RefObject<HTMLElement | null>;
  /**
   * `false`: the map does not fade toward the `occluderRef` edge because the element over it is
   * transparent and the map shows through. The initial view still fits the uncovered part.
   */
  shouldFadeUnderOccluder?: boolean;
  /** A `fitBounds` change eases the map to the new view instead of jumping. */
  isFitAnimated?: boolean;
  /** `false`: no hover highlight and no tooltip; zoom still works. */
  isInteractive?: boolean;
  /** Land is dimmed: the map is a background for what is drawn over it. */
  isLandMuted?: boolean;
  /** Background only: hidden from assistive technology. */
  isDecorative?: boolean;
  /**
   * What the map currently shows (a tab, a screen). A new key drops the user's zoom and moves from
   * the view on screen to the new initial view.
   */
  sceneKey?: string;
  /** `false`: a new `sceneKey` lands on the new view at once instead of flying there. */
  isSceneChangeAnimated?: boolean;
  /** The previous scene's dots and overlay, drawn fading out while the frame flies away. */
  leaving?: WorldMapLayer | null;
}

/** A scene's own layer over the countries: city dots and the overlay. */
export interface WorldMapLayer {
  key: string;
  countries: readonly MapCountry[];
  overlay?: (view: ViewBox) => ReactNode;
}

interface CityDot {
  key: string;
  cx: number;
  cy: number;
}

function projectCityDots(countries: readonly MapCountry[]): readonly CityDot[] {
  return countries.flatMap((country) =>
    country.cities.map((city) => {
      const [cx, cy] = projectToScreen(city.lng, city.lat);
      return { key: city.id, cx, cy };
    }),
  );
}

// City dot radius in canvas units at the whole-world view; proportionally smaller when zoomed.
const CITY_DOT_RADIUS = 1.8;

// Tooltip offset from the cursor, and fallback sizes (before the first ref measurement).
const TOOLTIP_OFFSET = 14;
const TOOLTIP_FALLBACK_WIDTH = 160;
const TOOLTIP_FALLBACK_HEIGHT = 80;

export function WorldMap({
  countries,
  tone,
  className,
  overlay,
  fitBounds = null,
  occluderRef,
  shouldFadeUnderOccluder = true,
  isFitAnimated = false,
  isInteractive = true,
  isLandMuted = false,
  isDecorative = false,
  sceneKey,
  isSceneChangeAnimated = true,
  leaving = null,
}: WorldMapProps) {
  const { t, i18n } = useTranslation("common");
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // How many pixels the panel covers on the left and the initial view both depend on the map
  // area size, so recompute before paint and on every resize.
  const [initialView, setInitialView] = useState<ViewBox>(WORLD_VIEW_BOX);
  const [occludedLeft, setOccludedLeft] = useState(0);
  useLayoutEffect(() => {
    // Measured on the wrap, the canvas's same-size parent: the banner-close glide scales the canvas,
    // and its transformed rect would shift the panel edge for good (a transform fires no resize).
    const wrap = wrapRef.current;
    if ((!fitBounds && !occluderRef) || !wrap) {
      setInitialView(WORLD_VIEW_BOX);
      setOccludedLeft(0);
      return;
    }

    const measure = () => {
      const canvasRect = wrap.getBoundingClientRect();
      const occluderRect = occluderRef?.current?.getBoundingClientRect();
      // The panel covers the map only if it lies over it; on mobile width it sits above the map.
      const isOverlapping =
        occluderRect !== undefined &&
        occluderRect.left < canvasRect.right &&
        occluderRect.right > canvasRect.left &&
        occluderRect.top < canvasRect.bottom &&
        occluderRect.bottom > canvasRect.top;
      const occluded = isOverlapping ? occluderRect.right - canvasRect.left : 0;
      setOccludedLeft(occluded);
      const next = fitBounds ? fitView(fitBounds, canvasRect, occluded) : WORLD_VIEW_BOX;
      // Resize ticks recompute an equal view as a new object; keeping the old one does not restart
      // a running transition.
      setInitialView((current) => (isSameView(current, next) ? current : next));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(wrap);
    return () => observer.disconnect();
  }, [fitBounds, occluderRef]);

  // A scene change starts from the view on screen, the user's zoom included, so it is captured
  // after `useMapZoom` below; the flight then drives the fitted view and resets the zoom.
  const [sceneFlight, setSceneFlight] = useState<ViewFlight | null>(null);
  const fittedView = useViewTransition(initialView, isFitAnimated, sceneFlight);
  const view = useMapZoom(canvasRef, svgRef, fittedView, sceneFlight);
  const [trackedSceneKey, setTrackedSceneKey] = useState(sceneKey);
  if (sceneKey !== trackedSceneKey) {
    setTrackedSceneKey(sceneKey);
    setSceneFlight({ from: view, isAnimated: isSceneChangeAnimated });
  }
  const isFadedUnderOccluder = shouldFadeUnderOccluder && occludedLeft > 0;
  const isZoomed = !isWorldView(view);
  // Cache the container geometry on cursor enter instead of calling getBoundingClientRect
  // (forces reflow) on every mouse move.
  const rectRef = useRef<DOMRect | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  // Leave handlers are off while not interactive, so a tooltip shown before must be dropped here.
  if (!isInteractive && hoveredId !== null) {
    setHoveredId(null);
  }
  const [pointer, setPointer] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [flip, setFlip] = useState<{ x: boolean; y: boolean }>({ x: false, y: false });

  const byId = useMemo(
    () => new Map(countries.map((country) => [country.id, country])),
    [countries],
  );

  // Resolve the country name from the ISO code via CLDR in the active language; territories
  // without a code (id = name) and unknown codes fall back to the name in the border data.
  const countryNames = useMemo(
    () => new Intl.DisplayNames([i18n.language], { type: "region", fallback: "none" }),
    [i18n.language],
  );
  const resolveCountryName = useCallback(
    (id: string): string => {
      if (/^[A-Z]{2}$/u.test(id)) {
        const localized = countryNames.of(id);
        if (localized && localized !== id) return localized;
      }

      return COUNTRY_NAMES.get(id) ?? id;
    },
    [countryNames],
  );

  const cacheRect = useCallback(() => {
    rectRef.current = wrapRef.current?.getBoundingClientRect() ?? null;
  }, []);

  const handleMouseMove = useCallback((event: MouseEvent<HTMLDivElement>) => {
    // Geometry is normally cached on onMouseEnter, but that does not fire if the cursor was
    // already over the map when it appeared (client navigation after adding a journey). Measure
    // lazily here, otherwise rect=null, an early return, and the tooltip sticks to the top-left
    // corner (pointer stays {0,0}).
    const rect = rectRef.current ?? wrapRef.current?.getBoundingClientRect() ?? null;
    // Defensive guard: getBoundingClientRect on a mounted node always returns a rect.
    /* v8 ignore next 3 */
    if (!rect) {
      return;
    }

    rectRef.current = rect;
    setPointer({ x: event.clientX - rect.left, y: event.clientY - rect.top });
    // Flip near the screen edge: if the tooltip does not fit right/below, draw it left/above the
    // cursor. Measure against the viewport (clientX/Y) to stay on screen; sizes come from the
    // previous frame (they change only when the country changes).
    const tooltip = tooltipRef.current;
    const width = tooltip?.offsetWidth ?? TOOLTIP_FALLBACK_WIDTH;
    const height = tooltip?.offsetHeight ?? TOOLTIP_FALLBACK_HEIGHT;
    setFlip({
      x: event.clientX + TOOLTIP_OFFSET + width > window.innerWidth,
      y: event.clientY + TOOLTIP_OFFSET + height > window.innerHeight,
    });
  }, []);

  // Countries depend on neither hover/cursor position (highlight is CSS :hover) nor zoom (it only
  // changes the viewBox), so memoize: mouse moves and zoom do not redraw ~180 paths.
  const countryShapes = useMemo(
    () => (
      <g>
        {COUNTRY_SHAPES.map((country) => {
          const status = byId.get(country.id)?.status;
          const fill =
            status === "visited"
              ? tone.visited
              : status === "wishlist"
                ? tone.wishlist
                : tone.land;
          return (
            <path
              key={country.id}
              className="world-map__country"
              d={country.path}
              // A style, not the attribute: CSS transitions run on computed style changes.
              style={{ fill }}
              stroke={tone.border}
              strokeWidth={0.6}
              vectorEffect="non-scaling-stroke"
              onMouseEnter={isInteractive ? () => setHoveredId(country.id) : undefined}
              onMouseLeave={isInteractive ? () => setHoveredId(null) : undefined}
            />
          );
        })}
      </g>
    ),
    [byId, tone, isInteractive],
  );

  const cityDots = useMemo(() => projectCityDots(countries), [countries]);
  const leavingCountries = leaving?.countries;
  const leavingDots = useMemo(() => (leavingCountries ? projectCityDots(leavingCountries) : []), [leavingCountries]);
  const cityDotRadius = CITY_DOT_RADIUS * (view.width / WORLD_VIEW_BOX.width);
  const renderCityDots = (dots: readonly CityDot[]) => (
    <g className="world-map__cities">
      {dots.map((dot) => (
        <circle
          key={dot.key}
          className="world-map__city-dot"
          cx={dot.cx}
          cy={dot.cy}
          r={cityDotRadius}
          fill={tone.cityDot}
          stroke="#ffffff"
          strokeWidth={0.5}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </g>
  );
  // Only a flown scene change is staged; the first scene and a jump appear as they are.
  const isSceneArriving = sceneFlight !== null && sceneFlight.isAnimated && !prefersReducedMotion();

  const hovered = hoveredId ? byId.get(hoveredId) : undefined;
  const hoveredName = hoveredId ? resolveCountryName(hoveredId) : "";
  // Cities without a name (still loading) stay out of the tooltip until they arrive. Order: by
  // first visit year (years arrive ascending), then by name within a year.
  const hoveredCities = useMemo(
    () =>
      (hovered?.cities ?? [])
        .filter((city): city is MapCity & { name: string } => city.name !== undefined)
        .sort(
          (left, right) =>
            left.years[0] - right.years[0] || left.name.localeCompare(right.name, i18n.language),
        ),
    [hovered, i18n.language],
  );

  const wrapClassName = [
    "world-map-wrap",
    isInteractive ? null : "world-map-wrap--static",
    isZoomed ? "world-map-wrap--zoomed" : null,
    isFadedUnderOccluder ? "world-map-wrap--occluded" : null,
    isLandMuted ? "world-map-wrap--muted" : null,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      ref={wrapRef}
      className={wrapClassName}
      aria-hidden={isDecorative || undefined}
      onMouseEnter={isInteractive ? cacheRect : undefined}
      onMouseMove={isInteractive ? handleMouseMove : undefined}
      onMouseLeave={isInteractive ? () => setHoveredId(null) : undefined}
    >
      {/* The map always fills the height (height:100%/width:auto in CSS); width overflow is
          cropped by the canvas, so the top/bottom stay at the padding regardless of window
          proportions. The tooltip is outside the canvas so it is not clipped. */}
      <div
        ref={canvasRef}
        className="world-map-canvas"
        style={{ "--map-occluded-left": `${isFadedUnderOccluder ? occludedLeft : 0}px` } as CSSProperties}
      >
        {/* Accessible name via aria-label, NOT <title>: browsers draw <title> as a native tooltip
            that overlaps our custom one (role="img" trips jsx-a11y/prefer-tag-over-role, so
            just aria-label). */}
        <svg
          ref={svgRef}
          className="world-map"
          viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`}
          aria-label={t("map.aria")}
          preserveAspectRatio="xMidYMid meet"
        >
          {countryShapes}
          {leaving && (
            <g key={`leaving:${leaving.key}`} className="world-map__leaving">
              {renderCityDots(leavingDots)}
              {leaving.overlay && <g className="world-map__overlay">{leaving.overlay(view)}</g>}
            </g>
          )}
          {/* Keyed by the scene: each arrival plays its own fade-in. */}
          <g key={sceneKey} className={isSceneArriving ? "world-map__arriving" : undefined}>
            {renderCityDots(cityDots)}
            {overlay && <g className="world-map__overlay">{overlay(view)}</g>}
          </g>
        </svg>
      </div>

      {hoveredId && (
        <div
          ref={tooltipRef}
          className="world-map__tooltip"
          style={{
            left: pointer.x,
            top: pointer.y,
            transform: `translate(${
              flip.x ? `calc(-100% - ${TOOLTIP_OFFSET}px)` : `${TOOLTIP_OFFSET}px`
            }, ${flip.y ? `calc(-100% - ${TOOLTIP_OFFSET}px)` : `${TOOLTIP_OFFSET}px`})`,
          }}
        >
          <span className="world-map__tooltip-title">{hoveredName}</span>
          {hovered?.status === "visited" ? (
            hoveredCities.length > 0 && (
              <ul className="world-map__tooltip-cities">
                {hoveredCities.map((city) => (
                  <li key={city.id}>
                    <span className="world-map__tooltip-city">{city.name}</span>
                    <span className="world-map__tooltip-years">{city.years.join(", ")}</span>
                  </li>
                ))}
              </ul>
            )
          ) : (
            <span className="world-map__tooltip-muted">
              {hovered?.status === "wishlist" ? t("map.wishlist") : t("map.notVisited")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
