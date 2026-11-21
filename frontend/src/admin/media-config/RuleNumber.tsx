import { NumberInput, Text } from "@mantine/core";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { EditableValue } from "../../components/EditableValue";

interface RuleNumberProps {
  label: string;
  value: number;
  unit: string;
  /** Whole numbers only (pixels); sizes in megabytes allow one decimal. */
  isInteger: boolean;
  isChanged: boolean;
  onChange: (value: number) => void;
}

/**
 * A number edited in place: the value turns into a field of the same size. Every valid keystroke goes
 * to the draft at once, so Save is reachable without leaving the field; Enter or leaving it closes the
 * field, Escape restores the value it opened with. Nothing is sent until the whole config is saved.
 */
export function RuleNumber({ label, value, unit, isInteger, isChanged, onChange }: RuleNumberProps) {
  const { t } = useTranslation("admin");
  const [isEditing, setIsEditing] = useState(false);
  const [input, setInput] = useState<string | number>(value);
  const [initialValue, setInitialValue] = useState(value);
  const [hasError, setHasError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const valueRef = useRef<HTMLButtonElement>(null);
  const hasEditedRef = useRef(false);

  // The field and the value replace each other, so focus follows whichever is shown; the first
  // render must not steal focus.
  useEffect(() => {
    if (isEditing) {
      hasEditedRef.current = true;
      inputRef.current?.select();
    } else if (hasEditedRef.current) {
      valueRef.current?.focus();
    }
  }, [isEditing]);

  const startEditing = () => {
    setInput(value);
    setInitialValue(value);
    setHasError(false);
    setIsEditing(true);
  };

  const changeInput = (next: string | number) => {
    setInput(next);
    const parsed = parsePositive(next);
    if (parsed !== null) {
      setHasError(false);
      onChange(parsed);
    }
  };

  const close = () => {
    if (parsePositive(input) === null) {
      setHasError(true);
      return;
    }

    setIsEditing(false);
  };

  const cancel = () => {
    onChange(initialValue);
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <EditableValue
        ref={valueRef}
        onClick={startEditing}
        aria-label={`${label}: ${value} ${unit}`}
        className={isChanged ? "rule-value rule-value--changed" : "rule-value"}
      >
        {value} {unit}
      </EditableValue>
    );
  }

  return (
    <div className="rule-number">
      <NumberInput
        ref={inputRef}
        value={input}
        onChange={changeInput}
        onBlur={close}
        onKeyDown={(event) => {
          if (event.key === "Enter") close();
          if (event.key === "Escape") cancel();
        }}
        aria-label={label}
        min={0}
        decimalScale={isInteger ? 0 : 1}
        allowNegative={false}
        hideControls
        rightSection={<span className="rule-number__unit">{unit}</span>}
        classNames={{ input: "rule-number__input" }}
      />
      {hasError && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt={4}>
          {t("rules.positiveNumber")}
        </Text>
      )}
    </div>
  );
}

/** The field's value as a number greater than zero, or `null` while it is empty or not positive. */
function parsePositive(input: string | number): number | null {
  const parsed = typeof input === "number" ? input : Number.parseFloat(input);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
