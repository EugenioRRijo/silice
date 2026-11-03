import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useContext } from "react";
import { MemoryRouter, useLocation, useParams } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { Marco } from "../../marco/Marco";
import { estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import { useNavegarSeguro } from "../../shell/navegarSeguro";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import { cuerpoDeVista } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "./logica";
import { ContextoDeLaHoja, useHojaDeLaObra } from "./ProveedorDeLaHoja";

// Tarea 3 del plan F4: el borrador de la Hoja vive en la obra (`ProveedorDeLaHoja`) y lo comparten Presupuesto, Archivos
// y planos y Versiones. Se monta el marco entero (barra lateral, «Cambios sin guardar») con la Hoja real en Presupuesto.
// Archivos y planos tiene su pantalla desde la Tarea 11 y Versiones desde la Tarea 6; aquí las tres secciones reciben la
// misma pantalla de prueba, que pinta según la sección de la ruta la Hoja real (Presupuesto) o un relleno que solo lee el
// contexto (Archivos y planos, Versiones). Oráculos escritos a mano: obras ficticias 7 («Casa Demo») y 8 («Torre B») de
// la carpeta de la empresa, versiones 002 (vigente) y 001.
configure({ asyncUtilTimeout: 5000 });

const m = (texto: string, exacto = texto) => ({ texto, exacto });

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "Bs",
    total: m("1234.5"),
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

// La vigente: la 002, hasta que la prueba guarda la 003.
let vigente = "002";

function borrador(id: string, proyecto: string, version: string | null): BorradorAbierto {
  return {
    id,
    base: { proyecto, version, vigente, lista: "Lista", espacio_de: version, solo_lectura: false, moneda: "Bs" },
    resumen: resumen(),
    instantanea: { creadas: 0, mensaje: null },
  };
}

function versiones(proyecto: string): VersionesRespuesta {
  return {
    proyecto,
    moneda: "Bs",
    por_omision: vigente,
    versiones: [
      ...(vigente === "003"
        ? [{ codigo: "003", fecha: "2026-10-31", motivo: "edicion", origen: "002", vigente: true, descartada: false, cambios: 2 }]
        : []),
      { codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: vigente === "002", descartada: false, cambios: 1 },
      { codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0 },
    ],
  };
}

let servidor: ReturnType<typeof servidorFalso>;

beforeEach(() => {
  const estado = estadoInicial();
  // Las dos obras con la 002 vigente, como dice la Hoja.
  estado.proyectos = estado.proyectos.map((p) => ({ ...p, version_vigente: 2 }));
  let abiertos = 0;
  vigente = "002";
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    const url = new URL(ruta, "http://silice.local");
    const camino = url.pathname;
    if (camino === "/v1/hoja/versiones") return json(versiones(url.searchParams.get("proyecto") ?? ""));
    if (camino === "/v1/hoja/borradores" && metodo === "POST") {
      const pedido = cuerpo as { proyecto: string; version: string | null };
      abiertos += 1;
      return json(borrador(`b-${abiertos}`, pedido.proyecto, pedido.version), 201);
    }
    if (/^\/v1\/hoja\/borradores\/[^/]+$/.test(camino) && metodo === "DELETE") return new Response(null, { status: 204 });
    if (camino.endsWith("/cambios")) return json({ cambios: [] });
    if (camino.endsWith("/cantidades") && metodo === "PUT") {
      const rev = (cuerpo as { rev: number }).rev + 1;
      return json({ rev, resumen: resumen({ rev, cambios: 1 }) });
    }
    if (camino.endsWith("/guardar") && metodo === "POST") {
      // La obra 7 pasa a tener la 003 vigente: lo dirán la lista de obras y la de versiones.
      vigente = "003";
      estado.proyectos = estado.proyectos.map((p) => (p.codigo === "7" ? { ...p, version_vigente: 3 } : p));
      return json({ codigo: "003", proyecto: "7", cambios: 2, total: m("1234.5"), primera: false, mensaje: "Guardada." });
    }
    const vista = cuerpoDeVista(camino);
    return vista === null ? undefined : json(vista);
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

// La pantalla de relleno de Archivos y planos y Versiones: lee el contexto sin exigirlo, para que el rojo falle por lo
// que dice y no porque falte el proveedor.
function Relleno({ titulo }: { titulo: string }) {
  const hoja = useContext(ContextoDeLaHoja);
  const navegar = useNavegarSeguro();
  return (
    <>
      <h1>{titulo}</h1>
      <p data-testid="borrador">{`borrador: ${hoja === null ? "sin hoja" : hoja.estado.estado}`}</p>
      {hoja !== null && <ConLaHoja />}
      <button type="button" onClick={() => void navegar("/obra/empresa/7/presupuesto?version=001")}>
        Abrir la 001
      </button>
      <button type="button" onClick={() => void navegar("/obra/empresa/8/presupuesto")}>
        Presupuesto de Torre B
      </button>
    </>
  );
}

function ConLaHoja() {
  const { aplicar, abrirGuardado } = useHojaDeLaObra();
  return (
    <>
      <button type="button" onClick={() => aplicar(resumen({ rev: 3, cambios: 2 }))}>
        Simular dos cambios
      </button>
      <button type="button" onClick={abrirGuardado}>
        Guardar desde aquí
      </button>
    </>
  );
}

function PorSeccion() {
  const { seccion } = useParams();
  if (seccion === "presupuesto") return <PaginaHoja />;
  return <Relleno titulo={seccion === "versiones" ? "Versiones" : "Archivos y planos"} />;
}

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <output data-testid="ruta">{`${pathname}${search}`}</output>;
}

function montar(en: string) {
  render(
    <MemoryRouter initialEntries={[en]}>
      <Marco
        sesion={sesionDe("ana")}
        alSalir={vi.fn()}
        alExpirar={vi.fn()}
        paginas={ligeras({ hoja: PorSeccion, versiones: PorSeccion, archivos: PorSeccion })}
      />
      <Ubicacion />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

const ruta = () => screen.getByTestId("ruta").textContent;
const textoDelBorrador = () => screen.queryByTestId("borrador")?.textContent ?? null;
const fichas = () => servidor.de("GET", "/v1/obras/resumen").length;
const aperturas = () => servidor.de("POST", "/v1/hoja/borradores").map((l) => l.cuerpo as { proyecto: string; version: string | null });
const descartes = () => servidor.llamadas.filter((l) => l.metodo === "DELETE" && l.ruta.startsWith("/v1/hoja/borradores/")).map((l) => l.ruta);
const arbol = () => screen.findByRole("tree", { name: "Obras" });
const irA = async (u: ReturnType<typeof userEvent.setup>, seccion: string) =>
  u.click(await within(await arbol()).findByRole("treeitem", { name: seccion }));
const pausa = () =>
  act(async () => {
    await new Promise((r) => setTimeout(r, 30));
  });
const borradorListoEnLaHoja = () => screen.findByRole("region", { name: "Estado del borrador" });
const borradorListoEnElRelleno = () => waitFor(() => expect(textoDelBorrador()).toBe("borrador: listo"));

describe("ProveedorDeLaHoja: el borrador vive en la obra", () => {
  test("abre el borrador una vez y lo conserva al pasar a Versiones y a Archivos", async () => {
    const u = montar("/obra/empresa/7/presupuesto");
    await borradorListoEnLaHoja();
    await irA(u, "Versiones");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/versiones"));
    await borradorListoEnElRelleno();
    await irA(u, "Archivos y planos");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/archivos"));
    await borradorListoEnElRelleno();
    await pausa();
    expect(aperturas()).toEqual([{ proyecto: "7", version: "002" }]);
    expect(descartes()).toEqual([]);
    // Moverse entre Presupuesto, Versiones y Archivos no vuelve a leer la ficha de la obra.
    expect(fichas()).toBe(1);
  });

  test("al ir al Resumen sin cambios descarta el borrador", async () => {
    const u = montar("/obra/empresa/7/presupuesto");
    await borradorListoEnLaHoja();
    await irA(u, "Resumen");
    await waitFor(() => expect(descartes()).toEqual(["/v1/hoja/borradores/b-1"]));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
  });

  test("al ir al Resumen con cambios pregunta y conserva el borrador", async () => {
    const u = montar("/obra/empresa/7/versiones");
    await borradorListoEnElRelleno();
    await u.click(screen.getByRole("button", { name: "Simular dos cambios" }));
    await irA(u, "Resumen");
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    // Ronda 2, menor 2: el borrador se conserva en el servidor y se retoma al volver; el diálogo lo dice y no habla de descartar.
    expect(pregunta).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Presupuesto. Sus cambios quedan guardados para retomarlos al volver.",
    );
    expect(within(pregunta).queryByRole("button", { name: /descartar/i })).toBeNull();
    await u.click(within(pregunta).getByRole("button", { name: "Salir" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/resumen"));
    await pausa();
    expect(descartes()).toEqual([]);
  });

  test("entre las secciones con hoja no pregunta, hacia Mercado sí (foco 1)", async () => {
    const u = montar("/obra/empresa/7/versiones");
    await borradorListoEnElRelleno();
    await u.click(screen.getByRole("button", { name: "Simular dos cambios" }));
    await irA(u, "Presupuesto");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto"));
    expect(await borradorListoEnLaHoja()).toHaveTextContent("2 cambios sin guardar");
    await irA(u, "Archivos y planos");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/archivos"));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    await irA(u, "Mercado");
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/obra/empresa/7/archivos");
    expect(aperturas()).toHaveLength(1);
  });

  test("en Resumen y Mercado no se abre ningún borrador", async () => {
    const u = montar("/obra/empresa/7/resumen");
    expect(await screen.findByRole("heading", { level: 1, name: "Resumen de la obra" })).toBeInTheDocument();
    await irA(u, "Mercado");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/mercado"));
    await pausa();
    expect(aperturas()).toEqual([]);
    expect(servidor.llamadas.filter((l) => l.ruta.startsWith("/v1/hoja/versiones"))).toEqual([]);
  });

  test("al llegar con ?version=001 abre esa versión y quita el parámetro", async () => {
    montar("/obra/empresa/7/presupuesto?version=001");
    await borradorListoEnLaHoja();
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto"));
    expect(aperturas()).toEqual([{ proyecto: "7", version: "001" }]);
  });

  test("con cambios, «Abrir la 001» pregunta «Descartar los cambios» (no «Cambios sin guardar») y luego la abre", async () => {
    const u = montar("/obra/empresa/7/versiones");
    await borradorListoEnElRelleno();
    await u.click(screen.getByRole("button", { name: "Simular dos cambios" }));
    await u.click(screen.getByRole("button", { name: "Abrir la 001" }));
    const pregunta = await screen.findByRole("alertdialog", { name: "Descartar los cambios" });
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(aperturas()).toHaveLength(1);
    await u.click(within(pregunta).getByRole("button", { name: "Descartar y abrir" }));
    await waitFor(() => expect(aperturas().at(-1)).toEqual({ proyecto: "7", version: "001" }));
    expect(descartes()).toEqual(["/v1/hoja/borradores/b-1"]);
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
  });

  test("la cabecera dice la versión abierta cuando no es la vigente (foco 5)", async () => {
    montar("/obra/empresa/7/presupuesto?version=001");
    await borradorListoEnLaHoja();
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    await waitFor(() => expect(cabecera).toHaveTextContent("Versión abierta: 001 (la vigente es 002)"));
  });

  test("con la vigente abierta, la cabecera dice la versión como antes", async () => {
    montar("/obra/empresa/7/presupuesto");
    await borradorListoEnLaHoja();
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    expect(cabecera).toHaveTextContent("Versión: 002");
    expect(cabecera).not.toHaveTextContent("Versión abierta");
  });

  test("«Guardar versión…» desde otra sección guarda con el rev al día (sin 409 «El borrador cambió»)", async () => {
    const u = montar("/obra/empresa/7/versiones");
    await borradorListoEnElRelleno();
    await u.click(screen.getByRole("button", { name: "Simular dos cambios" }));
    await u.click(screen.getByRole("button", { name: "Guardar desde aquí" }));
    const dialogo = await screen.findByRole("dialog", { name: "Guardar versión" });
    await u.type(within(dialogo).getByRole("textbox", { name: /^Fuente/ }), "Acta de obra 4");
    await u.click(within(dialogo).getByRole("button", { name: "Guardar versión" }));
    await waitFor(() =>
      expect(servidor.de("POST", "/v1/hoja/borradores/b-1/guardar").map((l) => l.cuerpo)).toEqual([{ rev: 3, fuente: "Acta de obra 4" }]),
    );
  });

  test("ir al Presupuesto de otra obra descarta el borrador de esta y abre el de aquella", async () => {
    const u = montar("/obra/empresa/7/versiones");
    await borradorListoEnElRelleno();
    await u.click(screen.getByRole("button", { name: "Presupuesto de Torre B" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/8/presupuesto"));
    await borradorListoEnLaHoja();
    await waitFor(() => expect(descartes()).toEqual(["/v1/hoja/borradores/b-1"]));
    expect(aperturas()).toEqual([
      { proyecto: "7", version: "002" },
      { proyecto: "8", version: "002" },
    ]);
  });
  // Ronda 2 (mayor del árbitro): tras guardar, la ficha y la lista de obras se vuelven a leer, y entrar al Resumen la lee otra vez.
  test("tras «Guardar versión…» se vuelven a leer la ficha y la lista de obras, y el Resumen ve la versión nueva", async () => {
    const u = montar("/obra/empresa/7/versiones");
    await borradorListoEnElRelleno();
    await waitFor(() => expect(fichas()).toBe(1));
    const obrasAntes = servidor.de("GET", "/v1/obras/todas").length;
    await u.click(screen.getByRole("button", { name: "Simular dos cambios" }));
    await u.click(screen.getByRole("button", { name: "Guardar desde aquí" }));
    const dialogo = await screen.findByRole("dialog", { name: "Guardar versión" });
    await u.type(within(dialogo).getByRole("textbox", { name: /^Fuente/ }), "Acta de obra 4");
    await u.click(within(dialogo).getByRole("button", { name: "Guardar versión" }));
    await waitFor(() => expect(fichas()).toBe(2));
    expect(servidor.de("GET", "/v1/obras/todas").length).toBeGreaterThan(obrasAntes);
    await irA(u, "Resumen");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/resumen"));
    await waitFor(() => expect(fichas()).toBe(3));
    await waitFor(() => expect(screen.getByRole("region", { name: "Obra abierta" })).toHaveTextContent("Versión: 003"));
  });

  // Ronda 2, menor 3: lo escrito en la pausa sale al dejar Presupuesto y queda en el borrador; luego salir pregunta.
  test("escribir una cantidad y pasar enseguida a Versiones y luego al Resumen pregunta y no descarta", async () => {
    const u = montar("/obra/empresa/7/presupuesto");
    await borradorListoEnLaHoja();
    fireEvent.change(await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 1" }), { target: { value: "5" } });
    await irA(u, "Versiones");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/versiones"));
    await waitFor(() => expect(servidor.de("PUT", "/v1/hoja/borradores/b-1/cantidades")).toHaveLength(1));
    await pausa();
    await irA(u, "Resumen");
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Salir" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/resumen"));
    await pausa();
    expect(descartes()).toEqual([]);
  });
});
