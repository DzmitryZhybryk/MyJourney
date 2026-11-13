import type { FormValidateInput, UseFormReturnType } from "@mantine/form";

import { ApiError, errorCodeToken } from "../../api/errors";
import type { CitySearchItem, TransportTypeEnum } from "../../api/sdk";

/** Journey fields, shared by add and edit. */
export type JourneyFormValues = {
  origin: CitySearchItem | null;
  destination: CitySearchItem | null;
  transport: TransportTypeEnum | null;
  year: string | null;
};

/** A journey deleted elsewhere: saving reports it, deleting treats it as already done. */
export const JOURNEY_NOT_FOUND_CODE = "journeys.journey_not_found";

const UNKNOWN_CITY_CODE = "journeys.unknown_city";

/**
 * Journey field validators.
 *
 * They return an i18n TOKEN (`journeys:addJourney.validation.*`), not text: it is resolved at
 * render (`resolveErrorToken`) so the error follows a language switch.
 */
export const JOURNEY_FORM_VALIDATE: FormValidateInput<JourneyFormValues> = {
  origin: (value) => (value ? null : "journeys:addJourney.validation.originRequired"),
  destination: (value, values) => {
    if (!value) {
      return "journeys:addJourney.validation.destinationRequired";
    }
    // Reject the same city on the frontend too; the backend checks the same by cityId.
    if (values.origin && values.origin.cityId === value.cityId) {
      return "journeys:addJourney.validation.sameCity";
    }
    return null;
  },
  transport: (value) => (value ? null : "journeys:addJourney.validation.transportRequired"),
  year: (value) => (value ? null : "journeys:addJourney.validation.yearRequired"),
};

/**
 * Highlights fields whose cities the backend rejected (`journeys.unknown_city`).
 *
 * The backend returns only the ids of the rejected cities; the form decides which field to highlight
 * by comparing them with the picked cities.
 *
 * Returns `true` if the error was handled and shown at the fields.
 */
export function applyCityError(
  err: unknown,
  values: JourneyFormValues,
  form: UseFormReturnType<JourneyFormValues>,
): boolean {
  if (!(err instanceof ApiError) || err.code !== UNKNOWN_CITY_CODE) {
    return false;
  }

  const rawIds = err.details?.city_ids;
  const rejected = new Set(Array.isArray(rawIds) ? rawIds.filter((id): id is string => typeof id === "string") : []);
  let isApplied = false;
  for (const field of ["origin", "destination"] as const) {
    const city = values[field];
    if (city && rejected.has(city.cityId)) {
      form.setFieldError(field, errorCodeToken(err.code));
      isApplied = true;
    }
  }

  return isApplied;
}
