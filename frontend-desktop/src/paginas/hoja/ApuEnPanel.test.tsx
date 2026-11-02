import { fileURLToPath } from "node:url";
import { configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as sass from "sass";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { vistaApu, vistaPresupuesto } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, DetalleApu, Resumen, VersionesRespuesta, VistaApu, VistaPresupuesto } from "./logica";

// Tarea 7 del plan F4: el APU de una partida se abre en un panel lateral desde su código en «Partidas», sin cambiar de
// pestaña, y comparte la partida elegida con la pestaña «Análisis de precio (APU)». Obra ficticia OF-001 con dos partidas
// civiles inventadas (E-01 y E-02) y una sin precio (P-03); los textos esperados están escritos a mano a partir del plan.
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const EDITA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};
const REVISA: SesionRespuesta = { ...EDITA, login: "rita", nombre: "Rita Gómez", roles: ["revisa"], acciones: ["leer_proyecto"] };

const ID = "id-borrador-aaaaaaaaaaaa";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};
const m = (texto: string, exacto = texto) => ({ texto, exacto });

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "USD",
    total: m("2703.86"),
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
}

const BORRADOR: BorradorAbierto = {
  id: ID,
  base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
  resumen: resumen(),
  instantanea: { creadas: 0, mensaje: null },
};

function presupuesto(total: string): VistaPresupuesto {
  const [fila] = vistaPresupuesto().filas;
  const renglon = (partida: string, descripcion: string, conPrecio: boolean) => ({
    ...fila!,
    clave: `${partida}|version`,
    partida,
    descripcion,
    unidad: "m3",
    quitable: true,
    pu: conPrecio ? m("12.00") : null,
    total: conPrecio ? m("120.00") : null,
  });
  return {
    ...vistaPresupuesto(),
    filas: [
      renglon("E-01", "Excavación en tierra", true),
      renglon("E-02", "Relleno compactado", true),
      renglon("P-03", "Partida sin análisis", false),
    ],
    total: m(total),
  };
}

function detalle(codigo: string, descripcion: string): DetalleApu {
  return { ...vistaApu().detalle!, codigo, descripcion, unidad: "m3" };
}

// Sin `partida`, el servidor elige la primera de su lista (E-02): así se ve que la pestaña muestra la elegida en el panel.
function apu(partida: string | null): VistaApu {
  return vistaApu({
    partidas: [
      { codigo: "E-02", descripcion: "Relleno compactado con pisón" },
      { codigo: "E-01", descripcion: "Excavación en tierra a mano" },
    ],
    seleccionada: partida === "E-01" ? "E-01" : "E-02",
    detalle: partida === "E-01" ? detalle("E-01", "Excavación en tierra a mano") : detalle("E-02", "Relleno compactado con pisón"),
  });
}

type Cuerpo = Record<string, unknown> & { rev: number };

