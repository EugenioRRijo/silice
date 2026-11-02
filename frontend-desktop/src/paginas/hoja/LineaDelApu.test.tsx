import { configure, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaApu, vistaEspacio, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "./logica";

// Tarea 8 del plan F4: «Agregar línea» y «Cambiar el insumo» son un solo diálogo (`LineaDelApu`) con dos modos. Cada línea
// del APU tiene «Cambiar» y «Quitar»; hay un solo «Agregar línea». En modo cambiar el tipo y la línea vienen fijos y solo se
// pide el insumo nuevo. Lo de cada petición (cuerpos, errores, el orden con la pausa) lo fijan `LineasApu.test.tsx` y
// `EdicionApu.test.tsx`; aquí, lo que es propio del diálogo único. Datos ficticios (AF-LLAVE de la obra OF-001).
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

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
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};
const m = (texto: string) => ({ texto, exacto: texto });
const RESUMEN: Resumen = {
  rev: 0,
  moneda: "USD",
  total: m("2703.86"),
  cambios: 0,
  pendientes_catalogo: 0,
  hallazgos: [],
  hay_plan: true,
  version_mas_nueva: null,
  guardado_como: null,
};

function borrador(soloLectura = false): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: soloLectura, moneda: "USD" },
    resumen: RESUMEN,
    instantanea: { creadas: 0, mensaje: null },
  };
}

describe("Un solo diálogo para las líneas del APU (Tarea 8)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let abierto: BorradorAbierto;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    abierto = borrador();
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = decodeURIComponent(url.pathname);
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json([]);
      if (camino === `/v1/hoja/borradores/${ID}/insumos`) return json({ insumos: [], hay_mas: false });
      if (camino.endsWith("/vistas/apu")) return json(vistaApu());
      if (camino.endsWith("/vistas/espacio")) return json(vistaEspacio());
      if (camino.endsWith("/vistas/parametros")) return json(vistaParametros());
      if (camino.endsWith("/vistas/auditoria")) return json(informeAuditoria());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  const escrituras = () => fetchFalso.mock.calls.filter(([, init]) => ["POST", "PUT"].includes(init?.method ?? "GET"));
  const escrituraDeApu = () => escrituras().filter(([r]) => /\/apu\//.test(String(r)));

  async function irAApu(sesion: SesionRespuesta = ARMA) {
    const valor: Aplicacion = {
      sesion,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(screen.getByRole("tab", { name: "Análisis de precio (APU)" }));
    await screen.findByText("Cierre de partida");
  }

  test("cada línea tiene «Cambiar» y «Quitar», hay un solo «Agregar línea» y el cambio de insumo plegado ya no existe", async () => {
    await irAApu();
    const cambiar = screen.getAllByRole("button", { name: /^Cambiar el insumo de / });
    expect(cambiar.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Cambiar el insumo de Llave de bola PVC 1/2, Materiales fila 1",
      "Cambiar el insumo de Herramientas menores, Equipos fila 1",
      "Cambiar el insumo de Plomero de 1ra N5, Mano de obra fila 1",
      "Cambiar el insumo de Ayudante N2, Mano de obra fila 2",
    ]);
    expect(cambiar.every((b) => b.textContent === "Cambiar")).toBe(true);
    expect(screen.getAllByRole("button", { name: /^Quitar / })).toHaveLength(4);
    expect(screen.getAllByRole("button", { name: "Agregar línea" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Cambiar el insumo de una línea (en la copia de esta versión)" })).toBeNull();
  });

  test("modo agregar: el título es «Agregar una línea» y pide tipo, insumo y cantidad", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Agregar línea" }));
    const caja = screen.getByRole("dialog", { name: "Agregar una línea" });
    expect(within(caja).getByRole("combobox", { name: "Tipo de línea" })).toHaveValue("material");
    expect(within(caja).getByRole("combobox", { name: "Insumo" })).toHaveFocus();
    expect(within(caja).getByRole("textbox", { name: /^Cantidad/ })).toBeInTheDocument();
    expect(within(caja).getByRole("button", { name: "Agregar al APU" })).toBeInTheDocument();
  });

  test("modo cambiar: el título nombra la línea, el tipo y la línea vienen fijos y solo se pide el insumo nuevo", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Cambiar el insumo de Ayudante N2, Mano de obra fila 2" }));
    const caja = screen.getByRole("dialog", { name: "Cambiar el insumo de Ayudante N2" });
    expect(caja).toHaveAttribute("aria-modal", "true");
    expect(within(caja).getByRole("combobox", { name: "Insumo" })).toHaveFocus();
    expect(within(caja).queryByRole("combobox", { name: "Tipo de línea" })).toBeNull();
    expect(within(caja).queryByRole("combobox", { name: "Línea" })).toBeNull();
    expect(within(caja).queryByRole("textbox", { name: /^Cantidad/ })).toBeNull();
    expect(within(caja).queryByRole("textbox", { name: "Unidad" })).toBeNull();
    expect(within(caja).getByRole("button", { name: "Usar este insumo" })).toBeInTheDocument();
    expect(within(caja).queryByRole("button", { name: "Agregar al APU" })).toBeNull();
  });

  test("modo cambiar: sin elegir un insumo no se manda nada y el error va al buscador", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Cambiar el insumo de Llave de bola PVC 1/2, Materiales fila 1" }));
    const caja = screen.getByRole("dialog", { name: /^Cambiar el insumo de/ });
    await userEvent.click(within(caja).getByRole("button", { name: "Usar este insumo" }));
    expect(escrituraDeApu()).toHaveLength(0);
    const buscador = within(caja).getByRole("combobox", { name: "Insumo" });
    expect(buscador).toHaveAttribute("aria-invalid", "true");
    expect(within(caja).getByText("Elija un insumo de la lista de precios de la versión.")).toBeInTheDocument();
    await vi.waitFor(() => expect(buscador).toHaveFocus());
  });

  test("Esc cierra el diálogo y el foco vuelve al «Cambiar» de esa línea, sin mandar nada", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Cambiar el insumo de Ayudante N2, Mano de obra fila 2" }));
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    await vi.waitFor(() =>
      expect(screen.getByRole("button", { name: "Cambiar el insumo de Ayudante N2, Mano de obra fila 2" })).toHaveFocus(),
    );
    expect(escrituraDeApu()).toHaveLength(0);
  });

  test("Cancelar también devuelve el foco al «Cambiar» de esa línea", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Cambiar el insumo de Herramientas menores, Equipos fila 1" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }));
    await vi.waitFor(() =>
      expect(screen.getByRole("button", { name: "Cambiar el insumo de Herramientas menores, Equipos fila 1" })).toHaveFocus(),
    );
  });

  test.each([
    ["una cuenta que revisa", REVISA, false],
    ["un borrador de solo lectura", ARMA, true],
  ])("con %s no se pinta «Cambiar», «Quitar» ni «Agregar línea» (Foco 3)", async (_nombre, sesion, soloLectura) => {
    abierto = borrador(soloLectura);
    await irAApu(sesion);
    expect(screen.getByText("Llave de bola PVC 1/2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Cambiar/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Quitar/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Agregar línea" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Usar este insumo" })).toBeNull();
  });
});
