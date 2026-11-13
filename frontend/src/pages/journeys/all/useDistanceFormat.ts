import { useMemo } from "react";
import { useTranslation } from "react-i18next";

/** Kilometres in the UI language, whole numbers: "7,661 km" / "7 661 км". */
export function useDistanceFormat(): Intl.NumberFormat {
  const { i18n } = useTranslation();
  return useMemo(
    () => new Intl.NumberFormat(i18n.language, { style: "unit", unit: "kilometer", maximumFractionDigits: 0 }),
    [i18n.language],
  );
}