describe("Presupuesto: el APU de una partida en panel lateral (Tarea 7)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let total: string;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    total = "2703.86";
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = decodeURIComponent(url.pathname);
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(BORRADOR, 201);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json([]);
      if (camino === `/v1/hoja/borradores/${ID}/apu/E-01` && metodo === "PUT") {
        const cuerpo = JSON.parse(String(init?.body)) as Cuerpo;
        // El servidor acepta y el total del presupuesto cambia: la tabla lo vuelve a leer.
        total = "2800.50";
        return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1, total: m("2800.50") }), apu: apu("E-01") });
      }
      if (camino.endsWith("/vistas/presupuesto")) return json(presupuesto(total));
      if (camino.endsWith("/vistas/apu")) return json(apu(url.searchParams.get("partida")));
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  const escrituras = (patron: RegExp) =>
    fetchFalso.mock.calls
      .filter(([r, init]) => (init?.method ?? "GET") === "PUT" && patron.test(decodeURIComponent(String(r))))
      .map(([r, init]) => ({ ruta: decodeURIComponent(String(r)), cuerpo: JSON.parse(String(init?.body)) as Cuerpo }));
  const lecturasDeApu = () =>
    fetchFalso.mock.calls.map(([r]) => new URL(String(r), "http://silice.local")).filter((u) => u.pathname.endsWith("/vistas/apu"));

  function montar(sesion: SesionRespuesta = EDITA) {
    const valor: Aplicacion = {
      sesion,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  // Espera la tabla de «Partidas» (la pestaña con que abre una obra civil) y devuelve el botón del código de E-01.
  async function botonDeE01(): Promise<HTMLElement> {
    await screen.findByText("Excavación en tierra");
    const boton = screen.queryByRole("button", { name: "Abrir el APU de E-01" });
    expect(boton, "el código de E-01 es el botón «Abrir el APU de E-01»").not.toBeNull();
    return boton!;
  }

  async function abrirPanel(sesion: SesionRespuesta = EDITA): Promise<HTMLElement> {
    montar(sesion);
    await userEvent.click(await botonDeE01());
    return screen.findByRole("complementary", { name: "APU de E-01 · Excavación en tierra · m³" });
  }

  test("«Abrir el APU de E-01» abre el panel con su APU, sin cambiar de pestaña", async () => {
    const panel = await abrirPanel();
    expect(screen.getByRole("tab", { name: "Partidas", selected: true })).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { level: 2, name: "APU de E-01 · Excavación en tierra · m³" })).toHaveFocus();
    expect(await within(panel).findByRole("textbox", { name: "Cantidad, Materiales fila 1" })).toHaveValue("1");
    expect(within(panel).getByRole("textbox", { name: "Rendimiento (unidades por día)" })).toHaveValue("20");
    expect(within(panel).getByText("Cierre de partida")).toBeInTheDocument();
    // El panel pide el APU de esa partida, no el que el servidor elegiría por su cuenta.
    expect(lecturasDeApu().map((u) => u.searchParams.get("partida"))).toEqual(["E-01"]);
    // La tabla sigue a la vista junto al panel.
    expect(screen.getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toBeInTheDocument();
  });

  test("editar una cantidad en el panel manda el mismo PUT que la pestaña y el total bajo la tabla se vuelve a leer", async () => {
    const panel = await abrirPanel();
    const campo = await within(panel).findByRole("textbox", { name: "Cantidad, Materiales fila 1" });
    fireEvent.change(campo, { target: { value: "2,5" } });
    await waitFor(() => expect(escrituras(/\/apu\//)).toHaveLength(1));
    expect(escrituras(/\/apu\//)).toEqual([
      {
        ruta: `/v1/hoja/borradores/${ID}/apu/E-01`,
        cuerpo: { rev: 0, rendimiento: "20", materiales: ["2,5"], equipos: ["1"], mano_obra: ["1", "1"] },
      },
    ]);
    await waitFor(() =>
      expect(screen.getByText("Total del presupuesto").closest("p")).toHaveTextContent("Total del presupuesto 2.800,50 USD"),
    );
    // La barra de estado del borrador también recibe el resumen nuevo.
    expect(within(screen.getByRole("region", { name: "Estado del borrador" })).getByText(/1 cambio sin guardar/)).toBeInTheDocument();
  });

  test("Esc cierra el panel y el foco vuelve al botón de esa fila", async () => {
    await abrirPanel();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("complementary", { name: /^APU de E-01/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Abrir el APU de E-01" })).toHaveFocus();
  });

  test("con el panel abierto, la pestaña «Análisis de precio (APU)» muestra E-01 elegida", async () => {
    await abrirPanel();
    await userEvent.click(screen.getByRole("tab", { name: "Análisis de precio (APU)" }));
    expect(await screen.findByRole("heading", { level: 2, name: "E-01 · Excavación en tierra a mano · m3" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "E-01 · Excavación en tierra a mano" })).toBeChecked();
    expect(lecturasDeApu().at(-1)?.searchParams.get("partida")).toBe("E-01");
  });

  test("elegir otra partida en la pestaña la deja elegida para el panel", async () => {
    montar();
    await botonDeE01();
    await userEvent.click(screen.getByRole("tab", { name: "Análisis de precio (APU)" }));
    await userEvent.click(await screen.findByRole("radio", { name: "E-01 · Excavación en tierra a mano" }));
    await screen.findByRole("heading", { level: 2, name: "E-01 · Excavación en tierra a mano · m3" });
    await userEvent.click(screen.getByRole("tab", { name: "Partidas" }));
    // Vuelve a «Partidas» sin panel abierto (se abre desde la fila); la pestaña APU sigue en E-01 al volver.
    await botonDeE01();
    expect(screen.queryByRole("complementary", { name: /^APU de/ })).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Análisis de precio (APU)" }));
    expect(await screen.findByRole("heading", { level: 2, name: "E-01 · Excavación en tierra a mano · m3" })).toBeInTheDocument();
  });

  test("una partida sin precio (sin APU en el catálogo) no ofrece abrir su APU", async () => {
    montar();
    await botonDeE01();
    expect(screen.getByRole("button", { name: "Abrir el APU de E-02" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abrir el APU de P-03" })).toBeNull();
    expect(screen.getByText("P-03")).toHaveClass("silice-hoja__codigo");
  });

  test("cuenta que revisa: el panel se abre con el APU y sus cifras, sin nada que escriba (Foco 3)", async () => {
    const panel = await abrirPanel(REVISA);
    expect(await within(panel).findByText("Cierre de partida")).toBeInTheDocument();
    expect(within(panel).getByText("Precio unitario")).toBeInTheDocument();
    expect(within(panel).getByText("Llave de bola PVC 1/2")).toBeInTheDocument();
    expect(within(panel).queryAllByRole("textbox")).toEqual([]);
    expect(within(panel).getByText("Rendimiento (unidades por día)")).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "Agregar línea" })).toBeNull();
    expect(within(panel).queryByRole("button", { name: /^Quitar/ })).toBeNull();
    expect(within(panel).queryByRole("button", { name: /Cambiar/ })).toBeNull();
    expect(escrituras(/./)).toEqual([]);
  });

  test("estructura (Foco 4): la tabla se desplaza en su caja y el panel queda al lado, con la regla de pasar por encima", async () => {
    const panel = await abrirPanel();
    const conPanel = panel.closest(".silice-con-panel");
    expect(conPanel, "el panel y la tabla comparten el contenedor `.silice-con-panel`").not.toBeNull();
    const caja = screen.getByRole("table", { name: "Presupuesto" }).closest(".silice-hoja__desplazable");
    expect(caja, "la tabla de Partidas va en su caja desplazable").not.toBeNull();
    expect(conPanel!.contains(caja)).toBe(true);
    expect(panel).toHaveClass("silice-panel-lateral", "silice-panel-lateral--ancho");

    const hoja = sass.compile(fileURLToPath(new URL("./hoja.scss", import.meta.url))).css;
    expect(hoja).toMatch(/\.silice-hoja__desplazable\s*\{[^}]*overflow-x:\s*auto/);
    // Ni la pestaña ni el contenedor fijan un ancho: se encogen hasta el visible.
    const pestana = /\.silice-hoja__pestana\s*\{([^}]*)\}/.exec(hoja)?.[1] ?? "";
    expect(pestana).toMatch(/min-inline-size:\s*0/);
    expect(pestana).not.toMatch(/(?:^|[;\s])(?:inline-size|width|min-width):\s*[1-9]/);
    const panelCss = sass.compile(fileURLToPath(new URL("../../comun/PanelLateral.scss", import.meta.url))).css;
    expect(panelCss).toMatch(/\.silice-con-panel\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto/);
    const muyGrande = /@media \(max-width: 1919\.98px\)\s*\{[\s\S]*?html\[data-silice-letra=["']?muy-grande["']?\] \.silice-panel-lateral--ancho\s*\{([^}]*)\}/.exec(
      panelCss,
    );
    expect(muyGrande?.[1] ?? "", "con letra muy grande el panel ancho pasa por encima").toMatch(/inline-size:\s*min\(40rem, 100%\)/);
  });
});
