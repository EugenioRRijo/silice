import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaReajuste from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["convertir_y_reajustar", "leer_proyecto"],
  modo_entrega: false,
};

const PROYECTOS = [{ codigo: "1", nombre: "Contrato S1", version_vigente: 2, version_codigo: "002", actualizado: null }];
const CONTEXTO = {
  versiones: [
    { codigo: "001", motivo: "", revalorada: false },
    { codigo: "002", motivo: "revaloracion", revalorada: true },
  ],
  periodicidades: ["mensual", "trimestral"],
  mecanismos: ["escalatoria", "comprobacion", "ambos"],
  estructuras: ["por_partida", "declarada"],
  componentes: ["materiales", "equipos", "mano_obra"],
};
const COLUMNAS = ["Período", "Escalatoria", "Comprobación", "Diferencia", "Reconocido", "Mecanismo", "Moneda", "Marcas"];
function calculo(parcial: Record<string, unknown> = {}) {
  return {
    estado: "cerrado",
    moneda: "Bs",
    columnas: COLUMNAS,
    filas: [
      {
        Período: "01/02/2027 a 28/02/2027",
        Escalatoria: "15300.00",
        Comprobación: "16000.00",
        Diferencia: "700.00",
        Reconocido: "15300.00",
        Mecanismo: "escalatoria",
        Moneda: "Bs",
        Marcas: "",
      },
      {
        Período: "Total",
        Escalatoria: "15300.00",
        Comprobación: "16000.00",
        Diferencia: "700.00",
        Reconocido: "15300.00",
        Mecanismo: "",
        Moneda: "Bs",
        Marcas: "estado: cerrado",
      },
    ],
    avisos: [],
    mensaje_parcial: "",
    parciales: [],
    ...parcial,
  };
}

