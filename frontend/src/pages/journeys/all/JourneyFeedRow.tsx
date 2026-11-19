import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { VisuallyHidden } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { cityLabel, type CityNameLookup } from "../../../api/cityNames";
import type { JourneyFeedEntry } from "../../../api/sdk";
import { TRANSPORT_ICONS } from "../../../components/transportIcons";
import { journeyCardPath } from "./journeyCardPath";
import { useAnimatedNumber } from "./motion";

const TRANSPORT_ICON_SIZE = 22;

interface JourneyFeedRowProps {
  journey: JourneyFeedEntry;
  nameOf: CityNameLookup;
  distanceFormat: Intl.NumberFormat;
  isDragDisabled: boolean;
  /** Year the row lands in if dropped now; set only on the dragged row. */
  dropYear: number | null;
}

/** Drag grip: two columns of dots; a UI control drawn in `currentColor`. */
function GripIcon() {
  return (
    <svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true" fill="currentColor">
      {[2, 6].map((x) => [2, 7, 12].map((y) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.3" />))}
    </svg>
  );
}

/**
 * Feed row: grip, transport, "from -> to" and distance. An ellipsis shows while names load.
 *
 * Everything but the grip is one link to the journey card. A row is dragged by the grip with
 * mouse, finger or keyboard (space, arrows, space); moving to another year shows "-> year" beside it.
 */
export function JourneyFeedRow({ journey, nameOf, distanceFormat, isDragDisabled, dropYear }: JourneyFeedRowProps) {
  const { t } = useTranslation("journeys");
  const { t: tCommon } = useTranslation("common");
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: journey.journeyId,
    disabled: isDragDisabled,
  });

  const unknownLabel = tCommon("map.unknownCity");
  const origin = cityLabel(nameOf(journey.origin.cityId), unknownLabel);
  const destination = cityLabel(nameOf(journey.destination.cityId), unknownLabel);
  const transportLabel = t(`addJourney.transport.${journey.transportType}`);
  const isChangingYear = isDragging && dropYear !== null && dropYear !== journey.traveledYear;
  const distanceKm = useAnimatedNumber(journey.distanceKm);

  return (
    <li
      ref={setNodeRef}
      className={isDragging ? "journey-row journey-row--dragging" : "journey-row"}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      data-flip-id={journey.journeyId}
    >
      <button
        type="button"
        ref={setActivatorNodeRef}
        className="journey-row__handle"
        aria-label={t("all.dragHandle")}
        disabled={isDragDisabled}
        {...attributes}
        {...listeners}
      >
        <GripIcon />
      </button>
      {/* The spaces between the parts are text: the link's accessible name would run them together
          ("AirMoscowtoLondon"); grid and flex layout do not render them. */}
      <Link to={journeyCardPath(journey.journeyId)} className="journey-row__open">
        <img
          src={TRANSPORT_ICONS[journey.transportType]}
          width={TRANSPORT_ICON_SIZE}
          height={TRANSPORT_ICON_SIZE}
          alt={transportLabel}
        />{" "}
        <span className="journey-row__route">
          <span className="journey-row__city">{origin ?? "…"}</span>{" "}
          <span className="journey-row__arrow" aria-hidden="true">
            →
          </span>
          <VisuallyHidden>{t("all.routeTo")}</VisuallyHidden>{" "}
          <span className="journey-row__city">{destination ?? "…"}</span>
        </span>{" "}
        {/* The key is the year: moving to the next year flips the hint again. */}
        {isChangingYear ? (
          <span key={dropYear} className="journey-row__drop-year">
            → {dropYear}
          </span>
        ) : (
          <span className="journey-row__distance">{distanceFormat.format(distanceKm)}</span>
        )}
      </Link>
    </li>
  );
}
