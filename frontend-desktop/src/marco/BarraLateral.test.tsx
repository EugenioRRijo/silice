import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, SesionRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { BarraLateral } from "./BarraLateral";
import type { SeccionId } from "./secciones";

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

let respuesta: { carpeta_actual: string | null; obras: ObraDeCarpetaRespuesta[] } | ErrorDeApi;

function servidor(obras: ObraDeCarpetaRespuesta[], carpetaActual: string | null = NORTE) {
  respuesta = { carpeta_actual: carpetaActual, obras };
}

beforeEach(() => {
  servidor([CLINICA, TORRE, GALPON]);
  pedirFalso.mockReset();
  pedirFalso.mockImplementation(async (ruta: string) => {
    if (ruta === "/v1/obras/todas") {
      if (respuesta instanceof ErrorDeApi) throw respuesta;
      return respuesta;
    }
    if (ruta === "/v1/carpeta") return { moneda: "Bs", declarada: true, lista: null, aviso: null };
    throw new Error(`petición inesperada: ${ruta}`);
  });
});

interface Opciones {
  sesion?: SesionRespuesta;
  abierta?: { carpeta: string | null; obraId: number } | null;
  seccion?: SeccionId | null;
  ruta?: string;
}

function pintar({ sesion = sesionDe("ana"), abierta = null, seccion = null, ruta = "/pendientes" }: Opciones = {}) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <ContextoAplicacion.Provider
        value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <BarraLateral obraAbierta={abierta} seccion={seccion} />
      </ContextoAplicacion.Provider>
    </MemoryRouter>,
  );
}

const arbol = () => screen.findByRole("tree", { name: "Obras" });

describe("BarraLateral: agrupación por carpeta", () => {
  it("con obras de dos carpetas hay un grupo por carpeta con su nombre", async () => {
    pintar();
    const norte = await screen.findByRole("group", { name: "Carpeta Norte" });
    const sur = screen.getByRole("group", { name: "Carpeta Sur" });
    expect(within(norte).getAllByRole("treeitem").map((e) => e.textContent)).toEqual(["Clínica Las Mercedes", "Torre B"]);
    expect(within(sur).getAllByRole("treeitem").map((e) => e.textContent)).toEqual(["Galpón Sur"]);
  });

  it("con una sola carpeta no hay grupos ni se nombra la carpeta", async () => {
    servidor([CLINICA, TORRE]);
    pintar();
    const lista = await arbol();
    expect(within(lista).getAllByRole("treeitem")).toHaveLength(2);
    expect(screen.queryByRole("group", { name: "Carpeta Norte" })).toBeNull();
    expect(document.body.textContent).not.toContain("Carpeta Norte");
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
    expect(secciones.map((s) => s.textContent)).toEqual(["Resumen", "Presupuesto", "Aprobaciones", "Mercado", "Control de obra"]);
    expect(secciones.map((s) => s.getAttribute("aria-current"))).toEqual([null, "page", null, null, null]);
    expect(secciones[1]).toHaveAttribute("href", "/obra/Carpeta%20Norte.db/1/presupuesto");
    expect(screen.queryByRole("treeitem", { name: "Archivos y planos" })).toBeNull();
    expect(screen.queryByRole("treeitem", { name: "Versiones" })).toBeNull();
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
    // «hoja» y «mercado» exigen editar_hoja y «control», control_de_obra: quien solo revisa no los ve.
    expect(secciones.map((s) => s.textContent)).toEqual(["Resumen", "Aprobaciones"]);
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

  it("Empresa lista sus entradas usables, con la activa marcada", async () => {
    // Quien ve las cinco: lo de la administración y, además, `leer_proyecto` (el catálogo).
    const todo = sesionDe("admin", { acciones: [...sesionDe("admin").acciones, "leer_proyecto"] });
    pintar({ sesion: todo, ruta: "/empresa/personas" });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    const enlaces = within(zona).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual([
      "Precios y catálogo",
      "Auditar un presupuesto",
      "Producción",
      "Empresa y personas",
      "Ayuda",
    ]);
    expect(enlaces[3]).toHaveAttribute("aria-current", "page");
    expect(enlaces[3]).toHaveAttribute("href", "/empresa/personas");
  });

  it("una entrada cuya pantalla la cuenta no puede usar no se muestra", async () => {
    pintar({ sesion: sesionDe("rita") });
    await arbol();
    const zona = screen.getByRole("navigation", { name: "Empresa" });
    // «existencias» exige operar_arenera y «administracion», administrar_cuentas.
    expect(within(zona).getAllByRole("link").map((e) => e.textContent)).toEqual([
      "Precios y catálogo",
      "Auditar un presupuesto",
      "Ayuda",
    ]);
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
    await u.keyboard("{ArrowDown}{ArrowDown}");
    expect(within(lista).getByRole("treeitem", { name: "Aprobaciones" })).toHaveFocus();
    await u.keyboard("{ArrowUp}");
    expect(within(lista).getByRole("treeitem", { name: "Presupuesto" })).toHaveFocus();
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

  it("los estilos lo pintan con el acento, el texto del marco, seminegrita y 40 px de alto, solo con variables del tema", () => {
    const estilos = leer("marco/BarraLateral.scss");
    const regla = /\.silice-marco-boton-principal\s*\{([^}]*)\}/.exec(estilos)?.[1] ?? "";
    expect(regla).toContain("background-color: var(--silice-acento)");
    expect(regla).toMatch(/(^|[\s;])color: var\(--silice-marco\)/);
    expect(regla).toMatch(/font-weight: 600/);
    expect(regla).toMatch(/block-size: 2\.5rem/);
    expect(regla).toMatch(/inline-size: 100%/);
    expect(estilos).toContain("background-color: var(--silice-lateral)");
    expect(estilos).toMatch(/inline-size: 14\.75rem/);
    expect(estilos).toContain("var(--silice-lateral-activo)");
    expect(estilos).toMatch(/3px solid var\(--silice-acento\)/);
    expect(estilos).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  it("el tema neutro da al texto sobre el acento un contraste de al menos 4,5:1", () => {
    // Los alias neutros de tokens.scss: acento = yellow-30 de Carbon, marco = background-inverse de g10 (gray-80).
    const tokens = leer("estilos/tokens.scss");
    expect(tokens).toContain("--silice-acento: #{colors.$yellow-30}");
    expect(tokens).toContain("--silice-marco: var(--cds-background-inverse)");
    const luminancia = (hex: string) => {
      const [r, g, b] = [1, 3, 5].map((i) => {
        const c = parseInt(hex.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
    };
    const [claro, oscuro] = [luminancia("#f1c21b"), luminancia("#393939")];
    expect((claro + 0.05) / (oscuro + 0.05)).toBeGreaterThanOrEqual(4.5);
  });
});
