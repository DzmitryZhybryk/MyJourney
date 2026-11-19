import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, errorCodeToken, resolveErrorToken } from "../../../api/errors";
import { deleteJourneyMutation } from "../../../api/sdk";
import { invalidateJourneyAggregates, removeJourneyFromFeed } from "../journeyCache";
import { JOURNEY_NOT_FOUND_CODE } from "../journeyFormRules";

interface JourneyDeleteDialogProps {
  opened: boolean;
  onClose: () => void;
  journeyId: string;
  /** "Origin → destination", named in the question. */
  route: string;
  /** The journey is gone from the feed cache; the card is to close. */
  onDeleted: () => void;
}

/**
 * Confirmation before deleting a journey: deletion cannot be undone, unlike an edit.
 *
 * A journey already deleted elsewhere (404) counts as deleted: the goal is met. The feed drops the
 * row without a request; maps, globe and years refetch in the background.
 */
export function JourneyDeleteDialog({ opened, onClose, journeyId, route, onDeleted }: JourneyDeleteDialogProps) {
  const { t } = useTranslation("journeys");
  const queryClient = useQueryClient();
  const [errorToken, setErrorToken] = useState<string | null>(null);
  const { mutateAsync, isPending } = useMutation(deleteJourneyMutation());

  const handleDelete = async () => {
    setErrorToken(null);
    try {
      await mutateAsync({ path: { journey_id: journeyId } });
    } catch (err) {
      if (!(err instanceof ApiError && err.code === JOURNEY_NOT_FOUND_CODE)) {
        setErrorToken(errorCodeToken(err instanceof ApiError ? err.code : "network"));
        return;
      }
    }

    removeJourneyFromFeed(queryClient, journeyId);
    void invalidateJourneyAggregates(queryClient);
    onDeleted();
  };

  const handleClose = () => {
    if (!isPending) {
      setErrorToken(null);
      onClose();
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      centered
      radius="lg"
      title={
        // Modal wraps the title in its own <h2>: the content must not be a heading too.
        <Text size="h4" fw={700} style={{ color: "var(--text)" }}>
          {t("card.deleteTitle")}
        </Text>
      }
    >
      <Stack gap="md">
        <Text size="sm" c="var(--text-muted)">
          {t("card.deleteBody", { route })}
        </Text>
        {errorToken && (
          <Text size="sm" fw={500} c="var(--text-error)" role="alert">
            {resolveErrorToken(errorToken)}
          </Text>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={handleClose} disabled={isPending}>
            {t("all.cancel")}
          </Button>
          <Button color="red" onClick={() => void handleDelete()} loading={isPending}>
            {t("all.delete")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
