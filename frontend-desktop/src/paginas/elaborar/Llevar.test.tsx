import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaElaborar from "./index";
import type { CalculoRespuesta, ItemComputo } from "../archivos/tipos";

// Tarea 12 del plan de montar un presupuesto: Elaborar lleva sus items a la Hoja de la obra elegida (sin guardar version)
// y navega a /hoja. Datos ficticios; los cuerpos esperados se escriben a mano.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const item = (origen: string, codigo: string, cantidad: string): ItemComputo => ({
  codigo_partida: codigo,
  descripcion: `Descripcion ${origen}`,
  unidad: "m2",
  cantidad,
  origen_id: origen,
  origen_tipo: "tabla",
  dominio: "telecom",
  regla: null,
  parametros: {},
  especificaciones: {},
});

// «1.125» es texto de maquina del computo (punto decimal): viaja tal cual, sin convertirlo en la pagina.
const ITEMS: ItemComputo[] = [item("fila-1", "OBRA-04", "210"), item("fila-2", "OBRA-06", "1.125"), item("fila-3", "OBRA-X", "7")];

const INFORME_VACIO = {
  codigo_presupuesto: "P-001",
  cumple: true,
  veredicto: "CUMPLE",
  total_hallazgos: 0,
  por_severidad: [],
  reglas_evaluadas: [],
  hallazgos: [],
  sin_hallazgos: "Se verifico y no hubo hallazgos.",
};

function calculo(pendientes: CalculoRespuesta["pendientes"] = []): CalculoRespuesta {
  return {
    codigo: "P-001",
    fecha: "2026-10-25",
    moneda: "Bs",
    total: "1000.00",
    total_exacto: "1000.00",
    partidas: [],
    por_severidad: [],
    informe: INFORME_VACIO,
    pendientes,
    plan_por_defecto: [],
  };
}

const PENDIENTE_OBRA_X = {
  codigo_partida: "OBRA-X",
  descripcion: "Descripcion fila-3",
  unidad: "m2",
  cantidad: "7",
  origen_id: "fila-3",
  propuestas: [],
  falla: "El modelo de similitud no esta disponible.",
};

type Manejador = (init: RequestInit | undefined) => Response | Promise<Response>;

describe("Llevar a la Hoja de la obra", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let rutas: Record<string, Manejador>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fijarCsrf("tok");
    fetchFalso.mockReset();
    rutas = {
      "GET /partidas?dominio=civil": () => json([]),
      "POST /computos/telecom": () => json(ITEMS),
      "POST /presupuestos/calcular": () => json(calculo([PENDIENTE_OBRA_X])),
      "POST /v1/hoja/llevar": () => json({ borrador_id: "b".repeat(22) }),
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const clave = `${init?.method ?? "GET"} ${String(ruta)}`;
      const manejador = rutas[clave];
      if (!manejador) throw new Error(`Ruta sin doble: ${clave}`);
      return manejador(init);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  function montar(proyecto: string | null, nombreProyecto: string | null = null) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto,
      nombreProyecto,
      caso: { nombre: "demo", ruta_relativa: "data/demo.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    const vista = render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/elaborar"]}>
          <Routes>
            <Route path="/elaborar" element={<PaginaElaborar />} />
            <Route path="/hoja" element={<p>Hoja de la obra abierta</p>} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    const usuario = userEvent.setup({ applyAccept: false });
    const cambiarObra = (otro: string) =>
      vista.rerender(
        <ContextoAplicacion.Provider value={{ ...valor, proyecto: otro }}>
          <MemoryRouter initialEntries={["/elaborar"]}>
            <Routes>
              <Route path="/elaborar" element={<PaginaElaborar />} />
              <Route path="/hoja" element={<p>Hoja de la obra abierta</p>} />
            </Routes>
          </MemoryRouter>
        </ContextoAplicacion.Provider>,
      );
    return { usuario, cambiarObra };
  }

  const llamadas = (clave: string) =>
    fetchFalso.mock.calls.filter(([r, i]) => `${i?.method ?? "GET"} ${String(r)}` === clave);
  const cuerpoJson = (clave: string, n = 0) => JSON.parse(String(llamadas(clave)[n][1]?.body)) as Record<string, unknown>;

  async function elaborar(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.selectOptions(screen.getByLabelText("Dominio"), "telecom");
    await usuario.upload(document.querySelector('input[type="file"]') as HTMLInputElement, new File(["a,b"], "muestra.csv"));
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await screen.findByText("Cómputo extraído");
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    await screen.findByText("Presupuesto elaborado");
  }

  test("sin obra elegida el botón no aparece y el cálculo no lleva obra", async () => {
    const { usuario } = montar(null);
    expect(screen.getByLabelText("Moneda")).toBeInTheDocument();
    await elaborar(usuario);
    expect(screen.queryByRole("button", { name: "Llevar a la Hoja de la obra" })).toBeNull();
    expect(cuerpoJson("POST /presupuestos/calcular")).not.toHaveProperty("proyecto");
  });

  test("con obra se valora con su lista, lleva las partidas sin los pendientes y navega a la Hoja", async () => {
    const { usuario } = montar("7", "Vivienda Demo 80 m2");
    // La moneda es la de la obra: no se escribe.
    expect(screen.queryByLabelText("Moneda")).toBeNull();
    expect(screen.getByText("Se valora con la lista de precios de la obra «Vivienda Demo 80 m2», en su moneda.")).toBeInTheDocument();
    await elaborar(usuario);
    expect(cuerpoJson("POST /presupuestos/calcular")).toMatchObject({ proyecto: "7" });

    expect(
      screen.getByText(
        "Lleva 2 partidas al borrador de la Hoja de «Vivienda Demo 80 m2», sin guardar una versión: la guarda usted desde la Hoja.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("El ítem pendiente no se lleva: no tiene partida en el catálogo.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Llevar a la Hoja de la obra" }));

    expect(await screen.findByText("Hoja de la obra abierta")).toBeInTheDocument();
    expect(llamadas("POST /v1/hoja/llevar")).toHaveLength(1);
    expect(cuerpoJson("POST /v1/hoja/llevar")).toEqual({
      proyecto: "7",
      partidas: [
        { codigo: "OBRA-04", cantidad: "210", calculo: "" },
        { codigo: "OBRA-06", cantidad: "1.125", calculo: "" },
      ],
    });
  });

  test("si la API no lo lleva, dice su detalle y se queda en Elaborar", async () => {
    rutas["POST /presupuestos/calcular"] = () => json(calculo());
    rutas["POST /v1/hoja/llevar"] = () =>
      json({ detalle: "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar." }, 409);
    const { usuario } = montar("7", "Casa Demo en USD");
    await elaborar(usuario);
    expect(screen.getByText(/^Lleva 3 partidas al borrador/)).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Llevar a la Hoja de la obra" }));

    expect(await alertaConTexto()).toHaveTextContent(
      "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.",
    );
    expect(screen.queryByText("Hoja de la obra abierta")).toBeNull();
    expect(screen.getByRole("button", { name: "Llevar a la Hoja de la obra" })).toBeEnabled();
  });

  test("si se elige otra obra después de elaborar, pide elaborar de nuevo antes de llevar", async () => {
    const { usuario, cambiarObra } = montar("7", "Vivienda Demo 80 m2");
    await elaborar(usuario);
    cambiarObra("8");
    expect(screen.queryByRole("button", { name: "Llevar a la Hoja de la obra" })).toBeNull();
    expect(
      screen.getByText("Elabore de nuevo el presupuesto con la obra elegida para llevarlo a su Hoja."),
    ).toBeInTheDocument();
  });
});
