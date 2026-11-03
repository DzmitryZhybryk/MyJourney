import { ActionIcon, Menu, Select, Text, UnstyledButton, VisuallyHidden } from "@mantine/core";
import { lazy, Suspense, useEffect, useRef, useState, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { cityLabel, type CityNameLookup } from "../../../api/cityNames";
import { resolveErrorToken } from "../../../api/errors";
import { zTransportTypeEnum, type CitySearchItem, type JourneyCity, type JourneyFeedEntry } from "../../../api/sdk";
import { CityAutocomplete } from "../../../components/CityAutocomplete";
import { SoonBadge } from "../../../components/SoonBadge";
import { SwapVerticalIcon } from "../../../components/SwapVerticalIcon";
import { TransportLabel } from "../../../components/TransportLabel";
import type { JourneyFormValues } from "../journeyFormRules";
import { journeyYearOptions } from "../journeyYears";
import { InlineField } from "./InlineField";
import { ALL_JOURNEYS_PATH } from "./journeyCardPath";
import { RouteDistancePreview } from "./RouteDistancePreview";
import { useDistanceFormat } from "./useDistanceFormat";
import { useJourneyCardSave } from "./useJourneyCardSave";

// Lazy: the dialog (and Mantine Modal) is needed only by someone deleting, and the feed page sits
// near its bundle budget (web/performance.md).
const JourneyDeleteDialog = lazy(() =>
  import("./JourneyDeleteDialog").then((module) => ({ default: module.JourneyDeleteDialog })),
);

// Fields shown under their own control; any other field error is reported for the whole card.
const CITY_FIELDS: ReadonlySet<string> = new Set(["origin", "destination"]);

type CityField = "origin" | "destination";
type EditedField = CityField | "year";

interface JourneyCardProps {
  /** The journey as the feed has it; its distance is the server's for its own pair. */
  journey: JourneyFeedEntry;
  nameOf: CityNameLookup;
}

/**
 * Journey card in place of the feed column (route /journeys/all/<id>): route, transport, year and
 * distance, then the photo report and impressions, which are not built yet.
 *
 * Every value is edited in place and saved at once (`useJourneyCardSave`); "Saved · Undo" in the
 * header reports the save. A city or the year turns into its field on click: picking saves, Esc or
 * leaving the field drops the edit. Swap saves both cities in one go: one city at a time could not
 * turn A -> B into B -> A, since each step would be "the same city twice". Deleting sits in the
 * "⋯" menu behind a confirmation and replaces the card's address with the list, so Back does not
 * lead to a journey that is gone. Focus moves to the title when a journey opens, and back to the
 * value after an edit ends from the keyboard. While a save runs the controls are `aria-disabled`,
 * not `disabled`: a disabled button drops the focus it holds to the body.
 */
export function JourneyCard({ journey, nameOf }: JourneyCardProps) {
  const { t } = useTranslation("journeys");
  const { t: tCommon } = useTranslation("common");
  const navigate = useNavigate();
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  // Mounted on the first open and kept, so closing plays the dialog's own transition.
  const [isDeleteLoaded, setIsDeleteLoaded] = useState(false);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const valueRefs = useRef<Partial<Record<EditedField, HTMLButtonElement | null>>>({});
  const focusBack = useRef<EditedField | null>(null);
  // Undo leaves with its status line: the focus it held goes to the title, not the body.
  const focusTitleAfterUndo = useRef(false);
  const distanceFormat = useDistanceFormat();
  const unknownLabel = tCommon("map.unknownCity");
  const toSearchItem = (city: JourneyCity): CitySearchItem => ({
    ...city,
    name: cityLabel(nameOf(city.cityId), unknownLabel) ?? "",
    population: null,
  });
  // Read once: afterwards the card holds what it saved, while the feed catches up in the background.
  const [initialValues] = useState<JourneyFormValues>(() => ({
    origin: toSearchItem(journey.origin),
    destination: toSearchItem(journey.destination),
    transport: journey.transportType,
    year: String(journey.traveledYear),
  }));
  // The current year is read once when the card appears: reading the clock every render is impure.
  const [yearOptions] = useState(() => journeyYearOptions(new Date().getFullYear()));
  const { form, isSaving, status, errorToken, commit, undo } = useJourneyCardSave(journey.journeyId, initialValues);
  const values = form.getValues();
  const [edited, setEdited] = useState<EditedField | null>(null);
  // The city field's own value while it is edited: `CityAutocomplete` empties it on typing.
  const [cityDraft, setCityDraft] = useState<CitySearchItem | null>(null);

  // A just picked city may not be in the names lookup yet; its picked name stands in.
  const labelOf = (city: CitySearchItem | null) =>
    city ? (cityLabel(nameOf(city.cityId), unknownLabel) ?? (city.name || "…")) : "…";
  const cityErrorToken = form.errors.origin ?? form.errors.destination;
  const cardErrorToken =
    errorToken ?? Object.entries(form.errors).find(([field, error]) => !CITY_FIELDS.has(field) && error)?.[1];
  const isEditingCity = edited === "origin" || edited === "destination";

  useEffect(() => {
    titleRef.current?.focus();
  }, [journey.journeyId]);

  useEffect(() => {
    if (edited === null && focusBack.current !== null) {
      valueRefs.current[focusBack.current]?.focus();
      focusBack.current = null;
    }
  }, [edited]);

  useEffect(() => {
    if (status !== "saved" && focusTitleAfterUndo.current) {
      titleRef.current?.focus();
      focusTitleAfterUndo.current = false;
    }
  }, [status]);

  const startEdit = (field: EditedField) => {
    if (isSaving) {
      return;
    }
    if (field !== "year") {
      const city = values[field];
      setCityDraft(city && { ...city, name: labelOf(city) });
    }
    setEdited(field);
  };

  // Focus goes back to the value only if it is still in the field (Esc, a pick from the list), not
  // when the user has moved on elsewhere.
  const endEdit = () => {
    focusBack.current = document.activeElement?.closest(".journey-card__editor") ? edited : null;
    setEdited(null);
  };

  const handleCityChange = (field: CityField) => (city: CitySearchItem | null) => {
    setCityDraft(city);
    if (city) {
      endEdit();
      void commit({ [field]: city });
    }
  };

  const handleUndo = (event: MouseEvent<HTMLButtonElement>) => {
    if (isSaving) {
      return;
    }
    focusTitleAfterUndo.current = document.activeElement === event.currentTarget;
    void undo();
  };

  const valueButton = (field: EditedField, label: string, className = "journey-card__value") => (
    <UnstyledButton
      ref={(element) => {
        valueRefs.current[field] = element;
      }}
      className={className}
      onClick={() => startEdit(field)}
      aria-disabled={isSaving}
    >
      {label}
    </UnstyledButton>
  );

  const cityValue = (field: CityField) =>
    edited === field ? (
      <InlineField className="journey-card__editor journey-card__editor--city" onCancel={endEdit} onLeave={endEdit}>
        <CityAutocomplete
          label={t(`addJourney.${field}.label`)}
          isLabelHidden
          placeholder={t(`addJourney.${field}.placeholder`)}
          value={cityDraft}
          onChange={handleCityChange(field)}
        />
      </InlineField>
    ) : (
      valueButton(field, labelOf(values[field]), "journey-card__value journey-card__city")
    );

  const route = (
    <>
      {cityValue("origin")}
      <span className="journey-card__arrow" aria-hidden="true">
        →
      </span>
      <VisuallyHidden>{` ${t("all.routeTo")} `}</VisuallyHidden>
      {cityValue("destination")}
    </>
  );

  return (
    <section className="journey-card journeys-card" aria-labelledby="journey-card-title" aria-busy={isSaving}>
      <div className="journey-card__top">
        <Link to={ALL_JOURNEYS_PATH} className="journey-card__back">
          <span aria-hidden="true">←</span> {t("card.back")}
        </Link>
        <output className="journey-card__status" aria-live="polite">
          {status === "saved" && (
            <>
              {t("card.saved")}
              <UnstyledButton className="journey-card__undo" onClick={handleUndo} aria-disabled={isSaving}>
                {t("card.undo")}
              </UnstyledButton>
            </>
          )}
          {status === "undone" && t("card.undone")}
        </output>
        <Menu position="bottom-end" shadow="md" radius="md">
          <Menu.Target>
            <ActionIcon variant="subtle" color="gray" size="lg" radius="md" aria-label={t("card.menu")}>
              <span aria-hidden="true" className="journey-card__menu-icon">
                ⋯
              </span>
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              color="red"
              onClick={() => {
                setIsDeleteLoaded(true);
                setIsDeleteOpen(true);
              }}
            >
              {t("card.deleteJourney")}
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </div>
      {isDeleteLoaded && (
        <Suspense fallback={null}>
          <JourneyDeleteDialog
            opened={isDeleteOpen}
            onClose={() => setIsDeleteOpen(false)}
            journeyId={journey.journeyId}
            route={`${labelOf(values.origin)} → ${labelOf(values.destination)}`}
            onDeleted={() => void navigate(ALL_JOURNEYS_PATH, { replace: true })}
          />
        </Suspense>
      )}

      <div className="journey-card__route">
        {/* A heading holds phrasing content only, so a city field (a block with its list) is shown
            in a plain row while it is edited. */}
        {isEditingCity ? (
          <div id="journey-card-title" className="journey-card__title">
            {route}
          </div>
        ) : (
          <h1 id="journey-card-title" ref={titleRef} tabIndex={-1} className="journey-card__title">
            {route}
          </h1>
        )}
        {!isEditingCity && (
          <UnstyledButton
            className="journey-card__swap"
            aria-label={t("addJourney.swap")}
            title={t("addJourney.swap")}
            onClick={() => void commit({ origin: values.destination, destination: values.origin })}
            aria-disabled={isSaving}
          >
            <SwapVerticalIcon />
          </UnstyledButton>
        )}
      </div>
      {cityErrorToken && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" className="journey-card__route-error">
          {resolveErrorToken(cityErrorToken)}
        </Text>
      )}

      <dl className="journey-card__facts">
        <div className="journey-card__fact">
          <dt>{t("card.transport")}</dt>
          <dd>
            <Menu position="bottom-start" shadow="md" radius="md" disabled={isSaving}>
              <Menu.Target>
                <UnstyledButton className="journey-card__value" aria-disabled={isSaving}>
                  {values.transport && <TransportLabel type={values.transport} />}
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                {zTransportTypeEnum.options.map((type) => (
                  <Menu.Item
                    key={type}
                    onClick={() => void commit({ transport: type })}
                    fw={type === values.transport ? 700 : 400}
                  >
                    <TransportLabel type={type} />
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
          </dd>
        </div>
        <div className="journey-card__fact">
          <dt>{t("card.year")}</dt>
          <dd>
            {edited === "year" ? (
              <InlineField className="journey-card__editor journey-card__editor--year" onCancel={endEdit} onLeave={endEdit}>
                <Select
                  aria-label={t("card.year")}
                  data={yearOptions}
                  value={values.year}
                  onChange={(year) => {
                    if (year) {
                      endEdit();
                      void commit({ year });
                    }
                  }}
                  searchable
                  allowDeselect={false}
                  defaultDropdownOpened
                  size="sm"
                  radius="md"
                />
              </InlineField>
            ) : (
              valueButton("year", values.year ?? "")
            )}
          </dd>
        </div>
        <div className="journey-card__fact">
          <dt>{t("card.distance")}</dt>
          <dd>
            <RouteDistancePreview
              journey={journey}
              origin={values.origin}
              destination={values.destination}
              distanceFormat={distanceFormat}
            />
          </dd>
        </div>
      </dl>

      {cardErrorToken && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert">
          {resolveErrorToken(cardErrorToken)}
        </Text>
      )}

      <section className="journey-card__section" aria-labelledby="journey-card-photos">
        <h2 id="journey-card-photos" className="journey-card__heading">
          {t("card.photos")} <SoonBadge />
        </h2>
        <Text size="sm" c="var(--text-muted)">
          {t("card.photosSoon")}
        </Text>
      </section>

      <section className="journey-card__section" aria-labelledby="journey-card-impressions">
        <h2 id="journey-card-impressions" className="journey-card__heading">
          {t("card.impressions")} <SoonBadge />
        </h2>
        <Text size="sm" c="var(--text-muted)">
          {t("card.impressionsSoon")}
        </Text>
      </section>
    </section>
  );
}
