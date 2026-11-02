import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { alertaConTexto } from "../../test/ayudas";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaIndices from "./index";
import type { Confirmacion, Contexto, Informe } from "./logica";

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

const CONTEXTO: Contexto = {
  tipos: [
    { id: "tasa", rotulo: "Tasa de referencia del USD (.xls trimestral)" },
    { id: "inpc", rotulo: "INPC (.xls mensual)" },
    { id: "csv", rotulo: "Una serie en CSV canonico (serie, fecha, valor, provisional, fuente)" },
  ],
  periodicidades: ["diaria", "mensual", "trimestral", "anual"],
  unidad_por_defecto: "indice_bs",
  extensiones: [".xls", ".xlsx", ".csv"],
  lee_xls: true,
  responsable: "Admin de Prueba <admin>",
};

const INFORME: Informe = {
  archivo: "indices.csv",
  huella: "a".repeat(64),
  fuente: "https://www.bcv.org.ve/x",
  fecha_descarga: "2026-10-11",
  filas_leidas: 4,
  filas_rechazadas: 1,
  provisionales: 1,
  series: [
    { clave: "INDICE-A", valores: 2, desde: "2026-01-01", hasta: "2026-02-01" },
    { clave: "INDICE-B", valores: 1, desde: "2026-01-01", hasta: "2026-01-01" },
  ],
  rechazos: [{ lugar: "indices.csv:4", motivo: "(serie, fecha) repetido" }],
  rechazos_omitidos: 0,
  advertencias: ["Aviso ficticio del lector."],
};

const CONFIRMACION: Confirmacion = {
  mensajes: ["INDICE-A: importada (2 valores)", "INDICE-B: ya importado; no se escribio nada"],
};

