import { Button, Group, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { applyApiError, resolveErrorToken, withLocalizedError } from "../../api/errors";
import { EditableValue } from "../../components/EditableValue";
import { useProfileUpdate } from "./useProfileUpdate";
import { validateDisplayName } from "./profileRules";

interface ProfileNameProps {
  displayName: string;
}

interface NameFormValues {
  displayName: string;
}

/**
 * The display name as the page heading, edited in place: the heading turns into a field of the
 * same size. Enter saves, Escape cancels; an unchanged name closes the field without a request.
 */
export function ProfileName({ displayName }: ProfileNameProps) {
  const { t } = useTranslation("profile");
  const [isEditing, setIsEditing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const update = useProfileUpdate();
  const inputRef = useRef<HTMLInputElement>(null);
  const form = useForm<NameFormValues>({
    mode: "controlled",
    initialValues: { displayName },
    validate: { displayName: validateDisplayName },
  });

  // The field replaces the button the user just pressed, so focus has to follow it there.
  useEffect(() => {
    if (isEditing) inputRef.current?.focus();
  }, [isEditing]);

  const startEditing = () => {
    form.setValues({ displayName });
    form.clearErrors();
    setFormError(null);
    setIsEditing(true);
  };

  const cancel = () => {
    setIsEditing(false);
  };

  const handleSubmit = async ({ displayName: rawName }: NameFormValues) => {
    const trimmed = rawName.trim();
    if (trimmed === displayName) {
      setIsEditing(false);
      return;
    }

    setFormError(null);
    try {
      await update.mutateAsync({ body: { displayName: trimmed } });
      setIsEditing(false);
    } catch (error) {
      setFormError(applyApiError(error, form));
    }
  };

  if (!isEditing) {
    return (
      <h1 className="profile-name profile-name__text">
        <EditableValue onClick={startEditing}>{displayName}</EditableValue>
      </h1>
    );
  }

  return (
    <form
      className="profile-name"
      onSubmit={form.onSubmit(handleSubmit)}
      noValidate
    >
      <TextInput
        {...withLocalizedError(form.getInputProps("displayName"))}
        ref={inputRef}
        onKeyDown={(event) => {
          if (event.key === "Escape") cancel();
        }}
        aria-label={t("name.label")}
        classNames={{ input: "profile-name__input" }}
        autoComplete="nickname"
      />
      <Group gap="sm" mt="sm">
        <Button type="submit" loading={update.isPending}>
          {t("name.save")}
        </Button>
        <Button variant="default" onClick={cancel} disabled={update.isPending}>
          {t("name.cancel")}
        </Button>
      </Group>
      {formError !== null && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="xs">
          {resolveErrorToken(formError)}
        </Text>
      )}
    </form>
  );
}
