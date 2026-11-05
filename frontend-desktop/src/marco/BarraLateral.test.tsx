import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, PendienteDeObra, SesionRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { BarraLateral } from "./BarraLateral";
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
  ruta = "/inicio/pendientes",
  pendientes = SIN_PENDIENTES,
}: Opciones = {}) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <ContextoAplicacion.Provider
        value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <ContextoPendientes.Provider value={pendientes}>
          <BarraLateral obraAbierta={abierta} />
        </ContextoPendientes.Provider>
        <Ubicacion />
      </ContextoAplicacion.Provider>
    </MemoryRouter>,
  );
}

const listaDeObras = () => screen.findByRole("list", { name: "Obras" });

describe("BarraLateral: lista sin carpetas (D-F3-3)", () => {
  it("con obras de dos carpetas no hay grupos por carpeta: las obras salen por nombre, seguidas", async () => {
    pintar();
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link").map((e) => e.textContent)).toEqual([
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
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link")).toHaveLength(2);
    expect(screen.queryByRole("group", { name: "Carpeta Norte" })).toBeNull();
    expect(document.body.textContent).not.toContain("Carpeta Norte");
  });

  it("las obras van por nombre aunque la API las traiga por carpeta: una de la carpeta Sur que empieza por A queda primera", async () => {
    servidor([CLINICA, TORRE, obra(SUR, 4, "Almacén Sur"), GALPON]);
    pintar();
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link").map((e) => e.textContent)).toEqual([
      "Almacén Sur",
      "Clínica Las Mercedes",
      "Galpón Sur",
      "Torre B",
    ]);
  });

  it("el orden ignora tildes y mayúsculas, y con el mismo nombre desempata por el título de la carpeta", async () => {
    servidor([obra(SUR, 3, "galpón"), obra(NORTE, 1, "Galpón"), obra(NORTE, 2, "Álamo")]);
    pintar();
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link").map((e) => e.textContent)).toEqual([
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
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link").map((e) => e.textContent)).toEqual(["Clínica Las Mercedes", "Torre B"]);
    expect(screen.queryByText("Galpón Sur")).toBeNull();
  });

  it("una cuenta sin CAMBIAR_CASO en la carpeta de la empresa solo ve las de la empresa", async () => {
    servidor([obra(null, 5, "Obra propia"), CLINICA], null);
    pintar({ sesion: sesionDe("rita") });
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link").map((e) => e.textContent)).toEqual(["Obra propia"]);
  });
});

describe("BarraLateral: lista plana, la obra abierta y su Resumen (F6, T5)", () => {
  const abierta = { carpeta: NORTE, obraId: 1 };
  const RUTA_DE_CLINICA = "/obra/Carpeta%20Norte.db/1/presupuesto/componer";

  it("las obras son una lista plana: un elemento por obra, sin sub-listas, sin chevrons y sin roles de árbol", async () => {
    pintar({ abierta, ruta: RUTA_DE_CLINICA });
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("listitem")).toHaveLength(3);
    expect(within(lista).queryByRole("list")).toBeNull();
    expect(lista.querySelector("ul")).toBeNull();
    expect(lista.querySelector("svg")).toBeNull();
    expect(document.querySelector('[role="tree"], [role="treeitem"], [role="group"], [aria-expanded], [aria-level]')).toBeNull();
    // Las secciones de la obra ya no cuelgan de la barra lateral: están en la barra de la obra.
    for (const seccion of ["Resumen", "Presupuesto", "Tramos", "Archivos y planos", "Versiones", "Aprobaciones", "Mercado", "Control de obra", "Riesgo"]) {
      expect(screen.queryByRole("link", { name: seccion })).toBeNull();
    }
  });

  it("cada obra enlaza a su Resumen, aunque la persona esté en otra sección o subvista de otra obra (no se conserva la sección)", async () => {
    pintar({ abierta, ruta: RUTA_DE_CLINICA });
    const lista = await listaDeObras();
    expect(within(lista).getByRole("link", { name: "Clínica Las Mercedes" })).toHaveAttribute("href", "/obra/Carpeta%20Norte.db/1/resumen");
    expect(within(lista).getByRole("link", { name: "Torre B" })).toHaveAttribute("href", "/obra/Carpeta%20Norte.db/2/resumen");
    expect(within(lista).getByRole("link", { name: "Galpón Sur" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/resumen");
  });

  it("la obra de la ruta lleva aria-current=page en cualquier sección o subvista; las demás no", async () => {
    pintar({ abierta, ruta: RUTA_DE_CLINICA });
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("aria-current")])).toEqual([
      ["Clínica Las Mercedes", "page"],
      ["Galpón Sur", null],
      ["Torre B", null],
    ]);
    expect(lista.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
  });

  it("sin obra abierta ninguna lleva aria-current", async () => {
    pintar();
    const lista = await listaDeObras();
    expect(lista.querySelectorAll("[aria-current]")).toHaveLength(0);
  });

  it("con el mismo número de obra en otra carpeta, solo la de la carpeta de la ruta está marcada (la clave es carpeta más número)", async () => {
    servidor([obra(NORTE, 1, "Clínica"), obra(SUR, 1, "Galpón")]);
    pintar({ abierta: { carpeta: SUR, obraId: 1 }, ruta: "/obra/Carpeta%20Sur.db/1/resumen" });
    const lista = await listaDeObras();
    expect(within(lista).getByRole("link", { name: "Galpón" })).toHaveAttribute("aria-current", "page");
    expect(within(lista).getByRole("link", { name: "Clínica" })).not.toHaveAttribute("aria-current");
  });

  it("ya no pide la lista de obras con tramos: la sección no depende de ella", async () => {
    pintar({ sesion: sesionDe("rita"), abierta, ruta: "/obra/Carpeta%20Norte.db/1/resumen" });
    await listaDeObras();
    expect(pedirFalso).not.toHaveBeenCalledWith("/v1/vial/obras");
  });
});

