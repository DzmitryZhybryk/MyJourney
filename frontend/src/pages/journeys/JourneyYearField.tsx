import { Select, Stack, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { resolveErrorToken } from "../../api/errors";
import type { JourneyFormValues } from "./journeyFormRules";
import { journeyYearOptions } from "./journeyYears";

interface JourneyYearFieldProps {
  form: UseFormReturnType<JourneyFormValues>;
}

/** Journey year: a list from the current year back 100 years. */
export function JourneyYearField({ form }: JourneyYearFieldProps) {
  const { t } = useTranslation("journeys");
  const values = form.getValues();

  // The current year is read once when the field appears: reading the clock every render is impure.
  const [yearOptions] = useState(() => journeyYearOptions(new Date().getFullYear()));

  return (
    <Stack gap="sm">
      <Text size="sm" fw={600}>
        {t("addJourney.date.legend")}
      </Text>

      <Select
        placeholder={t("addJourney.date.yearPlaceholder")}
        size="md"
        radius="md"
        searchable
        data={yearOptions}
        value={values.year}
        onChange={(value) => {
          form.setFieldValue("year", value);
          form.clearFieldError("year");
        }}
        error={resolveErrorToken(form.errors.year)}
      />
    </Stack>
  );
}
