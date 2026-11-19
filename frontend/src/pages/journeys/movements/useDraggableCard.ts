import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
} from "react";

import { placeCard, type Box } from "./cardPlacement";
import { readControlsPosition, saveControlsPosition, type CardPosition } from "./controlsPosition";

// Card step per keyboard arrow press, px.
const KEYBOARD_STEP_PX = 24;

const KEYBOARD_STEPS: Readonly<Record<string, readonly [number, number]>> = {
  ArrowLeft: [-KEYBOARD_STEP_PX, 0],
  ArrowRight: [KEYBOARD_STEP_PX, 0],
  ArrowUp: [0, -KEYBOARD_STEP_PX],
  ArrowDown: [0, KEYBOARD_STEP_PX],
};

interface DraggableCard {
  /** Card position; an empty object until measured, then the CSS spot applies. */
  style: CSSProperties;
  /** Tab handlers: drag, arrow keys, double click resets to the default corner. */
  handleProps: {
    onPointerDown: (event: PointerEvent<HTMLElement>) => void;
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
    onDoubleClick: () => void;
  };
}

function boxOf(element: HTMLElement): Box {
  return { left: element.offsetLeft, top: element.offsetTop, width: element.offsetWidth, height: element.offsetHeight };
}

/**
 * Puts the card on the nearest allowed spot to `wanted` (see placeCard); without `wanted`, in the
 * bottom-left corner of the frame. The panel counts only if it lies in the same map area.
 */
function resolvePosition(wanted: CardPosition | null, card: HTMLElement, panel: HTMLElement | null): CardPosition | null {
  const area = card.offsetParent;
  if (!(area instanceof HTMLElement)) {
    return null;
  }

  const overhangTop = Math.max(
    0,
    ...Array.from(card.children, (child) => (child instanceof HTMLElement ? -child.offsetTop : 0)),
  );
  const layout = {
    area: { width: area.clientWidth, height: area.clientHeight },
    card: { width: card.offsetWidth, height: card.offsetHeight },
    overhangTop,
    panel: panel && panel.offsetParent === area ? boxOf(panel) : null,
  };
  // Bottom-left corner: as far down and left as possible; the frame constraints settle it.
  return placeCard(wanted ?? { left: 0, top: layout.area.height }, layout);
}

/**
 * A draggable card over the map area: dragged by the tab, the position is remembered.
 *
 * The card stays in a frame aligned to the navigation panel and never overlaps the panel, neither
 * while dragging nor when the window shrinks. On mobile width the card is in flow
 * (`position: static`) and offsets do not apply.
 */
export function useDraggableCard(
  cardRef: RefObject<HTMLElement | null>,
  panelRef: RefObject<HTMLElement | null>,
): DraggableCard {
  // Where the user put the card; `null` means they did not, so the default spot.
  const [wanted, setWanted] = useState<CardPosition | null>(readControlsPosition);
  const [placed, setPlaced] = useState<CardPosition | null>(null);
  const dragStart = useRef<{ pointerX: number; pointerY: number; origin: CardPosition } | null>(null);

  const place = useCallback(
    (next: CardPosition | null) => {
      const card = cardRef.current;
      /* v8 ignore next 3 -- called from an effect and tab handlers once the card is already mounted */
      if (!card) {
        return null;
      }

      const position = resolvePosition(next, card, panelRef.current);
      setPlaced(position);
      return position;
    },
    [cardRef, panelRef],
  );

  // Recomputed on every map area resize: the panel and edges move with it.
  useLayoutEffect(() => {
    const area = cardRef.current?.offsetParent;
    place(wanted);
    if (!(area instanceof HTMLElement)) {
      return;
    }

    const observer = new ResizeObserver(() => place(wanted));
    observer.observe(area);
    return () => observer.disconnect();
  }, [cardRef, place, wanted]);

  const settle = useCallback(
    (next: CardPosition) => {
      const position = place(next);
      setWanted(position);
      saveControlsPosition(position);
    },
    [place],
  );

  const onPointerDown = useCallback(
    (event: PointerEvent<HTMLElement>) => {
      const card = cardRef.current;
      if (!card || (event.pointerType === "mouse" && event.button !== 0)) {
        return;
      }

      event.preventDefault();
      dragStart.current = {
        pointerX: event.clientX,
        pointerY: event.clientY,
        origin: { left: card.offsetLeft, top: card.offsetTop },
      };
      const handle = event.currentTarget;
      handle.setPointerCapture(event.pointerId);

      // The card follows the pointer by the same offset the pointer travelled from the grab point.
      const target = (pointer: globalThis.PointerEvent): CardPosition | null => {
        const start = dragStart.current;
        return start
          ? {
              left: start.origin.left + pointer.clientX - start.pointerX,
              top: start.origin.top + pointer.clientY - start.pointerY,
            }
          : null;
      };
      const onMove = (moveEvent: globalThis.PointerEvent) => {
        const next = target(moveEvent);
        if (next) {
          place(next);
        }
      };
      const onEnd = (endEvent: globalThis.PointerEvent) => {
        const next = target(endEvent);
        if (next) {
          settle(next);
        }

        dragStart.current = null;
        handle.removeEventListener("pointermove", onMove);
        handle.removeEventListener("pointerup", onEnd);
        handle.removeEventListener("pointercancel", onEnd);
      };
      handle.addEventListener("pointermove", onMove);
      handle.addEventListener("pointerup", onEnd);
      handle.addEventListener("pointercancel", onEnd);
    },
    [cardRef, place, settle],
  );

  const onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      const step = KEYBOARD_STEPS[event.key];
      const card = cardRef.current;
      if (!step || !card) {
        return;
      }

      event.preventDefault();
      settle({ left: card.offsetLeft + step[0], top: card.offsetTop + step[1] });
    },
    [cardRef, settle],
  );

  const onDoubleClick = useCallback(() => {
    setWanted(null);
    saveControlsPosition(null);
  }, []);

  const style: CSSProperties = placed ? { left: placed.left, top: placed.top, bottom: "auto" } : {};
  return { style, handleProps: { onPointerDown, onKeyDown, onDoubleClick } };
}