describe("BarraLateral: Vista general y «Costos y producción»", () => {
  // F6, T8 (diseño visual 3.1, punto 1): la primera entrada es «Vista general», que lleva a Inicio; las dos vistas de Inicio
  // (Vista general y Pendientes) son del mismo espacio, así que la entrada está activa en cualquiera de ellas.
  it.each(["/inicio/general", "/inicio/pendientes"])("«Vista general» es un enlace a #/inicio/general y está activo en %s", async (ruta) => {
    pintar({ ruta });
    await listaDeObras();
    const enlace = screen.getByRole("link", { name: "Vista general" });
    expect(enlace).toHaveAttribute("href", "/inicio/general");
    expect(enlace).toHaveAttribute("aria-current", "page");
  });

  it("«Vista general» no está activa fuera de Inicio, y ya no hay un enlace llamado «Pendientes» en la barra", async () => {
    pintar({ ruta: "/obra/empresa/7/resumen" });
    await listaDeObras();
    expect(screen.getByRole("link", { name: "Vista general" })).not.toHaveAttribute("aria-current");
    expect(screen.queryByRole("link", { name: "Pendientes" })).toBeNull();
  });

  // F6, T6: «Empresa y personas» y «Ayuda» pasaron a la Cuenta; la zona de abajo es «Costos y producción» (Auditar,
  // Precios, Costos de producción, en ese orden), sin el grupo anidado de antes.
  it("«Costos y producción» lista sus tres espacios usables, en ese orden, con el abierto marcado", async () => {
    // Quien ve todo: lo de la administración y, además, `leer_proyecto` (el catálogo y el libro).
    const todo = sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] });
    pintar({ sesion: todo, ruta: "/precios/catalogo" });
    await listaDeObras();
    const zona = screen.getByRole("navigation", { name: "Costos y producción" });
    const enlaces = within(zona).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual(["Auditar un presupuesto", "Precios y catálogo", "Costos de producción"]);
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual(["/auditoria/subir", "/precios/listas", "/produccion/resumen"]);
    expect(enlaces[1]).toHaveAttribute("aria-current", "page");
    expect(zona.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
    expect(within(zona).getByRole("heading", { level: 2, name: "Costos y producción" })).toBeInTheDocument();
    expect(within(zona).queryByRole("heading", { level: 3 })).toBeNull();
  });

  it("ya no ofrece «Empresa y personas» ni «Ayuda» (viven en la Cuenta) ni una zona llamada «Empresa»", async () => {
    const todo = sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] });
    pintar({ sesion: todo, ruta: "/inicio/pendientes" });
    await listaDeObras();
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).queryByRole("link", { name: "Empresa y personas" })).toBeNull();
    expect(within(lateral).queryByRole("link", { name: "Ayuda" })).toBeNull();
    expect(within(lateral).queryByRole("navigation", { name: "Empresa" })).toBeNull();
    expect(within(lateral).queryByRole("heading", { name: "Empresa" })).toBeNull();
    expect(lateral.querySelectorAll("a[href^='/empresa'], a[href^='/cuenta']")).toHaveLength(0);
  });

  it("quien arma entra a Precios por el Catálogo; el grupo lleva a la primera herramienta usable de cada espacio", async () => {
    pintar({ sesion: sesionDe("ana") });
    await listaDeObras();
    const zona = screen.getByRole("navigation", { name: "Costos y producción" });
    expect(within(zona).getByRole("link", { name: "Auditar un presupuesto" })).toHaveAttribute("href", "/auditoria/subir");
    expect(within(zona).getByRole("link", { name: "Precios y catálogo" })).toHaveAttribute("href", "/precios/catalogo");
    expect(within(zona).getByRole("link", { name: "Costos de producción" })).toHaveAttribute("href", "/produccion/resumen");
  });

  it("quien solo registra costos entra a Producción por «Costos del período»", async () => {
    pintar({ sesion: sesionDe("ana", { acciones: ["leer_proyecto", "registrar_costos_produccion"] }) });
    await listaDeObras();
    const zona = screen.getByRole("navigation", { name: "Costos y producción" });
    expect(within(zona).getByRole("link", { name: "Costos de producción" })).toHaveAttribute("href", "/produccion/costos");
  });

  it("un espacio sin herramienta que la cuenta pueda usar no se muestra", async () => {
    pintar({ sesion: sesionDe("rita") });
    await listaDeObras();
    const zona = screen.getByRole("navigation", { name: "Costos y producción" });
    // Rita no opera la arenera ni registra costos.
    expect(within(zona).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("href")])).toEqual([
      ["Auditar un presupuesto", "/auditoria/subir"],
      ["Precios y catálogo", "/precios/catalogo"],
    ]);
  });

  it.each([
    ["/auditoria/historial", "Auditar un presupuesto"],
    ["/precios/indices", "Precios y catálogo"],
    ["/produccion/costos", "Costos de producción"],
  ])("en %s solo «%s» está activa: coincide el primer segmento de la ruta", async (ruta, activa) => {
    pintar({ sesion: sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] }), ruta });
    await listaDeObras();
    const zona = screen.getByRole("navigation", { name: "Costos y producción" });
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
    expect(await screen.findByRole("link", { name: "Clínica Las Mercedes" })).toBeInTheDocument();
    expect(screen.queryByText("No se pudieron cargar las obras")).toBeNull();
  });

  it("sin obras dice «Todavía no hay obras» y ofrece Nueva obra", async () => {
    servidor([]);
    pintar();
    expect(await screen.findByText("Todavía no hay obras")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nueva obra" })).toBeInTheDocument();
  });
});

