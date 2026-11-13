import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cuerpoDeVista } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";

// Cabecera compacta del Presupuesto (decisión de Eugenio, 2026-11-05): a 1366×768 con letra Normal la primera partida debe
// verse sin desplazarse (antes empezaba a 1.069 px). El diseño, sin quitar información: una línea de estado (versión,
// cambios, aprobación y total) → una franja de acciones («Siguiente paso» con su botón y «Descargar Excel») → pestañas → una
// barra de herramientas de «Partidas» (agregar, aviso de decimales, «¿Qué es esto?») → tabla, sin huecos entre ellas.
// Obra ficticia OF-001. Los textos esperados se escribieron a mano desde el diseño aprobado, no desde el código.
configure({ asyncUtilTimeout: 5000 });

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

const json = (cuerpo: unknown, estado = 200) =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

const ARMA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};
const REVISA: SesionRespuesta = { ...ARMA, login: "rita", nombre: "Rita Gómez", roles: ["revisa"], acciones: ["leer_proyecto"] };

const ID = "id-borrador-aaaaaaaaaaaa";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-20", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};

function borrador(cambios = 0): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
    resumen: {
      rev: 2,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.8602323440440333" },
      cambios,
      pendientes_catalogo: 0,
      hallazgos: [],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
      espacio_vacio: true,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

const aprobaciones = (estado: string) => ({
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "",
  versiones: {
    "001": {
      estado,
      por: estado === "guardada" ? null : "Rita Gómez <rita>",
      el: estado === "guardada" ? null : "2026-10-25T10:30:00",
      notas: "",
      armo: false,
    },
  },
  eventos: [],
  ultima_aprobada: null,
});

describe("Presupuesto: cabecera compacta", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let abierto: BorradorAbierto;
  let estadoDeAprobacion: string;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    abierto = borrador();
    estadoDeAprobacion = "guardada";
    fetchFalso.mockImplementation(async (ruta, init) => {
      const texto = String(ruta);
      const camino = new URL(texto, "http://silice.local").pathname;
      const metodo = init?.method ?? "GET";
      if (camino === "/v1/aprobaciones" && metodo === "GET") return json(aprobaciones(estadoDeAprobacion));
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (camino.endsWith("/cambios")) return json({ rev: 2, cambios: [] });
      const vista = cuerpoDeVista(texto);
      if (vista !== null) return json(vista);
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(sesion: SesionRespuesta = ARMA) {
    const valor: Aplicacion = {
      sesion,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <MemoryRouter initialEntries={["/hoja"]}>
        <ContextoAplicacion.Provider value={valor}>
          <PaginaHoja />
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  async function listo() {
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    await screen.findByRole("table", { name: "Presupuesto" });
    return estado;
  }
  const antes = (a: Element, b: Element) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

  describe("la línea de estado", () => {
    test("reúne versión, estado de cambios, aprobación y total, sin título propio", async () => {
      abierto = borrador(2);
      montar();
      const estado = await listo();
      await waitFor(() => expect(estado.querySelector(".silice-hoja__aprobacion-etiqueta")).toHaveTextContent("Guardada"));
      expect(estado).toHaveTextContent("Versión 001");
      expect(estado).toHaveTextContent("2 cambios sin guardar");
      expect(within(estado).getByText("Aprobación:")).toBeInTheDocument();
      expect(estado).toHaveTextContent("Total 2.703,86 USD");
      // Deja de ser un bloque alto con su título: la región conserva el nombre, el h2 se va.
      expect(screen.queryByRole("heading", { name: "Estado del borrador" })).toBeNull();
    });

    test("va antes que la franja de acciones y las pestañas (estado → acciones → pestañas)", async () => {
      montar();
      const estado = await listo();
      const franja = await screen.findByRole("region", { name: "Siguiente paso" });
      const pestanas = screen.getByRole("tablist", { name: "Secciones del presupuesto" });
      expect(antes(estado, franja)).toBe(true);
      expect(antes(franja, pestanas)).toBe(true);
    });

    test("el total sigue también al pie de la tabla", async () => {
      montar();
      await listo();
      expect(await screen.findByText(/Total del presupuesto/)).toBeInTheDocument();
    });
  });

  describe("la franja de acciones", () => {
    test("«Siguiente paso» y «Descargar Excel» van en la misma fila de acciones, el principal primero", async () => {
      montar();
      await listo();
      const franja = await screen.findByRole("region", { name: "Siguiente paso" });
      const enviar = await within(franja).findByRole("button", { name: "Enviar a aprobación…" });
      const excel = screen.getByRole("button", { name: /Descargar Excel/ });
      // Una sola fila: el mismo contenedor, el botón del paso antes que el de Excel.
      expect(franja.parentElement).toContainElement(excel);
      expect(antes(enviar, excel)).toBe(true);
      expect(enviar).toHaveClass("cds--btn--primary");
      expect(excel).not.toHaveClass("cds--btn--primary");
    });

    test("hay un solo botón principal en toda la pantalla", async () => {
      montar();
      await listo();
      await screen.findByRole("button", { name: "Enviar a aprobación…" });
      expect(document.querySelectorAll(".cds--btn--primary")).toHaveLength(1);
    });

    test("«Descargar Excel» no se vuelve a montar al aparecer el paso (el botón que se tenía sigue vivo)", async () => {
      montar();
      await listo();
      const excel = screen.getByRole("button", { name: /Descargar Excel/ });
      await screen.findByRole("button", { name: "Enviar a aprobación…" });
      expect(excel).toBeInTheDocument();
    });

    test("sin paso que dar (aprobada) «Descargar Excel» sigue a la vista, antes de las pestañas", async () => {
      estadoDeAprobacion = "aprobada";
      montar();
      await listo();
      await waitFor(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).toHaveTextContent(/^Aprobada/));
      expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
      const excel = screen.getByRole("button", { name: /Descargar Excel/ });
      expect(antes(excel, screen.getByRole("tablist", { name: "Secciones del presupuesto" }))).toBe(true);
    });
  });

  describe("la barra de herramientas de «Partidas»", () => {
    const barra = () => screen.findByRole("group", { name: "Herramientas de Partidas" });

    test("reúne «Agregar partida», el aviso de decimales y «¿Qué es esto?», en ese orden", async () => {
      montar();
      await listo();
      const herramientas = await barra();
      const agregar = within(herramientas).getByRole("button", { name: "Agregar partida" });
      const decimales = within(herramientas).getByText(/Escriba los decimales con coma/);
      const ayuda = within(herramientas).getByRole("button", { name: "¿Qué es esto?" });
      expect(antes(agregar, decimales)).toBe(true);
      expect(antes(decimales, ayuda)).toBe(true);
    });

    test("está entre las pestañas y la tabla", async () => {
      montar();
      await listo();
      const herramientas = await barra();
      expect(antes(screen.getByRole("tablist", { name: "Secciones del presupuesto" }), herramientas)).toBe(true);
      expect(antes(herramientas, screen.getByRole("table", { name: "Presupuesto" }))).toBe(true);
    });

    test("«¿Qué es esto?» abierto pone su explicación dentro de la barra, tras los botones, y Esc devuelve el foco al botón", async () => {
      montar();
      await listo();
      const herramientas = await barra();
      const ayuda = within(herramientas).getByRole("button", { name: "¿Qué es esto?" });
      await userEvent.click(ayuda);
      const panel = within(herramientas).getByRole("region", { name: "Partidas" });
      expect(antes(ayuda, panel)).toBe(true);
      await userEvent.keyboard("{Escape}");
      expect(ayuda).toHaveFocus();
      expect(within(herramientas).queryByRole("region", { name: "Partidas" })).toBeNull();
    });

    test("quien solo revisa ve la barra con «¿Qué es esto?» y sin lo que escribe", async () => {
      montar(REVISA);
      await listo();
      const herramientas = await barra();
      expect(within(herramientas).getByRole("button", { name: "¿Qué es esto?" })).toBeInTheDocument();
      expect(within(herramientas).queryByRole("button", { name: "Agregar partida" })).toBeNull();
      expect(within(herramientas).queryByText(/Escriba los decimales con coma/)).toBeNull();
    });

    test("«Agregar partida» devuelve el foco a su botón al cancelar el diálogo", async () => {
      montar();
      await listo();
      const agregar = within(await barra()).getByRole("button", { name: "Agregar partida" });
      await userEvent.click(agregar);
      const dialogo = await screen.findByRole("dialog", { name: "Agregar partida" });
      await userEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
      await waitFor(() => expect(agregar).toHaveFocus());
    });
  });

  describe("sin hueco antes de la tabla", () => {
    // Causa del hueco de ~80 px: dos regiones vivas vacías (el aviso de «Partidas» y «Aplicando los cambios…») eran hijas de
    // la rejilla de la pestaña (`gap` de 1,5 rem): cada una, aunque de alto cero, sumaba un hueco. Una región viva vacía
    // debe sacarse del flujo (`.silice-hoja__region-viva:empty`), no dejar un contenedor vacío entre la barra y la tabla.
    test("todo hijo vacío de la pestaña es una región viva fuera del flujo", async () => {
      montar();
      await listo();
      await barra();
      const pestana = document.querySelector(".silice-hoja__pestana")!;
      const vacios = Array.from(pestana.children).filter((h) => h.textContent === "" && h.children.length === 0);
      expect(vacios.length).toBeGreaterThan(0);
      for (const v of vacios) expect(v).toHaveClass("silice-hoja__region-viva");
    });

    test("las regiones vivas vacías no ocupan lugar: están sacadas del flujo en la hoja de estilos", () => {
      const nodo = (
        globalThis as unknown as {
          process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
        }
      ).process;
      const scss = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8");
      expect(scss).toMatch(/\.silice-hoja__region-viva:empty\s*\{[^}]*position:\s*absolute/);
    });
  });

  const barra = () => screen.findByRole("group", { name: "Herramientas de Partidas" });
});