describe("Índices del BCV", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let contexto: () => Response;
  let leer: () => Response;
  let confirmar: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    contexto = () => json(CONTEXTO);
    leer = () => json(INFORME);
    confirmar = () => json(CONFIRMACION);
    fetchFalso.mockImplementation(async (ruta) => {
      const url = String(ruta);
      if (url === "/v1/indices/contexto") return contexto();
      if (url === "/v1/indices/leer") return leer();
      if (url === "/v1/indices/confirmar") return confirmar();
      return json({ detalle: "ruta inesperada " + url }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(alExpirar = vi.fn()) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaIndices />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  function llamadas(url: string) {
    return fetchFalso.mock.calls.filter(([ruta]) => String(ruta) === url);
  }

  async function esperarPagina() {
    return screen.findByRole("heading", { name: "Índices del BCV" });
  }

  async function elegirArchivo(nombre = "indices.csv", tipo = "csv") {
    const usuario = userEvent.setup();
    await esperarPagina();
    await usuario.selectOptions(screen.getByLabelText("Qué archivo es"), tipo);
    const campo = document.querySelector('input[type="file"]') as HTMLInputElement;
    await usuario.upload(campo, new File(["serie,fecha"], nombre));
    return usuario;
  }

  async function leerCsv() {
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Leer" }));
    await screen.findByRole("heading", { name: "Informe previo (todavía no se guardó nada)" });
    return usuario;
  }

  test("ofrece los tipos de archivo de la pantalla clásica y el responsable", async () => {
    montar();
    await esperarPagina();
    const tipo = screen.getByLabelText("Qué archivo es");
    const opciones = within(tipo).getAllByRole("option").map((o) => o.textContent);
    expect(opciones).toEqual(CONTEXTO.tipos.map((t) => t.rotulo));
    expect(screen.getByText(/«Leer» no escribe nada/)).toBeInTheDocument();
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/indices/contexto");
  });

  test("si el contexto falla muestra el error de la API y no el formulario", async () => {
    contexto = () => json({ detalle: "Su cuenta no tiene permiso para esta acción." }, 403);
    montar();
    expect(await alertaConTexto()).toHaveTextContent("Su cuenta no tiene permiso para esta acción.");
    expect(screen.queryByRole("button", { name: "Leer" })).not.toBeInTheDocument();
  });

  test("leer sin elegir archivo dice que lo elija y no llama a la API", async () => {
    montar();
    await esperarPagina();
    await userEvent.setup().click(screen.getByRole("button", { name: "Leer" }));
    expect(await alertaConTexto()).toHaveTextContent("Elija el archivo que bajó del BCV.");
    expect(llamadas("/v1/indices/leer")).toHaveLength(0);
  });

  test("leer un CSV manda el formulario y muestra recuentos, series, rechazos y advertencias", async () => {
    montar();
    await leerCsv();
    const [, opciones] = llamadas("/v1/indices/leer")[0];
    const cuerpo = opciones?.body as FormData;
    expect(opciones?.method).toBe("POST");
    expect(cuerpo.get("tipo")).toBe("csv");
    expect((cuerpo.get("archivo") as File).name).toBe("indices.csv");
    expect(cuerpo.get("fecha_descarga")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    const resumen = screen.getByRole("region", { name: "Resumen de la lectura" });
    expect(within(resumen).getByText("Filas leídas").nextSibling).toHaveTextContent("4");
    expect(within(resumen).getByText("Rechazadas").nextSibling).toHaveTextContent("1");
    expect(within(resumen).getByText("Provisionales").nextSibling).toHaveTextContent("1");
    const series = screen.getByRole("table", { name: "Series leídas" });
    expect(within(series).getByText("INDICE-A")).toBeInTheDocument();
    expect(within(series).getAllByText("2026-01-01")).toHaveLength(3);
    expect(within(screen.getByRole("table", { name: "Filas rechazadas" })).getByText("indices.csv:4")).toBeInTheDocument();
    expect(screen.getByText("Aviso ficticio del lector.")).toBeInTheDocument();
    expect(screen.getByText("Responsable de la importación: Admin de Prueba <admin>")).toBeInTheDocument();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  test("un CSV pide nombre, organismo, unidad y periodicidad de cada serie", async () => {
    montar();
    await leerCsv();
    expect(screen.getByLabelText("Nombre de INDICE-A")).toHaveValue("INDICE-A");
    expect(screen.getByLabelText("Organismo de INDICE-A")).toHaveValue("");
    expect(screen.getByLabelText("Unidad de INDICE-B")).toHaveValue("indice_bs");
    expect(screen.getByLabelText("Periodicidad de INDICE-B")).toHaveValue("mensual");
  });

  test("confirmar reenvía el archivo con la huella y las definiciones, y muestra los mensajes", async () => {
    montar();
    const usuario = await leerCsv();
    await usuario.type(screen.getByLabelText("Organismo de INDICE-A"), "Ente Demo");
    await usuario.type(screen.getByLabelText("Organismo de INDICE-B"), "Ente Demo");
    await usuario.selectOptions(screen.getByLabelText("Periodicidad de INDICE-A"), "trimestral");
    await usuario.click(screen.getByRole("button", { name: "Confirmar la importación" }));
    await screen.findByText("INDICE-A: importada (2 valores)");
    expect(screen.getByText("INDICE-B: ya importado; no se escribio nada")).toBeInTheDocument();
    const [, opciones] = llamadas("/v1/indices/confirmar")[0];
    const cuerpo = opciones?.body as FormData;
    expect(opciones?.method).toBe("POST");
    expect(cuerpo.get("huella")).toBe("a".repeat(64));
    expect((cuerpo.get("archivo") as File).name).toBe("indices.csv");
    expect(JSON.parse(String(cuerpo.get("definiciones")))).toEqual([
      { serie: "INDICE-A", nombre: "INDICE-A", organismo: "Ente Demo", unidad: "indice_bs", periodicidad: "trimestral" },
      { serie: "INDICE-B", nombre: "INDICE-B", organismo: "Ente Demo", unidad: "indice_bs", periodicidad: "mensual" },
    ]);
    // El informe ya se guardó: se retira, como en la pantalla clásica.
    expect(screen.queryByRole("heading", { name: /Informe previo/ })).not.toBeInTheDocument();
  });

  test("la tasa no pide definiciones y confirma con una lista vacía", async () => {
    montar();
    const usuario = await elegirArchivo("2_1_2c26_smc.xlsx", "tasa");
    await usuario.type(screen.getByLabelText("Dirección de la página del BCV de donde lo bajó"), "https://www.bcv.org.ve/x");
    await usuario.click(screen.getByRole("button", { name: "Leer" }));
    await screen.findByRole("heading", { name: /Informe previo/ });
    expect(screen.queryByLabelText("Organismo de INDICE-A")).not.toBeInTheDocument();
    const lectura = (llamadas("/v1/indices/leer")[0][1]?.body as FormData).get("fuente");
    expect(lectura).toBe("https://www.bcv.org.ve/x");
    await usuario.click(screen.getByRole("button", { name: "Confirmar la importación" }));
    await screen.findByText("INDICE-A: importada (2 valores)");
    const cuerpo = llamadas("/v1/indices/confirmar")[0][1]?.body as FormData;
    expect(cuerpo.get("definiciones")).toBe("[]");
    expect(cuerpo.get("tipo")).toBe("tasa");
  });

  test("un error al leer se muestra tal cual y no deja informe", async () => {
    leer = () => json({ detalle: "No se importo nada: indices.csv: el CSV debe estar en UTF-8" }, 422);
    montar();
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Leer" }));
    expect(await alertaConTexto()).toHaveTextContent("No se importo nada: indices.csv: el CSV debe estar en UTF-8");
    expect(screen.queryByRole("heading", { name: /Informe previo/ })).not.toBeInTheDocument();
  });

  test("un error al confirmar se muestra y conserva el informe para corregir", async () => {
    confirmar = () =>
      json(
        { detalle: "No se guardo nada: declare nombre, organismo, unidad y periodicidad de la serie INDICE-A" },
        422,
      );
    montar();
    const usuario = await leerCsv();
    await usuario.click(screen.getByRole("button", { name: "Confirmar la importación" }));
    expect(await alertaConTexto()).toHaveTextContent("No se guardo nada: declare nombre, organismo");
    expect(screen.getByRole("heading", { name: /Informe previo/ })).toBeInTheDocument();
  });

  test("leer de nuevo reemplaza el informe anterior y limpia el aviso de confirmación", async () => {
    montar();
    const usuario = await leerCsv();
    await usuario.click(screen.getByRole("button", { name: "Confirmar la importación" }));
    await screen.findByText("INDICE-A: importada (2 valores)");
    await usuario.click(screen.getByRole("button", { name: "Leer" }));
    await screen.findByRole("heading", { name: /Informe previo/ });
    expect(screen.queryByText("INDICE-A: importada (2 valores)")).not.toBeInTheDocument();
  });

  test("avisa de las filas rechazadas que no caben en la lista", async () => {
    leer = () => json({ ...INFORME, rechazos_omitidos: 3 });
    montar();
    await leerCsv();
    expect(screen.getByText("Hay 3 filas rechazadas más que no se muestran aquí.")).toBeInTheDocument();
  });

  test("un .xls en un equipo sin xlrd lo dice antes de leer", async () => {
    contexto = () => json({ ...CONTEXTO, lee_xls: false });
    montar();
    await elegirArchivo("4_5_7.xls", "inpc");
    expect(screen.getByText(/falta el componente xlrd/)).toBeInTheDocument();
  });

  test("la API que contesta 401 avisa a la aplicación", async () => {
    leer = () => json({ detalle: "Entre de nuevo." }, 401);
    const alExpirar = montar();
    const usuario = await elegirArchivo();
    await usuario.click(screen.getByRole("button", { name: "Leer" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
