import { Button, Group, Select, Stack, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { applyApiError, resolveErrorToken } from "../../api/errors";
import { createJourneyMutation, zTransportTypeEnum, type TransportTypeEnum } from "../../api/sdk";
import { CityAutocomplete } from "../../components/CityAutocomplete";
import { SwapVerticalIcon } from "../../components/SwapVerticalIcon";
import { TRANSPORT_ICONS } from "../../components/transportIcons";
import { invalidateJourneyAggregates, invalidateJourneyFeed } from "./journeyCache";
import { applyCityError, type JourneyFormValues } from "./journeyFormRules";
import { JourneyYearField } from "./JourneyYearField";

const TRANSPORT_ICON_SIZE = 22;

interface JourneyFormProps {
  form: UseFormReturnType<JourneyFormValues>;
}

/**
 * Add-journey form: from/to (autocomplete), transport and year. `form` is lifted into
 * AddJourneyPage so the hero globe reacts to input live. Submit builds the payload from the
 * picked cities, transport and year, POSTs `/v1/journeys` (`createJourney`) and on success goes
 * to `/journeys`.
 */
export function JourneyForm({ form }: JourneyFormProps) {
  const { t } = useTranslation("journeys");
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);

  // A new journey changes the maps, globe, feed and its years: invalidate everything.
  const { mutateAsync: submitJourney, isPending: submitting } = useMutation({
    ...createJourneyMutation(),
    onSuccess: () => Promise.all([invalidateJourneyAggregates(queryClient), invalidateJourneyFeed(queryClient)]),
  });

  // Swap from/to. The globe flips the route and the transport icon itself (its animation depends
  // on the origin -> destination order). Clear field errors so old validation (e.g. "pick a city")
  // does not stay on the moved value.
  const handleSwap = () => {
    const { origin, destination } = form.getValues();
    form.setValues({ origin: destination, destination: origin });
    form.clearFieldError("origin");
    form.clearFieldError("destination");
  };

  const handleSubmit = async (values: JourneyFormValues) => {
    const { origin, destination } = values;
    if (!origin || !destination || !values.transport || !values.year) {
      return;
    }

    setFormError(null);
    try {
      await submitJourney({
        body: {
          originCityId: origin.cityId,
          destinationCityId: destination.cityId,
          transportType: values.transport,
          traveledYear: Number(values.year),
        },
      });
      navigate("/journeys");
    } catch (err) {
      if (applyCityError(err, values, form)) {
        return;
      }

      // An operation error (not tied to a field) goes at form level by the submit button.
      const message = applyApiError(err, form);
      if (message) {
        setFormError(message);
      }
    }
  };

  const values = form.getValues();
  const selectedTransportIcon = values.transport ? TRANSPORT_ICONS[values.transport] : null;

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        {/* The swap button is in the DOM AFTER both fields (visually over the gap between them) so
            Tab goes from -> to without catching the button. */}
        <div className="add-journey__route">
          <Stack gap="md">
            <CityAutocomplete
              label={t("addJourney.origin.label")}
              placeholder={t("addJourney.origin.placeholder")}
              value={values.origin}
              onChange={(city) => form.setFieldValue("origin", city)}
              error={resolveErrorToken(form.errors.origin)}
            />

            <CityAutocomplete
              label={t("addJourney.destination.label")}
              placeholder={t("addJourney.destination.placeholder")}
              value={values.destination}
              onChange={(city) => form.setFieldValue("destination", city)}
              error={resolveErrorToken(form.errors.destination)}
            />
          </Stack>

          <button
            type="button"
            className="add-journey__swap"
            aria-label={t("addJourney.swap")}
            onClick={handleSwap}
            disabled={!values.origin && !values.destination}
          >
            <SwapVerticalIcon />
          </button>
        </div>

        <Select
          label={t("addJourney.transport.label")}
          placeholder={t("addJourney.transport.placeholder")}
          size="md"
          radius="md"
          data={zTransportTypeEnum.options.map((type) => ({ value: type, label: t(`addJourney.transport.${type}`) }))}
          value={values.transport}
          onChange={(value) => {
            form.setFieldValue("transport", value as TransportTypeEnum | null);
            form.clearFieldError("transport");
          }}
          leftSection={
            selectedTransportIcon ? (
              <img src={selectedTransportIcon} width={TRANSPORT_ICON_SIZE} height={TRANSPORT_ICON_SIZE} alt="" />
            ) : null
          }
          renderOption={({ option }) => (
            <Group gap="xs" wrap="nowrap">
              <img
                src={TRANSPORT_ICONS[option.value as TransportTypeEnum]}
                width={TRANSPORT_ICON_SIZE}
                height={TRANSPORT_ICON_SIZE}
                alt=""
              />
              <span>{option.label}</span>
            </Group>
          )}
          error={resolveErrorToken(form.errors.transport)}
        />

        <JourneyYearField form={form} />

        {formError && (
          <Text size="sm" fw={500} c="var(--text-error)">
            {resolveErrorToken(formError)}
          </Text>
        )}

        <Button type="submit" size="md" radius="md" fullWidth mt="xs" loading={submitting}>
          {t("addJourney.submit")}
        </Button>
      </Stack>
    </form>
  );
}
