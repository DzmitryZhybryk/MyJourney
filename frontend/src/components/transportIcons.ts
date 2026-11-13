import type { TransportTypeEnum } from "../api/sdk";
import carIcon from "../assets/emoji/car.svg";
import planeIcon from "../assets/emoji/plane.svg";
import shipIcon from "../assets/emoji/ship.svg";

/** Transport icon (Noto emoji SVG); its label comes from i18n. */
export const TRANSPORT_ICONS: Readonly<Record<TransportTypeEnum, string>> = {
  land: carIcon,
  air: planeIcon,
  water: shipIcon,
};
