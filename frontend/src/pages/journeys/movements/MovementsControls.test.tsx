import { fireEvent } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { stubOffsetLayout } from "../../../test/layout";
import { renderWithProviders, screen } from "../../../test/render";
import { MovementsControls } from "./MovementsControls";

const POSITION_KEY = "journeys-movements-controls-position";

// The map area is 1200x800, the navigation panel is on the left: (32, 100), 260x400, bottom at 500.
// The card is 260x160; the tab is inside it (offsetTop >= 0), nothing sticks out above the card.
const STAGE = { width: 1200, height: 800 };
const CARD = { width: 260, height: 160 };
const DEFAULT_POSITION = { left: 32, top: STAGE.height - 32 - CARD.height };

/** The card in the map area beside the panel, as the movements screen places it. */
function ControlsOnStage() {
  const panelRef = useRef<HTMLDivElement>(null);
  return (
    <div className="test-stage">
      <div ref={panelRef} className="test-panel" />
      <MovementsControls
        firstYear={2019}
        lastYear={2022}
        window={[2019, 2022]}
        onWindowChange={vi.fn()}
        transportTypes={["land", "air", "water"]}
        onTransportTypesChange={vi.fn()}
        panelRef={panelRef}
      />
    </div>
  );
}

function card(): HTMLElement {
  const element = screen.getByRole("region", { name: "Movements filters" });
  return element;
}

function cardPosition(): { left: number; top: number } {
  return { left: Number.parseFloat(card().style.left), top: Number.parseFloat(card().style.top) };
}

function dragHandle(from: { x: number; y: number }, to: { x: number; y: number }): void {
  const handle = screen.getByRole("button", { name: /Drag to move/u });
  fireEvent.pointerDown(handle, { pointerId: 1, pointerType: "mouse", button: 0, clientX: from.x, clientY: from.y });
  fireEvent.pointerMove(handle, { pointerId: 1, pointerType: "mouse", clientX: to.x, clientY: to.y });
  fireEvent.pointerUp(handle, { pointerId: 1, pointerType: "mouse", clientX: to.x, clientY: to.y });
}

describe("MovementsControls: перетаскиваемая карточка", () => {
  beforeEach(() => {
    localStorage.clear();
    stubOffsetLayout({
      "test-stage": STAGE,
      "test-panel": { left: 32, top: 100, width: 260, height: 400, parentClass: "test-stage" },
      "movements-controls": { ...CARD, parentClass: "test-stage" },
      "movements-controls__handle": { left: 218, top: 4, width: 32, height: 16, parentClass: "movements-controls" },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("стоит в левом нижнем углу рамки: левый край — как у панели, снизу — тот же отступ", () => {
    renderWithProviders(<ControlsOnStage />);

    expect(cardPosition()).toEqual(DEFAULT_POSITION);
  });

  it("едет за ушком и запоминает, куда его поставили", () => {
    renderWithProviders(<ControlsOnStage />);

    dragHandle({ x: 100, y: 700 }, { x: 600, y: 400 });

    const expected = { left: DEFAULT_POSITION.left + 500, top: DEFAULT_POSITION.top - 300 };
    expect(cardPosition()).toEqual(expected);
    expect(JSON.parse(localStorage.getItem(POSITION_KEY) ?? "null")).toEqual(expected);
  });

  it("на панель не заезжает — встаёт рядом с ней", () => {
    renderWithProviders(<ControlsOnStage />);

    // Drag up, right onto the panel: the nearest free spot is under it, with a gap.
    dragHandle({ x: 100, y: 700 }, { x: 100, y: 500 });

    expect(cardPosition()).toEqual({ left: DEFAULT_POSITION.left, top: 100 + 400 + 16 });
  });

  it("сдвигается стрелками с ушка", () => {
    renderWithProviders(<ControlsOnStage />);

    fireEvent.keyDown(screen.getByRole("button", { name: /Drag to move/u }), { key: "ArrowRight" });

    expect(cardPosition()).toEqual({ left: DEFAULT_POSITION.left + 24, top: DEFAULT_POSITION.top });
  });

  it("открывается там, где её оставили, а двойной клик по ушку возвращает в угол и забывает место", () => {
    localStorage.setItem(POSITION_KEY, JSON.stringify({ left: 600, top: 300 }));
    renderWithProviders(<ControlsOnStage />);
    expect(cardPosition()).toEqual({ left: 600, top: 300 });

    fireEvent.doubleClick(screen.getByRole("button", { name: /Drag to move/u }));

    expect(cardPosition()).toEqual(DEFAULT_POSITION);
    expect(localStorage.getItem(POSITION_KEY)).toBeNull();
  });

  it("правая и средняя кнопки мыши карточку не таскают", () => {
    renderWithProviders(<ControlsOnStage />);
    const handle = screen.getByRole("button", { name: /Drag to move/u });

    fireEvent.pointerDown(handle, { pointerId: 1, pointerType: "mouse", button: 2, clientX: 100, clientY: 700 });
    fireEvent.pointerMove(handle, { pointerId: 1, pointerType: "mouse", clientX: 600, clientY: 400 });

    expect(cardPosition()).toEqual(DEFAULT_POSITION);
  });
});
