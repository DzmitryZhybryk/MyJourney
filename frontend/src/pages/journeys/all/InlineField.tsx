import { useEffect, useRef, type ReactNode } from "react";

/**
 * Whether the field's dropdown with options is shown.
 *
 * Mantine marks an open list with `data-expanded` (and `aria-expanded` not on every field), but
 * city suggestions "open" empty on focus too. So the list counts as shown only if it has options.
 */
function isListShown(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement) || target.dataset.expanded === undefined) {
    return false;
  }

  const listId = target.getAttribute("aria-controls");
  return Boolean(listId && document.getElementById(listId)?.querySelector('[role="option"]'));
}

interface InlineFieldProps {
  className: string;
  /** Esc with no list open. */
  onCancel: () => void;
  /** Focus went somewhere outside the field. */
  onLeave: () => void;
  children: ReactNode;
}

/**
 * A journey card value while it is edited in place: the input inside takes focus when it appears.
 * Esc closes the field's open list first (city suggestions, years) and only then the edit; leaving
 * the field ends the edit too. Picking from a list keeps focus in the input, so it is not a leave.
 */
export function InlineField({ className, onCancel, onLeave, children }: InlineFieldProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    rootRef.current?.querySelector<HTMLElement>("input:not([type='hidden'])")?.focus();
  }, []);

  // A native listener: Mantine's React handlers run later, so look at the list itself, not at
  // `defaultPrevented`.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) {
      return;
    }

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && !isListShown(event.target)) {
        onCancel();
      }
    };
    root.addEventListener("keydown", handleKeyDown);

    return () => root.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  return (
    <div
      ref={rootRef}
      className={className}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          onLeave();
        }
      }}
    >
      {children}
    </div>
  );
}
