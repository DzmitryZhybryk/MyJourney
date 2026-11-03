import { Chip } from "@mantine/core";
import { useTranslation } from "react-i18next";

import { zTransportTypeEnum, type TransportTypeEnum } from "../../../api/sdk";
import { TransportLabel } from "../../../components/TransportLabel";

interface TransportChipsProps {
  transportTypes: readonly TransportTypeEnum[];
  onTransportTypesChange: (transportTypes: readonly TransportTypeEnum[]) => void;
}

/** Multi-select of feed transport types: icon and label, selection shown by fill. */
export function TransportChips({ transportTypes, onTransportTypesChange }: TransportChipsProps) {
  const { t } = useTranslation("journeys");

  return (
    <Chip.Group multiple value={[...transportTypes]} onChange={(value) => onTransportTypesChange(value as TransportTypeEnum[])}>
      <fieldset className="transport-chips">
        <legend className="all-journeys__filter-label">{t("all.transport")}</legend>
        <div className="transport-chips__row">
          {zTransportTypeEnum.options.map((type) => (
            <Chip key={type} value={type} variant="outline" size="md" className="transport-chips__chip">
              <TransportLabel type={type} />
            </Chip>
          ))}
        </div>
      </fieldset>
    </Chip.Group>
  );
}
