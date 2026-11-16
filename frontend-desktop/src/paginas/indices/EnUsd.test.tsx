import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import { EnUsd } from "./EnUsd";
import PaginaIndices from "./index";
import { textoDelResumen } from "./logicaUsd";
import type { OrigenesEnUsd, VistaEnUsd } from "./logicaUsd";

// RF-214 (ola 2, línea 4): «Un índice en USD» en «Índices del BCV». La interfaz no calcula nada: la API trae la serie
// nueva, el número de meses, una muestra de la cuenta ya escrita en es-VE y los meses que no se pueden; aquí solo se
// muestran. Se carga al pedirlo (no agrega una petición a la página). Datos FICTICIOS.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin de Prueba",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_precios"],
  modo_entrega: false,
};
const ORIGENES: OrigenesEnUsd = {
  series: [{ clave: "FIC-INPC", nombre: "INPC ficticio", organismo: "BCV (ficticio)" }],
  lados: ["venta", "compra"],
  lado_por_omision: "venta",
};
const VISTA: VistaEnUsd = {
  serie_nueva: "FIC-INPC-USD",
  nombre: "INPC ficticio en USD (tasa venta promedio del mes)",
  meses: 2,
  desde: "01/2026",
  hasta: "02/2027",
  provisionales: 0,
  muestra: [
    { mes: "01/2026", indice_bs: "200", tasa_promedio: "40,0000", valor: "5,000000" },
    { mes: "02/2027", indice_bs: "276", tasa_promedio: "46,0000", valor: "6,000000" },
  ],
  omitidos: [{ mes: "03/2027", motivo: "03/2027: del 09/03/2027 al 14/03/2027 no hay tasa del BCV de los 7 días anteriores (S1-R2)" }],
  huella: "b".repeat(64),
  ya_guardada: false,
};

