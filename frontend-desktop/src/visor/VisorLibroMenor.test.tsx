import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import oraculo from "../../../tests/fixtures/replica/libro_minimo.json";
import type { LibroAuditadoRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { fijarCsrf } from "../api/cliente";
import { crearHojaFalsa } from "./hojaFalsa";
import { Visor } from "./Visor";

// V-16: el Visor lleva a la franja los numeros de partida de la API y la etiqueta del libro menor sale con la cifra.
const replica = { ...oraculo, sha256: "a".repeat(64) } as unknown as LibroVisualRespuesta;

function auditoria(extra: Partial<LibroAuditadoRespuesta>): LibroAuditadoRespuesta {
  return {
    libro: { nombre: "libro_minimo.xlsx", sha256: "a".repeat(64) },
    fecha_libro: "2026-10-18",
    fecha_devolucion: "2026-10-18",
    cumple: false,
    por_severidad: { CRITICO: 0, ERROR: 1, ADVERTENCIA: 0, INFO: 0 },
    totales_libro: { TOTALGEN: "4876.56257" },
    totales_silice: { TOTALGEN: "5055.52157" },
    hallazgos: [],
    indicadores: [
      {
        clave: "TOTALGEN",
        titulo: "Total general",
        actual: "4876.56",
        meta: "5055.52",
        delta: "-178.96",
        delta_pct: "-3.54",
        sentido: "exactitud",
      },
    ],
    ...extra,
  };
}

const json = (cuerpo: unknown) =>
  new Response(JSON.stringify(cuerpo), { status: 200, headers: { "Content-Type": "application/json" } });

describe("Visor con libro menor (V-16)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const crearHoja = vi.fn(async () => crearHojaFalsa("PORTADA"));
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fijarCsrf("csrf-de-prueba");
  });
  afterEach(() => vi.unstubAllGlobals());

  async function abrir(respuesta: LibroAuditadoRespuesta) {
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada).endsWith("/v1/libros/replica") ? json(replica) : json(respuesta),
    );
    render(<Visor crearHoja={crearHoja} />);
    const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.setup().upload(entrada, new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx"));
    return screen.findByRole("region", { name: "Indicadores del libro" });
  }

  test("con partidas_con_omision de la API, la etiqueta dice cuantas y cuales", async () => {
    const franja = await abrir(auditoria({ partidas_con_omision: [2] }));
    expect(within(franja).getByRole("note").textContent).toContain("1 partida con costo directo incompleto (n.º"+String.fromCharCode(160)+"2)");
  });

  test("sin el campo (API anterior) o con la lista vacia, la etiqueta fija", async () => {
    const franja = await abrir(auditoria({ partidas_con_omision: [] }));
    expect(within(franja).getByRole("note")).toHaveTextContent(
      "Libro menor: puede deberse a partidas omitidas; revise antes de aceptar",
    );
  });

  test("con el libro mayor que Silice no hay etiqueta", async () => {
    const franja = await abrir(
      auditoria({
        indicadores: [
          { clave: "TOTALGEN", titulo: "Total general", actual: "5126.97", meta: "5055.52", delta: "71.45", delta_pct: "1.41", sentido: "exactitud" },
        ],
      }),
    );
    expect(within(franja).queryByRole("note")).toBeNull();
  });
});
