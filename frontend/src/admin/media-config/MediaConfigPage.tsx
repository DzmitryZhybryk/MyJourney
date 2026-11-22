import { Button, Chip, Group, Loader, Text } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, errorCodeToken, resolveErrorToken } from "../../api/errors";
import {
  getMediaConfigOptions,
  getMediaConfigQueryKey,
  getUploadRulesOptions,
  getUploadRulesQueryKey,
  updateMediaConfigMutation,
  type MediaConfigResponse,
  type MediaConfigSnapshot,
  type SideAxisEnum,
  type UploadRulesResponse,
} from "../../api/sdk";
import { AccountLabel } from "../AccountLabel";
import { useAccountsByIds } from "../useAccountsByIds";
import { RuleNumber } from "./RuleNumber";
import {
  bytesToMegabytes,
  countChangedRules,
  FORMAT_LABELS,
  IMAGE_FORMATS,
  isRuleChanged,
  megabytesToBytes,
  VIDEO_FORMATS,
  type KindRules,
  type MediaFormat,
} from "./mediaConfigRules";
import "./media-config.css";

const CONFLICT_CODE = "config_version_conflict";

type KindKey = keyof MediaConfigSnapshot;

/**
 * Upload rules of every file kind, edited as one draft and saved as one new config version.
 * Someone else's save in between makes the server answer 409: the newer version is loaded and the
 * draft is dropped, with a message saying so.
 */
export function MediaConfigPage() {
  const { t } = useTranslation("admin");
  // No background refetch: a newer version would remount the editor and drop the draft silently.
  // Someone else's save surfaces as 409 on Save, which drops the draft with a message.
  const config = useQuery({ ...getMediaConfigOptions(), staleTime: Infinity });
  // Only for the side axis: which side `minSide` is compared with is fixed in backend code.
  const uploadRules = useQuery(getUploadRulesOptions());
  const [noticeToken, setNoticeToken] = useState<string | null>(null);

  return (
    <section className="media-config-card" aria-labelledby="media-config-title">
      <h1 id="media-config-title" className="media-config-title">
        {t("sections.mediaConfig")}
      </h1>
      {noticeToken !== null && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="sm">
          {resolveErrorToken(noticeToken)}
        </Text>
      )}
      {config.isSuccess && (
        // A new version remounts the editor, so its draft starts from what is saved now.
        <MediaConfigEditor
          key={config.data.version}
          config={config.data}
          uploadRules={uploadRules.data}
          onNotice={setNoticeToken}
        />
      )}
      {config.isError && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="md">
          {t("loadError")}
        </Text>
      )}
      {config.isPending && <Loader className="media-config-card__loader" />}
    </section>
  );
}

interface MediaConfigEditorProps {
  config: MediaConfigResponse;
  uploadRules: UploadRulesResponse | undefined;
  onNotice: (token: string | null) => void;
}

function MediaConfigEditor({ config, uploadRules, onNotice }: MediaConfigEditorProps) {
  const { t } = useTranslation("admin");
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<MediaConfigSnapshot>(config.snapshot);
  const [errorToken, setErrorToken] = useState<string | null>(null);
  const [invalidFields, setInvalidFields] = useState<ReadonlySet<string>>(new Set());
  const update = useMutation(updateMediaConfigMutation());
  const changedCount = countChangedRules(config.snapshot, draft);

  const updateKind = <K extends KindKey>(kind: K, rules: MediaConfigSnapshot[K]) => {
    setDraft((current) => ({ ...current, [kind]: rules }));
  };

  const trackValidity = (field: string, isValid: boolean) => {
    setInvalidFields((current) => {
      if (isValid === !current.has(field)) return current;
      const next = new Set(current);
      if (isValid) next.delete(field);
      else next.add(field);
      return next;
    });
  };

  const save = async () => {
    setErrorToken(null);
    onNotice(null);
    try {
      await update.mutateAsync({ body: { editedVersion: config.version, snapshot: draft } });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getMediaConfigQueryKey() }),
        queryClient.invalidateQueries({ queryKey: getUploadRulesQueryKey() }),
      ]);
    } catch (error) {
      if (error instanceof ApiError && error.code === CONFLICT_CODE) {
        onNotice(errorCodeToken(CONFLICT_CODE));
        await queryClient.invalidateQueries({ queryKey: getMediaConfigQueryKey() });
        return;
      }

      setErrorToken(error instanceof ApiError ? errorCodeToken(error.code) : errorCodeToken("network"));
    }
  };

  return (
    <>
      <VersionFacts config={config} />

      <KindSection
        title={t("kinds.avatar")}
        saved={config.snapshot.avatar}
        draft={draft.avatar}
        formats={IMAGE_FORMATS}
        sideAxis={uploadRules?.avatar.minSideAxis}
        onValidityChange={(field, isValid) => trackValidity(`avatar.${field}`, isValid)}
        onChange={(rules) => updateKind("avatar", rules as MediaConfigSnapshot["avatar"])}
      />
      <KindSection
        title={t("kinds.journeyPhoto")}
        saved={config.snapshot.journeyPhoto}
        draft={draft.journeyPhoto}
        formats={IMAGE_FORMATS}
        sideAxis={uploadRules?.journeyPhoto.minSideAxis}
        onValidityChange={(field, isValid) => trackValidity(`journeyPhoto.${field}`, isValid)}
        onChange={(rules) => updateKind("journeyPhoto", rules as MediaConfigSnapshot["journeyPhoto"])}
      />
      <KindSection
        title={t("kinds.journeyVideo")}
        saved={config.snapshot.journeyVideo}
        draft={draft.journeyVideo}
        formats={VIDEO_FORMATS}
        sideAxis={undefined}
        onValidityChange={(field, isValid) => trackValidity(`journeyVideo.${field}`, isValid)}
        onChange={(rules) => updateKind("journeyVideo", rules as MediaConfigSnapshot["journeyVideo"])}
      />

      {changedCount > 0 && (
        <section className="media-config-savebar" aria-label={t("save.region")}>
          <span className="media-config-savebar__count">{t("save.pending", { count: changedCount })}</span>
          <Group gap="sm">
            <Button variant="default" onClick={() => setDraft(config.snapshot)} disabled={update.isPending}>
              {t("save.discard")}
            </Button>
            <Button onClick={() => void save()} loading={update.isPending} disabled={invalidFields.size > 0}>
              {t("save.submit")}
            </Button>
          </Group>
        </section>
      )}
      {errorToken !== null && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="xs" ta="right">
          {resolveErrorToken(errorToken)}
        </Text>
      )}
    </>
  );
}

