import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { CarpetaRespuesta, SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { formulariosSucios, olvidarFormularios } from "../../shell/sucio";
import type { Evaluacion } from "./cliente";
import PaginaComponer from "./index";

// Plan de montar un presupuesto, Tarea 4 (MP-1, D-MP1 y D-MP2): Componer dice la moneda de la carpeta de trabajo
// (`GET /v1/carpeta`, T2), ofrece crear la lista para armar si falta y, antes de guardar, pregunta a
// `POST /v1/composicion/prever` (T3) si algún precio tecleado quedará como variante. Datos ficticios; oráculos
// escritos a mano con los textos del plan.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

const SIN_LISTA =
  "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o convirtiendo la que tiene.";
const OTRA_MONEDA = "La lista vigente «Base ficticia» está en USD y la carpeta trabaja en Bs: conviértala antes de armar.";

const CON_LISTA: CarpetaRespuesta = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
  aviso: null,
};
const SIN_LISTA_BS: CarpetaRespuesta = { moneda: "Bs", declarada: true, lista: null, aviso: SIN_LISTA };
const LISTA_EN_USD: CarpetaRespuesta = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Base ficticia", moneda: "USD", fecha: "2026-07-01", origen: "prueba" },
  aviso: OTRA_MONEDA,
};
const CREADA: CarpetaRespuesta = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "MaPreX ficticio en Bs al 26/10/2026", moneda: "Bs", fecha: "2026-10-26", origen: "derivada" },
  aviso: null,
};

const VACIA: Evaluacion = {
  estado: "vacio",
  aviso: "Comience por la cabecera (código y descripción) y declare al menos un insumo.",
  desglose: null,
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};

const VALIDA: Evaluacion = {
  estado: "valido",
  aviso: null,
  desglose: {
    materiales: "1500.00",
    equipos: "120.50",
    mano_obra: "300.00",
    costo_directo: "1920.50",
    con_administracion: "1958.91",
    precio_unitario: "2074.44",
  },
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};

const SIN_VARIANTES = {
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-26" },
  lista_nueva: false,
  variantes: [],
};
const CON_VARIANTE = {
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-26" },
  lista_nueva: false,
  variantes: [
    {
      descripcion: "Cemento gris",
      unidad: "saco",
      precio_en_lista: "18.00",
      precio_tecleado: "20.00",
      codigo_variante: "MAT-FIC-001-B",
    },
  ],
};

const GUARDADO = {
  precio_unitario: "2074.44",
  mensaje: "Composición guardada para la partida FIC-1: precio unitario 2.074,44.",
  justificada: false,
  avisos: [],
};

interface Llamada {
  ruta: string;
  metodo: string;
  cuerpo: Record<string, unknown> | null;
}

const ESPERA = { timeout: 3000 };

