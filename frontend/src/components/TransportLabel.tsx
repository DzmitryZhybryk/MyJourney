import { useTranslation } from "react-i18next";

import type { TransportTypeEnum } from "../api/sdk";
import { TRANSPORT_ICONS } from "./transportIcons";

const ICON_SIZE = 20;

interface TransportLabelProps {
  type: TransportTypeEnum;
}

/** Transport type as icon plus label, for chips and the journey card. */
export function TransportLabel({ type }: TransportLabelProps) {
  const { t } = useTranslation("journeys");

  return (
    <span className="transport-label">
      <img src={TRANSPORT_ICONS[type]} width={ICON_SIZE} height={ICON_SIZE} alt="" />
      <span>{t(`addJourney.transport.${type}`)}</span>
    </span>
  );
}
