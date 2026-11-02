import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import RiesgoDeLaObra from "./RiesgoDeLaObra";

// Datos ficticios. «Mejora de la estimación» (Tarea 15, pantallas de informes): la pantalla lee las tres cifras con
// coma decimal y punto de miles, las manda con punto (fila 90) y escribe en es-VE los dos errores y la mejora que
// calcula el servidor. Oráculo a mano: real 160.000, original 141.700,50 y Sílice 159.666,11 → |141.700,50 − 160.000|
// ÷ 160.000 = 11,44 %; |159.666,11 − 160.000| ÷ 160.000 = 0,21 %; mejora 11,23 puntos.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "ver_riesgo"],
  modo_entrega: false,
};

const INSUMOS = {
  proyecto: "Vía Demo",
  version: "VIA-002",
  moneda: "USD",
  insumos: ["Cemento asfáltico"],
  componentes: [],
  mezclas: [],
  series: [{ codigo: "CEMENTO_ASFALTICO_PPI", nombre: "PPI de asfalto (proxy internacional)" }],
  inicio_linea_base: "2027-02-01",
};

const PROYECCION = {
  proyecto: "Vía Demo",
  version: "VIA-002",
  moneda: "USD",
  inicio: "2027-02-01",
  inicio_de: "linea_base",
  meses: 6,
  trayectorias: 2000,
  semilla: 1,
  total_base: "1000",
  p50: "159666.1091212",
  p80: "161000.5",
  reserva: "1000.5",
  contribucion: [{ insumo: "Cemento asfáltico", monto: "200.5" }],
  meses_usados: 24,
  supuestos: ["gasto uniforme en el plazo"],
  mezclas: [],
};

const MEJORA = { error_original_pct: "11.44", error_silice_pct: "0.21", mejora_pp: "11.23" };

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function valorDe(region: HTMLElement, rotulo: string): string | null {
  const dt = within(region).getByText(rotulo, { selector: "dt" });
  return dt.nextElementSibling?.textContent ?? null;
}

