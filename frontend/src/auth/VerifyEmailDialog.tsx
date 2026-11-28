import { Button, Group, Modal, PinInput, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type ErrorParams, errorCodeToken, resolveErrorToken } from "../api/errors";
import { refresh, sendEmailVerification, verifyEmail } from "../api/sdk";
import { setAccessToken } from "./tokenStore";

type Stage = "intro" | "code";

type DialogError = Readonly<{ token: string; params?: ErrorParams }>;

interface VerifyEmailDialogProps {
  opened: boolean;
  onClose: () => void;
  onVerified?: () => void;
}

const CODE_LENGTH = 6;
const ATTEMPTS_EXCEEDED_CODE = "auth.challenge_attempts_exceeded";
const SECONDS_PER_MINUTE = 60;

export function VerifyEmailDialog({ opened, onClose, onVerified }: VerifyEmailDialogProps) {
  const { t } = useTranslation(["auth", "errors"]);
  const [stage, setStage] = useState<Stage>("intro");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<DialogError | null>(null);

  // Reset in the close handler (not an effect on `opened`) so the next open starts at "intro".
  const handleClose = () => {
    setStage("intro");
    setCode("");
    setError(null);
    setSubmitting(false);
    onClose();
  };

  const handleSendCode = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await sendEmailVerification({ throwOnError: true });
      setStage("code");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          // Already verified in another session/tab: sync the token.
          await syncVerifiedClaim();
          onVerified?.();
          handleClose();
          return;
        }

        setError(toDialogError(err));
      } else {
        setError({ token: errorCodeToken("network") });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async () => {
    if (code.length !== CODE_LENGTH) {
      setError({ token: "auth:verifyEmail.codeIncomplete" });
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await verifyEmail({ body: { code }, throwOnError: true });
      await syncVerifiedClaim();
      onVerified?.();
      handleClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          // Already verified: close and sync.
          await syncVerifiedClaim();
          onVerified?.();
          handleClose();
          return;
        }

        // 410 (expired), 404 (not found), 429 (attempts exceeded): back to "intro" so the user
        // can request a new code.
        const shouldResetToIntro = err.status === 410 || err.status === 404 || err.status === 429;
        setError(toDialogError(err));
        if (shouldResetToIntro) {
          setStage("intro");
          setCode("");
        }
      } else {
        setError({ token: errorCodeToken("network") });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      centered
      radius="lg"
      title={
        // Modal wraps title in its own <h2>, so the content must NOT be a heading (nested headings
        // are invalid HTML and duplicate the heading for screen readers). Text keeps the look.
        <Text size="h4" fw={700} style={{ color: "var(--text)" }}>
          {t("verifyEmail.title")}
        </Text>
      }
    >
      <Stack gap="md">
        {stage === "intro" ? (
          <>
            <Text size="sm" c="var(--text-muted)">
              {t("verifyEmail.intro")}
            </Text>
            {error && (
              <Text size="sm" fw={500} c="var(--text-error)" role="alert">
                {resolveErrorToken(error.token, error.params)}
              </Text>
            )}
            <Group justify="flex-end">
              <Button variant="default" onClick={handleClose} disabled={submitting}>
                {t("verifyEmail.later")}
              </Button>
              <Button onClick={handleSendCode} loading={submitting}>
                {t("verifyEmail.sendCode")}
              </Button>
            </Group>
          </>
        ) : (
          <>
            <Text size="sm" c="var(--text-muted)">
              {t("verifyEmail.codeSent")}
            </Text>

            <Group justify="center">
              <PinInput
                length={CODE_LENGTH}
                type="number"
                oneTimeCode
                value={code}
                onChange={(value) => {
                  setError(null);
                  setCode(value);
                }}
                size="md"
                aria-label={t("verifyEmail.codeInputLabel")}
              />
            </Group>

            {error && (
              <Text size="sm" fw={500} ta="center" c="var(--text-error)" role="alert">
                {resolveErrorToken(error.token, error.params)}
              </Text>
            )}

            <Group justify="space-between">
              <Button variant="subtle" onClick={handleSendCode} disabled={submitting}>
                {t("verifyEmail.resendCode")}
              </Button>
              <Button onClick={handleVerify} loading={submitting}>
                {t("verifyEmail.verify")}
              </Button>
            </Group>
          </>
        )}
      </Stack>
    </Modal>
  );
}

/**
 * Maps an API error to the dialog's error. Exhausted attempts carry the wait until a new code in
 * `details.retry_after_seconds`; without a usable number the generic text is shown, never a raw
 * `{{minutes}}` placeholder.
 */
function toDialogError(err: ApiError): DialogError {
  const retryAfterSeconds = err.details?.retry_after_seconds;
  if (err.code !== ATTEMPTS_EXCEEDED_CODE || typeof retryAfterSeconds !== "number" || retryAfterSeconds < 0) {
    return { token: errorCodeToken(err.code) };
  }

  const minutes = Math.max(1, Math.ceil(retryAfterSeconds / SECONDS_PER_MINUTE));
  return { token: errorCodeToken(`${ATTEMPTS_EXCEEDED_CODE}_retry`), params: { minutes } };
}

/**
 * After verification the backend returns no new access token and the `email_verified` claim in
 * the current one stays false, so fetch a fresh token via /v1/auth/refresh/.
 */
async function syncVerifiedClaim(): Promise<void> {
  try {
    const { accessToken } = await refresh({ throwOnError: true });
    setAccessToken(accessToken);
  } catch {
    // Refresh may fail if the refresh cookie expired; the UI catches up on the next login.
  }
}