// La lista plana es de enlaces: el teclado es el de siempre (Tab y Mayús+Tab, Enter), sin la parada única, las flechas ni
// el despliegue del árbol de WAI-ARIA que tenía antes.
describe("BarraLateral: teclado de la lista plana (F6, T5)", () => {
  const abierta = { carpeta: NORTE, obraId: 1 };

  it("cada obra es un enlace que entra en el orden de tabulación, en el orden de la lista (sin parada única)", async () => {
    pintar({ abierta, ruta: "/obra/Carpeta%20Norte.db/1/resumen" });
    const lista = await listaDeObras();
    const enlaces = within(lista).getAllByRole("link");
    expect(enlaces).toHaveLength(3);
    for (const enlace of enlaces) expect(enlace).not.toHaveAttribute("tabindex", "-1");
    expect(lista.querySelectorAll('[tabindex="-1"]')).toHaveLength(0);
  });

  it("Tab recorre Vista general, Nueva obra y las obras en orden; Enter abre la obra enfocada", async () => {
    const u = userEvent.setup();
    pintar({ ruta: "/inicio/pendientes" });
    await listaDeObras();
    await u.tab();
    expect(screen.getByRole("link", { name: "Vista general" })).toHaveFocus();
    await u.tab();
    expect(screen.getByRole("button", { name: "Nueva obra" })).toHaveFocus();
    await u.tab();
    expect(screen.getByRole("link", { name: "Clínica Las Mercedes" })).toHaveFocus();
    await u.tab();
    expect(screen.getByRole("link", { name: "Galpón Sur" })).toHaveFocus();
    await u.keyboard("{Enter}");
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/obra/Carpeta%20Sur.db/3/resumen");
  });

  it("las flechas no mueven el foco entre obras: no hay patrón de árbol", async () => {
    const u = userEvent.setup();
    pintar({ ruta: "/inicio/pendientes" });
    const lista = await listaDeObras();
    const clinica = within(lista).getByRole("link", { name: "Clínica Las Mercedes" });
    clinica.focus();
    await u.keyboard("{ArrowDown}{ArrowRight}");
    expect(clinica).toHaveFocus();
  });
});

