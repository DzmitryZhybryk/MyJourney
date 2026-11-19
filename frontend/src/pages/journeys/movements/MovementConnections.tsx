import { useMemo } from "react";

import type { MapPoint } from "../../../api/sdk";
import { projectToScreen } from "../../../components/worldProjection";
import { ArrowMarker } from "./ArrowMarker";
import { layOutCityLabels } from "./labelPlacement";
import { piecePath, splitEdgeFade, type ArcPieces } from "./movementGeometry";

/** A from -> to route with its arc already projected. */
export interface ProjectedConnection {
  key: string;
  origin: MapPoint;
  destination: MapPoint;
  /** Years of journeys on the route, ascending: they decide whether the route falls in the year window. */
  years: readonly number[];
  arc: ArcPieces;
}

interface MovementConnectionsProps {
  connections: readonly ProjectedConnection[];
  /**
   * Share of the world width taken by the visible area. Arrows and dots are in canvas units;
   * without this correction they would grow with the map when zoomed in.
   */
  unitScale: number;
  /** City label by id; `undefined` means the name is still loading, no label. */
  labelOf: (cityId: string) => string | undefined;
}

// Sizes in canvas units when the whole map is visible.
const ARROW_SIZE = 7;
const DOT_RADIUS = 2.2;
const LABEL_FONT_SIZE = 8;
// Label offset from the dot edge, clearance from lines and neighbouring labels, halo stroke behind the text.
const LABEL_GAP = 2;
const LABEL_CLEARANCE = 1.2;
const LABEL_HALO_WIDTH = 2.4;
// An arc across the world edge fades at the cut over this length instead of ending abruptly mid-ocean.
const EDGE_FADE_LENGTH = 40;
// One marker per layer: the page has a single movements map.
const ARROW_MARKER_ID = "movement-arrow";

/**
 * Movements map layer over `WorldMap`: a dot with a name for each city and an arc with an arrow
 * for each route. Trips there and back share one arc, so arrows appear at both ends.
 */
export function MovementConnections({ connections, unitScale, labelOf }: MovementConnectionsProps) {
  const cityDots = useMemo(() => {
    const cities = new Map<string, { city: MapPoint; routeCount: number }>();
    for (const connection of connections) {
      for (const city of [connection.origin, connection.destination]) {
        const seen = cities.get(city.cityId);
        cities.set(city.cityId, { city, routeCount: (seen?.routeCount ?? 0) + 1 });
      }
    }

    return [...cities.values()].map(({ city, routeCount }) => {
      const [cx, cy] = projectToScreen(city.longitude, city.latitude);
      return { key: city.cityId, cx, cy, routeCount };
    });
  }, [connections]);

  // Labels keep a constant on-screen size, so the layout is recomputed with the zoom.
  const labels = useMemo(() => {
    const labelledCities = cityDots.flatMap((dot) => {
      const label = labelOf(dot.key);
      return label ? [{ cityId: dot.key, x: dot.cx, y: dot.cy, label, routeCount: dot.routeCount }] : [];
    });
    return layOutCityLabels(
      labelledCities,
      connections.map((connection) => connection.arc),
      {
        fontSize: LABEL_FONT_SIZE * unitScale,
        gap: (DOT_RADIUS + LABEL_GAP) * unitScale,
        dotRadius: DOT_RADIUS * unitScale,
        clearance: LABEL_CLEARANCE * unitScale,
      },
    );
  }, [cityDots, connections, labelOf, unitScale]);

  const arrowSize = ARROW_SIZE * unitScale;

  return (
    <>
      <defs>
        <ArrowMarker id={ARROW_MARKER_ID} size={arrowSize} className="movement-arrow" />
      </defs>
      {/* Dots under the lines: the arrow tip lands on the destination dot instead of hiding under it. */}
      <g>
        {cityDots.map((dot) => (
          <circle
            key={dot.key}
            className="movement-dot"
            cx={dot.cx}
            cy={dot.cy}
            r={DOT_RADIUS * unitScale}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </g>
      <g>
        {connections.map((connection, connectionIndex) => {
          const [first, second] = connection.arc;
          // The transparent wide stroke is the hover zone: the thin line itself is hard to hit.
          // It sits in the same group as the line pieces, so hovering any piece highlights the whole route.
          const hitZones = connection.arc.map((piece) => (
            <path
              key={`hit:${piece[0][0]},${piece[0][1]}`}
              className="movement-route__hit"
              d={piecePath(piece)}
              vectorEffect="non-scaling-stroke"
            />
          ));
          if (!second) {
            return (
              <g key={connection.key} className="movement-route">
                <path
                  className="movement-line"
                  d={piecePath(first)}
                  markerEnd={`url(#${ARROW_MARKER_ID})`}
                  vectorEffect="non-scaling-stroke"
                />
                {hitZones}
              </g>
            );
          }

          // An arc across the world edge is two pieces: the first fades toward the cut, the second
          // emerges from it. Only the tail at the cut fades; the rest of the arc is solid.
          const fadeLength = EDGE_FADE_LENGTH * unitScale;
          const pieces = [
            { split: splitEdgeFade(first, "end", fadeLength), endsAtDestination: false },
            { split: splitEdgeFade(second, "start", fadeLength), endsAtDestination: true },
          ];
          return (
            <g key={connection.key} className="movement-route">
              {pieces.map(({ split, endsAtDestination }, pieceIndex) => {
                const gradientId = `movement-edge-fade-${connectionIndex}-${pieceIndex}`;
                const [[innerX, innerY], [edgeX, edgeY]] = split.fadeAxis;
                const hasSolid = split.solid.length > 1;
                // The arrow goes on the part that ends at the destination point.
                const arrow = `url(#${ARROW_MARKER_ID})`;
                return (
                  <g key={gradientId}>
                    <defs>
                      <linearGradient
                        id={gradientId}
                        gradientUnits="userSpaceOnUse"
                        x1={innerX}
                        y1={innerY}
                        x2={edgeX}
                        y2={edgeY}
                      >
                        <stop offset="0" style={{ stopColor: "var(--movement-line)", stopOpacity: 1 }} />
                        <stop offset="1" style={{ stopColor: "var(--movement-line)", stopOpacity: 0 }} />
                      </linearGradient>
                    </defs>
                    <path
                      className="movement-line"
                      // Inline, not an attribute: the stroke from the line's CSS class would override an attribute.
                      style={{ stroke: `url(#${gradientId})` }}
                      d={piecePath(split.fade)}
                      markerEnd={endsAtDestination && !hasSolid ? arrow : undefined}
                      vectorEffect="non-scaling-stroke"
                    />
                    {hasSolid && (
                      <path
                        className="movement-line"
                        d={piecePath(split.solid)}
                        markerEnd={endsAtDestination ? arrow : undefined}
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                  </g>
                );
              })}
              {hitZones}
            </g>
          );
        })}
      </g>
      {/* Labels over the lines: if there is no crossing-free spot, an arc does not strike through the name. */}
      <g>
        {labels.map((label) => (
          <text
            key={label.cityId}
            className="movement-label"
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
    </>
  );
}
