import { Button, Input, Select, Switch, TextInput } from "@mantine/core";
import { useDebouncedCallback } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { getAccountOptionsOptions } from "../../api/sdk";
import { ROLE_LABEL_KEYS } from "./accountLabels";
import {
  DISPLAY_NAME_MAX_LENGTH,
  EMAIL_MAX_LENGTH,
  NO_FILTERS,
  type AccountsFilters as Filters,
  type ConsentFilter,
} from "./accountsSearch";

const DEBOUNCE_MS = 300;

interface AccountsFiltersProps {
  filters: Filters;
  hasFilters: boolean;
  onChange: (patch: Partial<Filters>) => void;
}

/** The filter bar of the account list: text filters apply after a pause in typing, the rest at once. */
export function AccountsFilters({ filters, hasFilters, onChange }: AccountsFiltersProps) {
  const { t } = useTranslation("admin");
  // Roles and plans never change while the screen is open.
  const options = useQuery({ ...getAccountOptionsOptions(), staleTime: Infinity });
  const roleOptions = (options.data?.roles ?? []).map((role) => ({ value: role, label: t(ROLE_LABEL_KEYS[role]) }));

  return (
    <search className="accounts-filters" aria-label={t("accounts.filters.region")}>
      <DebouncedTextFilter
        label={t("accounts.filters.email")}
        placeholder={t("accounts.filters.emailPlaceholder")}
        maxLength={EMAIL_MAX_LENGTH}
        className="accounts-filters__text--email"
        committed={filters.email}
        onCommit={(email) => onChange({ email })}
      />
      <DebouncedTextFilter
        label={t("accounts.filters.name")}
        placeholder={t("accounts.filters.namePlaceholder")}
        maxLength={DISPLAY_NAME_MAX_LENGTH}
        className="accounts-filters__text--name"
        committed={filters.displayName}
        onCommit={(displayName) => onChange({ displayName })}
      />
      <Select
        label={t("accounts.filters.role")}
        placeholder={t("accounts.filters.anyRole")}
        data={roleOptions}
        value={filters.role || null}
        onChange={(role) => onChange({ role: role ?? NO_FILTERS.role })}
        disabled={!options.isSuccess}
        clearable
        classNames={{ root: "accounts-filters__role" }}
      />
      <Select
        label={t("accounts.filters.consent")}
        placeholder={t("accounts.filters.consentAny")}
        data={[
          { value: "yes", label: t("accounts.filters.consentYes") },
          { value: "no", label: t("accounts.filters.consentNo") },
        ]}
        value={filters.consent === "any" ? null : filters.consent}
        onChange={(consent) => onChange({ consent: (consent ?? NO_FILTERS.consent) as ConsentFilter })}
        clearable
        classNames={{ root: "accounts-filters__consent" }}
      />
      {/* Label above like every other filter; the switch sits on the inputs' line instead of beside its text. */}
      <Input.Wrapper
        label={t("accounts.filters.includeDeleted")}
        id="accounts-include-deleted"
        classNames={{ root: "accounts-filters__deleted" }}
      >
        {/* Size "xl" is the one whose track matches the height of the default ("sm") inputs beside it. */}
        <Switch
          id="accounts-include-deleted"
          size="xl"
          checked={filters.includeDeleted}
          onChange={(event) => onChange({ includeDeleted: event.currentTarget.checked })}
        />
      </Input.Wrapper>
      {hasFilters && (
        <Button variant="default" onClick={() => onChange(NO_FILTERS)}>
          {t("accounts.filters.reset")}
        </Button>
      )}
    </search>
  );
}

interface DebouncedTextFilterProps {
  label: string;
  placeholder: string;
  maxLength: number;
  className: string;
  committed: string;
  onCommit: (value: string) => void;
}

function DebouncedTextFilter({
  label,
  placeholder,
  maxLength,
  className,
  committed,
  onCommit,
}: DebouncedTextFilterProps) {
  const [value, setValue] = useState(committed);
  const [seenCommitted, setSeenCommitted] = useState(committed);
  const commit = useDebouncedCallback((next: string) => onCommit(next.trim()), DEBOUNCE_MS);

  // The URL can change without typing (reset, back button): the field follows it, unless it already
  // shows that value with only surrounding spaces of difference.
  if (committed !== seenCommitted) {
    setSeenCommitted(committed);
    if (committed !== value.trim()) setValue(committed);
  }

  return (
    <TextInput
      label={label}
      placeholder={placeholder}
      maxLength={maxLength}
      value={value}
      onChange={(event) => {
        setValue(event.currentTarget.value);
        commit(event.currentTarget.value);
      }}
      classNames={{ root: `accounts-filters__text ${className}` }}
      style={{ "--filter-chars": String(value.length) }}
    />
  );
}