describe("BarraLateral: Nueva obra", () => {
  it("es un botón con la clase del botón principal, antes de la lista en el orden del documento", async () => {
    pintar();
    const lista = await listaDeObras();
    const boton = screen.getByRole("button", { name: "Nueva obra" });
    expect(boton).toHaveClass("silice-marco-boton-principal");
    expect(boton.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(boton.compareDocumentPosition(lista) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("no aparece si la cuenta no puede crear obras", async () => {
    pintar({ sesion: sesionDe("rita") });
    await listaDeObras();
    expect(screen.queryByRole("button", { name: "Nueva obra" })).toBeNull();
  });

  it("al pulsarlo abre el diálogo para crear una obra", async () => {
    pintar();
    await listaDeObras();
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
    pintar({ abierta: { carpeta: SUR, obraId: 3 }, ruta: "/obra/Carpeta%20Sur.db/3/resumen" });
    await listaDeObras();
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
    pintar({ abierta: { carpeta: SUR, obraId: 3 } });
    await listaDeObras();
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
    await listaDeObras();
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
    pintar({ abierta: { carpeta: SUR, obraId: 3 } });
    await listaDeObras();
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

describe("BarraLateral: un solo nivel (antes, niveles del árbol)", () => {
  it("con obras de dos carpetas hay un elemento de lista por obra, en un solo nivel, sin atributos de nivel ni de posición", async () => {
    pintar({ abierta: { carpeta: NORTE, obraId: 1 }, ruta: "/obra/Carpeta%20Norte.db/1/resumen" });
    const lista = await listaDeObras();
    const items = within(lista).getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual(["Clínica Las Mercedes", "Galpón Sur", "Torre B"]);
    for (const item of items) {
      expect(item.parentElement).toBe(lista);
      expect(item.querySelector("[aria-level], [aria-setsize], [aria-posinset]")).toBeNull();
    }
  });

  it("sin carpetas, también: un solo nivel, sea cual sea la obra abierta", async () => {
    servidor([CLINICA, TORRE]);
    pintar({ abierta: { carpeta: NORTE, obraId: 2 }, ruta: "/obra/Carpeta%20Norte.db/2/resumen" });
    const lista = await listaDeObras();
    expect(within(lista).getAllByRole("listitem")).toHaveLength(2);
    expect(lista.querySelectorAll("ul")).toHaveLength(0);
    expect(within(lista).getByRole("link", { name: "Torre B" })).toHaveAttribute("aria-current", "page");
  });
});

describe("BarraLateral: carga de las obras", () => {
  it("mientras llegan las obras dice «Cargando obras…» y no pinta una lista vacía", async () => {
    pedirFalso.mockImplementation(() => new Promise(() => {}));
    pintar();
    expect(await screen.findByText("Cargando obras…")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Obras" })).toBeNull();
    expect(screen.queryByText("Todavía no hay obras")).toBeNull();
  });

  it("al reintentar tras un error vuelve a decir «Cargando obras…» en vez de mostrar una lista vacía", async () => {
    respuesta = new ErrorDeApi(500, "falló");
    pintar();
    await screen.findByText("No se pudieron cargar las obras");
    pedirFalso.mockImplementation(() => new Promise(() => {}));
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Cargando obras…")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Obras" })).toBeNull();
  });

  it("mientras recarga conserva la lista que ya tenía", async () => {
    conCreacionDeCodigo("9");
    pintar();
    await listaDeObras();
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
      expect(screen.getByRole("list", { name: "Obras" })).toBeInTheDocument();
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
    await listaDeObras();
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
      expect(screen.getByTestId("ubicacion")).toHaveTextContent("/inicio/pendientes");
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

  it("Vista general lleva una píldora con el total y su nombre accesible dice «Vista general, 4 por hacer»", async () => {
    pintar({ pendientes: conPendientes(CUATRO) });
    await listaDeObras();
    const enlace = enlacePendientes("Vista general, 4 por hacer");
    expect(enlace).toHaveAttribute("href", "/inicio/general");
    expect(within(enlace).getByText("4")).toHaveClass("silice-pildora");
  });

  it("con un solo pendiente dice «Vista general, 1 por hacer»", async () => {
    pintar({ pendientes: conPendientes([CUATRO[0]!]) });
    await listaDeObras();
    expect(enlacePendientes("Vista general, 1 por hacer")).toBeInTheDocument();
  });

  it.each([
    ["sin ninguno", conPendientes([])],
    ["mientras carga", { estado: "cargando", recargar: vi.fn() } as PendientesDelMarco],
    ["con error", { estado: "error", mensaje: "falló", recargar: vi.fn() } as PendientesDelMarco],
  ])("%s no hay píldora ni número, y el enlace se llama solo «Vista general»", async (_caso, pendientes) => {
    pintar({ pendientes });
    await listaDeObras();
    const enlace = enlacePendientes("Vista general");
    expect(enlace.querySelector(".silice-pildora")).toBeNull();
    expect(enlace.textContent).toBe("Vista general");
  });

  it("cada obra con pendientes lleva la suya (carpeta y número); la de 0 no lleva ninguna", async () => {
    pintar({ pendientes: conPendientes(CUATRO) });
    const lista = await listaDeObras();
    const pildoraDe = (nombre: string) => within(lista).getByRole("link", { name: new RegExp(`^${nombre}`) }).querySelector(".silice-pildora");
    expect(pildoraDe("Clínica Las Mercedes")?.textContent).toBe("2");
    expect(pildoraDe("Torre B")?.textContent).toBe("1");
    expect(pildoraDe("Galpón Sur")?.textContent).toBe("1");
    expect(within(lista).getByRole("link", { name: "Clínica Las Mercedes, 2 por hacer" })).toBeInTheDocument();
  });

  it("la clave es carpeta más número: el mismo número en otra carpeta no cuenta", async () => {
    servidor([obra(NORTE, 1, "Clínica"), obra(SUR, 1, "Galpón")]);
    pintar({ pendientes: conPendientes([pendiente(SUR, 1, "x"), pendiente(SUR, 1, "y"), pendiente(SUR, 1, "z")]) });
    const lista = await listaDeObras();
    expect(within(lista).getByRole("link", { name: "Clínica" }).querySelector(".silice-pildora")).toBeNull();
    expect(within(lista).getByRole("link", { name: "Galpón, 3 por hacer" })).toBeInTheDocument();
  });

  it("una obra sin pendientes conserva su nombre accesible de siempre", async () => {
    pintar({ pendientes: conPendientes([pendiente(NORTE, 2, "c")]) });
    const lista = await listaDeObras();
    expect(within(lista).getByRole("link", { name: "Clínica Las Mercedes" })).toBeInTheDocument();
  });
});

describe("BarraLateral: obras con el mismo nombre (D-F3-3)", () => {
  it("dos obras llamadas igual en carpetas distintas muestran debajo su carpeta; las demás no", async () => {
    servidor([obra(NORTE, 1, "Galpón"), obra(SUR, 3, "Galpón"), obra(NORTE, 2, "Torre B")]);
    pintar();
    const lista = await listaDeObras();
    const filas = within(lista).getAllByRole("link");
    expect(filas.map((f) => f.textContent)).toEqual(["GalpónCarpeta Norte", "GalpónCarpeta Sur", "Torre B"]);
    expect(within(filas[0]!).getByText("Carpeta Norte")).toHaveClass("silice-marco-lateral__de-carpeta");
    expect(within(filas[2]!).queryByText(/Carpeta/)).toBeNull();
  });

  it("el nombre accesible de la homónima incluye su carpeta, y con píldora también el contador", async () => {
    servidor([obra(NORTE, 1, "Galpón"), obra(SUR, 3, "Galpón")]);
    pintar({ pendientes: conPendientes([pendiente(SUR, 3, "x")]) });
    const lista = await listaDeObras();
    expect(within(lista).getByRole("link", { name: "Galpón, Carpeta Norte" })).toBeInTheDocument();
    expect(within(lista).getByRole("link", { name: "Galpón, Carpeta Sur, 1 por hacer" })).toBeInTheDocument();
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
    const lista = await listaDeObras();
    const fila = within(lista).getByRole("link", { name: LARGO });
    const nombre = within(fila).getByText(LARGO);
    expect(nombre).toHaveClass("silice-marco-lateral__obra-nombre");
    return nombre;
  }

  it("el enlace de la obra conserva el nombre completo como nombre accesible y sin pasar el ratón no hay title", async () => {
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
// entradas de Empresa (hoy tres, las de «Costos y producción») se comían el alto: la zona de obras quedaba en casi nada. La zona de obras se queda con el alto que
// sobra y es la única que se desplaza; con letra Grande o Muy grande se compactan filas y títulos y la zona conserva un
// mínimo. jsdom no calcula el diseño: la estructura se prueba en el DOM y las reglas en el fuente; la medida real
// (cuántas obras caben a 1366×768) se hace en el navegador.
describe("BarraLateral: la zona de obras con letra grande", () => {
  it("la cabecera de Obras y «Nueva obra» quedan fuera de la lista, que tiene su propio desplazamiento", async () => {
    servidor([obra(NORTE, 1, "Torre"), TORRE]);
    pintar();
    const lista = await listaDeObras();
    const zona = lista.closest(".silice-marco-lateral__obras");
    expect(zona).not.toBeNull();
    expect(lista.parentElement).toBe(zona);
    expect(within(lista).queryByRole("button", { name: "Nueva obra" })).toBeNull();
    expect(within(zona as HTMLElement).getByRole("heading", { name: "Obras" })).toBeInTheDocument();
    const hojas = leer("marco/BarraLateral.scss");
    expect(regla(hojas, ".silice-marco-lateral__obras")).toMatch(/flex:\s*1 1 auto/);
    expect(regla(hojas, ".silice-marco-lateral__arbol")).toMatch(/overflow-y:\s*auto/);
    expect(regla(hojas, ".silice-marco-lateral__costos")).toMatch(/flex:\s*none/);
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

// Tarea 0 de F4: con letra Grande o Muy grande la zona se pliega para darle su alto al árbol (decisión de Eugenio al cierre
// de F3); desde F6, T6 la zona se llama «Costos y producción» y trae solo los tres espacios. Con letra normal sigue como
// antes. El tamaño se pone a mano en la raíz, como lo deja `aplicarTamanoLetra`.
describe("BarraLateral: «Costos y producción» plegable con letra grande (F4, Tarea 0; F6, T6)", () => {
  const TRES = ["Auditar un presupuesto", "Precios y catálogo", "Costos de producción"];
  const todo = () => sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] });
  const ponerLetra = (valor: string) => document.documentElement.setAttribute("data-silice-letra", valor);
  const zona = () => screen.getByRole("navigation", { name: "Costos y producción" });
  afterEach(() => document.documentElement.removeAttribute("data-silice-letra"));

  it("con letra normal el título es un h2 sin botón y se ven los tres espacios", async () => {
    pintar({ sesion: todo() });
    await listaDeObras();
    const titulo = within(zona()).getByRole("heading", { name: "Costos y producción" });
    expect(within(titulo).queryByRole("button")).toBeNull();
    expect(within(zona()).getAllByRole("link").map((e) => e.textContent)).toEqual(TRES);
  });

  it("con letra grande la zona arranca plegada", async () => {
    ponerLetra("grande");
    pintar({ sesion: todo() });
    await listaDeObras();
    const boton = within(zona()).getByRole("button", { name: "Costos y producción" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton.parentElement?.tagName).toBe("H2");
    expect(screen.queryByRole("link", { name: "Precios y catálogo" })).toBeNull();
  });

  it("al pulsar el título se despliega, con clic, Enter o Espacio, y aria-controls apunta a su lista", async () => {
    ponerLetra("muy-grande");
    const usuario = userEvent.setup();
    pintar({ sesion: todo() });
    await listaDeObras();
    const boton = within(zona()).getByRole("button", { name: "Costos y producción" });
    await usuario.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(within(zona()).getAllByRole("link").map((e) => e.textContent)).toEqual(TRES);
    const lista = document.getElementById(boton.getAttribute("aria-controls") ?? "");
    expect(lista).not.toBeNull();
    expect(lista?.tagName).toBe("UL");
    expect(lista).toContainElement(screen.getByRole("link", { name: "Costos de producción" }));
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

  it("con un espacio abierto arranca desplegada", async () => {
    ponerLetra("muy-grande");
    pintar({ sesion: todo(), ruta: "/precios/catalogo" });
    await listaDeObras();
    expect(within(zona()).getByRole("button", { name: "Costos y producción" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Precios y catálogo" })).toHaveAttribute("aria-current", "page");
  });

  it("con la Cuenta abierta arranca plegada: la Cuenta ya no es de esta zona", async () => {
    ponerLetra("muy-grande");
    pintar({ sesion: todo(), ruta: "/cuenta/ayuda" });
    await listaDeObras();
    expect(within(zona()).getByRole("button", { name: "Costos y producción" })).toHaveAttribute("aria-expanded", "false");
  });

  it("pasar de normal a muy grande en vivo la pliega, y volver a normal la muestra sin botón", async () => {
    pintar({ sesion: todo() });
    await listaDeObras();
    expect(screen.getByRole("link", { name: "Costos de producción" })).toBeInTheDocument();
    act(() => ponerLetra("muy-grande"));
    const boton = await within(zona()).findByRole("button", { name: "Costos y producción" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Costos de producción" })).toBeNull();
    act(() => ponerLetra("normal"));
    await waitFor(() => expect(within(zona()).queryByRole("button", { name: "Costos y producción" })).toBeNull());
    expect(screen.getByRole("link", { name: "Costos de producción" })).toBeInTheDocument();
  });

  it("el botón hereda la letra del título, tiene foco visible y con letra grande mide al menos 1,5 rem", () => {
    const hoja = leer("marco/BarraLateral.scss");
    const boton = regla(hoja, ".silice-marco-lateral__costos-boton");
    expect(boton).not.toBe("");
    expect(boton).toMatch(/font:\s*inherit/);
    expect(boton).toMatch(/color:\s*inherit/);
    expect(boton).toMatch(/text-transform:\s*inherit/);
    expect(regla(boton, "&:focus-visible")).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    const compacta = bloque(hoja, "@include u.con-letra-grande");
    expect(regla(compacta, ".silice-marco-lateral__costos-boton")).toMatch(/min-block-size:\s*1\.5rem/);
  });

  it("no quedan reglas de la zona «Empresa» ni de su subtítulo en la hoja de estilos", () => {
    const hoja = leer("marco/BarraLateral.scss");
    expect(hoja).not.toMatch(/__empresa|__subtitulo/);
  });
});

describe("BarraLateral con módulos apagados (plan vial, Tarea 19)", () => {
  function pintarConApagados(apagados: string[]) {
    return render(
      <MemoryRouter initialEntries={["/inicio/pendientes"]}>
        <ContextoAplicacion.Provider
          value={{ sesion: sesionDe("admin"), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), modulosApagados: apagados }}
        >
          <ContextoPendientes.Provider value={SIN_PENDIENTES}>
            <BarraLateral obraAbierta={null} />
          </ContextoPendientes.Provider>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  it("encendida, la zona «Costos y producción» ofrece «Costos de producción»", async () => {
    pintarConApagados([]);
    expect(await screen.findByRole("link", { name: "Costos de producción" })).toHaveAttribute("href", "/produccion/resumen");
  });

  it("con producción apagada, «Costos de producción» no aparece en la barra y los otros espacios sí", async () => {
    pintarConApagados(["produccion"]);
    const zona = await screen.findByRole("navigation", { name: "Costos y producción" });
    expect(within(zona).getAllByRole("link").map((e) => e.textContent)).toEqual(["Auditar un presupuesto", "Precios y catálogo"]);
    expect(screen.queryByRole("link", { name: "Costos de producción" })).toBeNull();
  });
});
