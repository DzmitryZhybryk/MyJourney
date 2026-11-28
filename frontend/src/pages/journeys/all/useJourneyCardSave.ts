import { useForm, type UseFormReturnType } from "@mantine/form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ApiError, applyApiError, errorCodeToken } from "../../../api/errors";
import { updateJourneyMutation } from "../../../api/sdk";
import { invalidateJourneyAggregates, invalidateJourneyFeed } from "../journeyCache";
import {
  applyCityError,
  JOURNEY_FORM_VALIDATE,
  JOURNEY_NOT_FOUND_CODE,
  type JourneyFormValues,
} from "../journeyFormRules";

// How long "Saved · Undo" stays after a save.
const STATUS_MS = 5000;

/** What the card says after a save: "saved" offers Undo, "undone" confirms it. */
export type JourneyCardStatus = "saved" | "undone";

export interface JourneyCardSave {
  /** Values the card shows (the last saved ones between commits) and the field errors. */
  form: UseFormReturnType<JourneyFormValues>;
  isSaving: boolean;
  status: JourneyCardStatus | null;
  /** Error of the whole save, an i18n token. */
  errorToken: string | null;
  /** Saves the journey with these fields changed; nothing is sent when nothing changes. */
  commit: (patch: Partial<JourneyFormValues>) => Promise<void>;
  /** Saves the values from before the last save. */
  undo: () => Promise<void>;
}

function isSameJourney(left: JourneyFormValues, right: JourneyFormValues): boolean {
  return (
    left.origin?.cityId === right.origin?.cityId &&
    left.destination?.cityId === right.destination?.cityId &&
    left.transport === right.transport &&
    left.year === right.year
  );
}

/**
 * Instant save of the journey card: every commit sends the whole journey (`PUT` replaces all
 * fields), one at a time. A commit validates first; a field error or a failed save puts the shown
 * values back to the last saved ones and keeps the error. After a save "Saved · Undo" shows for a
 * few seconds; Undo saves the previous values and offers no further undo.
 *
 * Undo restores values, not the place inside a year: the backend puts a journey that changes year
 * at the end of that year.
 */
export function useJourneyCardSave(journeyId: string, initialValues: JourneyFormValues): JourneyCardSave {
  const queryClient = useQueryClient();
  // Errors are cleared when a commit starts, not on every value change: putting the saved values
  // back after a failed check would otherwise wipe the error it just showed.
  const form = useForm<JourneyFormValues>({
    mode: "controlled",
    initialValues,
    validate: JOURNEY_FORM_VALIDATE,
    clearInputErrorOnChange: false,
  });
  // Refs, not state: a commit reads them after awaiting, when the render it started in is stale.
  const saved = useRef(initialValues);
  const previous = useRef<JourneyFormValues | null>(null);
  const isSavingRef = useRef(false);
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<JourneyCardStatus | null>(null);
  const [errorToken, setErrorToken] = useState<string | null>(null);
  const { mutateAsync } = useMutation({
    ...updateJourneyMutation(),
    // Not awaited: the card is already right, the feed and maps catch up in the background.
    onSuccess: () => {
      void invalidateJourneyAggregates(queryClient);
      void invalidateJourneyFeed(queryClient);
    },
  });

  useEffect(() => {
    if (status === null) {
      return;
    }

    const timer = window.setTimeout(() => setStatus(null), STATUS_MS);
    return () => window.clearTimeout(timer);
  }, [status]);

  const save = async (next: JourneyFormValues, isUndo: boolean) => {
    if (isSavingRef.current) {
      return;
    }

    form.clearErrors();
    setErrorToken(null);
    if (isSameJourney(next, saved.current)) {
      form.setValues(saved.current);
      return;
    }

    form.setValues(next);
    const { hasErrors } = await form.validate();
    const { origin, destination, transport, year } = next;
    if (hasErrors || !origin || !destination || !transport || !year) {
      form.setValues(saved.current);
      return;
    }

    isSavingRef.current = true;
    setIsSaving(true);
    try {
      await mutateAsync({
        path: { journey_id: journeyId },
        body: {
          originCityId: origin.cityId,
          destinationCityId: destination.cityId,
          transportType: transport,
          traveledYear: Number(year),
        },
      });
      previous.current = isUndo ? null : saved.current;
      saved.current = next;
      setStatus(isUndo ? "undone" : "saved");
    } catch (err) {
      form.setValues(saved.current);
      setStatus(null);
      if (err instanceof ApiError && err.code === JOURNEY_NOT_FOUND_CODE) {
        setErrorToken(errorCodeToken(JOURNEY_NOT_FOUND_CODE));
        void invalidateJourneyFeed(queryClient);
      } else if (!applyCityError(err, next, form)) {
        setErrorToken(applyApiError(err, form));
      }
    } finally {
      isSavingRef.current = false;
      setIsSaving(false);
    }
  };

  return {
    form,
    isSaving,
    status,
    errorToken,
    commit: (patch) => save({ ...saved.current, ...patch }, false),
    undo: async () => {
      if (previous.current !== null) {
        await save(previous.current, true);
      }
    },
  };
}
