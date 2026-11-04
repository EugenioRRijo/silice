import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, PendienteDeObra, SesionRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { BarraLateral } from "./BarraLateral";
import type { SeccionId } from "./secciones";
import { ContextoPendientes } from "./usePendientes";
import type { PendientesDelMarco } from "./usePendientes";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosBienvenida.test.ts).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const leer = (ruta: string) => fs.readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

// Bloque `{ … }` que sigue a `apertura` en un fuente SCSS, con sus llaves anidadas.
const bloque = (fuente: string, apertura: string) => {
  const i = fuente.indexOf(apertura);
  if (i < 0) return "";
  let nivel = 0;
  for (let j = fuente.indexOf("{", i); j < fuente.length; j++) {
    if (fuente[j] === "{") nivel++;
    if (fuente[j] === "}" && --nivel === 0) return fuente.slice(i, j + 1);
  }
  return "";
};
const regla = (fuente: string, selector: string) => bloque(fuente, `${selector} {`);

// Carpetas y obras inventadas.
const NORTE = "Carpeta Norte.db";
const SUR = "Carpeta Sur.db";
function obra(carpeta: string | null, obra_id: number, nombre: string): ObraDeCarpetaRespuesta {
  const titulo = carpeta === null ? "Carpeta de la empresa" : carpeta.replace(/\.db$/, "");
  return { carpeta, carpeta_titulo: titulo, obra_id, obra: nombre, version_codigo: null };
}
const CLINICA = obra(NORTE, 1, "Clínica Las Mercedes");
const TORRE = obra(NORTE, 2, "Torre B");
const GALPON = obra(SUR, 3, "Galpón Sur");

// Las obras de la carpeta abierta que ya tienen tramos viales guardados (`GET /v1/vial/obras`).
let vialesDelServidor: number[] = [];

let respuesta:
  | { carpeta_actual: string | null; carpeta_actual_titulo: string; obras: ObraDeCarpetaRespuesta[] }
  | ErrorDeApi;

// El título de la carpeta abierta lo da el servidor; por omisión el mismo que le daría a una carpeta con obras.
function servidor(obras: ObraDeCarpetaRespuesta[], carpetaActual: string | null = NORTE, titulo?: string) {
  const deLaCarpeta = carpetaActual === null ? "Carpeta de la empresa" : carpetaActual.replace(/\.db$/, "");
  respuesta = { carpeta_actual: carpetaActual, carpeta_actual_titulo: titulo ?? deLaCarpeta, obras };
}

beforeEach(() => {
  servidor([CLINICA, TORRE, GALPON]);
  vialesDelServidor = [];
  pedirFalso.mockReset();
  pedirFalso.mockImplementation(async (ruta: string) => {
    if (ruta === "/v1/obras/todas") {
      if (respuesta instanceof ErrorDeApi) throw respuesta;
      return respuesta;
    }
    if (ruta === "/v1/vial/obras") return { obras: vialesDelServidor };
    if (ruta === "/v1/carpeta") return { moneda: "Bs", declarada: true, lista: null, aviso: null };
    throw new Error(`petición inesperada: ${ruta}`);
  });
});

interface Opciones {
  sesion?: SesionRespuesta;
  abierta?: { carpeta: string | null; obraId: number } | null;
  seccion?: SeccionId | null;
  ruta?: string;
  // Lo que el marco ya cargó de los pendientes; por omisión, ninguno.
  pendientes?: PendientesDelMarco;
}

const SIN_PENDIENTES: PendientesDelMarco = { estado: "listo", pendientes: [], carpetasOmitidas: 0, recargar: vi.fn() };

function Ubicacion() {
  return <output data-testid="ubicacion">{useLocation().pathname}</output>;
}

function pintar({
  sesion = sesionDe("ana"),
  abierta = null,
  seccion = null,
  ruta = "/pendientes",
  pendientes = SIN_PENDIENTES,
}: Opciones = {}) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <ContextoAplicacion.Provider
        value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <ContextoPendientes.Provider value={pendientes}>
          <BarraLateral obraAbierta={abierta} seccion={seccion} />
        </ContextoPendientes.Provider>
        <Ubicacion />
      </ContextoAplicacion.Provider>
    </MemoryRouter>,
  );
}

const arbol = () => screen.findByRole("tree", { name: "Obras" });

describe("BarraLateral: árbol sin carpetas (D-F3-3)", () => {
  it("con obras de dos carpetas no hay grupos por carpeta: las obras salen por nombre, seguidas", async () => {
    pintar();
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem").map((e) => e.textContent)).toEqual([
      "Clínica Las Mercedes",
      "Galpón Sur",
      "Torre B",
    ]);
    expect(screen.queryByRole("group", { name: "Carpeta Norte" })).toBeNull();
    expect(screen.queryByRole("group", { name: "Carpeta Sur" })).toBeNull();
    expect(document.body.textContent).not.toContain("Carpeta Norte");
    expect(document.body.textContent).not.toContain("Carpeta Sur");
  });

  it("con una sola carpeta no hay grupos ni se nombra la carpeta", async () => {
    servidor([CLINICA, TORRE]);
    pintar();
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem")).toHaveLength(2);
    expect(screen.queryByRole("group", { name: "Carpeta Norte" })).toBeNull();
    expect(document.body.textContent).not.toContain("Carpeta Norte");
  });

  it("las obras van por nombre aunque la API las traiga por carpeta: una de la carpeta Sur que empieza por A queda primera", async () => {
    servidor([CLINICA, TORRE, obra(SUR, 4, "Almacén Sur"), GALPON]);
    pintar();
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem").map((e) => e.textContent)).toEqual([
      "Almacén Sur",
      "Clínica Las Mercedes",
      "Galpón Sur",
      "Torre B",
    ]);
  });

  it("el orden ignora tildes y mayúsculas, y con el mismo nombre desempata por el título de la carpeta", async () => {
    servidor([obra(SUR, 3, "galpón"), obra(NORTE, 1, "Galpón"), obra(NORTE, 2, "Álamo")]);
    pintar();
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem").map((e) => e.textContent)).toEqual([
      "Álamo",
      "GalpónCarpeta Norte",
      "galpónCarpeta Sur",
    ]);
  });

  it("una cuenta sin CAMBIAR_CASO no ve obras de otra carpeta que la abierta, aunque la respuesta las traiga", async () => {
    const sinCambiar = sesionDe("ana", {
      acciones: sesionDe("ana").acciones.filter((a) => a !== "cambiar_caso"),
    });
    pintar({ sesion: sinCambiar });
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem").map((e) => e.textContent)).toEqual(["Clínica Las Mercedes", "Torre B"]);
    expect(screen.queryByText("Galpón Sur")).toBeNull();
  });

  it("una cuenta sin CAMBIAR_CASO en la carpeta de la empresa solo ve las de la empresa", async () => {
    servidor([obra(null, 5, "Obra propia"), CLINICA], null);
    pintar({ sesion: sesionDe("rita") });
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem").map((e) => e.textContent)).toEqual(["Obra propia"]);
  });
});

