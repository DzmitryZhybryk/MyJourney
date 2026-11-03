import { Chip, Group, Text, UnstyledButton, VisuallyHidden } from "@mantine/core";
import { useRef, type RefObject } from "react";
import { useTranslation } from "react-i18next";

import { zTransportTypeEnum, type TransportTypeEnum } from "../../../api/sdk";
import { TRANSPORT_ICONS } from "../../../components/transportIcons";
import { useDraggableCard } from "./useDraggableCard";
import { YearRangeSlider } from "./YearRangeSlider";

/** Year window `[from, to]`, both bounds inclusive. */
export type YearWindow = readonly [number, number];

const TRANSPORT_ICON_SIZE = 20;

interface MovementsControlsProps {
  firstYear: number;
  lastYear: number;
  window: YearWindow;
  /** A window bound moved to another year; the map changes live while dragging. */
  onWindowChange: (window: YearWindow) => void;
  transportTypes: readonly TransportTypeEnum[];
  onTransportTypesChange: (transportTypes: readonly TransportTypeEnum[]) => void;
  /** Navigation panel: the card does not overlap it and aligns to its edges. */
  panelRef: RefObject<HTMLElement | null>;
}

/** Drag grip: two rows of dots; a UI control drawn in `currentColor`. */
function GripIcon() {
  return (
    <svg width="16" height="8" viewBox="0 0 16 8" aria-hidden="true" fill="currentColor">
      {[2, 8, 14].map((x) => [2, 6].map((y) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.3" />))}
    </svg>
  );
}

/**
 * Movements map filters (year window and transport types) in a draggable card.
 *
 * Lines appear and disappear live while the slider is dragged (see YearRangeSlider). The card is
 * moved by the tab above its top edge (arrow keys work too); a double click on the tab returns
 * it to the default corner.
 */
export function MovementsControls({
  firstYear,
  lastYear,
  window,
  onWindowChange,
  transportTypes,
  onTransportTypesChange,
  panelRef,
}: MovementsControlsProps) {
  const { t } = useTranslation("journeys");
  const cardRef = useRef<HTMLElement>(null);
  const { style, handleProps } = useDraggableCard(cardRef, panelRef);

  const isSingleYear = firstYear === lastYear;
  const hasTransport = transportTypes.length > 0;

  return (
    <section ref={cardRef} className="movements-controls journeys-card" style={style} aria-label={t("movements.controls")}>
      <UnstyledButton
        className="movements-controls__handle"
        aria-label={t("movements.move")}
        title={t("movements.move")}
        {...handleProps}
      >
        <GripIcon />
      </UnstyledButton>

      {/* A single year needs only a label: nothing to move in a slider. */}
      {isSingleYear ? (
        <Text className="movements-controls__single-year">{firstYear}</Text>
      ) : (
        <YearRangeSlider
          firstYear={firstYear}
          lastYear={lastYear}
          window={window}
          onWindowChange={onWindowChange}
          fromLabel={t("movements.yearFrom")}
          toLabel={t("movements.yearTo")}
        />
      )}

      <Chip.Group multiple value={[...transportTypes]} onChange={(value) => onTransportTypesChange(value as TransportTypeEnum[])}>
        <fieldset className="movements-controls__transport">
          <VisuallyHidden component="legend">{t("movements.transport")}</VisuallyHidden>
          {/* Icons only, in a row, evenly spaced; the label is for screen readers and the tooltip.
              Selection shows by fill, no tick. */}
          <Group gap={6} grow wrap="nowrap">
            {zTransportTypeEnum.options.map((type) => (
              <Chip
                key={type}
                value={type}
                variant="outline"
                size="md"
                className="movements-controls__chip"
                title={t(`addJourney.transport.${type}`)}
              >
                <img
                  className={`movements-controls__icon movements-controls__icon--${type}`}
                  src={TRANSPORT_ICONS[type]}
                  width={TRANSPORT_ICON_SIZE}
                  height={TRANSPORT_ICON_SIZE}
                  alt=""
                />
                <VisuallyHidden>{t(`addJourney.transport.${type}`)}</VisuallyHidden>
              </Chip>
            ))}
          </Group>
        </fieldset>
      </Chip.Group>

      {!hasTransport && (
        <Text size="sm" c="var(--text-muted)">
          {t("movements.noTransport")}
        </Text>
      )}
    </section>
  );
}
