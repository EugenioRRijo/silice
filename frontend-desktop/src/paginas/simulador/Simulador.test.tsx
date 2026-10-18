import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaSimulador from "./index";
import { MENSAJE_SEMILLA, MENSAJE_SIN_FILAS } from "./logica";

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

const FILAS = [
  { tipo: "material", insumo: "Arena lavada", unidad: "m3", precio: "30.00" },
  { tipo: "mano_obra", insumo: "Peon ficticio", unidad: "jornal", precio: "12.50" },
];

describe("Simulador de listas", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaSimulador />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function cuerpoEnviado(llamada: number): unknown {
    const init = fetchFalso.mock.calls[llamada][1] as RequestInit;
    return JSON.parse(String(init.body));
  }

  test("aclara que es una herramienta de prueba y trae los valores por omision", () => {
    montar();
    expect(screen.getByText(/Herramienta de prueba, no una fuente de mercado/)).toBeInTheDocument();
    expect(screen.getByLabelText("Semilla")).toHaveValue("42");
    expect(screen.getByLabelText("Variación máxima (%)")).toHaveValue("5");
    expect(screen.getByLabelText(/Insumos \(separados por coma/)).toHaveValue("");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("genera la lista: manda el cuerpo por omision y muestra los precios tal como llegan", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const tabla = await screen.findByRole("table", { name: "Lista simulada" });
    expect(tabla).toHaveTextContent("Arena lavada");
    expect(tabla).toHaveTextContent("30.00");
    expect(tabla).toHaveTextContent("12.50");
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/simulador");
    expect((fetchFalso.mock.calls[0][1] as RequestInit).method).toBe("POST");
    expect(cuerpoEnviado(0)).toEqual({ semilla: 42, variacion_max: "5", insumos: null });
    expect(screen.getByRole("button", { name: "Descargar CSV" })).toBeEnabled();
  });

  test("manda lo que se escribio", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "7");
    await usuario.clear(screen.getByLabelText("Variación máxima (%)"));
    await usuario.type(screen.getByLabelText("Variación máxima (%)"), "2.5");
    await usuario.type(screen.getByLabelText(/Insumos \(separados/), "Arena lavada, Peon ficticio");
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table");
    expect(cuerpoEnviado(0)).toEqual({
      semilla: 7,
      variacion_max: "2.5",
      insumos: "Arena lavada, Peon ficticio",
    });
  });

  test("el CSV se pide con el mismo cuerpo que genero la tabla y baja con el nombre de la API", async () => {
    const usuario = userEvent.setup();
    const clics: string[] = [];
    Object.defineProperty(URL, "createObjectURL", { value: () => "blob:falso", configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clics.push(this.download);
    });
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada) === "/v1/simulador/csv"
        ? new Response("tipo,insumo,unidad,precio\r\n", {
            headers: { "Content-Disposition": 'attachment; filename="lista_simulada.csv"' },
          })
        : json({ filas: FILAS }),
    );
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table");
    // Cambiar el campo despues de generar no cambia lo que se descarga.
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "99");
    await usuario.click(screen.getByRole("button", { name: "Descargar CSV" }));
    await waitFor(() => expect(clics).toEqual(["lista_simulada.csv"]));
    expect(fetchFalso.mock.calls[1][0]).toBe("/v1/simulador/csv");
    expect(cuerpoEnviado(1)).toEqual({ semilla: 42, variacion_max: "5", insumos: null });
    expect(((fetchFalso.mock.calls[1][1] as RequestInit).headers as Headers).get("X-Silice-CSRF")).toBe("tok");
  });

  test("sin filas dice el mensaje de Streamlit y no ofrece la descarga", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: [] }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await screen.findByText(MENSAJE_SIN_FILAS)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lista simulada" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Descargar CSV" })).not.toBeInTheDocument();
  });

  test("el error de la API se muestra tal cual y no queda la lista anterior", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ filas: FILAS }));
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "La variacion maxima no es un numero decimal: [<class 'decimal.ConversionSyntax'>]" }, 422),
    );
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table");
    await usuario.clear(screen.getByLabelText("Variación máxima (%)"));
    await usuario.type(screen.getByLabelText("Variación máxima (%)"), "cinco");
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("La variacion maxima no es un numero decimal");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("sin lista vigente (409) muestra el detalle", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ detalle: "no hay ninguna lista de precios vigente al 2026-10-18" }, 409));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await alertaConTexto()).toHaveTextContent("no hay ninguna lista de precios vigente");
  });

  test("una semilla invalida avisa junto al campo y no manda nada", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "-3");
    expect(await screen.findByText(MENSAJE_SEMILLA)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar lista simulada" })).toBeDisabled();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("un 401 avisa que la sesion vencio", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await alertaConTexto();
    expect(alExpirar).toHaveBeenCalledOnce();
  });

  test("mientras espera muestra el esqueleto y no deja generar dos veces", async () => {
    const usuario = userEvent.setup();
    let responder: (r: Response) => void = () => {};
    fetchFalso.mockReturnValue(new Promise<Response>((res) => (responder = res)));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await screen.findByRole("status", { name: "Cargando lista simulada" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar lista simulada" })).toBeDisabled();
    responder(json({ filas: FILAS }));
    expect(await screen.findByRole("table", { name: "Lista simulada" })).toBeInTheDocument();
  });
});
