import { act, configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { Marco } from "../../marco/Marco";
import { estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import { cuerpoDeVista } from "../hoja/datosDePrueba";
import PaginaHoja from "../hoja/index";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "../hoja/logica";
import { importada, respuestaDeFusion } from "./datosDePlano";
import PaginaArchivos from "./index";
import type { ImportacionDeObra } from "./logica";
import { olvidarImportaciones } from "./useImportacion";

// Tarea 11 del plan F4: la sección «Archivos y planos» de la obra. Se monta el marco entero (árbol de la obra, proveedor
// de la Hoja, Presupuesto real) para ver que el plano entra en el MISMO borrador que el Presupuesto. Oráculos escritos a
// mano: obra ficticia 7 («Casa Demo») de la carpeta de la empresa, versión 002, y un registro con un plano guardado en
// VIV-002 y un cómputo que sigue en el borrador.
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

const PLANO_GUARDADO: ImportacionDeObra = {
  tipo: "plano",
  archivo: "planta-baja.dxf",
  fecha_hora: "2026-10-31T14:05:09",
  usuario: "Ana Pérez <ana>",
  resumen: "33 filas en el espacio",
  version: "VIV-002",
  guardada: true,
};
const COMPUTO_SIN_GUARDAR: ImportacionDeObra = {
  tipo: "computo",
  archivo: "movimiento.csv",
  fecha_hora: "2026-11-01T09:30:00",
  usuario: "Ana Pérez <ana>",
  resumen: "18 partidas llevadas",
  version: null,
  guardada: false,
};
const PLANO_FUSIONADO: ImportacionDeObra = {
  tipo: "plano",
  archivo: "of001.dxf",
  fecha_hora: "2026-11-02T10:15:00",
  usuario: "Ana Pérez <ana>",
  resumen: "33 filas en el espacio",
  version: null,
  guardada: false,
};

// Lo que el servidor simulado tiene de la obra; cada prueba lo cambia antes de montar.
let conVersiones = true;
let espacioVacio = true;
// El borrador que abre el servidor es de solo lectura (menor 7 de la Tarea 11).
let soloLectura = false;
let registro: ImportacionDeObra[] = [];
let apagados: string[] = [];
let fusionado = false;
let servidor: ReturnType<typeof servidorFalso>;

function versiones(proyecto: string): VersionesRespuesta {
  return {
    proyecto,
    moneda: "Bs",
    por_omision: conVersiones ? "002" : null,
    versiones: conVersiones
      ? [{ codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 }]
      : [],
  };
}

function borrador(id: string, proyecto: string, version: string | null): BorradorAbierto {
  return {
    id,
    base: { proyecto, version, vigente: version, lista: "Lista", espacio_de: version, solo_lectura: soloLectura, moneda: "Bs" },
    resumen: resumen({ espacio_vacio: espacioVacio }),
    instantanea: { creadas: 0, mensaje: null },
  };
}

const RESUMEN_FUSIONADO = resumen({ rev: 1, cambios: 3, total: m("3000.50"), espacio_vacio: false });

beforeEach(() => {
  conVersiones = true;
  espacioVacio = true;
  soloLectura = false;
  registro = [COMPUTO_SIN_GUARDAR, PLANO_GUARDADO];
  apagados = [];
  fusionado = false;
  olvidarImportaciones();
  let abiertos = 0;
  const estado = estadoInicial();
  estado.proyectos = estado.proyectos.map((p) => ({ ...p, version_vigente: 2 }));
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    const url = new URL(ruta, "http://silice.local");
    const camino = url.pathname;
    if (camino === "/v1/modulos") {
      return json({
        modulos: ["produccion", "vial", "edificacion", "riesgo"].map((clave) => ({
          clave,
          nombre: clave,
          activo: !apagados.includes(clave),
          cambiado_por: null,
          cambiado_el: null,
        })),
      });
    }
    if (camino === "/v1/hoja/versiones") return json(versiones(url.searchParams.get("proyecto") ?? ""));
    if (camino === "/v1/hoja/importaciones") return json({ importaciones: registro });
    if (camino === "/v1/hoja/borradores" && metodo === "POST") {
      const pedido = cuerpo as { proyecto: string; version: string | null };
      abiertos += 1;
      return json(borrador(`b-${abiertos}`, pedido.proyecto, pedido.version), 201);
    }
    const propio = /^\/v1\/hoja\/borradores\/([^/]+)$/.exec(camino);
    if (propio && metodo === "DELETE") return new Response(null, { status: 204 });
    if (propio && metodo === "GET") {
      const b = borrador(propio[1]!, "7", conVersiones ? "002" : null);
      return json({ id: b.id, base: b.base, resumen: fusionado ? RESUMEN_FUSIONADO : b.resumen });
    }
    if (/\/plano$/.test(camino) && metodo === "POST") return json(importada());
    if (camino.endsWith("/plano/fusionar")) {
      fusionado = true;
      registro = [PLANO_FUSIONADO, ...registro];
      return json({ ...respuestaDeFusion(1), resumen: RESUMEN_FUSIONADO });
    }
    if (camino.endsWith("/cambios")) return json({ cambios: [] });
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

function Ubicacion() {
  const { pathname } = useLocation();
  return <output data-testid="ruta">{pathname}</output>;
}

function montar(en = "/obra/empresa/7/archivos", sesion: SesionRespuesta = sesionDe("ana")) {
  render(
    <MemoryRouter initialEntries={[en]}>
      <Marco sesion={sesion} alSalir={vi.fn()} alExpirar={vi.fn()} paginas={ligeras({ hoja: PaginaHoja, archivos: PaginaArchivos })} />
      <Ubicacion />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

const ruta = () => screen.getByTestId("ruta").textContent;
const arbol = () => screen.findByRole("tree", { name: "Obras" });
const irA = async (u: ReturnType<typeof userEvent.setup>, seccion: string) =>
  u.click(await within(await arbol()).findByRole("treeitem", { name: seccion }));
const tablaDelRegistro = () => screen.findByRole("table", { name: "Registro de importaciones" });
const filas = (tabla: HTMLElement) =>
  within(tabla)
    .getAllByRole("row")
    .slice(1)
    .map((f) => within(f).getAllByRole("cell").map((c) => c.textContent));
const principales = () => [...document.querySelectorAll(".cds--btn--primary")].map((b) => b.textContent);
const lecturasDelRegistro = () => servidor.llamadas.filter((l) => l.metodo === "GET" && l.ruta.startsWith("/v1/hoja/importaciones")).length;
const aperturas = () => servidor.de("POST", "/v1/hoja/borradores").map((l) => l.cuerpo as { proyecto: string; version: string | null });
const pausa = () =>
  act(async () => {
    await new Promise((r) => setTimeout(r, 30));
  });

async function abrirElDialogo(u: ReturnType<typeof userEvent.setup>) {
  await u.click(await screen.findByRole("button", { name: "Subir plano o cómputo" }));
  return screen.findByRole("dialog", { name: "Subir plano o cómputo" });
}

async function leerUnPlano(u: ReturnType<typeof userEvent.setup>) {
  const dialogo = await abrirElDialogo(u);
  await u.upload(dialogo.querySelector('input[type="file"]') as HTMLInputElement, new File(["0\nEOF"], "of001.dxf"));
  await u.click(within(dialogo).getByRole("button", { name: "Leer plano" }));
  await within(dialogo).findByRole("heading", { name: "Informe de la importación de of001.dxf" });
  return dialogo;
}

describe("Archivos y planos (Tarea 11 de F4)", () => {
  test("un h1 «Archivos y planos» y el registro de la obra, con la fecha en es-VE y lo no guardado «sin guardar»", async () => {
    montar();
    expect(await screen.findByRole("heading", { level: 1, name: "Archivos y planos" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const tabla = await tablaDelRegistro();
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Nombre",
      "Tipo",
      "Fecha y hora",
      "Quién",
      "Qué produjo",
      "Versión",
    ]);
    await waitFor(() =>
      expect(filas(tabla)).toEqual([
        ["movimiento.csv", "Cómputo .csv", "01/11/2026 09:30", "Ana Pérez <ana>", "18 partidas llevadas", "sin guardar"],
        ["planta-baja.dxf", "Plano .dxf", "31/10/2026 14:05", "Ana Pérez <ana>", "33 filas en el espacio", "VIV-002"],
      ]),
    );
    expect(servidor.llamadas.some((l) => l.ruta === "/v1/hoja/importaciones?proyecto=7")).toBe(true);
  });

  test("el registro vacío lo dice", async () => {
    registro = [];
    montar();
    expect(await screen.findByText("Todavía no se ha importado ningún archivo en esta obra.")).toBeInTheDocument();
  });

  test("«Subir plano o cómputo» es el único botón principal; abre el diálogo y un .dxf se lee sobre el borrador del proveedor", async () => {
    const u = montar();
    await screen.findByRole("button", { name: "Subir plano o cómputo" });
    expect(principales()).toEqual(["Subir plano o cómputo"]);
    const dialogo = await abrirElDialogo(u);
    // Con el diálogo abierto, el único principal a la vista es el del paso del flujo.
    expect(principales()).toEqual(["Leer plano"]);
    await u.upload(dialogo.querySelector('input[type="file"]') as HTMLInputElement, new File(["0\nEOF"], "of001.dxf"));
    await u.click(within(dialogo).getByRole("button", { name: "Leer plano" }));
    await within(dialogo).findByRole("heading", { name: "Informe de la importación de of001.dxf" });
    expect(servidor.de("POST", "/v1/hoja/borradores/b-1/plano")).toHaveLength(1);
    expect(principales()).toEqual(["Fusionar con el espacio del borrador"]);
    expect(aperturas()).toEqual([{ proyecto: "7", version: "002" }]);
  });

  test("fusionar refresca el borrador del proveedor y vuelve a pedir el registro: la fila nueva sale «sin guardar»", async () => {
    const u = montar();
    const dialogo = await leerUnPlano(u);
    const antes = lecturasDelRegistro();
    await u.click(within(dialogo).getByRole("button", { name: "Fusionar con el espacio del borrador" }));
    await within(dialogo).findByText(/Se fusionó «of001.dxf»/);
    await waitFor(() => expect(servidor.de("GET", "/v1/hoja/borradores/b-1").length).toBeGreaterThan(0));
    await waitFor(() => expect(lecturasDelRegistro()).toBe(antes + 1));
    await u.click(within(dialogo).getByRole("button", { name: "Cerrar" }));
    const tabla = await tablaDelRegistro();
    await waitFor(() => expect(filas(tabla)[0]).toEqual(["of001.dxf", "Plano .dxf", "02/11/2026 10:15", "Ana Pérez <ana>", "33 filas en el espacio", "sin guardar"]));
  });

  test("tras fusionar, ir a Presupuesto no abre otro borrador: sigue el mismo, con los cambios del plano", async () => {
    const u = montar();
    const dialogo = await leerUnPlano(u);
    await u.click(within(dialogo).getByRole("button", { name: "Fusionar con el espacio del borrador" }));
    await within(dialogo).findByText(/Se fusionó «of001.dxf»/);
    await waitFor(() => expect(within(dialogo).getByRole("button", { name: "Cerrar" })).toBeEnabled());
    await u.click(within(dialogo).getByRole("button", { name: "Cerrar" }));
    await irA(u, "Presupuesto");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto"));
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    expect(await within(estado).findByText(/3 cambios sin guardar/)).toBeInTheDocument();
    await pausa();
    expect(aperturas()).toEqual([{ proyecto: "7", version: "002" }]);
    expect(servidor.llamadas.filter((l) => l.metodo === "DELETE" && l.ruta.startsWith("/v1/hoja/borradores/"))).toEqual([]);
  });

  test("en una obra en blanco, el plano se importa sobre el borrador en blanco (Foco 2)", async () => {
    conVersiones = false;
    const u = montar();
    await leerUnPlano(u);
    expect(aperturas()).toEqual([{ proyecto: "7", version: null }]);
    expect(servidor.de("POST", "/v1/hoja/borradores/b-1/plano")).toHaveLength(1);
  });

  test("Esc cierra el diálogo y el foco vuelve a «Subir plano o cómputo»", async () => {
    const u = montar();
    await abrirElDialogo(u);
    await u.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(screen.getByRole("button", { name: "Subir plano o cómputo" })).toHaveFocus());
  });

  test("elegir una fila abre el panel con lo que guardó el registro", async () => {
    const u = montar();
    const tabla = await tablaDelRegistro();
    await u.click(await within(tabla).findByRole("button", { name: "Ver el informe de planta-baja.dxf" }));
    const panel = screen.getByRole("complementary", { name: "Informe de la importación de planta-baja.dxf" });
    expect(within(panel).getByText("33 filas en el espacio")).toBeInTheDocument();
    expect(within(panel).getByText("VIV-002")).toBeInTheDocument();
    expect(within(panel).getByText("31/10/2026 14:05")).toBeInTheDocument();
    expect(within(panel).getByText("Plano .dxf")).toBeInTheDocument();
  });

  test("quien revisa ve el registro y el panel del informe, pero nada que suba, ni franja con botón, ni botón principal (Foco 3)", async () => {
    const u = montar("/obra/empresa/7/archivos", sesionDe("rita"));
    const tabla = await tablaDelRegistro();
    await waitFor(() => expect(filas(tabla)).toHaveLength(2));
    await u.click(within(tabla).getByRole("button", { name: "Ver el informe de movimiento.csv" }));
    expect(screen.getByRole("complementary", { name: "Informe de la importación de movimiento.csv" })).toBeInTheDocument();
    await pausa();
    expect(screen.queryByRole("button", { name: "Subir plano o cómputo" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Describir el espacio a mano" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
    expect(principales()).toEqual([]);
  });

  test("quien arma con un borrador de solo lectura ve el registro y el informe, sin subir ni describir el espacio (Foco 3)", async () => {
    soloLectura = true;
    const u = montar();
    const tabla = await tablaDelRegistro();
    await waitFor(() => expect(filas(tabla)).toHaveLength(2));
    await u.click(within(tabla).getByRole("button", { name: "Ver el informe de movimiento.csv" }));
    expect(screen.getByRole("complementary", { name: "Informe de la importación de movimiento.csv" })).toBeInTheDocument();
    await pausa();
    expect(screen.queryByRole("button", { name: "Subir plano o cómputo" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Describir el espacio a mano" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Te falta" })).toBeNull();
    expect(principales()).toEqual([]);
  });

  test("«Describir el espacio a mano» lleva a Presupuesto con «Espacio y metrajes» a la vista y elegida", async () => {
    const u = montar();
    await u.click(await screen.findByRole("link", { name: "Describir el espacio a mano" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto"));
    const pestana = await screen.findByRole("tab", { name: "Espacio y metrajes" });
    expect(pestana).toHaveAttribute("aria-selected", "true");
  });

  test("con el espacio pedido y aún vacío, la franja «Te falta» lleva el único botón principal, que abre el diálogo", async () => {
    const u = montar();
    await u.click(await screen.findByRole("link", { name: "Describir el espacio a mano" }));
    await screen.findByRole("tab", { name: "Espacio y metrajes" });
    await irA(u, "Archivos y planos");
    const franja = await screen.findByRole("region", { name: "Siguiente paso" });
    expect(franja).toHaveTextContent("Te falta: subir el plano o describir el espacio");
    expect(principales()).toEqual(["Subir plano o cómputo"]);
    expect(within(franja).getByRole("button", { name: "Subir plano o cómputo" })).toBeInTheDocument();
    await u.click(within(franja).getByRole("button", { name: "Subir plano o cómputo" }));
    expect(await screen.findByRole("dialog", { name: "Subir plano o cómputo" })).toBeInTheDocument();
    expect(principales()).toEqual(["Leer plano"]);
  });

  test("sin pedir el espacio no hay franja", async () => {
    montar();
    await screen.findByRole("button", { name: "Subir plano o cómputo" });
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
  });

  test("en «Espacio y metrajes» ya no está el bloque «Importar plano (DXF o IFC)» y sí el enlace a Archivos y planos", async () => {
    espacioVacio = false;
    const u = montar("/obra/empresa/7/presupuesto");
    expect(await screen.findByRole("tab", { name: "Espacio y metrajes" })).toHaveAttribute("aria-selected", "true");
    await screen.findByText("Cantidades derivadas");
    expect(screen.queryByRole("button", { name: "Importar plano (DXF o IFC)" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Leer plano" })).toBeNull();
    await u.click(screen.getByRole("link", { name: "Importar un plano en Archivos y planos" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/archivos"));
    expect(await screen.findByRole("heading", { level: 1, name: "Archivos y planos" })).toBeInTheDocument();
  });

  // Tarea 12 (decisión del orquestador): edificación apaga los planos y el espacio, no los cómputos. La sección se sigue
  // ofreciendo; lo que cambia dentro lo prueba `CargarComputo.test.tsx`.
  test("con «edificación» apagada, «Archivos y planos» sigue en el árbol de la obra y se abre", async () => {
    apagados = ["edificacion"];
    const u = montar("/obra/empresa/7/presupuesto");
    const lista = await arbol();
    await within(lista).findByRole("treeitem", { name: "Presupuesto" });
    await pausa();
    await u.click(await within(lista).findByRole("treeitem", { name: "Archivos y planos" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/archivos"));
    expect(await screen.findByRole("heading", { level: 1, name: "Archivos y planos" })).toBeInTheDocument();
  });

  test("con «edificación» encendida, «Archivos y planos» está en el árbol de la obra", async () => {
    montar("/obra/empresa/7/presupuesto");
    const lista = await arbol();
    expect(await within(lista).findByRole("treeitem", { name: "Archivos y planos" })).toBeInTheDocument();
  });
});
