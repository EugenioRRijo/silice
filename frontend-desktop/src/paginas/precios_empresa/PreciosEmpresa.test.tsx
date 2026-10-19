import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaPreciosEmpresa from "./index";
import type { Estado, Hallazgos, ListaCreada } from "./logica";
import { hoyIso } from "./logica";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Administrador",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_precios"],
  modo_entrega: false,
};

const SOLO_BASES: Estado = {
  bases: [
    { id: 2, nombre: "MaPreX julio 2026 en Bs", moneda: "Bs" },
    { id: 1, nombre: "Linea base 01/01/2026", moneda: "USD" },
  ],
  listas: [],
};
const CON_LISTA: Estado = { ...SOLO_BASES, listas: [{ id: 5, nombre: "Contratista Demo, C.A. 2026-09-20" }] };

const CREADA: ListaCreada = {
  nombre: "Contratista Demo, C.A. 2026-09-20",
  propios: 10,
  desconocidos: [],
  mensaje: "Lista «Contratista Demo, C.A. 2026-09-20» creada con 10 precios propios.",
  aviso: null,
};

const HALLAZGOS: Hallazgos = {
  columnas: ["Regla", "Severidad", "Descripción", "Impacto"],
  filas: [
    { Regla: "R11", Severidad: "ADVERTENCIA", Descripción: "ARENA LAVADA: precio vencido", Impacto: "11328.78" },
    { Regla: "R12", Severidad: "ERROR", Descripción: "PEGAMENTO: fuera de rango", Impacto: "" },
  ],
  nota: "Sin version, el impacto es por unidad de insumo. Nada de esto se guarda.",
};