describe("BarraLateral: obra abierta", () => {
  const abierta = { carpeta: NORTE, obraId: 1 };

  it("despliega solo la obra abierta con las secciones que tienen pantalla; la activa lleva aria-current", async () => {
    pintar({ abierta, seccion: "presupuesto", ruta: "/obra/Carpeta%20Norte.db/1/presupuesto" });
    const lista = await arbol();
    const filaClinica = within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes" });
    expect(filaClinica).toHaveAttribute("aria-expanded", "true");
    expect(within(lista).getByRole("treeitem", { name: "Torre B" })).toHaveAttribute("aria-expanded", "false");
    const secciones = within(screen.getByRole("group", { name: "Clínica Las Mercedes" })).getAllByRole("treeitem");
    expect(secciones.map((s) => s.textContent)).toEqual(["Resumen", "Presupuesto", "Tramos", "Archivos y planos", "Versiones", "Aprobaciones", "Mercado", "Control de obra", "Riesgo"]);
    expect(secciones.map((s) => s.getAttribute("aria-current"))).toEqual([null, "page", null, null, null, null, null, null, null]);
    expect(secciones[1]).toHaveAttribute("href", "/obra/Carpeta%20Norte.db/1/presupuesto");
  });

  it("sin obra abierta ninguna está desplegada", async () => {
    pintar();
    const lista = await arbol();
    for (const fila of within(lista).getAllByRole("treeitem")) expect(fila).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("treeitem", { name: "Presupuesto" })).toBeNull();
  });

  it("una sección cuya pantalla la cuenta no puede usar no se muestra", async () => {
    pintar({ sesion: sesionDe("rita"), abierta, seccion: "resumen", ruta: "/obra/Carpeta%20Norte.db/1/resumen" });
    await arbol();
    const secciones = within(screen.getByRole("group", { name: "Clínica Las Mercedes" })).getAllByRole("treeitem");
    // «control» exige control_de_obra: quien solo revisa no lo ve. «Presupuesto», «Archivos y planos», «Versiones» y
    // «Mercado» sí, en solo lectura (F4 2b, Eugenio, 2026-10-31; Tareas 11 y 6; Tarea 13, ronda 2). «Riesgo» exige
    // ver_riesgo, que también tiene quien revisa (F6, T2: sección propia de la obra).
    expect(secciones.map((s) => s.textContent)).toEqual(["Resumen", "Presupuesto", "Archivos y planos", "Versiones", "Aprobaciones", "Mercado", "Riesgo"]);
  });
});

describe("BarraLateral: «Tramos» en toda obra mientras el módulo vial esté encendido", () => {
  const nombres = (obraAbierta: string) =>
    within(screen.getByRole("group", { name: obraAbierta })).getAllByRole("treeitem").map((s) => s.textContent);
  const clinica = { carpeta: NORTE, obraId: 1 };
  const rutaDeClinica = "/obra/Carpeta%20Norte.db/1/resumen";

  it("una obra sin tramos guardados también ofrece «Tramos», entre Presupuesto y Aprobaciones", async () => {
    pintar({ abierta: clinica, seccion: "resumen", ruta: rutaDeClinica });
    await arbol();
    expect(await screen.findByRole("treeitem", { name: "Tramos" })).toHaveAttribute("href", "/obra/Carpeta%20Norte.db/1/tramos");
    expect(nombres("Clínica Las Mercedes")).toEqual(["Resumen", "Presupuesto", "Tramos", "Archivos y planos", "Versiones", "Aprobaciones", "Mercado", "Control de obra", "Riesgo"]);
  });

  it("otra obra de la misma carpeta también", async () => {
    pintar({ abierta: { carpeta: NORTE, obraId: 2 }, seccion: "resumen", ruta: "/obra/Carpeta%20Norte.db/2/resumen" });
    await arbol();
    expect(await screen.findByRole("treeitem", { name: "Tramos" })).toBeInTheDocument();
  });

  it("la sección en la que se está se marca como la actual", async () => {
    pintar({ abierta: clinica, seccion: "tramos", ruta: "/obra/Carpeta%20Norte.db/1/tramos" });
    await arbol();
    expect(await screen.findByRole("treeitem", { name: "Tramos" })).toHaveAttribute("aria-current", "page");
  });

  it("ya no pide la lista de obras con tramos: la sección no depende de ella", async () => {
    pintar({ sesion: sesionDe("rita"), abierta: clinica, seccion: "resumen", ruta: rutaDeClinica });
    await arbol();
    expect(pedirFalso).not.toHaveBeenCalledWith("/v1/vial/obras");
  });
});

