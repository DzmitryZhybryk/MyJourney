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
  const valueRef = useRef<HTMLButtonElement>(null);
  const hasEditedRef = useRef(false);
  const form = useForm<NameFormValues>({
    mode: "controlled",
    initialValues: { displayName },
    validate: { displayName: validateDisplayName },
  });

  // The field and the value replace each other, so focus has to follow whichever one is shown;
  // otherwise closing the field drops focus to <body>. The first render must not steal focus.
  useEffect(() => {
    if (isEditing) {
      hasEditedRef.current = true;
      inputRef.current?.focus();
    } else if (hasEditedRef.current) {
      valueRef.current?.focus();
    }
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
        <EditableValue ref={valueRef} onClick={startEditing}>{displayName}</EditableValue>
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
          // A request in flight keeps the form: closing it would hide the error of a failed save.
          if (event.key === "Escape" && !update.isPending) cancel();
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
