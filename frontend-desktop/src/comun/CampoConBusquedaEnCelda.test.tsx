import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { CampoConBusqueda } from "./CampoConBusqueda";
import type { GrupoDeResultados } from "./logicaBusqueda";

// AC1: lo que CampoConBusqueda necesita para vivir dentro de una celda de tabla: la etiqueta no se ve (el nombre accesible
// sí) y Esc con la lista cerrada puede dejar lo elegido en paz.

const VACIO = { titulo: "¿No lo encuentra?", pasos: "Pruebe con otra palabra." };
const GRUPOS: GrupoDeResultados<string>[] = [
  {
    rotulo: "Insumos del catálogo",
    hayMas: false,
    opciones: [{ clave: "i:1", principal: "Cemento ficticio", secundaria: ["MAT-1"], valor: "MAT-1" }],
  },
];

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  vi.stubGlobal("jest", { advanceTimersByTime: vi.advanceTimersByTime.bind(vi) });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function EnTabla({ escLimpia }: { escLimpia?: boolean }) {
  const [texto, setTexto] = useState("");
  return (
    <CampoConBusqueda<string>
      id="celda"
      etiqueta="Descripción, fila 1"
      etiquetaOculta
      texto={texto}
      alCambiarTexto={setTexto}
      buscar={() => Promise.resolve(GRUPOS)}
      alElegir={(o) => setTexto(o.valor)}
      escLimpia={escLimpia}
      vacio={VACIO}
      alExpirar={() => {}}
    />
  );
}

async function elegirLaOpcion() {
  const u = userEvent.setup({ delay: null, advanceTimers: vi.advanceTimersByTime.bind(vi) });
  const entrada = screen.getByRole("combobox", { name: "Descripción, fila 1" });
  await u.type(entrada, "cem");
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
  await u.keyboard("{ArrowDown}{Enter}");
  return { u, entrada };
}

describe("CampoConBusqueda: en una celda", () => {
  test("etiquetaOculta deja el nombre accesible y quita la etiqueta de la vista", () => {
    render(<EnTabla />);
    const entrada = screen.getByRole("combobox", { name: "Descripción, fila 1" });
    expect(document.querySelector(`label[for="${entrada.id}"]`)).toHaveClass("cds--visually-hidden");
  });

  test("con escLimpia en falso, Esc con la lista cerrada no borra lo elegido", async () => {
    render(<EnTabla escLimpia={false} />);
    const { u, entrada } = await elegirLaOpcion();
    expect(entrada).toHaveValue("MAT-1");
    await u.keyboard("{Escape}");
    expect(entrada).toHaveValue("MAT-1");
  });

  test("por omisión Esc con la lista cerrada sigue borrando lo elegido", async () => {
    render(<EnTabla />);
    const { u, entrada } = await elegirLaOpcion();
    expect(entrada).toHaveValue("MAT-1");
    await u.keyboard("{Escape}");
    expect(entrada).toHaveValue("");
  });
});
