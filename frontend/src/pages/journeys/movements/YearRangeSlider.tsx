import { RangeSlider, UnstyledButton } from "@mantine/core";
import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { clamp } from "../../../components/globe/route";
import type { YearWindow } from "./MovementsControls";
import { yearLabelCenters, type ThumbIndex } from "./yearLabelCenters";

// Thumbs follow the pointer smoothly: the step is a hundredth of a year, not a whole year.
const SMOOTH_STEP = 0.01;
// Track height; Mantine insets the sides by the same amount, so thumbs travel inside those insets, px.
const TRACK_SIZE = 4;
// Year ticks are no closer than this: over half a century the scale would turn into beads, px.
const MIN_TICK_SPACING_PX = 10;
const TICK_STEPS = [1, 2, 5, 10, 20, 50, 100] as const;

const KEYBOARD_YEAR_STEPS: Readonly<Record<string, number>> = {
  ArrowLeft: -1,
  ArrowDown: -1,
  ArrowRight: 1,
  ArrowUp: 1,
};

type SliderPosition = [number, number];

interface YearRangeSliderProps {
  firstYear: number;
  lastYear: number;
  window: YearWindow;
  onWindowChange: (window: YearWindow) => void;
  fromLabel: string;
  toLabel: string;
}

/** The year window under the thumbs: each thumb maps to its nearest year. */
function toWindow([from, to]: SliderPosition): YearWindow {
  return [Math.round(from), Math.round(to)];
}

function isSameWindow(left: YearWindow, right: YearWindow): boolean {
  return left[0] === right[0] && left[1] === right[1];
}

// A year is at most four digits.
const YEAR_DIGITS = 4;

interface EditableYearProps {
  year: number;
  /** Allowed years for this thumb, inclusive: from the scale edge to the neighbouring thumb. */
  min: number;
  max: number;
  label: string;
  onCommit: (year: number) => void;
}

/**
 * The year under a thumb, which can be typed by hand: a click turns it into an input, Enter or
 * leaving the field applies, Escape cancels.
 *
 * A year outside the allowed range snaps to the nearest bound: 200 on a scale starting at 1976
 * becomes 1976. An empty field changes nothing. The field hint names the allowed years.
 */
function EditableYear({ year, min, max, label, onCommit }: EditableYearProps) {
  const [draft, setDraft] = useState<string | null>(null);

  if (draft === null) {
    return (
      <UnstyledButton className="movements-controls__year" aria-label={label} title={label} onClick={() => setDraft(String(year))}>
        {year}
      </UnstyledButton>
    );
  }

  const commit = () => {
    setDraft(null);
    if (draft !== "") {
      onCommit(clamp(Number.parseInt(draft, 10), min, max));
    }
  };

  return (
    <input
      className="movements-controls__year movements-controls__year-input"
      aria-label={label}
      title={`${min}–${max}`}
      inputMode="numeric"
      maxLength={YEAR_DIGITS}
      value={draft}
      // The field appears on a user click, so focusing it is the expected behaviour.
      // eslint-disable-next-line jsx-a11y/no-autofocus
      autoFocus
      onFocus={(event) => event.currentTarget.select()}
      onChange={(event) => setDraft(event.currentTarget.value.replace(/\D/gu, ""))}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.currentTarget.blur();
        } else if (event.key === "Escape") {
          setDraft(null);
        }
      }}
    />
  );
}

/**
 * Year window slider: thumbs move smoothly while the window moves by whole years.
 *
 * While a thumb is dragged the window changes when it passes the midpoint between years, so the
 * map follows immediately. Under each thumb is the year it is currently closest to; it can be
 * typed by hand and the thumb moves. Labels that get close do not overlap (see yearLabelCenters).
 * A released thumb glides to its year. Arrow keys move a thumb by a whole year, not a smooth step.
 */
