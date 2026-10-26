import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef } from "react";
import { describe, expect, test } from "vitest";
import { useAtraparFoco } from "./useAtraparFoco";

// Un solo foco atrapado para el sidebar en capa y el dialogo «Cambios sin guardar».
function Caja() {
  const caja = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(caja);
  return (
    <>
      <button type="button">fuera antes</button>
      <div ref={caja} tabIndex={-1} data-testid="caja" onKeyDown={atrapar}>
        <a href="#/uno">Uno</a>
        <button type="button" disabled>
          Deshabilitado
        </button>
        <div style={{ display: "none" }}>
          <a href="#/oculto">Oculto</a>
        </div>
        <button type="button">Dos</button>
        <a href="#/tres">Tres</a>
      </div>
      <button type="button">fuera despues</button>
    </>
  );
}

describe("useAtraparFoco", () => {
  test("Tab desde el último vuelve al primero y Mayús+Tab desde el primero va al último", async () => {
    const u = userEvent.setup();
    render(<Caja />);
    screen.getByRole("link", { name: "Tres" }).focus();
    await u.tab();
    expect(screen.getByRole("link", { name: "Uno" })).toHaveFocus();
    await u.tab({ shift: true });
    expect(screen.getByRole("link", { name: "Tres" })).toHaveFocus();
  });

  test("en medio, Tab sigue el orden natural y salta lo deshabilitado y lo oculto", async () => {
    const u = userEvent.setup();
    render(<Caja />);
    screen.getByRole("link", { name: "Uno" }).focus();
    await u.tab();
    expect(screen.getByRole("button", { name: "Dos" })).toHaveFocus();
  });

  test("Mayús+Tab con el foco en la propia caja va al último", async () => {
    const u = userEvent.setup();
    render(<Caja />);
    screen.getByTestId("caja").focus();
    await u.tab({ shift: true });
    expect(screen.getByRole("link", { name: "Tres" })).toHaveFocus();
  });
});