describe("Precios de la empresa", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let estado: () => Response;
  let referencia: () => Response;
  let crear: () => Response;
  let hallazgos: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    estado = () => json(SOLO_BASES);
    referencia = () => json({ mensaje: "Referencia «MaPreX julio 2026 en Bs» cargada con 111 precios." });
    crear = () => json(CREADA, 201);
    hallazgos = () => json(HALLAZGOS);
    fetchFalso.mockImplementation(async (ruta, opciones) => {
      const url = String(ruta);
      const metodo = opciones?.method ?? "GET";
      if (url === "/v1/precios-empresa" && metodo === "GET") return estado();
      if (url === "/v1/precios-empresa/referencia" && metodo === "POST") return referencia();
      if (url === "/v1/precios-empresa/listas" && metodo === "POST") return crear();
      if (url.includes("/hallazgos?fecha=")) return hallazgos();
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
        <PaginaPreciosEmpresa />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  function llamadas(fragmento: string, metodo = "GET") {
    return fetchFalso.mock.calls.filter(
      ([ruta, o]) => String(ruta).includes(fragmento) && (o?.method ?? "GET") === metodo,
    );
  }

  function lecturasDelEstado() {
    return fetchFalso.mock.calls.filter(([ruta, o]) => String(ruta) === "/v1/precios-empresa" && (o?.method ?? "GET") === "GET");
  }

  function campoArchivo(): HTMLInputElement {
    return document.querySelector('input[type="file"]') as HTMLInputElement;
  }

  async function llenarYEnviar(moneda: string | null = "Bs", conArchivo = true) {
    const usuario = userEvent.setup();
    await screen.findByLabelText("Empresa (nombre)");
    await usuario.type(screen.getByLabelText("Empresa (nombre)"), "Contratista Demo, C.A.");
    await usuario.type(screen.getByLabelText("RIF"), "J-00000000-0");
    await usuario.type(screen.getByLabelText("Fuente de la lista (de donde salen estos precios)"), "lista interna 2026-09");
    if (moneda) await usuario.selectOptions(screen.getByLabelText("Moneda de la lista"), moneda);
    if (conArchivo) await usuario.upload(campoArchivo(), new File(["tipo,insumo"], "precios.csv"));
    await usuario.click(screen.getByRole("button", { name: "Crear la lista de la empresa" }));
    return usuario;
  }

  test("muestra la ayuda, las tres secciones y las listas base como «nombre (moneda)»", async () => {
    montar();
    expect(await screen.findByRole("option", { name: "MaPreX julio 2026 en Bs (Bs)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Linea base 01/01/2026 (USD)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Precios de la empresa" })).toBeInTheDocument();
    expect(screen.getByText(/La lista de su empresa: una copia de la lista base/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "1. La referencia MaPreX en bolivares" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2. La lista de la empresa" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "3. Precios vencidos o fuera de rango (R11 y R12)" })).toBeInTheDocument();
    expect(screen.getByLabelText("Fecha de la lista")).toHaveValue(hoyIso());
    expect(screen.getByLabelText("Moneda de la lista")).toHaveValue("");
    expect(screen.getByText("Todavia no hay listas de empresa en este caso.")).toBeInTheDocument();
  });

  test("sin listas de precios en el caso no ofrece el formulario", async () => {
    estado = () => json({ bases: [], listas: [] });
    montar();
    expect(await screen.findByText("El caso no tiene listas de precios: cargue una en Actualizar precios.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear la lista de la empresa" })).toBeNull();
    expect(screen.getByRole("button", { name: "Cargar la referencia MaPreX en Bs" })).toBeInTheDocument();
  });

  test("un fallo al leer el caso se muestra con su detalle", async () => {
    estado = () => json({ detalle: "No se pudo leer o escribir el caso abierto." }, 503);
    montar();
    expect(await screen.findByText("No se pudo leer o escribir el caso abierto.")).toBeInTheDocument();
  });

  test("la sesion vencida avisa al shell", async () => {
    estado = () => json({ detalle: "Sesion vencida." }, 401);
    const alExpirar = montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("carga la referencia, muestra el mensaje y vuelve a leer las bases", async () => {
    montar();
    const usuario = userEvent.setup();
    await usuario.click(await screen.findByRole("button", { name: "Cargar la referencia MaPreX en Bs" }));
    expect(await screen.findByText("Referencia «MaPreX julio 2026 en Bs» cargada con 111 precios.")).toBeInTheDocument();
    expect(llamadas("/v1/precios-empresa/referencia", "POST")).toHaveLength(1);
    await waitFor(() => expect(lecturasDelEstado()).toHaveLength(2));
  });

  test("un error al cargar la referencia sale como aviso", async () => {
    referencia = () => json({ detalle: "No se cargo la referencia: algo ficticio." }, 422);
    montar();
    const usuario = userEvent.setup();
    await usuario.click(await screen.findByRole("button", { name: "Cargar la referencia MaPreX en Bs" }));
    expect(await screen.findByText("No se cargo la referencia: algo ficticio.")).toBeInTheDocument();
  });

  test.each([
    ["moneda", null, true],
    ["archivo", "Bs", false],
  ])("sin %s no se envia nada y se dice por que", async (_nombre, moneda, conArchivo) => {
    montar();
    await llenarYEnviar(moneda, conArchivo);
    expect(
      await screen.findByText("Elija la moneda de la lista y el archivo de precios: no tienen valor por defecto."),
    ).toBeInTheDocument();
    expect(llamadas("/v1/precios-empresa/listas", "POST")).toHaveLength(0);
  });

  test("crea la lista: manda el formulario, muestra el mensaje y vuelve a leer las listas", async () => {
    montar();
    await screen.findByLabelText("Empresa (nombre)");
    estado = () => json(CON_LISTA);
    await llenarYEnviar();
    expect(await screen.findByText(CREADA.mensaje)).toBeInTheDocument();
    const [, opciones] = llamadas("/v1/precios-empresa/listas", "POST")[0];
    const cuerpo = opciones?.body as FormData;
    expect(cuerpo.get("empresa")).toBe("Contratista Demo, C.A.");
    expect(cuerpo.get("rif")).toBe("J-00000000-0");
    expect(cuerpo.get("base_id")).toBe("2");
    expect(cuerpo.get("moneda")).toBe("Bs");
    expect(cuerpo.get("fecha")).toBe(hoyIso());
    expect(cuerpo.get("fuente")).toBe("lista interna 2026-09");
    expect(cuerpo.get("nombre")).toBe("");
    expect((cuerpo.get("archivo") as File).name).toBe("precios.csv");
    // la lista nueva ya aparece en la seccion 3 y se piden sus hallazgos
    expect(await screen.findByRole("option", { name: "Contratista Demo, C.A. 2026-09-20" })).toBeInTheDocument();
    await waitFor(() => expect(llamadas("/listas/5/hallazgos?fecha=")).toHaveLength(1));
  });

  test("los insumos desconocidos se avisan y se listan sin darlos de alta", async () => {
    crear = () =>
      json(
        {
          ...CREADA,
          propios: 1,
          desconocidos: ["INSUMO INEXISTENTE DEMO"],
          mensaje: "Lista «X» creada con 1 precios propios.",
          aviso: "Estos insumos no estan en el catalogo y no entraron a la lista (UC-17 4a):",
        },
        201,
      );
    montar();
    await llenarYEnviar();
    expect(await screen.findByText("Estos insumos no estan en el catalogo y no entraron a la lista (UC-17 4a):")).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Insumos que no entraron a la lista" });
    expect(within(tabla).getByText("INSUMO INEXISTENTE DEMO")).toBeInTheDocument();
  });

  test("un rechazo del servidor sale como aviso con su detalle", async () => {
    crear = () => json({ detalle: "No se creo la lista: moneda 'EUR': la lista se rechaza (UC-17 4b)" }, 422);
    montar();
    await llenarYEnviar();
    expect(await screen.findByText(/No se creo la lista: moneda 'EUR'/)).toBeInTheDocument();
    expect(screen.queryByText(/creada con/)).toBeNull();
  });

  test("los hallazgos se piden con la fecha de evaluacion y se muestran tal cual llegan", async () => {
    estado = () => json(CON_LISTA);
    montar();
    expect(await screen.findByText("ARENA LAVADA: precio vencido")).toBeInTheDocument();
    const [ruta] = llamadas("/listas/5/hallazgos?fecha=")[0];
    expect(String(ruta)).toBe(`/v1/precios-empresa/listas/5/hallazgos?fecha=${hoyIso()}`);
    expect(screen.getByText("11328.78")).toBeInTheDocument();
    expect(screen.getByText("Sin version, el impacto es por unidad de insumo. Nada de esto se guarda.")).toBeInTheDocument();
    expect(screen.getByText("Advertencia")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
    const usuario = userEvent.setup();
    const fecha = screen.getByLabelText("Fecha de evaluacion");
    await usuario.clear(fecha);
    await usuario.type(fecha, "2026-10-01");
    await waitFor(() => expect(llamadas("/listas/5/hallazgos?fecha=2026-10-01")).toHaveLength(1));
  });

  test("un error al leer los hallazgos sale como aviso", async () => {
    estado = () => json(CON_LISTA);
    hallazgos = () => json({ detalle: "la lista 5 no es una lista de empresa de este caso" }, 404);
    montar();
    expect(await screen.findByText("la lista 5 no es una lista de empresa de este caso")).toBeInTheDocument();
  });

  test("nada de lo escrito queda en el almacenamiento del navegador", async () => {
    montar();
    await llenarYEnviar();
    await screen.findByText(CREADA.mensaje);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});