describe("Componer en la moneda de la carpeta de trabajo", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let llamadas: Llamada[];
  let carpeta: () => Response;
  let crearLista: (cuerpo: Record<string, unknown>) => Response;
  let prevision: () => Response;
  let guardado: () => Response;
  let evaluacion: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    llamadas = [];
    carpeta = () => json(CON_LISTA);
    crearLista = () => json(CREADA, 201);
    prevision = () => json(SIN_VARIANTES);
    guardado = () => json(GUARDADO);
    evaluacion = () => json(VACIA);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      const metodo = init?.method ?? "GET";
      const cuerpo = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : null;
      llamadas.push({ ruta, metodo, cuerpo });
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal", "destajo"] });
      if (ruta === "/v1/composicion/evaluar") return evaluacion();
      if (ruta.startsWith("/v1/composicion/partidas/")) {
        return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (ruta.startsWith("/v1/composicion/referencia") || ruta.startsWith("/v1/composicion/similares")) return json([]);
      if (ruta === "/v1/composicion/prever") return prevision();
      if (ruta === "/v1/composicion/guardar") return guardado();
      if (ruta === "/v1/carpeta" && metodo === "GET") return carpeta();
      if (ruta === "/v1/carpeta/lista-para-armar" && metodo === "POST") return crearLista(cuerpo ?? {});
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
    olvidarFormularios();
  });

  function de(ruta: string, metodo?: string): Llamada[] {
    return llamadas.filter((l) => l.ruta === ruta && (metodo === undefined || l.metodo === metodo));
  }

  function montar(ruta = "/componer", aplicacion: Partial<Aplicacion> = {}) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      ...aplicacion,
    };
    const vista = render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={[ruta]}>
          <Routes>
            <Route path="/componer" element={<PaginaComponer />} />
            <Route path="/hoja" element={<p>Pantalla ficticia de la Hoja</p>} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    return { ...vista, valor };
  }

  async function conCondiciones(u: ReturnType<typeof userEvent.setup>) {
    await u.type(screen.getByLabelText("Código"), "FIC-1");
    await u.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
  }

  // --- la moneda a la vista -------------------------------------------------------------------------

  test("dice «Precios en Bs» sobre las tablas y el precio unitario como «2.074,44 Bs»; no hay selector de moneda", async () => {
    const u = userEvent.setup();
    evaluacion = () => json(VALIDA);
    montar();
    const moneda = await screen.findByText("Precios en Bs", {}, ESPERA);
    const insumos = screen.getByRole("heading", { name: "Insumos" }).closest("section") as HTMLElement;
    expect(insumos).toContainElement(moneda);
    const materiales = screen.getByRole("table", { name: "Insumos: Materiales" });
    expect(moneda.compareDocumentPosition(materiales) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await u.type(screen.getByLabelText("Código"), "FIC-1");
    const desglose = await screen.findByRole("table", { name: "Desglose del precio unitario" }, ESPERA);
    const fila = within(desglose).getByText("Precio unitario").closest("tr") as HTMLElement;
    expect(within(fila).getByText("2.074,44 Bs")).toBeInTheDocument();
    // El exacto, tal como lo dio la API, sigue a un toque.
    expect(within(fila).getByText("2.074,44 Bs")).toHaveAttribute("title", "2074.44");
    expect(screen.queryByRole("combobox", { name: /moneda/i })).not.toBeInTheDocument();
    expect(de("/v1/carpeta", "GET")).toHaveLength(1);
    // La carpeta se lee de `/v1/carpeta`, no del resumen viejo de la carpeta.
    expect(llamadas.some((l) => l.ruta === "/v1/casos/actual")).toBe(false);
  });

  // --- sin lista para armar ------------------------------------------------------------------------

  test("sin lista para armar dice el aviso de la carpeta, ofrece crearla desde MaPreX y no guarda", async () => {
    const u = userEvent.setup();
    carpeta = () => json(SIN_LISTA_BS);
    montar();
    const aviso = await screen.findByText(SIN_LISTA, { exact: false }, ESPERA);
    // Va antes de la cabecera de la partida: se ve sin desplazarse.
    const cabecera = screen.getByRole("heading", { name: "Cabecera de la partida" });
    expect(aviso.compareDocumentPosition(cabecera) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("button", { name: "Crear la lista a partir de MaPreX" })).toBeEnabled();
    // Sin lista en otra moneda no hay nada que convertir.
    expect(screen.queryByRole("button", { name: "Convertir la lista que tiene" })).not.toBeInTheDocument();
    await conCondiciones(u);
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeDisabled();
  });

  test("«Crear la lista a partir de MaPreX» la pide a la carpeta y luego habilita Guardar", async () => {
    const u = userEvent.setup();
    carpeta = () => json(SIN_LISTA_BS);
    montar();
    await conCondiciones(u);
    await u.click(await screen.findByRole("button", { name: "Crear la lista a partir de MaPreX" }, ESPERA));
    await waitFor(() => expect(screen.getByRole("button", { name: "Guardar composición" })).toBeEnabled(), ESPERA);
    expect(de("/v1/carpeta/lista-para-armar", "POST").map((l) => l.cuerpo)).toEqual([{ desde: "maprex" }]);
    expect(screen.queryByText(SIN_LISTA, { exact: false })).not.toBeInTheDocument();
    // Lo dice y el foco no se pierde con el botón que desaparece.
    const hecho = screen.getByText("Lista para armar creada: MaPreX ficticio en Bs al 26/10/2026. Ya puede guardar la composición.");
    expect(hecho.closest("[tabindex='-1']")).toHaveFocus();
  });

  test("con la lista vigente en otra moneda ofrece también «Convertir la lista que tiene»", async () => {
    const u = userEvent.setup();
    carpeta = () => json(LISTA_EN_USD);
    crearLista = () => json({ ...CREADA, lista: { ...CREADA.lista!, nombre: "Base ficticia en Bs al 26/10/2026" } }, 201);
    montar();
    expect(await screen.findByText(OTRA_MONEDA, { exact: false }, ESPERA)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear la lista a partir de MaPreX" })).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Convertir la lista que tiene" }));
    await waitFor(() => expect(de("/v1/carpeta/lista-para-armar", "POST").map((l) => l.cuerpo)).toEqual([{ desde: "convertir" }]));
    expect(await screen.findByText(/Lista para armar creada: Base ficticia en Bs al 26\/10\/2026/, {}, ESPERA)).toBeInTheDocument();
  });

  test("si la lista no se puede crear dice por qué y el aviso sigue", async () => {
    const u = userEvent.setup();
    const SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.";
    carpeta = () => json({ ...SIN_LISTA_BS, moneda: "USD" });
    crearLista = () => json({ detalle: SIN_TASA }, 409);
    montar();
    // En una carpeta en USD, MaPreX (en Bs) se convierte: se dice antes de pulsar.
    expect(await screen.findByText(/se convertirán a USD con la tasa del BCV/, {}, ESPERA)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Crear la lista a partir de MaPreX" }));
    expect(await screen.findByText(SIN_TASA, {}, ESPERA)).toBeInTheDocument();
    expect(screen.getByText(SIN_LISTA, { exact: false })).toBeInTheDocument();
  });

  test("otro 409 (sin tasa) no se presenta como «Sin cambios» aunque al releer ya no haya aviso", async () => {
    const u = userEvent.setup();
    const SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.";
    carpeta = () => json({ ...SIN_LISTA_BS, moneda: "USD" });
    crearLista = () => json({ detalle: SIN_TASA }, 409);
    montar();
    const crear = await screen.findByRole("button", { name: "Crear la lista a partir de MaPreX" }, ESPERA);
    // Entretanto otra pestaña dejó la carpeta con lista: el aviso se va al releer.
    carpeta = () => json({ ...CON_LISTA, moneda: "USD", lista: { ...CON_LISTA.lista!, moneda: "USD" } });
    await u.click(crear);
    await waitFor(() => expect(de("/v1/carpeta", "GET")).toHaveLength(2), ESPERA);
    await waitFor(() => expect(screen.queryByText(SIN_LISTA, { exact: false })).not.toBeInTheDocument(), ESPERA);
    expect(screen.queryByText("Sin cambios")).not.toBeInTheDocument();
    expect(screen.queryByText(SIN_TASA)).not.toBeInTheDocument();
  });

  test("si la carpeta ya tenía lista (aviso viejo), el 409 relee la carpeta, quita el aviso y lo dice", async () => {
    const u = userEvent.setup();
    const YA_TIENE = "La carpeta de trabajo ya tiene lista para armar («Lista ficticia de Bs»): no se creó otra.";
    carpeta = () => json(SIN_LISTA_BS);
    crearLista = () => json({ detalle: YA_TIENE }, 409);
    montar();
    await conCondiciones(u);
    const crear = await screen.findByRole("button", { name: "Crear la lista a partir de MaPreX" }, ESPERA);
    // Mientras tanto, otra pestaña creó la lista.
    carpeta = () => json(CON_LISTA);
    await u.click(crear);
    await waitFor(() => expect(screen.queryByText(SIN_LISTA, { exact: false })).not.toBeInTheDocument(), ESPERA);
    expect(de("/v1/carpeta", "GET")).toHaveLength(2);
    const dicho = screen.getByText(YA_TIENE);
    expect(dicho.closest("[tabindex='-1']")).toHaveFocus();
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeEnabled();
  });

  test("ninguna cadena visible dice «caso»", async () => {
    carpeta = () => json(LISTA_EN_USD);
    montar();
    await screen.findByText(OTRA_MONEDA, { exact: false }, ESPERA);
    expect(document.body.textContent).not.toMatch(/caso/i);
  });

  // --- prever antes de guardar (D-MP2) ---------------------------------------------------------------

  test("Guardar pregunta primero a prever; con una variante abre el diálogo y «Volver» no guarda", async () => {
    const u = userEvent.setup();
    prevision = () => json(CON_VARIANTE);
    montar();
    await conCondiciones(u);
    const boton = screen.getByRole("button", { name: "Guardar composición" });
    await u.click(boton);
    const dialogo = await screen.findByRole("dialog", {}, ESPERA);
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(
      within(dialogo).getByText("“Cemento gris” ya está a 18,00 Bs; con 20,00 Bs se creará una variante solo para este APU."),
    ).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: "Volver" })).toHaveFocus();
    await u.click(within(dialogo).getByRole("button", { name: "Volver" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(de("/v1/composicion/prever", "POST")).toHaveLength(1);
    expect(de("/v1/composicion/guardar")).toHaveLength(0);
    expect(boton).toHaveFocus();
  });

  test("«Guardar así» guarda con el mismo cuerpo que se previó", async () => {
    const u = userEvent.setup();
    prevision = () => json(CON_VARIANTE);
    montar();
    await conCondiciones(u);
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    await u.click(await screen.findByRole("button", { name: "Guardar así" }, ESPERA));
    expect(await screen.findByText(GUARDADO.mensaje, {}, ESPERA)).toBeInTheDocument();
    const [previsto] = de("/v1/composicion/prever", "POST");
    const [guardadoEnviado] = de("/v1/composicion/guardar", "POST");
    expect(guardadoEnviado.cuerpo).toEqual(previsto.cuerpo);
    expect(previsto.cuerpo).toMatchObject({ codigo: "FIC-1", condiciones: "Condiciones ficticias", justificacion: null });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("sin variantes guarda de una vez, después de prever", async () => {
    const u = userEvent.setup();
    montar();
    await conCondiciones(u);
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    expect(await screen.findByText(GUARDADO.mensaje, {}, ESPERA)).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const orden = llamadas.filter((l) => l.metodo === "POST" && /prever|guardar/.test(l.ruta)).map((l) => l.ruta);
    expect(orden).toEqual(["/v1/composicion/prever", "/v1/composicion/guardar"]);
  });

  test("foco 1: si prever responde 409 por la moneda, lo dice, no guarda y vuelve a leer la carpeta", async () => {
    const u = userEvent.setup();
    prevision = () => json({ detalle: OTRA_MONEDA }, 409);
    montar();
    await conCondiciones(u);
    carpeta = () => json(LISTA_EN_USD);
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    expect(await screen.findAllByText(OTRA_MONEDA, { exact: false }, ESPERA)).not.toHaveLength(0);
    expect(de("/v1/composicion/guardar")).toHaveLength(0);
    // La carpeta se relee: el aviso con sus salidas aparece arriba.
    expect(await screen.findByRole("button", { name: "Convertir la lista que tiene" }, ESPERA)).toBeInTheDocument();
  });

  // --- cambios sin guardar (foco 2) -------------------------------------------------------------------

  test("con una fila escrita queda registrada como cambios sin guardar; al guardar, ya no", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByText("Precios en Bs", {}, ESPERA);
    expect(formulariosSucios()).toEqual([]);
    await u.click(screen.getByRole("button", { name: "Agregar fila a Materiales" }));
    // Una fila agregada y vacía todavía no tiene nada que perder.
    expect(formulariosSucios()).toEqual([]);
    await u.type(screen.getByLabelText("Descripción, fila 1"), "Arena ficticia");
    expect(formulariosSucios()).toEqual(["componer"]);
    await u.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    await screen.findByText(GUARDADO.mensaje, {}, ESPERA);
    expect(formulariosSucios()).toEqual([]);
    // Otro cambio después de guardar vuelve a ser trabajo sin guardar.
    await u.type(screen.getByLabelText("Descripción, fila 1"), " lavada");
    expect(formulariosSucios()).toEqual(["componer"]);
  });

  test("al vaciar lo escrito deja de haber cambios sin guardar", async () => {
    const u = userEvent.setup();
    montar();
    await u.type(screen.getByLabelText("Unidad"), "m2");
    expect(formulariosSucios()).toEqual(["componer"]);
    await u.clear(screen.getByLabelText("Unidad"));
    expect(formulariosSucios()).toEqual([]);
  });

  // --- desde la Hoja ---------------------------------------------------------------------------------

  // F4, Tarea 9, baja 21: Componer se abre en panel desde «Agregar partida», sin salir de la obra; la pantalla sola ya no
  // ofrece volver a la Hoja, ni aunque la dirección traiga `volver=hoja`.
  test("con ?codigo=OBRA-07&volver=hoja llega con el código y, guardada, no ofrece «Volver a la Hoja»", async () => {
    const u = userEvent.setup();
    montar("/componer?codigo=OBRA-07&volver=hoja");
    expect(screen.getByLabelText("Código")).toHaveValue("OBRA-07");
    await waitFor(() => expect(de("/v1/composicion/partidas/OBRA-07")).toHaveLength(1), ESPERA);
    // Lo que trajo la Hoja no es trabajo de la persona.
    expect(formulariosSucios()).toEqual([]);
    expect(screen.queryByRole("button", { name: "Volver a la Hoja" })).not.toBeInTheDocument();
    await u.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    await screen.findByText(GUARDADO.mensaje, {}, ESPERA);
    expect(de("/v1/composicion/guardar")[0].cuerpo).toMatchObject({ codigo: "OBRA-07" });
    expect(screen.queryByRole("button", { name: "Volver a la Hoja" })).not.toBeInTheDocument();
  });

  test("sin volver=hoja, guardada, no ofrece volver a la Hoja", async () => {
    const u = userEvent.setup();
    montar();
    await conCondiciones(u);
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    await screen.findByText(GUARDADO.mensaje, {}, ESPERA);
    expect(screen.queryByRole("button", { name: "Volver a la Hoja" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Elaborar un presupuesto" })).toBeInTheDocument();
  });

  // --- contrato real de T2 ---------------------------------------------------------------------------

  test("con la respuesta real de /v1/carpeta (USD, vigente «Base» en Bs) ofrece convertir y, convertida, guarda", async () => {
    // La forma exacta que da la API (tests/unit/test_api_carpeta.py,
    // test_carpeta_usd_con_lista_vigente_en_bs_avisa_y_la_muestra_para_convertir).
    const u = userEvent.setup();
    const AVISO_REAL = "La lista vigente «Base» está en Bs y la carpeta trabaja en USD: conviértala antes de armar.";
    carpeta = () =>
      json({
        moneda: "USD",
        declarada: true,
        lista: { nombre: "Base", moneda: "Bs", fecha: "2026-07-01", origen: "prueba" },
        aviso: AVISO_REAL,
      });
    crearLista = () =>
      json(
        {
          moneda: "USD",
          declarada: true,
          lista: { nombre: "Base en USD al 26/10/2026", moneda: "USD", fecha: "2026-10-26", origen: "derivada" },
          aviso: null,
        },
        201,
      );
    montar();
    expect(await screen.findByText(AVISO_REAL, { exact: false }, ESPERA)).toBeInTheDocument();
    expect(screen.getByText("Precios en USD")).toBeInTheDocument();
    expect(screen.getByText(/Convertir pasa los precios de «Base» de Bs a USD con la tasa del BCV/)).toBeInTheDocument();
    await conCondiciones(u);
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeDisabled();
    await u.click(screen.getByRole("button", { name: "Convertir la lista que tiene" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Guardar composición" })).toBeEnabled(), ESPERA);
    expect(de("/v1/carpeta/lista-para-armar", "POST").map((l) => l.cuerpo)).toEqual([{ desde: "convertir" }]);
    expect(
      screen.getByText("Lista para armar creada: Base en USD al 26/10/2026. Ya puede guardar la composición."),
    ).toBeInTheDocument();
  });
});
