import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cuerpoDeVista } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Hallazgos, VersionesRespuesta } from "./logica";

// Tarea 5 del plan F4: la franja «Te falta / Siguiente paso» del Presupuesto, con un solo botón principal por pantalla, y las
// filas afectadas. Obra ficticia OF-001 con las versiones 001 y 002; la API es de mentira, con la forma de
// `api/rutas/hoja.py` y `api/rutas/aprobaciones.py`. Los textos esperados se escribieron a mano desde el plan.
configure({ asyncUtilTimeout: 5000 });

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

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
const fila = (codigo: string, vigente: boolean) => ({
  codigo,
  fecha: "2026-10-20",
  motivo: "",
  origen: "",
  vigente,
  descartada: false,
  cambios: 0,
});
const SIN_VERSIONES: VersionesRespuesta = { proyecto: "OF-001", moneda: "USD", por_omision: null, versiones: [] };
const SOLO_001: VersionesRespuesta = { proyecto: "OF-001", moneda: "USD", por_omision: "001", versiones: [fila("001", true)] };
const CON_002: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [fila("002", true), fila("001", false)],
};

interface Opciones {
  version?: string | null;
  vigente?: string | null;
  cambios?: number;
  hallazgos?: Hallazgos[];
  soloLectura?: boolean;
}

