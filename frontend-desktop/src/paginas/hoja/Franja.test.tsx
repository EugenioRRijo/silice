import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ProveedorDeAnuncios } from "../../comun/Anunciador";
import { vaciarRecursosParaPruebas } from "../../comun/recurso";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cuerpoDeVista } from "./datosDePrueba";
import type { ReactNode } from "react";
import { EstadoDelBorrador } from "./EstadoDelBorrador";
import { FranjaDelPresupuesto } from "./FranjaDelPresupuesto";
import PaginaHoja from "./index";
import type { BorradorAbierto, Hallazgos, VersionesRespuesta } from "./logica";

// Tarea 5 del plan F4: la franja «Te falta / Siguiente paso» del Presupuesto, con un solo botón principal por pantalla.
// Obra ficticia OF-001 con las versiones 001 y 002; la API es de mentira, con la forma de `api/rutas/hoja.py` y
// `api/rutas/aprobaciones.py`. Los textos esperados se escribieron a mano desde el plan.
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
  desgloses?: number;
}

function borrador({ version = "001", vigente = version, cambios = 0, hallazgos = [], soloLectura = false, desgloses }: Opciones = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente, lista: "Lista", espacio_de: version, solo_lectura: soloLectura, moneda: "USD" },
    resumen: {
      rev: 2,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.8602323440440333" },
      cambios,
      ...(desgloses === undefined ? {} : { desgloses }),
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
    vaciarRecursosParaPruebas();
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
  afterEach(() => {
    vaciarRecursosParaPruebas();
    vi.unstubAllGlobals();
  });

  function aplicacion(sesion: SesionRespuesta): Aplicacion {
    return { sesion, proyecto: "OF-001", caso: { nombre: "obra", ruta_relativa: "data/obra.db" }, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  }
  function montar(sesion: SesionRespuesta = ARMA) {
    return render(
      <MemoryRouter initialEntries={["/hoja"]}>
        <ContextoAplicacion.Provider value={aplicacion(sesion)}>
          <ProveedorDeAnuncios>
            <PaginaHoja />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  const franja = () => screen.findByRole("region", { name: "Siguiente paso" });
  const primarios = () => Array.from(document.querySelectorAll(".cds--btn--primary"));
  // Lo que debe estar en pantalla antes de contar: el borrador abierto y la grilla del Presupuesto.
  async function listo() {
    await screen.findByRole("region", { name: "Estado del borrador" });
    await screen.findByRole("grid", { name: "Presupuesto" });
  }

  test("borrador en blanco: «Falta: Agregue la primera partida» y su botón enfoca «Partida» en la fila de alta", async () => {
    versiones = SIN_VERSIONES;
    abierto = borrador({ version: null, vigente: null });
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Falta: Agregue la primera partida");
    await userEvent.click(within(zona).getByRole("button", { name: "Agregar la primera partida" }));
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Partida" })).toHaveFocus());
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

  // Anexo A.6: si lo único pendiente es el desglose del desperdicio, guardar no crea versión; el botón dice lo que va a pasar.
  test.each<[string, string, number, number]>([
    ["solo el desglose", "Guardar ajuste de desperdicio…", 1, 1],
    ["solo desgloses (2)", "Guardar ajuste de desperdicio…", 2, 2],
    ["una celda y un desglose", "Guardar versión…", 2, 1],
    ["solo celdas", "Guardar versión…", 2, 0],
  ])("con %s, el botón de la franja dice «%s»", async (_nombre, rotulo, cambios, desgloses) => {
    abierto = borrador({ cambios, desgloses });
    montar();
    const zona = await franja();
    expect(await within(zona).findByRole("button", { name: rotulo })).toBeInTheDocument();
    expect(within(zona).queryByRole("button", { name: rotulo === "Guardar versión…" ? "Guardar ajuste de desperdicio…" : "Guardar versión…" })).toBeNull();
  });

  test("el estado del borrador conserva el total sin IVA y «Descartar cambios» (fantasma), sin el botón de guardar", () => {
    abierto = borrador({ cambios: 2 });
    render(<EstadoDelBorrador borrador={abierto} puedeEditar alDescartar={vi.fn()} />);
    const estado = screen.getByRole("region", { name: "Estado del borrador" });
    expect(within(estado).queryByRole("button", { name: /^Guardar/ })).toBeNull();
    expect(within(estado).getByRole("button", { name: "Descartar cambios" })).toHaveClass("cds--btn--ghost");
    expect(estado).toHaveTextContent("Total sin IVA 2.703,86 USD");
  });

  // B1-3: la cabecera de la superficie nueva trae lugares para «Problemas (n)» y «Más acciones». La vista por pestañas no los
  // usa (sigue con «Descargar Excel» a la vista), así que aquí se monta la franja sola con los dos lugares llenos.
  describe("lugares de la cabecera fija: «Problemas (n)» y «Más acciones»", () => {
    function montarFranja(extra: { problemas?: ReactNode; masAcciones?: ReactNode }) {
      return render(
        <MemoryRouter>
          <ContextoAplicacion.Provider value={aplicacion(ARMA)}>
            <FranjaDelPresupuesto
              proyecto="OF-001"
              borrador={abierto}
              puedeEditar
              alAgregarPartida={vi.fn()}
              alGuardar={vi.fn()}
              alVerRevision={vi.fn()}
              alHacerVersionNueva={vi.fn()}
              {...extra}
            />
          </ContextoAplicacion.Provider>
        </MemoryRouter>,
      );
    }

    test("el orden de lectura y de tabulación es Problemas, el principal y Más acciones; hay un solo principal", async () => {
      montarFranja({
        problemas: <button type="button">Problemas (3)</button>,
        masAcciones: <button type="button">Más acciones del presupuesto</button>,
      });
      const principal = await screen.findByRole("button", { name: "Enviar a aprobación…" });
      const problemas = screen.getByRole("button", { name: "Problemas (3)" });
      const mas = screen.getByRole("button", { name: "Más acciones del presupuesto" });
      const antes = (a: Element, b: Element) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      expect(antes(problemas, principal)).toBe(true);
      expect(antes(principal, mas)).toBe(true);
      expect(primarios()).toEqual([principal]);
    });

    test("con «Más acciones» puesto, «Descargar Excel» sale de la vista (va dentro del menú)", async () => {
      montarFranja({ masAcciones: <button type="button">Más acciones del presupuesto</button> });
      await screen.findByRole("button", { name: "Enviar a aprobación…" });
      expect(screen.queryByRole("button", { name: /Descargar Excel/ })).toBeNull();
    });

    test("sin esos lugares, «Descargar Excel» sigue a la vista", async () => {
      montarFranja({});
      await screen.findByRole("button", { name: "Enviar a aprobación…" });
      expect(screen.getByRole("button", { name: /Descargar Excel/ })).toBeInTheDocument();
    });

    test("la cabecera va dentro de un contenedor fijo que consulta su estado de desplazamiento", async () => {
      montarFranja({});
      const region = await screen.findByRole("region", { name: "Estado del borrador" });
      expect(region.closest(".silice-hoja__cabecera-fija")).not.toBeNull();
    });
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

    test("«Agregar al presupuesto» en la fila de alta es terciario", async () => {
      montar();
      await listo();
      expect(screen.getByRole("button", { name: "Agregar al presupuesto" })).toHaveClass("cds--btn--tertiary");
    });
  });

  test("con graves: «Falta: Hay 2 hallazgos graves…» e «Ir a Revisión» abre el inspector «Problemas»", async () => {
    abierto = borrador({ hallazgos: [{ severidad: "ERROR", total: 1 }, { severidad: "CRITICO", total: 1 }, { severidad: "ADVERTENCIA", total: 4 }] });
    montar();
    const zona = await franja();
    expect(zona).toHaveTextContent("Falta: Hay 2 hallazgos graves: revíselos antes de enviar");
    await userEvent.click(within(zona).getByRole("button", { name: "Ir a Revisión" }));
    expect(await screen.findByRole("complementary", { name: "Problemas" })).toBeInTheDocument();
  });

  test("devuelta: «Hacer una versión nueva» enfoca la grilla con el aviso de siempre", async () => {
    alLeerAprobaciones = () => json(aprobacionesCon({ "001": "devuelta" }));
    montar();
    await listo();
    const zona = await franja();
    expect(zona).toHaveTextContent("Falta: La versión 001 fue devuelta: corrija lo observado");
    await userEvent.click(within(zona).getByRole("button", { name: "Hacer una versión nueva" }));
    await waitFor(() => expect(document.activeElement?.closest("[role='grid']")).not.toBeNull());
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

  // Decisión 8 de la Tarea 5: 403 y 404 también son «fallo» (antes no decían nada); menor 2 del árbitro (cierre de F4).
  test.each([403, 404, 503])("si no se pudo leer la aprobación (%i), la franja no ofrece enviar", async (estado) => {
    alLeerAprobaciones = () => json({ detalle: "No se pudo leer la carpeta de trabajo." }, estado);
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
      expect(zona).toHaveTextContent("Falta: La versión 001 fue devuelta: corrija lo observado");
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
      ["devuelta", "Falta: La versión 001 fue devuelta: corrija lo observado"],
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
      expect(zona).toHaveTextContent("Falta: Hay 1 hallazgo grave: revíselo antes de enviar");
      expect(within(zona).getByRole("button", { name: "Ir a Revisión" })).toBeInTheDocument();
    });
  });
});