export function YearRangeSlider({ firstYear, lastYear, window, onWindowChange, fromLabel, toLabel }: YearRangeSliderProps) {
  const [position, setPosition] = useState<SliderPosition>([window[0], window[1]]);
  const [movingThumb, setMovingThumb] = useState<ThumbIndex>(1);
  const [trackedWindow, setTrackedWindow] = useState<YearWindow>(window);
  // The window changed from outside: thumbs move to it; our own rounded position is left alone.
  if (trackedWindow !== window) {
    setTrackedWindow(window);
    if (!isSameWindow(toWindow(position), window)) {
      setPosition([window[0], window[1]]);
    }
  }

  // Slider width in pixels: tick spacing and label positions depend on it.
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [trackWidth, setTrackWidth] = useState(0);
  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    /* v8 ignore next 3 -- the wrapper renders with the slider, the effect runs after mount */
    if (!wrapper) {
      return;
    }

    const measure = () => setTrackWidth(wrapper.getBoundingClientRect().width);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, []);

  const pxPerYear = (trackWidth - 2 * TRACK_SIZE) / (lastYear - firstYear);
  const marks = useMemo(() => {
    const tickStep = TICK_STEPS.find((step) => step * pxPerYear >= MIN_TICK_SPACING_PX) ?? TICK_STEPS.at(-1);
    return Array.from({ length: lastYear - firstYear + 1 }, (_, index) => firstYear + index)
      .filter((year) => tickStep !== undefined && year % tickStep === 0)
      .map((year) => ({ value: year }));
  }, [firstYear, lastYear, pxPerYear]);

  const changePosition = (next: SliderPosition) => {
    // The thumb whose value changed is the one that moved: its label is the one that yields when they get close.
    if (next[0] !== position[0]) {
      setMovingThumb(0);
    } else if (next[1] !== position[1]) {
      setMovingThumb(1);
    }

    setPosition(next);
    const nextWindow = toWindow(next);
    if (!isSameWindow(nextWindow, window)) {
      onWindowChange(nextWindow);
    }
  };

  /** Puts a thumb on a year: within the scale and no further than the neighbouring thumb. */
  const moveThumbTo = (thumbIndex: ThumbIndex, year: number) => {
    const next: SliderPosition = [window[0], window[1]];
    next[thumbIndex] = clamp(year, firstYear, lastYear);
    // Thumbs never jump over each other: hitting the neighbour, a thumb stops level with it.
    if (next[0] > next[1]) {
      next[thumbIndex] = next[1 - thumbIndex];
    }

    changePosition(next);
  };

  const stepByKeyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    const yearStep = KEYBOARD_YEAR_STEPS[event.key];
    const target = event.target;
    if (yearStep === undefined || !(target instanceof HTMLElement) || target.getAttribute("role") !== "slider") {
      return;
    }

    // Intercept before Mantine: its step is a hundredth of a year, the slider would crawl on arrow keys.
    event.preventDefault();
    event.stopPropagation();
    const thumbIndex = target.getAttribute("aria-label") === toLabel ? 1 : 0;
    moveThumbTo(thumbIndex, window[thumbIndex] + yearStep);
  };

  const [fromYear, toYear] = toWindow(position);
  // Thumb center on screen, by the same formula as Mantine: inside the track's side insets.
  const thumbX = (value: number) => TRACK_SIZE + (value - firstYear) * pxPerYear;
  const [fromCenter, toCenter] = yearLabelCenters([thumbX(position[0]), thumbX(position[1])], movingThumb, trackWidth);

  return (
    <div ref={wrapperRef} className="movements-controls__slider" onKeyDownCapture={stepByKeyboard}>
      <RangeSlider
        size={TRACK_SIZE}
        color="var(--movement-line)"
        min={firstYear}
        max={lastYear}
        step={SMOOTH_STEP}
        minRange={0}
        value={position}
        onChange={changePosition}
        onChangeEnd={(end) => {
          const snapped = toWindow(end);
          setPosition([snapped[0], snapped[1]]);
        }}
        marks={marks}
        label={null}
        thumbFromLabel={fromLabel}
        thumbToLabel={toLabel}
      />
      {/* Years under the thumbs move with them; when they meet, the labels do not overlap. */}
      <div className="movements-controls__years">
        <span className="movements-controls__year-group" style={{ left: fromCenter }}>
          <EditableYear year={fromYear} min={firstYear} max={toYear} label={fromLabel} onCommit={(year) => moveThumbTo(0, year)} />
        </span>
        <span className="movements-controls__year-group" style={{ left: toCenter }}>
          <EditableYear year={toYear} min={fromYear} max={lastYear} label={toLabel} onCommit={(year) => moveThumbTo(1, year)} />
        </span>
      </div>
    </div>
  );
}