describe("BarraLateral: zonas Pendientes y Empresa", () => {
  it("Pendientes es un enlace a #/pendientes y está activo en esa ruta", async () => {
    pintar({ ruta: "/pendientes" });
    await arbol();
    const enlace = screen.getByRole("link", { name: "Pendientes" });
    expect(enlace).toHaveAttribute("href", "/pendientes");
    expect(enlace).toHaveAttribute("aria-current", "page");
  });

  // F6, T4: la zona Empresa trae el grupo «Costos y producción» (Auditar, Precios, Costos de producción, en ese orden);
  // «Empresa y personas» y «Ayuda» quedan como estaban hasta T6.
  it("Empresa lista el grupo «Costos y producción» y sus entradas usables, con la activa marcada", async () => {
    // Quien ve todo: lo de la administración y, además, `leer_proyecto` (el catálogo y el libro).
    const todo = sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] });
    pintar({ sesion: todo, ruta: "/empresa/personas" });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    const enlaces = within(zona).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual([
      "Auditar un presupuesto",
      "Precios y catálogo",
      "Costos de producción",
      "Empresa y personas",
      "Ayuda",
    ]);
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual([
      "/auditoria/subir",
      "/precios/listas",
      "/produccion/resumen",
      "/empresa/personas",
      "/empresa/ayuda",
    ]);
    expect(enlaces[3]).toHaveAttribute("aria-current", "page");
    expect(zona.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
    const grupo = within(zona).getByRole("heading", { level: 3, name: "Costos y producción" });
    expect(within(zona).getByRole("list", { name: "Costos y producción" })).toContainElement(enlaces[0]);
    expect(grupo.compareDocumentPosition(enlaces[0]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("quien arma entra a Precios por el Catálogo; el grupo lleva a la primera herramienta usable de cada espacio", async () => {
    pintar({ sesion: sesionDe("ana") });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    expect(within(zona).getByRole("link", { name: "Auditar un presupuesto" })).toHaveAttribute("href", "/auditoria/subir");
    expect(within(zona).getByRole("link", { name: "Precios y catálogo" })).toHaveAttribute("href", "/precios/catalogo");
    expect(within(zona).getByRole("link", { name: "Costos de producción" })).toHaveAttribute("href", "/produccion/resumen");
  });

  it("quien solo registra costos entra a Producción por «Costos del período»", async () => {
    pintar({ sesion: sesionDe("ana", { acciones: ["registrar_costos_produccion"] }) });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    expect(within(zona).getByRole("link", { name: "Costos de producción" })).toHaveAttribute("href", "/produccion/costos");
  });

  it("un espacio sin herramienta que la cuenta pueda usar no se muestra", async () => {
    pintar({ sesion: sesionDe("rita") });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    // Rita no opera la arenera ni registra costos; «administracion» exige administrar_cuentas.
    expect(within(zona).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("href")])).toEqual([
      ["Auditar un presupuesto", "/auditoria/subir"],
      ["Precios y catálogo", "/precios/catalogo"],
      ["Ayuda", "/empresa/ayuda"],
    ]);
  });

  it.each([
    ["/auditoria/historial", "Auditar un presupuesto"],
    ["/precios/indices", "Precios y catálogo"],
    ["/produccion/costos", "Costos de producción"],
  ])("en %s solo «%s» está activa: coincide el primer segmento de la ruta", async (ruta, activa) => {
    pintar({ sesion: sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] }), ruta });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    const marcadas = within(zona).getAllByRole("link").filter((e) => e.getAttribute("aria-current") === "page");
    expect(marcadas.map((e) => e.textContent)).toEqual([activa]);
  });
});

describe("BarraLateral: carga", () => {
  it("si falla la lista dice que no se pudo cargar y Reintentar vuelve a pedirla", async () => {
    respuesta = new ErrorDeApi(500, "Fallo del servidor.");
    pintar();
    expect(await screen.findByText("No se pudieron cargar las obras")).toBeInTheDocument();
    servidor([CLINICA]);
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByRole("treeitem", { name: "Clínica Las Mercedes" })).toBeInTheDocument();
    expect(screen.queryByText("No se pudieron cargar las obras")).toBeNull();
  });

  it("sin obras dice «Todavía no hay obras» y ofrece Nueva obra", async () => {
    servidor([]);
    pintar();
    expect(await screen.findByText("Todavía no hay obras")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nueva obra" })).toBeInTheDocument();
  });
});

describe("BarraLateral: teclado (patrón tree de WAI-ARIA)", () => {
  const abierta = { carpeta: NORTE, obraId: 1 };

  it("solo un elemento del árbol entra en el orden de tabulación", async () => {
    pintar({ abierta, seccion: "resumen" });
    const lista = await arbol();
    const tabulables = within(lista)
      .getAllByRole("treeitem")
      .filter((e) => e.getAttribute("tabindex") === "0");
    expect(tabulables).toHaveLength(1);
  });

  it("flecha abajo y arriba recorren las filas visibles", async () => {
    const u = userEvent.setup();
    pintar({ abierta, seccion: "resumen" });
    const lista = await arbol();
    const clinica = within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes" });
    clinica.focus();
    await u.keyboard("{ArrowDown}");
    expect(within(lista).getByRole("treeitem", { name: "Resumen" })).toHaveFocus();
    await u.keyboard("{ArrowDown}{ArrowDown}{ArrowDown}{ArrowDown}{ArrowDown}");
    expect(within(lista).getByRole("treeitem", { name: "Aprobaciones" })).toHaveFocus();
    await u.keyboard("{ArrowUp}");
    expect(within(lista).getByRole("treeitem", { name: "Versiones" })).toHaveFocus();
  });

  it("flecha derecha despliega una obra plegada y flecha izquierda la pliega", async () => {
    const u = userEvent.setup();
    pintar({ abierta, seccion: "resumen" });
    const lista = await arbol();
    const torre = within(lista).getByRole("treeitem", { name: "Torre B" });
    torre.focus();
    await u.keyboard("{ArrowRight}");
    expect(torre).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("group", { name: "Torre B" })).toBeInTheDocument();
    await u.keyboard("{ArrowLeft}");
    expect(torre).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("group", { name: "Torre B" })).toBeNull();
  });

  it("flecha izquierda en una sección vuelve a su obra", async () => {
    const u = userEvent.setup();
    pintar({ abierta, seccion: "resumen" });
    const lista = await arbol();
    within(lista).getByRole("treeitem", { name: "Mercado" }).focus();
    await u.keyboard("{ArrowLeft}");
    expect(within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes" })).toHaveFocus();
  });
});