describe("Reajuste de precios", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let contexto: () => Response;
  let calcular: () => Response;
  let guardar: () => Response;
  let excel: () => Response;
  const guardado = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    guardado.mockReset();
    URL.createObjectURL = vi.fn(() => "blob:falso");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      guardado(this.download);
    });
    contexto = () => json(CONTEXTO);
    calcular = () => json(calculo());
    guardar = () => json({ estudio: 7, estado: "cerrado" });
    excel = () =>
      new Response("xlsx", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="reajuste_001.xlsx"' },
      });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://x");
      if (url.pathname === "/v1/proyectos") return json(PROYECTOS);
      if (url.pathname === "/v1/reajuste/contexto") return contexto();
      if (url.pathname === "/v1/reajuste/calcular" && init?.method === "POST") return calcular();
      if (url.pathname === "/v1/reajuste/guardar" && init?.method === "POST") return guardar();
      if (url.pathname === "/v1/reajuste/excel" && init?.method === "POST") return excel();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function montar(proyecto: string | null = "1") {
    const aplicacion: Aplicacion = { sesion: SESION, proyecto, caso: null, recargarProyectos: vi.fn(), alExpirar };
    return render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <PaginaReajuste />
      </ContextoAplicacion.Provider>,
    );
  }

  function post(ruta: string) {
    const llamada = fetchFalso.mock.calls.find(([r, init]) => r === ruta && init?.method === "POST");
    return llamada ? (JSON.parse(String(llamada[1]?.body)) as Record<string, unknown>) : undefined;
  }

  async function llenar(u: ReturnType<typeof userEvent.setup>) {
    await u.type(screen.getByLabelText("Inicio del contrato"), "2026-01-15");
    await u.type(screen.getByLabelText("Duración (meses)"), "24");
    await u.type(screen.getByLabelText("R (fracción no reajustable)"), "0.10");
    await u.type(screen.getByLabelText("Serie, Componentes fila 1"), "FIC-MAT");
    await u.type(screen.getByLabelText("Desde, Periodos fila 1"), "2027-02-01");
  }

  test("sin proyecto abierto dice qué hacer", async () => {
    montar(null);
    expect(await screen.findByText(/Abra un proyecto en la barra superior/)).toBeInTheDocument();
  });

  test("un proyecto sin versiones pide guardar la del contrato", async () => {
    contexto = () => json({ ...CONTEXTO, versiones: [] });
    montar();
    expect(await screen.findByText(/no tiene versiones guardadas/)).toBeInTheDocument();
  });

  test("arranca con la versión más antigua, la cláusula, los componentes y las revaloradas", async () => {
    montar();
    expect(await screen.findByLabelText("Versión del contrato")).toHaveValue("001");
    expect(screen.getByText("Versiones revaloradas para la comprobación directa: 002")).toBeInTheDocument();
    expect(screen.getByLabelText("Periodicidad")).toHaveValue("mensual");
    expect(screen.getByLabelText("Componente, Componentes fila 2")).toHaveValue("equipos");
    expect(screen.getByLabelText("Componente, Componentes fila 2")).toHaveAttribute("readonly");
  });

  test("sin revaloradas avisa que la comprobación quedará no disponible", async () => {
    contexto = () => json({ ...CONTEXTO, versiones: [{ codigo: "001", motivo: "", revalorada: false }] });
    montar();
    expect(await screen.findByText(/ninguna \(la comprobación quedará «no disponible»\)/)).toBeInTheDocument();
  });

  test("calcular manda lo escrito y pinta la tabla lado a lado con el texto de la API", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await llenar(u);
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const tabla = await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect(within(tabla).getAllByText("15300.00").length).toBeGreaterThan(0);
    expect(within(tabla).getByText("Total")).toBeInTheDocument();
    const cuerpo = post("/v1/reajuste/calcular") as {
      proyecto: string;
      version: string;
      clausula: Record<string, string>;
      componentes: Record<string, string>[];
      periodos: Record<string, string>[];
      ejecutado: unknown[];
      con_valuaciones: boolean;
    };
    expect(cuerpo.proyecto).toBe("Contrato S1");
    expect(cuerpo.version).toBe("001");
    expect(cuerpo.clausula.fecha_inicio).toBe("2026-01-15");
    expect(cuerpo.clausula.duracion_meses).toBe("24");
    expect(cuerpo.clausula.r).toBe("0.10");
    expect(cuerpo.componentes[0]).toEqual({ componente: "materiales", serie: "FIC-MAT", peso: "" });
    expect(cuerpo.periodos).toEqual([
      { desde: "2027-02-01", hasta: "", version_comprobacion: "", excepcion: "" },
    ]);
    expect(cuerpo.ejecutado).toEqual([]);
    expect(cuerpo.con_valuaciones).toBe(false);
  });

  test("los avisos y el estudio parcial se dicen", async () => {
    calcular = () =>
      json(
        calculo({
          estado: "parcial al corte",
          avisos: ["La comprobación del periodo 2 no está disponible."],
          mensaje_parcial: "El ultimo periodo aun no cierra: el estudio se guardara «parcial al corte» al 10/02/2027.",
        }),
      );
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    expect(await screen.findByText(/La comprobación del periodo 2 no está disponible/)).toBeInTheDocument();
    expect(screen.getByText(/El ultimo periodo aun no cierra/)).toBeInTheDocument();
  });

  test("un dato malo muestra el mensaje de la API y no deja tabla", async () => {
    calcular = () => json({ detalle: "Escriba «Inicio del contrato»: es obligatorio (UC-18)." }, 422);
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    expect((await alertaConTexto()).textContent).toContain("Escriba «Inicio del contrato»");
    expect(screen.queryByRole("table", { name: "Escalatoria y comprobación, lado a lado" })).not.toBeInTheDocument();
  });

  test("cambiar un dato después de calcular retira la tabla: lo guardado sería otra cosa", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    await u.type(screen.getByLabelText("Duración (meses)"), "2");
    expect(screen.queryByRole("table", { name: "Escalatoria y comprobación, lado a lado" })).not.toBeInTheDocument();
  });

  test("guardar manda la fuente y el responsable y dice el número del estudio", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByLabelText("Fuente del estudio");
    await u.type(screen.getByLabelText("Fuente del estudio"), "memoria");
    await u.type(screen.getByLabelText("Responsable del estudio"), "Ing. Prueba");
    await u.click(screen.getByRole("button", { name: "Guardar estudio" }));
    expect(await screen.findByText("Estudio 7 guardado (cerrado).")).toBeInTheDocument();
    const cuerpo = post("/v1/reajuste/guardar") as Record<string, unknown>;
    expect(cuerpo.fuente).toBe("memoria");
    expect(cuerpo.responsable).toBe("Ing. Prueba");
    expect(cuerpo.reemplaza_a).toBeNull();
  });

  test("un cerrado puede reemplazar a un parcial y lo manda", async () => {
    calcular = () => json(calculo({ parciales: [{ id: 3, fecha_calculo: "2027-02-10" }] }));
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const lista = await screen.findByLabelText("Reemplaza al estudio parcial");
    expect(within(lista).getByRole("option", { name: "3 (calculado el 10/02/2027)" })).toBeInTheDocument();
    await u.selectOptions(lista, "3");
    await u.click(screen.getByRole("button", { name: "Guardar estudio" }));
    await screen.findByText(/guardado/);
    expect((post("/v1/reajuste/guardar") as Record<string, unknown>).reemplaza_a).toBe(3);
  });

  test("el Excel se descarga con el nombre que propone la API", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await u.click(await screen.findByRole("button", { name: "Descargar Excel" }));
    await waitFor(() => expect(guardado).toHaveBeenCalledWith("reajuste_001.xlsx"));
    expect((post("/v1/reajuste/excel") as Record<string, unknown>).proyecto).toBe("Contrato S1");
  });

  test("con las valuaciones desaparece la tabla de lo ejecutado y se avisa a la API", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    expect(screen.getByRole("table", { name: "Ejecutado" })).toBeInTheDocument();
    await u.click(screen.getByLabelText(/Tomar lo ejecutado de las valuaciones registradas/));
    expect(screen.queryByRole("table", { name: "Ejecutado" })).not.toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect((post("/v1/reajuste/calcular") as Record<string, unknown>).con_valuaciones).toBe(true);
  });

  test("agrega y quita filas de periodos", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await u.click(screen.getByRole("button", { name: "Agregar fila a Periodos" }));
    expect(screen.getByLabelText("Desde, Periodos fila 2")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Quitar Periodos fila 2" }));
    expect(screen.queryByLabelText("Desde, Periodos fila 2")).not.toBeInTheDocument();
  });

  test("un 401 avisa que la sesión venció", async () => {
    contexto = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
