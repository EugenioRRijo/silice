import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { UsarPrecio } from "./UsarPrecio";
import type { Estudio } from "./logica";

// Tarea 25 (plan de montar un presupuesto; diseno §11, meta 4): al usar un precio de compra, la casilla «Declararlo
// precio del corte» lo deja ademas como precio del corte de la obra abierta, para que Control de obra separe el desvio
// de precio. Contrato de `api/rutas/mercado.py`: `declarar_en` (la obra) solo viaja si se marco la casilla, y la
// respuesta trae `corte`, la frase que lo confirma. Datos ficticios.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "control_de_obra"],
  modo_entrega: false,
};

const COMPRA: Estudio = {
  lado: "compra",
  codigo: "CEM-GRIS",
  moneda: "Bs",
  estadisticas: {
    n: 1,
    minimo: "20.00",
    q1: "20.00",
    mediana: "20.00",
    promedio: "20.00",
    maximo: "20.00",
    ids: [1],
    otras_monedas: 0,
    dias: 90,
  },
  propuesta: { precio: "20.00", razon: "Mediana de 1 observación; la más barata vista: 20,00 Bs." },
  piso: null,
  precio_unitario: null,
  observaciones: [],
};
const COBRO: Estudio = { ...COMPRA, lado: "cobro", codigo: "OBRA-04", piso: "41.40", precio_unitario: "45.54" };
const CONFIRMADO = "Declarado precio del corte de la obra «Vivienda demo» desde el 26/10/2026.";
const CASILLA = "Declararlo precio del corte de la obra Vivienda demo";

const fetchFalso = vi.fn<typeof fetch>();

function cuerpos(): unknown[] {
  return fetchFalso.mock.calls
    .filter(([url, init]) => init?.method === "POST" && String(url).endsWith("/usar"))
    .map(([, init]) => JSON.parse(String(init?.body)));
}

function montar(estudio: Estudio, extra: Partial<Aplicacion> = {}) {
  const valor: Aplicacion = {
    sesion: SESION,
    proyecto: "VIV-001",
    nombreProyecto: "Vivienda demo",
    caso: { nombre: "demo", ruta_relativa: "data/demo.db" },
    recargarProyectos: vi.fn(),
    alExpirar: vi.fn(),
    ...extra,
  };
  render(
    <ContextoAplicacion.Provider value={valor}>
      <UsarPrecio estudio={estudio} />
    </ContextoAplicacion.Provider>,
  );
  return userEvent.setup();
}

async function usarYConfirmar(u: ReturnType<typeof userEvent.setup>) {
  await u.click(screen.getByRole("button", { name: "Usar este precio" }));
  await u.click(await screen.findByRole("button", { name: "Confirmar" }));
}

describe("Declararlo precio del corte", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async (url, init) => {
      const ruta = String(url);
      if (ruta.endsWith("/afectados")) return json({ apus: ["OBRA-04"] });
      if (ruta.endsWith("/usar") && init?.method === "POST") {
        const cuerpo = JSON.parse(String(init.body)) as { declarar_en?: string };
        return json({ lista: "Lista demo al 26/10/2026", corte: cuerpo.declarar_en ? CONFIRMADO : null });
      }
      return json({ detalle: `ruta inesperada ${ruta}` }, 500);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  test("marcada, la compra se declara en la obra abierta, se avisa antes y se confirma después", async () => {
    const u = montar(COMPRA);
    const casilla = screen.getByRole("checkbox", { name: CASILLA });
    expect(casilla).not.toBeChecked();
    expect(
      screen.getByText("Control de obra lo usará para separar el desvío de precio («Precios declarados de insumos»)."),
    ).toBeInTheDocument();
    await u.click(casilla);
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    expect(
      await screen.findByText("También quedará como precio del corte de la obra Vivienda demo desde hoy."),
    ).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Confirmar" }));
    await screen.findByText(`Precio guardado en «Lista demo al 26/10/2026». ${CONFIRMADO}`);
    expect(cuerpos()).toEqual([{ precio: "20,00", observacion_id: null, declarar_en: "VIV-001" }]);
  });

  test("sin marcar, el cuerpo es el de siempre y no se habla del corte", async () => {
    const u = montar(COMPRA);
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    await screen.findByRole("button", { name: "Confirmar" });
    expect(screen.queryByText(/precio del corte de la obra/)).not.toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Confirmar" }));
    await screen.findByText("Precio guardado en «Lista demo al 26/10/2026».");
    expect(cuerpos()).toEqual([{ precio: "20,00", observacion_id: null }]);
  });

  test("tras usar el precio la casilla vuelve a quedar sin marcar", async () => {
    const u = montar(COMPRA);
    await u.click(screen.getByRole("checkbox", { name: CASILLA }));
    await usarYConfirmar(u);
    await waitFor(() => expect(screen.getByRole("checkbox", { name: CASILLA })).not.toBeChecked());
  });

  test("sin obra abierta no hay casilla, y en lo que cobramos tampoco", () => {
    montar(COMPRA, { proyecto: null, nombreProyecto: undefined });
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  test("en lo que cobramos no hay casilla", () => {
    montar(COBRO);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  test("si la obra no admite el precio (404), se dice en el aviso y no se da por guardado", async () => {
    fetchFalso.mockImplementation(async (url) => {
      const ruta = String(url);
      if (ruta.endsWith("/afectados")) return json({ apus: [] });
      return json({ detalle: "«Cemento gris» no es un material de la línea base de la obra «Vivienda demo»." }, 404);
    });
    const u = montar(COMPRA);
    await u.click(screen.getByRole("checkbox", { name: CASILLA }));
    await usarYConfirmar(u);
    expect(
      await screen.findByText("«Cemento gris» no es un material de la línea base de la obra «Vivienda demo»."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Precio guardado/)).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: CASILLA })).toBeChecked();
  });
});
