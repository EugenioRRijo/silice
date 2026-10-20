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

  type Usuario = ReturnType<typeof userEvent.setup>;
  async function irA(u: Usuario, paso: "1. La cláusula" | "2. Períodos y lo ejecutado") {
    await u.click(screen.getByRole("tab", { name: paso }));
  }

  async function llenar(u: ReturnType<typeof userEvent.setup>) {
    await u.type(screen.getByLabelText("Inicio del contrato"), "2026-01-15");
    await u.type(screen.getByLabelText("Duración (meses)"), "24");
    await u.type(screen.getByLabelText("R (fracción no reajustable)"), "0.10");
    await u.type(screen.getByLabelText("Serie, Componentes fila 1"), "FIC-MAT");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.type(screen.getByLabelText("Desde, Períodos fila 1"), "2027-02-01");
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
    const u = userEvent.setup();
    montar();
    expect(await screen.findByLabelText("Versión del contrato")).toHaveValue("001");
    expect(screen.getByLabelText("Periodicidad")).toHaveValue("mensual");
    expect(screen.getByLabelText("Componente, Componentes fila 2")).toHaveValue("Equipos");
    expect(screen.getByLabelText("Componente, Componentes fila 2")).toHaveAttribute("readonly");
    await irA(u, "2. Períodos y lo ejecutado");
    expect(screen.getByText("Versiones revaloradas para la comprobación directa: 002")).toBeInTheDocument();
  });

  test("los textos visibles no llevan jerga interna de las especificaciones (V-17)", async () => {
    montar();
    await screen.findByLabelText("Versión del contrato");
    const visible = document.body.textContent ?? "";
    expect(visible).not.toMatch(/S1 §|S1-R\d+|\(I0\)/);
    expect(screen.getByText(/La cláusula de reajuste \(a cotejar con la Gaceta\)/)).toBeInTheDocument();
  });
  test("los desplegables y los componentes muestran rótulos en español y mandan el valor interno (VB-5)", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    const visible = () => document.body.textContent ?? "";
    expect(visible()).not.toMatch(/comprobacion|por_partida|mano_obra/);
    expect(screen.getByLabelText("Componente, Componentes fila 3")).toHaveValue("Mano de obra");
    const mecanismo = screen.getByLabelText("Mecanismo");
    expect(within(mecanismo).getByRole("option", { name: "Comprobación directa" })).toHaveValue("comprobacion");
    expect(within(mecanismo).getByRole("option", { name: "Ambos (escalatoria y comprobación)" })).toHaveValue("ambos");
    const estructura = screen.getByLabelText("Estructura");
    expect(within(estructura).getByRole("option", { name: "Por partida" })).toHaveValue("por_partida");
    expect(within(screen.getByLabelText("Periodicidad")).getByRole("option", { name: "Mensual" })).toHaveValue("mensual");
    expect(within(screen.getByLabelText(/Mecanismo pagadero/)).getByRole("option", { name: "Ninguno" })).toHaveValue("");
    await u.selectOptions(mecanismo, "Comprobación directa");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    const cuerpo = post("/v1/reajuste/calcular") as { clausula: Record<string, string>; componentes: Record<string, string>[] };
    expect(cuerpo.clausula.mecanismo).toBe("comprobacion");
    expect(cuerpo.componentes[2]).toEqual({ componente: "mano_obra", serie: "", peso: "" });
  });

  test("sin revaloradas avisa que la comprobación quedará no disponible", async () => {
    contexto = () => json({ ...CONTEXTO, versiones: [{ codigo: "001", motivo: "", revalorada: false }] });
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    expect(await screen.findByText(/ninguna \(la comprobación quedará «no disponible»\)/)).toBeInTheDocument();
  });

  test("calcular manda lo escrito y pinta la tabla lado a lado con el texto de la API", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await llenar(u);
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const tabla = await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect(within(tabla).getAllByText("15.300,00").length).toBeGreaterThan(0);
    expect(within(tabla).getAllByText("15.300,00")[0]).toHaveAttribute("title", "15300.00");
    expect(within(tabla).queryByText("15300.00")).toBeNull();
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

  test("el resultado va en dos tablas cortas y las marcas como nota por período (VB-10)", async () => {
    // Las 12 columnas y las filas tal como las manda la API (aplicacion/reajuste.COLUMNAS_REAJUSTE); los oraculos
    // 15.300,00 / 16.000,00 / -0,82 son los de tests/unit/test_ui_reajuste.py.
    const columnas = ["Período", "Escalatoria", "Comprobación", "Diferencia", "Reconocido", "Mecanismo", "Moneda", "Escalatoria (otra)", "Comprobación (otra)", "Diferencia (otra)", "Tasa", "Marcas"];
    const periodo = {
      Período: "01/02/2027 a 28/02/2027", Escalatoria: "15300.00", Comprobación: "16000.00", Diferencia: "700.00",
      Reconocido: "15300.00", Mecanismo: "escalatoria", Moneda: "Bs", "Escalatoria (otra)": "17.88",
      "Comprobación (otra)": "18.70", "Diferencia (otra)": "-0.82", Tasa: "855.70", Marcas: "precios fijos el primer año (art. 134, a cotejar)",
    };
    const total = { ...periodo, Período: "Total", Mecanismo: "", Tasa: "", Marcas: "estado: cerrado; Nota de reconsideración" };
    calcular = () => json(calculo({ columnas, filas: [periodo, total], avisos: ["Nota de reconsideración"] }));
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const principal = await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect(within(principal).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Período", "Escalatoria", "Comprobación", "Diferencia", "Reconocido", "Mecanismo", "Moneda",
    ]);
    expect(within(principal).getAllByText("15.300,00")[0]).toHaveAttribute("title", "15300.00");
    expect(within(principal).getAllByText("16.000,00")[0]).toHaveAttribute("title", "16000.00");
    expect(within(principal).getByTitle("escalatoria")).toHaveTextContent("Escalatoria");
    const otra = screen.getByRole("table", { name: "En la otra moneda" });
    expect(within(otra).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Período", "Escalatoria", "Comprobación", "Diferencia", "Tasa",
    ]);
    expect(within(otra).getAllByText("-0,82")[0]).toHaveAttribute("title", "-0.82");
    expect(screen.queryByRole("columnheader", { name: "Marcas" })).toBeNull();
    const marcas = screen.getByRole("list", { name: "Marcas por período" });
    expect(within(marcas).getAllByRole("listitem").map((l) => l.textContent)).toEqual([
      "01/02/2027 a 28/02/2027: precios fijos el primer año (art. 134, a cotejar)",
    ]);
    expect(screen.getByText("Estado del estudio: cerrado.")).toBeInTheDocument();
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
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    expect(await screen.findByText(/La comprobación del periodo 2 no está disponible/)).toBeInTheDocument();
    expect(screen.getByText(/El ultimo periodo aun no cierra/)).toBeInTheDocument();
  });

  test("un dato malo muestra el mensaje de la API y no deja tabla", async () => {
    calcular = () => json({ detalle: "Escriba «Inicio del contrato»: es obligatorio (UC-18)." }, 422);
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    expect((await alertaConTexto()).textContent).toContain("Escriba «Inicio del contrato»");
    expect(screen.queryByRole("table", { name: "Escalatoria y comprobación, lado a lado" })).not.toBeInTheDocument();
  });

  test("tras calcular, el foco va al título del resultado (VB-13)", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const titulo = await screen.findByRole("heading", { name: "Escalatoria y comprobación, lado a lado" });
    await waitFor(() => expect(titulo).toHaveFocus());
  });

  test("tras calcular con un dato malo, el foco va al aviso de error (VB-13)", async () => {
    calcular = () => json({ detalle: "Escriba «Inicio del contrato»: es obligatorio." }, 422);
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const aviso = await alertaConTexto();
    await waitFor(() => expect(document.activeElement).not.toBe(document.body));
    expect(document.activeElement?.contains(aviso)).toBe(true);
  });

  test("las fechas ISO de los mensajes y avisos del núcleo se leen en dd/mm/aaaa (VB-19)", async () => {
    calcular = () =>
      json({ detalle: "No se pudo calcular: el periodo 2027-02-01–2027-03-31 cruza el aniversario 2027-01-15: partalo (UC-18 3b)" }, 422);
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    expect((await alertaConTexto()).textContent).toContain("el periodo 01/02/2027–31/03/2027 cruza el aniversario 15/01/2027");
    calcular = () => json(calculo({ avisos: ["La tasa del 2027-02-28 es provisional."] }));
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    expect(await screen.findByText("La tasa del 28/02/2027 es provisional.")).toBeInTheDocument();
  });

  test("cambiar un dato después de calcular retira la tabla: lo guardado sería otra cosa", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    await irA(u, "1. La cláusula");
    await u.type(screen.getByLabelText("Duración (meses)"), "2");
    expect(screen.queryByRole("table", { name: "Escalatoria y comprobación, lado a lado" })).not.toBeInTheDocument();
  });

  test("guardar manda la fuente y el responsable y dice el número del estudio", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
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
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    const lista = await screen.findByLabelText("Reemplaza al estudio parcial");
    expect(within(lista).getByRole("option", { name: "3 (calculado el 10/02/2027)" })).toBeInTheDocument();
    await u.selectOptions(lista, "3");
    await u.click(screen.getByRole("button", { name: "Guardar estudio" }));
    await screen.findByText(/guardado/);
    expect((post("/v1/reajuste/guardar") as Record<string, unknown>).reemplaza_a).toBe(3);
  });

  test("tras guardar, el boton se apaga hasta que se edite algo (no hay estudios duplicados)", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await u.click(await screen.findByRole("button", { name: "Guardar estudio" }));
    await screen.findByText("Estudio 7 guardado (cerrado).");
    expect(screen.getByRole("button", { name: "Guardar estudio" })).toBeDisabled();
  });

  test("una respuesta que llega despues de editar se descarta: no queda una tabla vieja", async () => {
    let soltar: (r: Response) => void = () => undefined;
    calcular = () => new Promise<Response>((resolver) => (soltar = resolver)) as unknown as Response;
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await irA(u, "1. La cláusula");
    await u.type(screen.getByLabelText("Duración (meses)"), "2");
    soltar(json(calculo()));
    await irA(u, "2. Períodos y lo ejecutado");
    await waitFor(() => expect(screen.getByRole("button", { name: "Calcular" })).toBeEnabled());
    expect(screen.queryByRole("table", { name: "Escalatoria y comprobación, lado a lado" })).not.toBeInTheDocument();
  });

  test("el Excel se descarga con el nombre que propone la API", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await u.click(await screen.findByRole("button", { name: "Descargar Excel" }));
    await waitFor(() => expect(guardado).toHaveBeenCalledWith("reajuste_001.xlsx"));
    expect((post("/v1/reajuste/excel") as Record<string, unknown>).proyecto).toBe("Contrato S1");
  });

  test("con las valuaciones desaparece la tabla de lo ejecutado y se avisa a la API", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
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
    await irA(u, "2. Períodos y lo ejecutado");
    await u.click(screen.getByRole("button", { name: "Agregar fila a Períodos" }));
    expect(screen.getByLabelText("Desde, Períodos fila 2")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Quitar Períodos fila 2" }));
    expect(screen.queryByLabelText("Desde, Períodos fila 2")).not.toBeInTheDocument();
  });

  test("un 401 avisa que la sesión venció", async () => {
    contexto = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("las fechas usan el selector de fecha y el formulario se agrupa en pasos", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    for (const nombre of ["Inicio del contrato", "El primer año corre desde", "Mes base de los índices"]) {
      expect(screen.getByLabelText(nombre)).toHaveAttribute("type", "date");
    }
    expect(screen.getByRole("tab", { name: "1. La cláusula" })).toBeInTheDocument();
    await irA(u, "2. Períodos y lo ejecutado");
    for (const nombre of ["Desde, Períodos fila 1", "Hasta, Períodos fila 1"]) {
      expect(screen.getByLabelText(nombre)).toHaveAttribute("type", "date");
    }
    expect(document.body.textContent).not.toContain("AAAA-MM-DD");
  });

  test("Período con tilde en la interfaz", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByLabelText("Versión del contrato");
    await irA(u, "2. Períodos y lo ejecutado");
    expect(screen.queryAllByText(/Periodos?/)).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Agregar fila a Períodos" })).toBeInTheDocument();
  });
});