describe("Un índice en USD (RF-214)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let origenes: () => Response;
  let ver: () => Response;
  let confirmar: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    origenes = () => json(ORIGENES);
    ver = () => json(VISTA);
    confirmar = () => json({ mensajes: ["FIC-INPC-USD: guardada con 2 meses en USD."] });
    fetchFalso.mockImplementation(async (ruta) => {
      const url = String(ruta);
      if (url === "/v1/indices/en-usd/origenes") return origenes();
      if (url === "/v1/indices/en-usd/ver") return ver();
      if (url === "/v1/indices/en-usd/confirmar") return confirmar();
      if (url === "/v1/indices/contexto")
        return json({ tipos: [], periodicidades: [], unidad_por_defecto: "indice_bs", extensiones: [], lee_xls: true, responsable: "" });
      return json({ detalle: "ruta inesperada " + url }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(nodo = <EnUsd />) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(<ContextoAplicacion.Provider value={valor}>{nodo}</ContextoAplicacion.Provider>);
  }
  const cuerpos = (url: string) =>
    fetchFalso.mock.calls.filter(([r]) => String(r) === url).map(([, i]) => JSON.parse(String(i?.body)));

  test("la página de índices trae la sección, y no pide nada de ella hasta abrirla", async () => {
    montar(<PaginaIndices />);
    expect(await screen.findByRole("heading", { name: "Un índice en USD" })).toBeInTheDocument();
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(1));
    expect(String(fetchFalso.mock.calls[0]![0])).toBe("/v1/indices/contexto");
  });

  test("al abrirla ofrece los índices en bolívares y la tasa de venta por omisión", async () => {
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Expresar un índice en USD" }));
    const indice = await screen.findByRole("combobox", { name: "Índice en bolívares" });
    expect(within(indice).getAllByRole("option").map((o) => o.textContent)).toEqual(["FIC-INPC · INPC ficticio"]);
    const lado = screen.getByRole("combobox", { name: "Tasa del BCV" });
    expect(lado).toHaveValue("venta");
  });

  test("«Revisar» manda la serie y el lado y muestra la cuenta tal cual la da el servidor", async () => {
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Expresar un índice en USD" }));
    await userEvent.selectOptions(await screen.findByRole("combobox", { name: "Tasa del BCV" }), "compra");
    await userEvent.click(screen.getByRole("button", { name: "Revisar" }));
    expect(await screen.findByText("FIC-INPC-USD")).toBeInTheDocument();
    expect(cuerpos("/v1/indices/en-usd/ver")).toEqual([{ serie: "FIC-INPC", lado: "compra" }]);
    expect(screen.getByText("2 meses en USD, de 01/2026 a 02/2027.")).toBeInTheDocument();
    const muestra = screen.getByRole("table", { name: "La cuenta del primer y el último mes" });
    for (const texto of ["01/2026", "200", "40,0000", "5,000000", "6,000000"]) {
      expect(within(muestra).getByText(texto)).toBeInTheDocument();
    }
    const omitidos = screen.getByRole("table", { name: "Meses que no se pueden expresar en USD" });
    expect(within(omitidos).getByText(VISTA.omitidos[0]!.motivo)).toBeInTheDocument();
  });

  test("«Guardar la serie en USD» manda la huella revisada y dice lo que hizo", async () => {
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Expresar un índice en USD" }));
    await screen.findByRole("combobox", { name: "Índice en bolívares" });
    await userEvent.click(screen.getByRole("button", { name: "Revisar" }));
    await userEvent.click(await screen.findByRole("button", { name: "Guardar la serie en USD" }));
    expect(await screen.findByText("FIC-INPC-USD: guardada con 2 meses en USD.")).toBeInTheDocument();
    expect(cuerpos("/v1/indices/en-usd/confirmar")).toEqual([{ serie: "FIC-INPC", lado: "venta", huella: "b".repeat(64) }]);
  });

  test("un 409 se muestra tal cual", async () => {
    const detalle = "Los índices o las tasas cambiaron desde que lo revisó: revíselo de nuevo.";
    confirmar = () => json({ detalle }, 409);
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Expresar un índice en USD" }));
    await screen.findByRole("combobox", { name: "Índice en bolívares" });
    await userEvent.click(screen.getByRole("button", { name: "Revisar" }));
    await userEvent.click(await screen.findByRole("button", { name: "Guardar la serie en USD" }));
    expect(await alertaConTexto()).toHaveTextContent(detalle);
  });

  test("sin índices en bolívares lo dice y no ofrece revisar", async () => {
    origenes = () => json({ ...ORIGENES, series: [] });
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Expresar un índice en USD" }));
    expect(await screen.findByText(/No hay índices mensuales en bolívares importados/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revisar" })).toBeNull();
  });

  test("sin meses que expresar no ofrece guardar; una serie ya guardada lo dice", async () => {
    ver = () => json({ ...VISTA, meses: 0, desde: "", hasta: "", muestra: [], ya_guardada: true });
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Expresar un índice en USD" }));
    await screen.findByRole("combobox", { name: "Índice en bolívares" });
    await userEvent.click(screen.getByRole("button", { name: "Revisar" }));
    expect(await screen.findByText("Ningún mes se puede expresar en USD con las tasas importadas.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar la serie en USD" })).toBeNull();
    expect(screen.getByText("Ya está guardada con estos mismos valores.")).toBeInTheDocument();
  });

  test("el resumen dice los meses y los provisionales con su plural", () => {
    expect(textoDelResumen({ ...VISTA, meses: 1, desde: "01/2026", hasta: "01/2026" })).toBe("1 mes en USD, de 01/2026 a 01/2026.");
    expect(textoDelResumen({ ...VISTA, provisionales: 1 })).toBe("2 meses en USD, de 01/2026 a 02/2027 (1 provisional).");
    expect(textoDelResumen({ ...VISTA, provisionales: 2 })).toBe("2 meses en USD, de 01/2026 a 02/2027 (2 provisionales).");
  });
});