function borrador({ version = "001", vigente = version, cambios = 0, hallazgos = [], soloLectura = false }: Opciones = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente, lista: "Lista", espacio_de: version, solo_lectura: soloLectura, moneda: "USD" },
    resumen: {
      rev: 2,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.8602323440440333" },
      cambios,
      pendientes_catalogo: 0,
      hallazgos,
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
      espacio_vacio: true,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

const estadoDe = (estado: string) => ({
  estado,
  por: estado === "guardada" ? null : "Rita Gómez <rita>",
  el: estado === "guardada" ? null : "2026-10-25T10:30:00",
  notas: estado === "devuelta" ? "Falta el acero de la losa." : "",
  armo: false,
});
const aprobacionesCon = (estados: Record<string, string>) => ({
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "",
  versiones: Object.fromEntries(Object.entries(estados).map(([v, e]) => [v, estadoDe(e)])),
  eventos: [],
  ultima_aprobada: null,
});

describe("Presupuesto: la franja del paso (Tarea 5)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let versiones: VersionesRespuesta;
  let abierto: BorradorAbierto;
  let alLeerAprobaciones: () => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    versiones = SOLO_001;
    abierto = borrador();
    alLeerAprobaciones = () => json(aprobacionesCon({ "001": "guardada" }));
    fetchFalso.mockImplementation(async (ruta, init) => {
      const texto = String(ruta);
      const camino = new URL(texto, "http://silice.local").pathname;
      const metodo = init?.method ?? "GET";
      if (camino === "/v1/aprobaciones" && metodo === "GET") return alLeerAprobaciones();
      if (camino === "/v1/hoja/versiones") return json(versiones);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (camino.endsWith("/cambios")) return json({ rev: 2, cambios: [] });
      const vista = cuerpoDeVista(texto);
      if (vista !== null) return json(vista);
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function aplicacion(sesion: SesionRespuesta): Aplicacion {
    return { sesion, proyecto: "OF-001", caso: { nombre: "obra", ruta_relativa: "data/obra.db" }, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  }
  // Dentro de un enrutador: el diálogo «Agregar partida» lo necesita (como en AgregarPartida.test.tsx).
  function montar(sesion: SesionRespuesta = ARMA) {
    return render(
      <MemoryRouter initialEntries={["/hoja"]}>
        <ContextoAplicacion.Provider value={aplicacion(sesion)}>
          <PaginaHoja />
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  const franja = () => screen.findByRole("region", { name: "Siguiente paso" });
  const primarios = () => Array.from(document.querySelectorAll(".cds--btn--primary"));
  // Lo que debe estar en pantalla antes de contar: el borrador abierto y la tabla de Partidas.
  async function listo() {
    await screen.findByRole("region", { name: "Estado del borrador" });
    await screen.findByRole("table", { name: "Presupuesto" });
  }

  test("borrador en blanco: «Te falta: Agregue la primera partida» y su botón abre «Agregar partida»", async () => {
    versiones = SIN_VERSIONES;
    abierto = borrador({ version: null, vigente: null });
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Te falta: Agregue la primera partida");
    await userEvent.click(within(zona).getByRole("button", { name: "Agregar la primera partida" }));
    expect(await screen.findByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
  });

  test("con 2 cambios: «Siguiente paso: Hay 2 cambios sin guardar» y «Guardar versión…» abre el diálogo de guardar", async () => {
    abierto = borrador({ cambios: 2 });
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Siguiente paso: Hay 2 cambios sin guardar");
    await userEvent.click(within(zona).getByRole("button", { name: "Guardar versión…" }));
    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByRole("heading", { name: "Guardar versión" })).toBeInTheDocument();
  });

  test("el estado del borrador conserva el total y «Descartar cambios» (fantasma), sin el botón de guardar", async () => {
    abierto = borrador({ cambios: 2 });
    montar();
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    expect(within(estado).queryByRole("button", { name: /^Guardar/ })).toBeNull();
    expect(within(estado).getByRole("button", { name: "Descartar cambios" })).toHaveClass("cds--btn--ghost");
    expect(estado).toHaveTextContent("Total 2.703,86 USD");
  });

  describe("como mucho un botón principal en cada estado, y es el de la franja", () => {
    test.each<[string, () => void, string | null]>([
      [
        "en blanco",
        () => {
          versiones = SIN_VERSIONES;
          abierto = borrador({ version: null, vigente: null });
        },
        "Agregar la primera partida",
      ],
      ["con cambios", () => (abierto = borrador({ cambios: 2 })), "Guardar versión…"],
      ["con graves", () => (abierto = borrador({ hallazgos: [{ severidad: "ERROR", total: 2 }] })), "Ir a Revisión"],
      ["devuelta", () => (alLeerAprobaciones = () => json(aprobacionesCon({ "001": "devuelta" }))), "Hacer una versión nueva"],
      ["en aprobación", () => (alLeerAprobaciones = () => json(aprobacionesCon({ "001": "en_aprobacion" }))), null],
      ["aprobada", () => (alLeerAprobaciones = () => json(aprobacionesCon({ "001": "aprobada" }))), null],
      ["guardada", () => {}, "Enviar a aprobación…"],
    ])("%s", async (_nombre, preparar, boton) => {
      preparar();
      montar();
      await listo();
      if (boton === null) {
        await waitFor(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).not.toBeNull());
        expect(primarios()).toEqual([]);
        return;
      }
      const zona = await franja();
      const principal = await within(zona).findByRole("button", { name: boton });
      expect(primarios()).toEqual([principal]);
    });

    test("«Agregar partida» sobre la tabla es terciario", async () => {
      montar();
      await listo();
      expect(screen.getByRole("button", { name: "Agregar partida" })).toHaveClass("cds--btn--tertiary");
    });
  });

  test("con graves: «Te falta: Hay 2 hallazgos graves…» e «Ir a Revisión» abre la pestaña «Revisión»", async () => {
    abierto = borrador({ hallazgos: [{ severidad: "ERROR", total: 1 }, { severidad: "CRITICO", total: 1 }, { severidad: "ADVERTENCIA", total: 4 }] });
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Te falta: Hay 2 hallazgos graves: revíselos antes de enviar");
    await userEvent.click(within(zona).getByRole("button", { name: "Ir a Revisión" }));
    expect(await screen.findByRole("tab", { name: "Revisión", selected: true })).toBeInTheDocument();
  });

  test("devuelta: «Hacer una versión nueva» lleva a «Partidas» con el aviso de siempre", async () => {
    alLeerAprobaciones = () => json(aprobacionesCon({ "001": "devuelta" }));
    montar();
    await listo();
    await userEvent.click(screen.getByRole("tab", { name: "Revisión" }));
    const zona = await franja();
    expect(zona).toHaveTextContent("Te falta: La versión 001 fue devuelta: corrija lo observado");
    await userEvent.click(within(zona).getByRole("button", { name: "Hacer una versión nueva" }));
    expect(await screen.findByRole("tab", { name: "Partidas", selected: true })).toBeInTheDocument();
    const aprobacion = screen.getByRole("region", { name: "Aprobación de la versión" });
    expect(within(aprobacion).getByRole("status")).toHaveTextContent("Corrija y guarde: será una versión nueva.");
    expect(aprobacion).toHaveTextContent("Notas de Rita Gómez: Falta el acero de la losa.");
  });

  test("en aprobación: la franja lo dice y no ofrece nada", async () => {
    alLeerAprobaciones = () => json(aprobacionesCon({ "001": "en_aprobacion" }));
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Siguiente paso: La versión 001 espera dictamen");
    expect(within(zona).queryByRole("button")).toBeNull();
  });

  test("aprobada: no hay franja", async () => {
    alLeerAprobaciones = () => json(aprobacionesCon({ "001": "aprobada" }));
    montar();
    await listo();
    await waitFor(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).toHaveTextContent(/^Aprobada/));
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
  });

  test("«Enviar a aprobación…» abre el diálogo de envío con la nota opcional", async () => {
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Siguiente paso: Envíe la versión 001 a aprobación");
    await userEvent.click(await within(zona).findByRole("button", { name: "Enviar a aprobación…" }));
    const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
    expect(within(dialogo).getByRole("textbox", { name: "Nota para quien revisa (opcional)" })).toHaveFocus();
  });

  test("mientras se lee la aprobación no se adelanta «Envíe…» (no parpadea)", async () => {
    alLeerAprobaciones = () => new Promise<Response>(() => {});
    montar();
    await listo();
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
  });

  test("si no se pudo leer la aprobación, la franja no ofrece enviar", async () => {
    alLeerAprobaciones = () => json({ detalle: "No se pudo leer la carpeta de trabajo." }, 503);
    montar();
    await listo();
    await screen.findByText("No se pudo leer el estado de aprobación de esta versión.");
    expect(screen.queryByRole("button", { name: "Enviar a aprobación…" })).toBeNull();
  });

  test("versión abierta distinta de la vigente: la franja no ofrece enviar (Foco 5)", async () => {
    versiones = CON_002;
    abierto = borrador({ version: "001", vigente: "002" });
    alLeerAprobaciones = () => json(aprobacionesCon({ "001": "guardada", "002": "guardada" }));
    montar();
    await listo();
    await waitFor(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).not.toBeNull());
    expect(screen.queryByRole("button", { name: "Enviar a aprobación…" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
  });

  describe("Foco 3: sin permiso de edición la franja informa y no ofrece escribir", () => {
    const DE_ESCRITURA = /^(Agregar la primera partida|Guardar|Hacer una versión nueva|Enviar a aprobación)/;

    test("borrador de solo lectura, devuelta: el texto sale, sin «Hacer una versión nueva»", async () => {
      abierto = borrador({ soloLectura: true });
      alLeerAprobaciones = () => json(aprobacionesCon({ "001": "devuelta" }));
      montar();
      const zona = await franja();
      expect(zona).toHaveTextContent("Te falta: La versión 001 fue devuelta: corrija lo observado");
      expect(within(zona).queryByRole("button")).toBeNull();
      expect(screen.queryByRole("button", { name: DE_ESCRITURA })).toBeNull();
    });

    test("borrador de solo lectura, guardada: enviar obra sobre la versión guardada y se ofrece (Eugenio, 2026-10-31)", async () => {
      abierto = borrador({ soloLectura: true });
      montar();
      const zona = await franja();
      expect(await within(zona).findByRole("button", { name: "Enviar a aprobación…" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /^(Agregar|Guardar|Hacer una versión nueva)/ })).toBeNull();
    });

    test.each([
      ["guardada", "Siguiente paso: Envíe la versión 001 a aprobación"],
      ["devuelta", "Te falta: La versión 001 fue devuelta: corrija lo observado"],
    ])("cuenta que revisa, %s: el texto sale y ningún botón que escriba", async (estado, texto) => {
      alLeerAprobaciones = () => json(aprobacionesCon({ "001": estado }));
      montar(REVISA);
      const zona = await franja();
      expect(zona).toHaveTextContent(texto);
      expect(within(zona).queryByRole("button")).toBeNull();
      expect(screen.queryByRole("button", { name: DE_ESCRITURA })).toBeNull();
      expect(primarios()).toEqual([]);
    });

    test("cuenta que revisa, con graves: «Ir a Revisión» sí sale (solo lee)", async () => {
      abierto = borrador({ hallazgos: [{ severidad: "ERROR", total: 1 }] });
      montar(REVISA);
      const zona = await franja();
      expect(zona).toHaveTextContent("Te falta: Hay 1 hallazgo grave: revíselo antes de enviar");
      expect(within(zona).getByRole("button", { name: "Ir a Revisión" })).toBeInTheDocument();
    });
  });

  describe("filas afectadas", () => {
    test("un renglón con un hallazgo ERROR lleva la clase y dice «Error»; uno sin hallazgos no la lleva", async () => {
      montar();
      const tabla = await screen.findByRole("table", { name: "Presupuesto" });
      const conError = within(tabla).getByRole("row", { name: /AF-SALIDA/ });
      const sinHallazgos = within(tabla).getByRole("row", { name: /AF-LLAVE/ });
      expect(conError).toHaveClass("silice-fila--afectada");
      expect(within(conError).getByText("Error")).toBeInTheDocument();
      expect(within(conError).getByRole("button", { name: /^Ver en Revisión/ })).toBeInTheDocument();
      expect(sinHallazgos).not.toHaveClass("silice-fila--afectada");
    });

    test("quien revisa ve las mismas filas afectadas (es lectura)", async () => {
      montar(REVISA);
      const tabla = await screen.findByRole("table", { name: "Presupuesto" });
      expect(within(tabla).getByRole("row", { name: /AF-SALIDA/ })).toHaveClass("silice-fila--afectada");
    });
  });
});
