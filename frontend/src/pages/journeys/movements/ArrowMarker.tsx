interface ArrowMarkerProps {
  id: string;
  /** Arrowhead size in canvas units: it does not depend on the stroke width of the line it ends. */
  size: number;
  /** Class of the arrowhead shape: the layer colours it. */
  className: string;
}

/** Arrowhead for the end of an arc (`marker-end`): the tip lands exactly on the path end. */
export function ArrowMarker({ id, size, className }: ArrowMarkerProps) {
  return (
    <marker
      id={id}
      viewBox="0 0 10 10"
      refX="10"
      refY="5"
      markerUnits="userSpaceOnUse"
      markerWidth={size}
      markerHeight={size}
      orient="auto"
    >
      <path className={className} d="M0 1L10 5L0 9Z" />
    </marker>
  );
}