describe("Mejora de la estimación", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let mejora: () => Response;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();
  const libros: URL[] = [];

  function montar(nombreProyecto: string | null = "Vía Demo") {
    render(
      <ContextoAplicacion.Provider value={{ sesion: ANA, proyecto: nombreProyecto === null ? null : "7", nombreProyecto, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <RiesgoDeLaObra />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function cuerpoDeLaMejora(): Record<string, unknown> {
    const llamada = fetchFalso.mock.calls.find((c) => new URL(String(c[0]), "http://prueba").pathname === "/v1/riesgo/mejora");
    return JSON.parse(String(llamada?.[1]?.body)) as Record<string, unknown>;
  }

  const seccion = () => screen.getByRole("region", { name: "Mejora de la estimación" });

  async function escribir(rotulo: string, texto: string) {
    const campo = within(seccion()).getByLabelText(rotulo);
    await usuario.clear(campo);
    await usuario.type(campo, texto);
  }

  async function llenarYCalcular(real = "160.000", original = "141.700,50", silice = "159.666,11") {
    await escribir("Costo final real", real);
    await escribir("Presupuesto original", original);
    await escribir("Estimación de Sílice", silice);
    await usuario.click(within(seccion()).getByRole("button", { name: "Calcular la mejora" }));
  }

  beforeEach(() => {
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    libros.length = 0;
    vi.stubGlobal("fetch", fetchFalso);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", { value: () => "blob:falso", configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: () => undefined, configurable: true });
    mejora = () => json(MEJORA);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/hoja/versiones") {
        return json({ proyecto: "Vía Demo", moneda: "USD", por_omision: "VIA-002", versiones: [{ codigo: "VIA-002" }] });
      }
      if (url.pathname === "/v1/riesgo/insumos" && metodo === "GET") return json(INSUMOS);
      if (url.pathname === "/v1/riesgo/proyeccion" && metodo === "POST") return json(PROYECCION);
      if (url.pathname === "/v1/riesgo/mejora" && metodo === "POST") return mejora();
      if (url.pathname === "/v1/riesgo/reportes/mejora") {
        libros.push(url);
        return new Response("PK", { status: 200, headers: { "Content-Disposition": 'attachment; filename="mejora.xlsx"' } });
      }
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("lee las cifras con coma, las manda con punto y muestra los errores y la mejora en es-VE", async () => {
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    expect(screen.queryByRole("region", { name: "Mejora de la estimación" })).not.toBeNull();
    expect(within(seccion()).getByRole("heading", { level: 2, name: "Mejora de la estimación" })).toBeInTheDocument();
    await llenarYCalcular();
    const resultado = await screen.findByRole("region", { name: "Resultado de la mejora" });
    expect(valorDe(resultado, "Error del presupuesto original")).toBe("11,44 %");
    expect(valorDe(resultado, "Error de la estimación de Sílice")).toBe("0,21 %");
    expect(valorDe(resultado, "Mejora")).toBe("11,23 puntos");
    expect(within(resultado).getByText(/Sílice se acercó más al costo real/)).toBeInTheDocument();
    expect(cuerpoDeLaMejora()).toEqual({ costo_final_real: "160000", presupuesto_original: "141700.50", estimacion_silice: "159666.11" });
    await waitFor(() => expect(document.activeElement).toBe(resultado));
  });

  test("sin obra abierta también se calcula: la mejora no lee la obra", async () => {
    montar(null);
    await llenarYCalcular();
    expect(await screen.findByRole("region", { name: "Resultado de la mejora" })).toBeInTheDocument();
  });

  test("la estimación de Sílice viene con el P50 de la proyección y se puede cambiar", async () => {
    montar();
    const silice = within(seccion()).getByLabelText("Estimación de Sílice");
    expect(silice).toHaveValue("");
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(within(seccion()).getByLabelText("Estimación de Sílice")).toHaveValue("159.666,11");
    expect(within(seccion()).getByText(/P50 de la proyección de VIA-002 \(USD\)/)).toBeInTheDocument();
    await escribir("Estimación de Sílice", "150.000");
    await escribir("Costo final real", "160.000");
    await escribir("Presupuesto original", "141.700,50");
    await usuario.click(within(seccion()).getByRole("button", { name: "Calcular la mejora" }));
    await screen.findByRole("region", { name: "Resultado de la mejora" });
    expect(cuerpoDeLaMejora()).toMatchObject({ estimacion_silice: "150000" });
  });

  // Hallazgo 9 del recorrido: el presupuesto original llegaba vacío aunque la proyección conoce el total base.
  test("el presupuesto original viene con el total base de la proyección y se puede cambiar", async () => {
    montar();
    const original = within(seccion()).getByLabelText("Presupuesto original");
    expect(original).toHaveValue("");
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(within(seccion()).getByLabelText("Presupuesto original")).toHaveValue("1.000,00");
    expect(
      within(seccion()).getByText("Viene del total base de la proyección de VIA-002 (USD); puede cambiarlo."),
    ).toBeInTheDocument();
    await escribir("Presupuesto original", "141.700,50");
    expect(within(seccion()).queryByText(/Viene del total base/)).toBeNull();
    await escribir("Costo final real", "160.000");
    await usuario.click(within(seccion()).getByRole("button", { name: "Calcular la mejora" }));
    await screen.findByRole("region", { name: "Resultado de la mejora" });
    expect(cuerpoDeLaMejora()).toMatchObject({ presupuesto_original: "141700.50", estimacion_silice: "159666.11" });
  });

  test("una mejora negativa se muestra con su signo y se dice", async () => {
    mejora = () => json({ error_original_pct: "2.00", error_silice_pct: "5.50", mejora_pp: "-3.50" });
    montar();
    await llenarYCalcular("100", "98", "105,50");
    const resultado = await screen.findByRole("region", { name: "Resultado de la mejora" });
    expect(valorDe(resultado, "Mejora")).toBe("-3,50 puntos");
    expect(within(resultado).getByText(/Sílice se alejó más del costo real que el presupuesto original/)).toBeInTheDocument();
  });

  test("el error del servidor se muestra con su texto y recibe el foco", async () => {
    mejora = () => json({ detalle: "el costo final real debe ser mayor que cero" }, 422);
    montar();
    await llenarYCalcular("0", "100", "100");
    const alerta = await within(seccion()).findByRole("alert");
    expect(alerta).toHaveTextContent("el costo final real debe ser mayor que cero");
    await waitFor(() => expect(document.activeElement).toBe(alerta.closest("[tabindex]")));
    expect(screen.queryByRole("region", { name: "Resultado de la mejora" })).toBeNull();
  });

  test("una cifra mal escrita no se envía y se dice junto al campo", async () => {
    montar();
    await llenarYCalcular("160.000", "2.5", "159.666,11");
    expect(await within(seccion()).findByText(/Use la coma para los decimales/)).toBeInTheDocument();
    expect(fetchFalso.mock.calls.some((c) => String(c[0]).includes("/v1/riesgo/mejora"))).toBe(false);
  });

  test("baja el informe de mejora en Excel con las cifras calculadas", async () => {
    montar();
    expect(within(seccion()).queryByRole("button", { name: "Descargar el informe de mejora (Excel)" })).toBeNull();
    await llenarYCalcular();
    const resultado = await screen.findByRole("region", { name: "Resultado de la mejora" });
    await usuario.click(within(resultado).getByRole("button", { name: "Descargar el informe de mejora (Excel)" }));
    await waitFor(() => expect(libros).toHaveLength(1));
    expect(Object.fromEntries(libros[0].searchParams)).toEqual({
      costo_final_real: "160000",
      presupuesto_original: "141700.50",
      estimacion_silice: "159666.11",
    });
  });

  test("al cambiar una cifra después de calcular, el resultado viejo se retira", async () => {
    montar();
    await llenarYCalcular();
    await screen.findByRole("region", { name: "Resultado de la mejora" });
    await escribir("Costo final real", "170.000");
    expect(screen.queryByRole("region", { name: "Resultado de la mejora" })).toBeNull();
  });
});