interface VersionFactsProps {
  config: MediaConfigResponse;
}

function VersionFacts({ config }: VersionFactsProps) {
  const { t, i18n } = useTranslation("admin");
  const findAccount = useAccountsByIds(config.createdBy === null ? [] : [config.createdBy]);
  const savedAt = new Intl.DateTimeFormat(i18n.language, { dateStyle: "long", timeStyle: "short" }).format(
    new Date(config.createdAt),
  );

  return (
    <dl className="media-config-facts">
      <div className="media-config-fact">
        <dt className="media-config-fact__term">{t("version.number")}</dt>
        <dd className="media-config-fact__value">{config.version}</dd>
      </div>
      <div className="media-config-fact">
        <dt className="media-config-fact__term">{t("version.savedAt")}</dt>
        <dd className="media-config-fact__value">{savedAt}</dd>
      </div>
      <div className="media-config-fact">
        <dt className="media-config-fact__term">{t("version.savedBy")}</dt>
        <dd className="media-config-fact__value">
          {config.createdBy === null ? (
            t("version.initial")
          ) : (
            <AccountLabel accountId={config.createdBy} account={findAccount(config.createdBy)} />
          )}
        </dd>
      </div>
    </dl>
  );
}

interface KindSectionProps {
  title: string;
  saved: KindRules;
  draft: KindRules;
  formats: readonly MediaFormat[];
  sideAxis: SideAxisEnum | undefined;
  onChange: (rules: KindRules) => void;
  onValidityChange: (field: "maxSizeBytes" | "minSide", isValid: boolean) => void;
}

function KindSection({ title, saved, draft, formats, sideAxis, onChange, onValidityChange }: KindSectionProps) {
  const { t } = useTranslation("admin");
  const sizeLabel = t("rules.maxSize");
  const sideLabel = t(sideAxis === undefined ? "rules.minSide.any" : `rules.minSide.${sideAxis}`);

  const changeFormats = (selected: string[]) => {
    // At least one format must stay allowed: the server rejects an empty list.
    if (selected.length === 0) return;
    const allowed = formats.filter((format) => selected.includes(format));
    onChange({ ...draft, formats: allowed } as KindRules);
  };

  return (
    <section className="media-config-kind" aria-label={title}>
      <h2 className="media-config-kind__title">{title}</h2>
      <dl className="media-config-facts">
        <div className="media-config-fact">
          <dt className="media-config-fact__term">{sizeLabel}</dt>
          <dd className="media-config-fact__value">
            <RuleNumber
              label={sizeLabel}
              value={bytesToMegabytes(draft.maxSizeBytes)}
              unit={t("units.megabytes")}
              isInteger={false}
              isChanged={isRuleChanged(saved, draft, "maxSizeBytes")}
              onChange={(megabytes) => onChange({ ...draft, maxSizeBytes: megabytesToBytes(megabytes) })}
              onValidityChange={(isValid) => onValidityChange("maxSizeBytes", isValid)}
            />
          </dd>
        </div>
        <div className="media-config-fact">
          <dt className="media-config-fact__term">{t("rules.formats")}</dt>
          <dd className="media-config-fact__value">
            <Chip.Group multiple value={[...draft.formats]} onChange={changeFormats}>
              <Group
                gap={6}
                className={
                  isRuleChanged(saved, draft, "formats") ? "rule-formats rule-formats--changed" : "rule-formats"
                }
              >
                {formats.map((format) => (
                  <Chip key={format} value={format} size="xs" variant="outline">
                    {FORMAT_LABELS[format]}
                  </Chip>
                ))}
              </Group>
            </Chip.Group>
          </dd>
        </div>
        {"minSide" in draft && (
          <div className="media-config-fact">
            <dt className="media-config-fact__term">{sideLabel}</dt>
            <dd className="media-config-fact__value">
              <RuleNumber
                label={sideLabel}
                value={draft.minSide}
                unit={t("units.pixels")}
                isInteger
                isChanged={isRuleChanged(saved, draft, "minSide")}
                onChange={(minSide) => onChange({ ...draft, minSide })}
                onValidityChange={(isValid) => onValidityChange("minSide", isValid)}
              />
            </dd>
          </div>
        )}
      </dl>
    </section>
  );
}