describe("BarraLateral: Nueva obra", () => {
  it("es un botón con la clase del botón principal, antes del árbol en el orden del documento", async () => {
    pintar();
    const lista = await arbol();
    const boton = screen.getByRole("button", { name: "Nueva obra" });
    expect(boton).toHaveClass("silice-marco-boton-principal");
    expect(boton.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(boton.compareDocumentPosition(lista) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("no aparece si la cuenta no puede crear obras", async () => {
    pintar({ sesion: sesionDe("rita") });
    await arbol();
    expect(screen.queryByRole("button", { name: "Nueva obra" })).toBeNull();
  });

  it("al pulsarlo abre el diálogo para crear una obra", async () => {
    pintar();
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    expect(await screen.findByRole("dialog", { name: "Nueva obra" })).toBeInTheDocument();
    await waitFor(() => expect(pedirFalso).toHaveBeenCalledWith("/v1/carpeta"));
  });

  // Tarea 6b: la obra se crea donde está la persona; no hay selector de carpeta ni cambio de carpeta.
  function conCreacion() {
    pedirFalso.mockImplementation(async (ruta: string, opciones?: { metodo?: string }) => {
      if (ruta === "/v1/obras/todas") return respuesta;
      if (ruta === "/v1/carpeta") return { moneda: "Bs", declarada: true, lista: null, aviso: null };
      if (ruta === "/v1/proyectos" && opciones?.metodo === "POST") return { codigo: "9", nombre: "Nueva" };
      throw new Error(`petición inesperada: ${ruta}`);
    });
  }
  // En otra carpeta que la abierta no se conoce la moneda: la persona la elige.
  async function escribirYCrear(moneda?: string) {
    const campo = screen.getByRole("combobox", { name: "Moneda" });
    if (moneda) await userEvent.selectOptions(campo, moneda);
    else await waitFor(() => expect(campo).toHaveValue("Bs"));
    await userEvent.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Nueva");
    await userEvent.click(screen.getByRole("button", { name: "Crear obra" }));
  }
  const envios = () => pedirFalso.mock.calls.filter(([r]) => r === "/v1/proyectos");
  const cambiosDeCarpeta = () => pedirFalso.mock.calls.filter(([r]) => r === "/v1/casos/actual");

  it("con una obra abierta en otra carpeta dice dónde se creará, sin selector, y manda esa carpeta sin cambiar la de la sesión", async () => {
    conCreacion();
    pintar({ abierta: { carpeta: SUR, obraId: 3 }, seccion: "resumen", ruta: "/obra/Carpeta%20Sur.db/3/resumen" });
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    const caja = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(within(caja).getByText("Se creará en Carpeta Sur")).toBeInTheDocument();
    expect(within(caja).queryByRole("combobox", { name: "Carpeta" })).toBeNull();
    await escribirYCrear("USD");
    await waitFor(() => expect(envios()).toHaveLength(1));
    expect(envios()[0]![1]).toMatchObject({ metodo: "POST", cuerpo: expect.objectContaining({ carpeta: SUR }) });
    expect(cambiosDeCarpeta()).toEqual([]);
  });

  it("en otra carpeta que la de la sesión no se propone la moneda de la sesión y es obligatoria", async () => {
    conCreacion(); // la sesión está en la carpeta Norte y /v1/carpeta responde Bs
    pintar({ abierta: { carpeta: SUR, obraId: 3 }, seccion: "resumen" });
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    const caja = await screen.findByRole("dialog", { name: "Nueva obra" });
    await waitFor(() => expect(pedirFalso).toHaveBeenCalledWith("/v1/carpeta"));
    expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("");
    expect(within(caja).queryByText("Es la moneda de esta carpeta (Bs).")).toBeNull();
    await userEvent.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Nueva");
    await userEvent.click(within(caja).getByRole("button", { name: "Crear obra" }));
    expect(await within(caja).findByText("Elija la moneda de la obra.")).toBeInTheDocument();
    expect(envios()).toEqual([]);
  });

  it("sin obra en la ruta se crea en la carpeta abierta de la sesión, aunque no tenga obras (la empresa se llama «empresa»)", async () => {
    servidor([CLINICA, GALPON], null);
    conCreacion();
    pintar();
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    const caja = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(within(caja).getByText("Se creará en Carpeta de la empresa")).toBeInTheDocument();
    expect(within(caja).queryByRole("combobox", { name: "Carpeta" })).toBeNull();
    await escribirYCrear();
    await waitFor(() => expect(envios()).toHaveLength(1));
    expect(envios()[0]![1]).toMatchObject({ cuerpo: expect.objectContaining({ carpeta: "empresa" }) });
    expect(cambiosDeCarpeta()).toEqual([]);
  });

  it("al crear cierra el diálogo y lleva a la obra nueva en la carpeta donde se creó", async () => {
    conCreacion();
    pintar({ abierta: { carpeta: SUR, obraId: 3 }, seccion: "resumen" });
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    await screen.findByRole("dialog", { name: "Nueva obra" });
    await escribirYCrear("USD");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Nueva obra" })).toBeNull();
      expect(pedirFalso.mock.calls.filter(([r]) => r === "/v1/obras/todas").length).toBeGreaterThan(1); // recargó
    });
  });

  it("los estilos lo pintan con el complementario, texto blanco, sin borde, seminegrita y 40 px de alto, solo con variables del tema", () => {
    const estilos = leer("marco/BarraLateral.scss");
    const regla = /\.silice-marco-boton-principal\s*\{([^}]*)\}/.exec(estilos)?.[1] ?? "";
    // Mismo tono que el botón principal de Carbon (Tarea 4c): reutiliza sus tokens, sin repetir las mezclas.
    expect(regla).toContain("background-color: var(--cds-button-primary)");
    expect(regla).not.toContain("silice-boton-borde");
    expect(regla).toMatch(/border:\s*none/);
    const hover = /&:hover\s*\{([^}]*)\}/.exec(estilos.slice(estilos.indexOf(".silice-marco-boton-principal")))?.[1] ?? "";
    expect(hover).toContain("background-color: var(--cds-button-primary-hover)");
    expect(hover).not.toMatch(/filter/);
    const activo = /&:active\s*\{([^}]*)\}/.exec(estilos.slice(estilos.indexOf(".silice-marco-boton-principal")))?.[1] ?? "";
    expect(activo).toContain("background-color: var(--cds-button-primary-active)");
    expect(regla).not.toMatch(/color-mix/);
    expect(regla).toMatch(/(^|[\s;])color: var\(--cds-text-on-color\)/);
    expect(regla).toMatch(/font-weight: 600/);
    expect(regla).toMatch(/block-size: 2\.5rem/);
    expect(regla).toMatch(/inline-size: 100%/);
    // Foco: contorno blanco hacia dentro; el del marco no se vería sobre el complementario (en el neutro es el mismo color).
    const foco = /&:focus-visible\s*\{([^}]*)\}/.exec(estilos.slice(estilos.indexOf(".silice-marco-boton-principal")))?.[1] ?? "";
    expect(foco).toContain("outline: 2px solid var(--cds-text-on-color)");
    expect(foco).toContain("outline-offset: -4px");
    expect(foco).not.toContain("--silice-marco");
    expect(estilos).toContain("background-color: var(--silice-lateral)");
    expect(estilos).toMatch(/inline-size: 14\.75rem/);
    expect(estilos).toContain("var(--silice-lateral-activo)");
    // La raya del activo es del color del marco (8,83:1 sobre el fondo del activo en el tema neutro), no del acento.
    expect(estilos).toMatch(/&\[aria-current="page"\]\s*\{[^}]*3px solid var\(--silice-marco\)/);
    expect(estilos).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  it("el tema neutro da al texto sobre el acento un contraste de al menos 4,5:1", () => {
    // Los alias neutros de tokens.scss: acento = yellow-20 de Carbon, marco = background-inverse de g10 (gray-80).
    const tokens = leer("estilos/tokens.scss");
    expect(tokens).toContain("--silice-acento: #{colors.$yellow-20}");
    expect(tokens).toContain("--silice-marco: var(--cds-background-inverse)");
    const luminancia = (hex: string) => {
      const [r, g, b] = [1, 3, 5].map((i) => {
        const c = parseInt(hex.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
    };
    const [claro, oscuro] = [luminancia("#fddc69"), luminancia("#393939")];
    expect((claro + 0.05) / (oscuro + 0.05)).toBeGreaterThanOrEqual(4.5);
  });
});

describe("BarraLateral: dónde se crea la obra", () => {
  it("el título de la carpeta abierta sin obras lo da el servidor, no se arma en el front", async () => {
    servidor([], NORTE, "Título que da el servidor");
    pedirFalso.mockImplementation(async (ruta: string) => {
      if (ruta === "/v1/obras/todas") return respuesta;
      if (ruta === "/v1/carpeta") return { moneda: "Bs", declarada: true, lista: null, aviso: null };
      throw new Error(`petición inesperada: ${ruta}`);
    });
    pintar();
    await screen.findByText("Todavía no hay obras");
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    const caja = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(within(caja).getByText("Se creará en Título que da el servidor")).toBeInTheDocument();
  });
});

describe("BarraLateral: niveles del árbol", () => {
  const nivel = (e: HTMLElement) => [e.getAttribute("aria-level"), e.getAttribute("aria-setsize"), e.getAttribute("aria-posinset")];

  it("con obras de dos carpetas, todas son de nivel 1 y sus secciones de nivel 2, con su tamaño y su posición", async () => {
    pintar({ abierta: { carpeta: NORTE, obraId: 1 }, seccion: "resumen", ruta: "/obra/Carpeta%20Norte.db/1/resumen" });
    const lista = await arbol();
    expect(nivel(within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes" }))).toEqual(["1", "3", "1"]);
    expect(nivel(within(lista).getByRole("treeitem", { name: "Galpón Sur" }))).toEqual(["1", "3", "2"]);
    expect(nivel(within(lista).getByRole("treeitem", { name: "Torre B" }))).toEqual(["1", "3", "3"]);
    const secciones = within(screen.getByRole("group", { name: "Clínica Las Mercedes" })).getAllByRole("treeitem");
    // Resumen, Presupuesto, Tramos, Archivos y planos, Versiones, Aprobaciones, Mercado, Control de obra y Riesgo.
    expect(secciones.map(nivel)).toEqual([
      ["2", "9", "1"],
      ["2", "9", "2"],
      ["2", "9", "3"],
      ["2", "9", "4"],
      ["2", "9", "5"],
      ["2", "9", "6"],
      ["2", "9", "7"],
      ["2", "9", "8"],
      ["2", "9", "9"],
    ]);
  });

  it("sin carpetas, las obras son de nivel 1 y sus secciones de nivel 2", async () => {
    servidor([CLINICA, TORRE]);
    pintar({ abierta: { carpeta: NORTE, obraId: 2 }, seccion: "resumen", ruta: "/obra/Carpeta%20Norte.db/2/resumen" });
    const lista = await arbol();
    expect(nivel(within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes" }))).toEqual(["1", "2", "1"]);
    expect(nivel(within(lista).getByRole("treeitem", { name: "Torre B" }))).toEqual(["1", "2", "2"]);
    const primera = within(screen.getByRole("group", { name: "Torre B" })).getAllByRole("treeitem")[0]!;
    expect(nivel(primera)).toEqual(["2", "9", "1"]);
  });
});

describe("BarraLateral: carga de las obras", () => {
  it("mientras llegan las obras dice «Cargando obras…» y no pinta un árbol vacío", async () => {
    pedirFalso.mockImplementation(() => new Promise(() => {}));
    pintar();
    expect(await screen.findByText("Cargando obras…")).toBeInTheDocument();
    expect(screen.queryByRole("tree")).toBeNull();
    expect(screen.queryByText("Todavía no hay obras")).toBeNull();
  });

  it("al reintentar tras un error vuelve a decir «Cargando obras…» en vez de mostrar un árbol vacío", async () => {
    respuesta = new ErrorDeApi(500, "falló");
    pintar();
    await screen.findByText("No se pudieron cargar las obras");
    pedirFalso.mockImplementation(() => new Promise(() => {}));
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Cargando obras…")).toBeInTheDocument();
    expect(screen.queryByRole("tree")).toBeNull();
  });

  it("mientras recarga conserva el árbol que ya tenía", async () => {
    conCreacionDeCodigo("9");
    pintar();
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    await screen.findByRole("dialog", { name: "Nueva obra" });
    pedirFalso.mockImplementation(async (ruta: string, op?: { metodo?: string }) => {
      if (ruta === "/v1/obras/todas") return new Promise(() => {});
      if (ruta === "/v1/carpeta") return { moneda: "Bs", declarada: true, lista: null, aviso: null };
      if (ruta === "/v1/proyectos" && op?.metodo === "POST") return { codigo: "9", nombre: "Nueva" };
      throw new Error(`petición inesperada: ${ruta}`);
    });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Moneda" }), "USD");
    await userEvent.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Nueva");
    await userEvent.click(screen.getByRole("button", { name: "Crear obra" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Nueva obra" })).toBeNull();
      expect(screen.getByRole("tree", { name: "Obras" })).toBeInTheDocument();
      expect(screen.queryByText("Cargando obras…")).toBeNull();
    });
  });
});

function conCreacionDeCodigo(codigo: string) {
  pedirFalso.mockImplementation(async (ruta: string, opciones?: { metodo?: string }) => {
    if (ruta === "/v1/obras/todas") return respuesta;
    if (ruta === "/v1/carpeta") return { moneda: "Bs", declarada: true, lista: null, aviso: null };
    if (ruta === "/v1/proyectos" && opciones?.metodo === "POST") return { codigo, nombre: "Nueva" };
    throw new Error(`petición inesperada: ${ruta}`);
  });
}

describe("BarraLateral: la obra recién creada", () => {
  async function crearConCodigo(codigo: string) {
    conCreacionDeCodigo(codigo);
    pintar();
    await arbol();
    await userEvent.click(screen.getByRole("button", { name: "Nueva obra" }));
    await screen.findByRole("dialog", { name: "Nueva obra" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Moneda" }), "USD");
    await userEvent.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Nueva");
    await userEvent.click(screen.getByRole("button", { name: "Crear obra" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Nueva obra" })).toBeNull());
  }

  it("con un código entero abre la obra nueva", async () => {
    await crearConCodigo("9");
    await waitFor(() => expect(screen.getByTestId("ubicacion")).toHaveTextContent("/obra/Carpeta%20Norte.db/9/resumen"));
  });

  it("con un código que no es un entero no navega a una ruta con NaN y deja la lista recargada", async () => {
    await crearConCodigo("abc");
    await waitFor(() => {
      expect(screen.getByTestId("ubicacion")).toHaveTextContent("/pendientes");
      expect(screen.getByTestId("ubicacion").textContent).not.toContain("NaN");
      expect(pedirFalso.mock.calls.filter(([r]) => r === "/v1/obras/todas").length).toBeGreaterThan(1);
    });
  });
});

function pendiente(carpeta: string | null, obra_id: number, texto: string): PendienteDeObra {
  const nombre = [CLINICA, TORRE, GALPON].find((o) => o.carpeta === carpeta && o.obra_id === obra_id)?.obra ?? "Otra";
  return {
    carpeta,
    obra_id,
    obra: nombre,
    grupo: "compras",
    urgencia: "bloquea",
    texto,
    accion: { texto: "Abrir", pagina: "hoja" },
  };
}
const conPendientes = (pendientes: PendienteDeObra[]): PendientesDelMarco => ({
  estado: "listo",
  pendientes,
  carpetasOmitidas: 0,
  recargar: vi.fn(),
});
const enlacePendientes = (nombre: string) => screen.getByRole("link", { name: nombre });

describe("BarraLateral: contadores (rediseño F3)", () => {
  const CUATRO = [
    pendiente(NORTE, 1, "a"),
    pendiente(NORTE, 1, "b"),
    pendiente(NORTE, 2, "c"),
    pendiente(SUR, 3, "d"),
  ];

  it("Pendientes lleva una píldora con el total y su nombre accesible dice «Pendientes, 4 por hacer»", async () => {
    pintar({ pendientes: conPendientes(CUATRO) });
    await arbol();
    const enlace = enlacePendientes("Pendientes, 4 por hacer");
    expect(enlace).toHaveAttribute("href", "/pendientes");
    expect(within(enlace).getByText("4")).toHaveClass("silice-pildora");
  });

  it("con un solo pendiente dice «Pendientes, 1 por hacer»", async () => {
    pintar({ pendientes: conPendientes([CUATRO[0]!]) });
    await arbol();
    expect(enlacePendientes("Pendientes, 1 por hacer")).toBeInTheDocument();
  });

  it.each([
    ["sin ninguno", conPendientes([])],
    ["mientras carga", { estado: "cargando", recargar: vi.fn() } as PendientesDelMarco],
    ["con error", { estado: "error", mensaje: "falló", recargar: vi.fn() } as PendientesDelMarco],
  ])("%s no hay píldora ni número, y el enlace se llama solo «Pendientes»", async (_caso, pendientes) => {
    pintar({ pendientes });
    await arbol();
    const enlace = enlacePendientes("Pendientes");
    expect(enlace.querySelector(".silice-pildora")).toBeNull();
    expect(enlace.textContent).toBe("Pendientes");
  });

  it("cada obra con pendientes lleva la suya (carpeta y número); la de 0 no lleva ninguna", async () => {
    pintar({ pendientes: conPendientes(CUATRO) });
    const lista = await arbol();
    const pildoraDe = (nombre: string) => within(lista).getByRole("treeitem", { name: new RegExp(`^${nombre}`) }).querySelector(".silice-pildora");
    expect(pildoraDe("Clínica Las Mercedes")?.textContent).toBe("2");
    expect(pildoraDe("Torre B")?.textContent).toBe("1");
    expect(pildoraDe("Galpón Sur")?.textContent).toBe("1");
    expect(within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes, 2 por hacer" })).toBeInTheDocument();
  });

  it("la clave es carpeta más número: el mismo número en otra carpeta no cuenta", async () => {
    servidor([obra(NORTE, 1, "Clínica"), obra(SUR, 1, "Galpón")]);
    pintar({ pendientes: conPendientes([pendiente(SUR, 1, "x"), pendiente(SUR, 1, "y"), pendiente(SUR, 1, "z")]) });
    const lista = await arbol();
    expect(within(lista).getByRole("treeitem", { name: "Clínica" }).querySelector(".silice-pildora")).toBeNull();
    expect(within(lista).getByRole("treeitem", { name: "Galpón, 3 por hacer" })).toBeInTheDocument();
  });

  it("una obra sin pendientes conserva su nombre accesible de siempre", async () => {
    pintar({ pendientes: conPendientes([pendiente(NORTE, 2, "c")]) });
    const lista = await arbol();
    expect(within(lista).getByRole("treeitem", { name: "Clínica Las Mercedes" })).toBeInTheDocument();
  });
});

describe("BarraLateral: obras con el mismo nombre (D-F3-3)", () => {
  it("dos obras llamadas igual en carpetas distintas muestran debajo su carpeta; las demás no", async () => {
    servidor([obra(NORTE, 1, "Galpón"), obra(SUR, 3, "Galpón"), obra(NORTE, 2, "Torre B")]);
    pintar();
    const lista = await arbol();
    const filas = within(lista).getAllByRole("treeitem");
    expect(filas.map((f) => f.textContent)).toEqual(["GalpónCarpeta Norte", "GalpónCarpeta Sur", "Torre B"]);
    expect(within(filas[0]!).getByText("Carpeta Norte")).toHaveClass("silice-marco-lateral__de-carpeta");
    expect(within(filas[2]!).queryByText(/Carpeta/)).toBeNull();
  });

  it("el nombre accesible de la homónima incluye su carpeta, y con píldora también el contador", async () => {
    servidor([obra(NORTE, 1, "Galpón"), obra(SUR, 3, "Galpón")]);
    pintar({ pendientes: conPendientes([pendiente(SUR, 3, "x")]) });
    const lista = await arbol();
    expect(within(lista).getByRole("treeitem", { name: "Galpón, Carpeta Norte" })).toBeInTheDocument();
    expect(within(lista).getByRole("treeitem", { name: "Galpón, Carpeta Sur, 1 por hacer" })).toBeInTheDocument();
  });
});

// Cierre de F3 (H6): un nombre largo de obra ocupaba hasta 4 lineas en la barra lateral. Se limita a 2 con puntos
// suspensivos; el nombre completo queda en `title` y en el nombre accesible.
describe("BarraLateral: nombres largos de obra", () => {
  const LARGO = "Rehabilitación integral del edificio de oficinas y estacionamiento de la urbanización Los Samanes, etapa dos";

  // jsdom no calcula el diseño: las medidas del recorte se simulan sobre el propio elemento.
  function medir(el: HTMLElement, scrollHeight: number, clientHeight: number) {
    Object.defineProperty(el, "scrollHeight", { configurable: true, value: scrollHeight });
    Object.defineProperty(el, "clientHeight", { configurable: true, value: clientHeight });
  }

  async function nombreLargo() {
    servidor([obra(NORTE, 7, LARGO), TORRE]);
    pintar();
    const lista = await arbol();
    const fila = within(lista).getByRole("treeitem", { name: LARGO });
    const nombre = within(fila).getByText(LARGO);
    expect(nombre).toHaveClass("silice-marco-lateral__obra-nombre");
    return nombre;
  }

  it("el treeitem conserva el nombre completo como nombre accesible y sin pasar el ratón no hay title", async () => {
    const nombre = await nombreLargo();
    expect(nombre).not.toHaveAttribute("title");
  });

  it("al pasar el ratón por un nombre recortado (scrollHeight mayor que clientHeight) aparece el title completo", async () => {
    const nombre = await nombreLargo();
    medir(nombre, 80, 40);
    await userEvent.hover(nombre);
    expect(nombre).toHaveAttribute("title", LARGO);
  });

  it("al pasar el ratón por un nombre que cabe no hay title", async () => {
    const nombre = await nombreLargo();
    medir(nombre, 40, 40);
    await userEvent.hover(nombre);
    expect(nombre).not.toHaveAttribute("title");
  });

  it("si el nombre deja de estar recortado, el title se quita en el siguiente paso del ratón", async () => {
    const nombre = await nombreLargo();
    medir(nombre, 80, 40);
    await userEvent.hover(nombre);
    expect(nombre).toHaveAttribute("title");
    medir(nombre, 40, 40);
    await userEvent.unhover(nombre);
    await userEvent.hover(nombre);
    expect(nombre).not.toHaveAttribute("title");
  });

  it("la hoja de estilos limita el nombre a 2 líneas con puntos suspensivos", () => {
    const fuente = leer("marco/BarraLateral.scss");
    const i = fuente.indexOf(".silice-marco-lateral__obra-nombre {");
    expect(i).toBeGreaterThan(-1);
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    expect(regla).toMatch(/-webkit-line-clamp:\s*2/);
    expect(regla).toMatch(/-webkit-box-orient:\s*vertical/);
    expect(regla).toMatch(/display:\s*-webkit-box/);
    expect(regla).toMatch(/overflow:\s*hidden/);
  });
});

// Cierre de F3 (menor 6): con letra «Muy grande» (1,5) a 1366×768 el rem pasa de 28 px y Pendientes, los títulos y las cinco
// entradas de Empresa se comían el alto: la zona de obras quedaba en casi nada. La zona de obras se queda con el alto que
// sobra y es la única que se desplaza; con letra Grande o Muy grande se compactan filas y títulos y la zona conserva un
// mínimo. jsdom no calcula el diseño: la estructura se prueba en el DOM y las reglas en el fuente; la medida real
// (cuántas obras caben a 1366×768) se hace en el navegador.
describe("BarraLateral: la zona de obras con letra grande", () => {
  it("la cabecera de Obras y «Nueva obra» quedan fuera del árbol, que tiene su propio desplazamiento", async () => {
    servidor([obra(NORTE, 1, "Torre"), TORRE]);
    pintar();
    const lista = await arbol();
    const zona = lista.closest(".silice-marco-lateral__obras");
    expect(zona).not.toBeNull();
    expect(lista.parentElement).toBe(zona);
    expect(within(lista).queryByRole("button", { name: "Nueva obra" })).toBeNull();
    expect(within(zona as HTMLElement).getByRole("heading", { name: "Obras" })).toBeInTheDocument();
    const hojas = leer("marco/BarraLateral.scss");
    expect(regla(hojas, ".silice-marco-lateral__obras")).toMatch(/flex:\s*1 1 auto/);
    expect(regla(hojas, ".silice-marco-lateral__arbol")).toMatch(/overflow-y:\s*auto/);
    expect(regla(hojas, ".silice-marco-lateral__empresa")).toMatch(/flex:\s*none/);
  });

  it("_umbrales.scss ofrece un mixin para letra Grande y Muy grande, sin consultas de ancho propias", () => {
    const fuente = leer("marco/_umbrales.scss");
    const mixin = bloque(fuente, "@mixin con-letra-grande");
    expect(mixin).toMatch(/html\[data-silice-letra="grande"\]/);
    expect(mixin).toMatch(/html\[data-silice-letra="muy-grande"\]/);
    expect(mixin).not.toMatch(/@media/);
  });

  it("con letra grande se compactan filas y títulos y la zona de obras conserva un mínimo; nada se esconde", () => {
    const hoja = leer("marco/BarraLateral.scss");
    expect(hoja).toMatch(/@use\s+"umbrales"\s+as\s+u;/);
    const compacta = bloque(hoja, "@include u.con-letra-grande");
    expect(compacta).not.toBe("");
    expect(regla(compacta, ".silice-marco-lateral__fila")).toMatch(/min-block-size:\s*1\.5rem/);
    expect(regla(compacta, ".silice-marco-lateral__titulo")).toMatch(/padding:\s*0\.5rem 1rem 0\.25rem/);
    expect(regla(compacta, ".silice-marco-lateral__obras")).toMatch(/min-block-size:\s*10rem/);
    expect(compacta).not.toMatch(/display:\s*none/);
    expect(compacta).not.toMatch(/silice-letra/);
  });
});

// Tarea 0 de F4: con letra Grande o Muy grande «Empresa» se pliega para darle su alto al árbol (decisión de Eugenio al
// cierre de F3). Con letra normal sigue como antes. El tamaño se pone a mano en la raíz, como lo deja `aplicarTamanoLetra`.
describe("BarraLateral: Empresa plegable con letra grande (F4, Tarea 0)", () => {
  const CINCO = ["Auditar un presupuesto", "Precios y catálogo", "Costos de producción", "Empresa y personas", "Ayuda"];
  const todo = () => sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] });
  const ponerLetra = (valor: string) => document.documentElement.setAttribute("data-silice-letra", valor);
  const zona = () => screen.getByRole("navigation", { name: "Empresa" });
  afterEach(() => document.documentElement.removeAttribute("data-silice-letra"));

  it("con letra normal Empresa es un h2 sin botón y se ven sus entradas", async () => {
    pintar({ sesion: todo() });
    await arbol();
    const titulo = within(zona()).getByRole("heading", { name: "Empresa" });
    expect(within(titulo).queryByRole("button")).toBeNull();
    expect(within(zona()).getAllByRole("link").map((e) => e.textContent)).toEqual(CINCO);
  });

  it("con letra grande Empresa arranca plegada", async () => {
    ponerLetra("grande");
    pintar({ sesion: todo() });
    await arbol();
    const boton = within(zona()).getByRole("button", { name: "Empresa" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton.parentElement?.tagName).toBe("H2");
    expect(screen.queryByRole("link", { name: "Precios y catálogo" })).toBeNull();
  });

  it("al pulsar Empresa se despliega, con clic, Enter o Espacio, y aria-controls apunta a su lista", async () => {
    ponerLetra("muy-grande");
    const usuario = userEvent.setup();
    pintar({ sesion: todo() });
    await arbol();
    const boton = within(zona()).getByRole("button", { name: "Empresa" });
    await usuario.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(within(zona()).getAllByRole("link").map((e) => e.textContent)).toEqual(CINCO);
    const lista = document.getElementById(boton.getAttribute("aria-controls") ?? "");
    expect(lista).not.toBeNull();
    expect(lista?.tagName).toBe("UL");
    expect(lista).toContainElement(screen.getByRole("link", { name: "Ayuda" }));
    await usuario.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "false");
    boton.focus();
    await usuario.keyboard("{Enter}");
    expect(boton).toHaveAttribute("aria-expanded", "true");
    await usuario.keyboard("{Enter}");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await usuario.keyboard(" ");
    expect(boton).toHaveAttribute("aria-expanded", "true");
  });

  it("con una entrada de Empresa o un espacio abierto arranca desplegada", async () => {
    ponerLetra("muy-grande");
    pintar({ sesion: todo(), ruta: "/precios/catalogo" });
    await arbol();
    expect(within(zona()).getByRole("button", { name: "Empresa" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Precios y catálogo" })).toHaveAttribute("aria-current", "page");
  });

  it("pasar de normal a muy grande en vivo la pliega, y volver a normal la muestra sin botón", async () => {
    pintar({ sesion: todo() });
    await arbol();
    expect(screen.getByRole("link", { name: "Ayuda" })).toBeInTheDocument();
    act(() => ponerLetra("muy-grande"));
    const boton = await within(zona()).findByRole("button", { name: "Empresa" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Ayuda" })).toBeNull();
    act(() => ponerLetra("normal"));
    await waitFor(() => expect(within(zona()).queryByRole("button", { name: "Empresa" })).toBeNull());
    expect(screen.getByRole("link", { name: "Ayuda" })).toBeInTheDocument();
  });

  it("el botón hereda la letra del título, tiene foco visible y con letra grande mide al menos 1,5 rem", () => {
    const hoja = leer("marco/BarraLateral.scss");
    const boton = regla(hoja, ".silice-marco-lateral__empresa-boton");
    expect(boton).not.toBe("");
    expect(boton).toMatch(/font:\s*inherit/);
    expect(boton).toMatch(/color:\s*inherit/);
    expect(boton).toMatch(/text-transform:\s*inherit/);
    expect(regla(boton, "&:focus-visible")).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    const compacta = bloque(hoja, "@include u.con-letra-grande");
    expect(regla(compacta, ".silice-marco-lateral__empresa-boton")).toMatch(/min-block-size:\s*1\.5rem/);
  });
});

describe("BarraLateral con módulos apagados (plan vial, Tarea 19)", () => {
  function pintarConApagados(apagados: string[]) {
    return render(
      <MemoryRouter initialEntries={["/pendientes"]}>
        <ContextoAplicacion.Provider
          value={{ sesion: sesionDe("admin"), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), modulosApagados: apagados }}
        >
          <ContextoPendientes.Provider value={SIN_PENDIENTES}>
            <BarraLateral obraAbierta={null} seccion={null} />
          </ContextoPendientes.Provider>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  it("encendida, la zona Empresa ofrece «Costos de producción»", async () => {
    pintarConApagados([]);
    expect(await screen.findByRole("link", { name: "Costos de producción" })).toHaveAttribute("href", "/produccion/resumen");
  });

  it("con producción apagada, «Costos de producción» no aparece en la barra y los otros espacios sí", async () => {
    pintarConApagados(["produccion"]);
    const empresa = await screen.findByRole("navigation", { name: "Empresa" });
    expect(within(empresa).getAllByRole("link").map((e) => e.textContent)).toEqual([
      "Auditar un presupuesto",
      "Precios y catálogo",
      "Empresa y personas",
      "Ayuda",
    ]);
    expect(screen.queryByRole("link", { name: "Costos de producción" })).toBeNull();
  });
});
