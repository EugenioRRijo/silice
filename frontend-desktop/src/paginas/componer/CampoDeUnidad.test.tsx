import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { CampoDeUnidad } from "./CampoDeUnidad";
import { TablaInsumos } from "./TablaInsumos";
import { RUTA_DE_UNIDADES } from "./unidades";

// AC4 (pedido de Eugenio del 2026-10-21): «Unidad» sugiere las unidades que ya usa el catálogo de la carpeta
// (`GET /v1/consulta/unidades`) y sigue admitiendo una propia. Datos ficticios con la forma de `api/rutas/consulta.py`.

const UNIDADES = [
  { unidad: "m3", usos: 12, grafias: ["m3", "m³"] },
  { unidad: "m2", usos: 9, grafias: ["m2"] },
  { unidad: "saco", usos: 4, grafias: ["saco"] },
];

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

let estado: number;
const fetchFalso = vi.fn<typeof fetch>();
beforeEach(() => {
  estado = 200;
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  fetchFalso.mockImplementation(async (ruta) =>
    String(ruta) === RUTA_DE_UNIDADES
      ? json(estado === 200 ? { unidades: UNIDADES } : { detalle: "Sin sesión." }, estado)
      : json({ detalle: "No hay." }, 404),
  );
});
afterEach(() => vi.unstubAllGlobals());

function Campo({ alExpirar = vi.fn() }: { alExpirar?: () => void }) {
  const [texto, setTexto] = useState("");
  return (
    <>
      <CampoDeUnidad id="unidad" etiqueta="Unidad" texto={texto} alCambiar={setTexto} alExpirar={alExpirar} />
      <output aria-label="Guardado">{texto}</output>
    </>
  );
}

describe("CampoDeUnidad", () => {
  test("con una letra sugiere las unidades del catálogo, con sus grafías y su uso; al elegir queda la unidad", async () => {
    const u = userEvent.setup();
    render(<Campo />);
    const campo = screen.getByRole("combobox", { name: "Unidad" });
    await u.type(campo, "m");
    const opcion = await screen.findByRole("option", { name: /^m3/ });
    expect(opcion).toHaveTextContent("m3, m³ · 12 veces en el catálogo");
    expect(screen.getByRole("option", { name: /^m2/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /^saco/ })).toBeNull();
    await u.click(opcion);
    expect(campo).toHaveValue("m3");
    expect(screen.getByLabelText("Guardado")).toHaveTextContent("m3");
  });

  test("se puede usar una unidad que no está en el catálogo", async () => {
    const u = userEvent.setup();
    render(<Campo />);
    const campo = screen.getByRole("combobox", { name: "Unidad" });
    await u.type(campo, "pulg");
    await u.click(await screen.findByRole("option", { name: "Usar «pulg» tal cual" }));
    expect(campo).toHaveValue("pulg");
  });

  test("la lista se pide una sola vez aunque se busque varias veces", async () => {
    const u = userEvent.setup();
    render(<Campo />);
    const campo = screen.getByRole("combobox", { name: "Unidad" });
    await u.type(campo, "m");
    await screen.findByRole("option", { name: /^m3/ });
    await u.clear(campo);
    await u.type(campo, "sa");
    await screen.findByRole("option", { name: /^saco/ });
    expect(fetchFalso.mock.calls.filter(([r]) => String(r) === RUTA_DE_UNIDADES)).toHaveLength(1);
  });

  test("una sesión vencida (401) avisa a la aplicación", async () => {
    estado = 401;
    const alExpirar = vi.fn();
    const u = userEvent.setup();
    render(<Campo alExpirar={alExpirar} />);
    await u.type(screen.getByRole("combobox", { name: "Unidad" }), "m");
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});

describe("TablaInsumos: la columna «Unidad» de los materiales", () => {
  function Tabla() {
    const [unidad, setUnidad] = useState("");
    return (
      <TablaInsumos
        tipo="materiales"
        filas={[{ descripcion: "Cemento gris ficticio", unidad, cantidad: "", precio: "" }]}
        modalidades={[]}
        alCambiar={(_, clave, valor) => {
          if (clave === "unidad") setUnidad(valor);
        }}
        alAgregar={vi.fn()}
        alBorrar={vi.fn()}
        alCompletar={vi.fn()}
        alExpirar={vi.fn()}
      />
    );
  }

  test("sugiere las unidades del catálogo y lo elegido llena la celda", async () => {
    const u = userEvent.setup();
    render(<Tabla />);
    const celda = screen.getByRole("combobox", { name: "Unidad, fila 1" });
    await u.type(celda, "sa");
    await u.click(await screen.findByRole("option", { name: /^saco/ }));
    expect(celda).toHaveValue("saco");
  });
});
