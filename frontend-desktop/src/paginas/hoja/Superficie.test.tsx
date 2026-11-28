import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ProveedorDeAnuncios } from "../../comun/Anunciador";
import { vaciarRecursosParaPruebas } from "../../comun/recurso";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cuerpoDeVista } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";

// Lote B1-10 (ficha-b1 §3.4 y §4): la página del Presupuesto monta la superficie. `…/presupuesto` muestra la grilla con un solo
// h1; las pestañas de antes no están aquí (viven en `pestanas.tsx`, subvista «Espacio, plan y ajustes»). El borrador, las
// versiones y la oferta de retomar son del proveedor. Datos ficticios.
configure({ asyncUtilTimeout: 5000 });

const json = (cuerpo: unknown, estado = 200) =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [{ codigo: "002", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};

const BORRADOR: BorradorAbierto = {
  id: "id-superficie-aaaaaaaaaa",
  base: { proyecto: "OF-001", version: "002", vigente: "002", lista: "Lista", espacio_de: "002", solo_lectura: false, moneda: "USD" },
  resumen: {
    rev: 0,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.8602323440440333" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
  },
  instantanea: { creadas: 0, mensaje: null },
};

const APROBACIONES = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "",
  versiones: { "002": { estado: "guardada", por: null, el: null, notas: "", armo: false } },
  eventos: [],
  ultima_aprobada: null,
};

function Ubicacion() {
  const { pathname, state } = useLocation();
  return (
    <output data-testid="ubicacion" data-estado={JSON.stringify(state)}>
      {pathname}
    </output>
  );
}

let irAlPresupuesto: (estado: unknown) => void = () => undefined;
function Navegante() {
  const navegar = useNavigate();
  useEffect(() => {
    irAlPresupuesto = (estado) => void navegar("/presupuesto", { state: estado });
  }, [navegar]);
  return null;
}

describe("PaginaHoja: la superficie del Presupuesto (B1-10)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let ofertas: unknown[];
  let versiones: VersionesRespuesta;

  beforeEach(() => {
    vaciarRecursosParaPruebas();
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    ofertas = [];
    versiones = VERSIONES;
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      const camino = new URL(url, "http://silice.local").pathname;
      if (camino === "/v1/aprobaciones") return json(APROBACIONES);
      if (url.startsWith("/v1/hoja/versiones")) return json(versiones);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: ofertas });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(BORRADOR, 201);
      if (camino.startsWith("/v1/hoja/borradores/") && metodo === "DELETE") return new Response(null, { status: 204 });
      if (cuerpoDeVista(url) !== null) return json(cuerpoDeVista(url));
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });

  afterEach(() => {
    vaciarRecursosParaPruebas();
    vi.unstubAllGlobals();
  });

  function montar(proyecto: string | null = "OF-001", inicial = "/presupuesto") {
    const aplicacion: Aplicacion = {
      sesion: SESION,
      proyecto,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <MemoryRouter initialEntries={[inicial]}>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <Navegante />
            <PaginaHoja />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
        <Ubicacion />
      </MemoryRouter>,
    );
  }

  test("muestra la grilla de partidas con un solo h1 «Presupuesto» y sin las pestañas de antes", async () => {
    montar();
    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    expect(within(grilla).getByRole("rowheader", { name: "AF-LLAVE" })).toBeInTheDocument();
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1).toHaveLength(1);
    expect(h1[0]).toHaveTextContent("Presupuesto");
    expect(h1[0]).toHaveClass("cds--type-heading-04");
    expect(screen.queryByRole("tab")).toBeNull();
    expect(screen.queryByRole("tablist")).toBeNull();
    // La cabecera fija y la frase están: el total y los problemas, sin cambiar de pestaña.
    expect(screen.getByRole("region", { name: "Estado del borrador" })).toBeInTheDocument();
    expect(await screen.findByText(/El presupuesto suma .* sin IVA en 2 partidas\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Problemas \(/ })).toBeInTheDocument();
  });

  test("sin obra pide elegir una y no llama a la API", () => {
    montar(null);
    expect(screen.getByText("Elija una obra")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("mientras abre el borrador se ve el esqueleto de la grilla, sin cifras", async () => {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url.startsWith("/v1/hoja/versiones")) return json(versiones);
      if (url === "/v1/hoja/borradores" && (init?.method ?? "GET") === "GET") return json({ borradores: [] });
      return new Promise<Response>(() => {});
    });
    montar();
    const progreso = await screen.findByRole("progressbar", { name: "Cargando el presupuesto" });
    const esqueleto = progreso.closest<HTMLElement>("[aria-busy='true']")!;
    expect(within(esqueleto).getAllByRole("columnheader")).toHaveLength(7);
    expect(esqueleto.textContent).not.toMatch(/\d/);
  });

  test("con un borrador con cambios guardado, ofrece retomarlo y no abre la grilla hasta decidir (§1.7)", async () => {
    ofertas = [{ id: "borrador-viejo", proyecto: "OF-001", version: "002", cambios: 3, tocado: "2026-10-05T10:00:00" }];
    montar();
    expect(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (3 cambios)" })).toBeInTheDocument();
    expect(screen.queryByRole("grid", { name: "Presupuesto" })).toBeNull();
  });

  test("llegar desde Componer con la partida en el estado de la ruta la deja elegida en la fila de alta, una sola vez", async () => {
    montar();
    await screen.findByRole("grid", { name: "Presupuesto" });
    irAlPresupuesto({ agregarPartida: { codigo: "FRI-01", descripcion: "Friso de pared", unidad: "m2" } });
    const partida = await screen.findByDisplayValue("FRI-01 · Friso de pared");
    expect(partida).toHaveAttribute("role", "combobox");
    await waitFor(() => expect(screen.getByRole("textbox", { name: /^Cantidad/ })).toHaveFocus());
    // El estado de la ruta se limpia: volver a montar no repite el pedido.
    await waitFor(() => expect(screen.getByTestId("ubicacion").getAttribute("data-estado")).toBe("null"));
  });

  test("«Ver en el presupuesto» (estado enfocarGrilla) lleva el foco a la grilla cuando llega la vista y limpia el estado", async () => {
    montar();
    await screen.findByRole("grid", { name: "Presupuesto" });
    const u = userEvent.setup();
    await u.click(document.body);
    irAlPresupuesto({ enfocarGrilla: true });
    await waitFor(() => expect(document.activeElement?.closest("[role='grid']")).not.toBeNull());
    await waitFor(() => expect(screen.getByTestId("ubicacion").getAttribute("data-estado")).toBe("null"));
  });
});
