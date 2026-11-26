import { fileURLToPath } from "node:url";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
import * as sass from "sass";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { Marco } from "../../marco/Marco";
import { caso, estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { EstadoDelServidor, Respondedor } from "../../shell/obras/datosDePrueba";
import { PAGINAS } from "../../shell/rutas";
import type { PaginaDef } from "../../shell/rutas";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import { UltimasAuditorias } from "./UltimasAuditorias";

// Inicio › Resumen (`#/inicio/general`, especificación 00-inicio-resumen.html) montado dentro del Marco real.
// Oráculos escritos a mano con obras, carpetas y cifras ficticias.

const RUTA_CARTERA = "/v1/obras/resumen/todas";
const RUTA_PENDIENTES = "/v1/obras/pendientes/todas";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=100";
const RUTA_CARPETA = "/v1/carpeta";
const RUTA_PARTIDAS = "/partidas";
const RUTA_INSUMOS = "/insumos";
const RUTA_ARENERA = "/v1/produccion/existencias";
const RUTA_CUENTAS = "/v1/cuentas";
const SUR = "Carpeta Sur.db";

const CUENTA_ADMIN = { id: 1, login: "admin", nombre: "Admin Ficticio", roles: ["administrador"], activa: true };
const CUENTA_ANA = { id: 2, login: "ana", nombre: "Ana Pérez", roles: ["arma"], activa: true };

interface Pendiente {
  carpeta: string | null;
  obra_id: number;
  obra: string;
  grupo: string;
  urgencia: "bloquea" | "aviso";
  texto: string;
  accion: { texto: string; pagina: string };
}

const CEMENTO: Pendiente = {
  carpeta: null,
  obra_id: 7,
  obra: "Casa Demo",
  grupo: "compras",
  urgencia: "bloquea",
  texto: "Falta pedir el cemento",
  accion: { texto: "Abrir el presupuesto", pagina: "hoja" },
};
const DEVUELTA: Pendiente = {
  carpeta: SUR,
  obra_id: 3,
  obra: "Galpón Sur",
  grupo: "aprobar",
  urgencia: "bloquea",
  texto: "V2 devuelta con observaciones",
  accion: { texto: "Hacer una versión nueva", pagina: "hoja" },
};
const PRECIOS: Pendiente = {
  carpeta: null,
  obra_id: 8,
  obra: "Torre B",
  grupo: "precios",
  urgencia: "aviso",
  texto: "3 precios con más de 90 días",
  accion: { texto: "Actualizar precios", pagina: "actualizacion" },
};

// Cartera con dos monedas: Bs y USD nunca se suman entre sí (429.637,10 no debe aparecer jamás).
const DOS_MONEDAS = {
  hoy: "2026-11-05",
  por_moneda: [
    { moneda: "Bs", obras: 2, total: "334570.5", en_ejecucion: 1 },
    { moneda: "USD", obras: 1, total: "95066.6", en_ejecucion: 0 },
  ],
  obras: [
    {
      carpeta: null,
      carpeta_titulo: "Carpeta de la empresa",
      obra_id: 7,
      nombre: "Casa Demo",
      moneda: "Bs",
      etapa: "en_ejecucion",
      etapa_texto: "En ejecución",
      total: "334570.5",
      avance_real: "62.5",
      avance_plan: "70.0",
    },
    {
      carpeta: null,
      carpeta_titulo: "Carpeta de la empresa",
      obra_id: 8,
      nombre: "Torre B",
      moneda: "Bs",
      etapa: "en_elaboracion",
      etapa_texto: "En elaboración",
      total: null,
      avance_real: null,
      avance_plan: null,
    },
    {
      carpeta: SUR,
      carpeta_titulo: "Carpeta Sur",
      obra_id: 3,
      nombre: "Galpón Sur",
      moneda: "USD",
      etapa: "atrasada",
      etapa_texto: "Atrasada",
      total: "95066.6",
      avance_real: "10.0",
      avance_plan: "25.5",
    },
  ],
  carpetas_omitidas: 0,
};

const SOLO_BS = {
  ...DOS_MONEDAS,
  por_moneda: [DOS_MONEDAS.por_moneda[0]!],
  obras: DOS_MONEDAS.obras.slice(0, 2),
};

const SIN_OBRAS = { hoy: "2026-11-05", por_moneda: [], obras: [], carpetas_omitidas: 0 };

const AUDITORIA = { id: 1, archivo: "presupuesto-1.xlsx", fecha: "2026-10-18T14:32:00", tipo: "libro", errores: 2, advertencias: 5 };
const CARPETA_CON_LISTA = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista Julio", moneda: "Bs", fecha: "2026-07-15", origen: "empresa" },
  aviso: null,
};
const PARTIDAS_DEMO = [
  { codigo: "C-001", descripcion: "Excavación", unidad: "m3", dominio: "civil" },
  { codigo: "C-002", descripcion: "Concreto", unidad: "m3", dominio: "civil" },
];
const INSUMOS_DEMO = [
  { codigo: "M-001", descripcion: "Cemento gris", tipo: "MATERIAL", unidad: "saco", precio_vigente: "420.00" },
  { codigo: "M-002", descripcion: "Cabilla", tipo: "MATERIAL", unidad: "kg", precio_vigente: null },
];
const ARENERA_DEMO = [
  { codigo: "ARE-01", nombre: "Arena lavada", unidad_venta: "t", existencia: "4850.0", minima: "100", queda_poco: false, negativa: false },
];

let servidor: ReturnType<typeof servidorFalso>;
let cartera: Respondedor;
let pendientes: Respondedor;
let auditorias: Respondedor;
let carpetaResp: Respondedor;
let partidasResp: Respondedor;
let insumosResp: Respondedor;
let areneraResp: Respondedor;
let cuentas: Respondedor;
let apagados: string[];

const lista = (...p: Pendiente[]): Respondedor => () => json({ pendientes: p, carpetas_omitidas: 0 });

function instalar() {
  const estado: EstadoDelServidor = estadoInicial();
  estado.casos = [...estado.casos, caso(SUR)];
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    if (metodo !== "GET") return undefined;
    if (ruta === RUTA_CARTERA) return cartera(metodo, ruta, cuerpo);
    if (ruta === RUTA_PENDIENTES) return pendientes(metodo, ruta, cuerpo);
    if (ruta === RUTA_AUDITORIAS) return auditorias(metodo, ruta, cuerpo);
    if (ruta === RUTA_CARPETA) return carpetaResp(metodo, ruta, cuerpo);
    if (ruta === RUTA_PARTIDAS) return partidasResp(metodo, ruta, cuerpo);
    if (ruta === RUTA_INSUMOS) return insumosResp(metodo, ruta, cuerpo);
    if (ruta === RUTA_ARENERA) return areneraResp(metodo, ruta, cuerpo);
    if (ruta === RUTA_CUENTAS) return cuentas(metodo, ruta, cuerpo);
    if (ruta === "/v1/modulos") {
      const claves = ["produccion", "vial", "riesgo", "edificacion"];
      return json({
        modulos: claves.map((clave) => ({ clave, nombre: clave, activo: !apagados.includes(clave), cambiado_por: null, cambiado_el: null })),
      });
    }
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
}

beforeEach(() => {
  apagados = [];
  cartera = () => json(DOS_MONEDAS);
  pendientes = lista(CEMENTO, DEVUELTA, PRECIOS);
  auditorias = () => json([AUDITORIA]);
  carpetaResp = () => json(CARPETA_CON_LISTA);
  partidasResp = () => json(PARTIDAS_DEMO);
  insumosResp = () => json(INSUMOS_DEMO);
  areneraResp = () => json(ARENERA_DEMO);
  cuentas = () => json({ cuentas: [CUENTA_ADMIN], aviso_arma_y_revisa: "" });
  instalar();
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <output data-testid="ruta">{`${pathname}${search}`}</output>;
}
const ruta = () => screen.getByTestId("ruta").textContent;
function IrA({ destino }: { destino: string }) {
  const navegar = useNavigate();
  return <button onClick={() => navegar(destino)}>{`Ir a ${destino}`}</button>;
}

function conVistaGeneral(): PaginaDef[] {
  const real = PAGINAS.find((p) => p.id === "inicio");
  if (!real) throw new Error("Falta la pantalla «inicio» en shell/rutas.ts.");
  return ligeras().map((p) => (p.id === "inicio" ? { ...p, cargar: real.cargar } : p));
}

function montar({ sesion = sesionDe("ana"), en = "/inicio/general", ir }: { sesion?: SesionRespuesta; en?: string; ir?: string } = {}) {
  return render(
    <MemoryRouter initialEntries={[en]}>
      <Marco sesion={sesion} alSalir={vi.fn()} alExpirar={vi.fn()} paginas={conVistaGeneral()} />
      <Ubicacion />
      {ir && <IrA destino={ir} />}
    </MemoryRouter>,
  );
}

const bloque = (nombre: string) => screen.findByRole("region", { name: nombre }, { timeout: 3000 });
const pedidas = (r: string) => servidor.de("GET", r).length;

describe("Inicio › Resumen: h1 de la cartera y orden de las secciones", () => {
  test("el h1 resume cuántas obras y su total por moneda, seguido de la cartera, su avance, los problemas por obra y lo cargado", async () => {
    montar();
    await bloque("La cartera de obras");
    await bloque("Avance de la cartera");
    await bloque("Problemas abiertos por obra");
    await bloque("Lo que hay cargado");

    const h1 = await screen.findByRole("heading", { level: 1, name: "3 obras por 334.570,50 Bs y 95.066,60 USD" });
    expect(h1).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText("Vista general · corte al 05/11/2026")).toBeInTheDocument();

    const titulos = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    const propios = titulos.filter((t) =>
      ["La cartera de obras", "Avance de la cartera", "Problemas abiertos por obra", "Lo que hay cargado"].includes(t ?? ""),
    );
    expect(propios).toEqual(["La cartera de obras", "Avance de la cartera", "Problemas abiertos por obra", "Lo que hay cargado"]);

    const barra = screen.getByRole("navigation", { name: "Inicio" });
    expect(within(barra).getByRole("link", { name: "Vista general" })).toHaveAttribute("aria-current", "page");
    expect(within(barra).getByRole("link", { name: "Pendientes" })).not.toHaveAttribute("aria-current");
  });

  test("con una sola moneda el h1 dice «2 obras por 334.570,50 Bs» y no pinta ceros ni tarjeta de la otra moneda", async () => {
    cartera = () => json(SOLO_BS);
    montar();
    expect(await screen.findByRole("heading", { level: 1, name: "2 obras por 334.570,50 Bs" })).toBeInTheDocument();
    await bloque("Cartera en Bs");
    expect(screen.queryByRole("region", { name: "Cartera en USD" })).toBeNull();
  });

  test("con dos monedas nunca aparece ninguna suma entre Bs y USD", async () => {
    montar();
    const bs = await bloque("Cartera en Bs");
    const usd = await bloque("Cartera en USD");
    expect(document.body.textContent).not.toContain("429.637");
    expect(document.body.textContent).not.toContain("429637");
    expect(bs.textContent).not.toContain("USD");
    expect(usd.textContent).not.toContain("Bs");
  });
});

describe("Inicio › Resumen: la cartera y sus avisos", () => {
  test("carpetas_omitidas > 0 se avisa en plural y en singular", async () => {
    cartera = () => json({ ...DOS_MONEDAS, carpetas_omitidas: 2 });
    const plural = montar();
    const b2 = await bloque("La cartera de obras");
    expect(await within(b2).findByText("No se pudieron leer 2 carpetas; sus obras no aparecen en la cartera.")).toBeInTheDocument();
    plural.unmount();

    cartera = () => json({ ...DOS_MONEDAS, carpetas_omitidas: 1 });
    montar();
    const b1 = await bloque("La cartera de obras");
    expect(await within(b1).findByText("No se pudo leer 1 carpeta; sus obras no aparecen en la cartera.")).toBeInTheDocument();
  });

  test("«¿Qué es esto?» explica cómo se calcula el total cuando hay cartera, y no aparece en vacío", async () => {
    const u = userEvent.setup();
    const conDatos = montar();
    const seccion = await bloque("La cartera de obras");
    const boton = await within(seccion).findByRole("button", { name: "¿Qué es esto?" });
    await u.click(boton);
    expect(within(seccion).getByRole("region", { name: "Cómo se calcula el total" })).toHaveTextContent(
      "El total de cada obra es el de su línea base o, sin ella, el de su versión vigente. Cada moneda se suma por separado: Bs y USD nunca se mezclan.",
    );
    conDatos.unmount();

    cartera = () => json(SIN_OBRAS);
    montar();
    const vacia = await bloque("La cartera de obras");
    expect(within(vacia).queryByRole("button", { name: "¿Qué es esto?" })).toBeNull();
  });
});

describe("Inicio › Resumen: el avance y las tablas accesibles", () => {
  const seccionAvance = async () => within(await bloque("Avance de la cartera"));

  test("la tabla de avance escribe etapa_texto del servidor, espacios duros en porcentajes y enlaces a cada obra", async () => {
    const u = userEvent.setup();
    const obras = DOS_MONEDAS.obras.map((o) => (o.obra_id === 7 ? { ...o, etapa_texto: "En ejecución desde octubre" } : o));
    cartera = () => json({ ...DOS_MONEDAS, obras });
    montar();
    const t = await seccionAvance();
    await u.click(t.getByText("Ver como tabla"));
    const tabla = await t.findByRole("table", { name: "Obras de la cartera y su avance contra el plan" });
    const casa = within(tabla).getByRole("link", { name: "Casa Demo" }).closest("tr")!;
    expect(casa).toHaveTextContent("En ejecución desde octubre");
    expect(casa).toHaveTextContent("334.570,50 Bs");
    expect(casa.querySelector(".silice-inicio__avance .silice-cifra")?.textContent).toBe("Real\u00a062,5\u00a0% · Plan\u00a070,0\u00a0%");
    expect(casa.querySelector(".fiori-kpi__barra-real")).toHaveStyle({ inlineSize: "62.5%" });
    expect(casa.querySelector(".fiori-kpi__barra-meta")).toHaveStyle({ inlineSize: "70%" });

    const torre = within(tabla).getByRole("link", { name: "Torre B" }).closest("tr")!;
    expect(within(torre).getByText("Sin avance")).toBeInTheDocument();
    expect(within(torre).getByText("Sin versión")).toBeInTheDocument();

    expect(within(tabla).getByRole("link", { name: "Galpón Sur" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/resumen");
    expect(within(tabla).getByRole("link", { name: "Casa Demo" })).toHaveAttribute("href", "/obra/empresa/7/resumen");

    const region = tabla.closest<HTMLElement>('[role="region"]');
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region).toHaveAccessibleName("Obras de la cartera y su avance contra el plan: desplazar horizontalmente");
  });

  describe("la hoja de estilos de las tablas de obras", () => {
    const ESTILOS = "./inicio.scss";
    const css = sass.compile(fileURLToPath(new URL(ESTILOS, import.meta.url))).css;
    const bloqueDesde = (inicio: number): string => {
      const abre = css.indexOf("{", inicio);
      let nivel = 0;
      for (let i = abre; i < css.length; i++) {
        if (css[i] === "{") nivel++;
        if (css[i] === "}" && --nivel === 0) return css.slice(abre + 1, i);
      }
      return "";
    };

    test("apila las filas cuando el contenedor mide menos de 42 rem, sin umbrales en px", () => {
      expect(css).toMatch(/\.silice-inicio__obras\s*\{[^}]*container-type:\s*inline-size/);
      const i = css.search(/@container\s*\(max-inline-size:\s*42rem\)/);
      expect(i).toBeGreaterThanOrEqual(0);
      const apilada = bloqueDesde(i);
      expect(apilada).toMatch(/td\[data-etiqueta\]\s*\{[^}]*display:\s*flex/);
      expect(apilada).toMatch(/td\[data-etiqueta\]::before\s*\{[^}]*content:\s*attr\(data-etiqueta\)\s*":"/);
      expect(css).not.toMatch(/@container\s*\(max-(inline-size|width):\s*[\d.]+px/);
    });
  });
});

describe("Inicio › Resumen: «Problemas abiertos por obra»", () => {
  test("agrupa los pendientes por obra con su palabra («bloquea» / «aviso»), muestra «Ninguno» donde no hay y enlaza a la bandeja", async () => {
    pendientes = lista(CEMENTO, PRECIOS);
    montar();
    const b = await bloque("Problemas abiertos por obra");
    const tabla = await within(b).findByRole("table", { name: "Problemas abiertos de cada obra, con su gravedad" });

    const casa = within(tabla).getByRole("link", { name: "Casa Demo" }).closest("tr")!;
    expect(casa).toHaveTextContent("1 bloquea");

    const torre = within(tabla).getByRole("link", { name: "Torre B" }).closest("tr")!;
    expect(torre).toHaveTextContent("1 aviso");

    const galpon = within(tabla).getByRole("link", { name: "Galpón Sur" }).closest("tr")!;
    expect(galpon).toHaveTextContent("Ninguno");

    expect(within(b).getByText(/Suman 1 bloquea · 1 aviso\./)).toBeInTheDocument();
    expect(within(b).getByRole("link", { name: "Ir a la bandeja de pendientes (2)" })).toHaveAttribute("href", "/inicio/pendientes");
  });

  test("sin pendientes dice que ninguna obra tiene problemas abiertos hoy y no ofrece ir a la bandeja", async () => {
    pendientes = lista();
    montar();
    const b = await bloque("Problemas abiertos por obra");
    expect(await within(b).findByText("Ninguna obra tiene problemas abiertos hoy.")).toBeInTheDocument();
    expect(within(b).queryByRole("link", { name: /bandeja/ })).toBeNull();
  });

  test("al volver de una obra vuelve a pedir los pendientes y refleja lo resuelto", async () => {
    const u = userEvent.setup();
    let actuales = [CEMENTO, PRECIOS];
    pendientes = () => json({ pendientes: actuales, carpetas_omitidas: 0 });
    montar({ ir: "/obra/empresa/7/presupuesto" });
    const antes = await bloque("Problemas abiertos por obra");
    await within(antes).findByText("1 bloquea");
    expect(pedidas(RUTA_PENDIENTES)).toBe(1);

    await u.click(screen.getByRole("button", { name: "Ir a /obra/empresa/7/presupuesto" }));
    await screen.findByRole("heading", { level: 1, name: "Presupuesto" }, { timeout: 3000 });
    actuales = [PRECIOS];
    await u.click(within(screen.getByRole("banner")).getByRole("link", { name: "Sílice" }));

    const despues = await bloque("Problemas abiertos por obra");
    await waitFor(() => expect(pedidas(RUTA_PENDIENTES)).toBe(2));
    const casa = (await within(despues).findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa).toHaveTextContent("Ninguno");
    expect(ruta()).toBe("/inicio/general");
  });
});

describe("Inicio › Resumen: tarjetas de «Lo que hay cargado»", () => {
  test("muestra libros auditados, lista de precios vigente y vigencia, partidas e insumos del catálogo, y producción", async () => {
    montar();
    const seccion = await bloque("Lo que hay cargado");

    const libros = within(seccion).getByRole("article", { name: "Libros auditados" });
    expect(await within(libros).findByText("1")).toBeInTheDocument();
    expect(libros).toHaveTextContent("Último el 18/10/2026 (presupuesto-1.xlsx) · 2 errores, 5 advertencias");
    expect(within(libros).getByRole("link", { name: "Ir a Auditoría" })).toHaveAttribute("href", "/auditoria/subir");

    const listaVig = within(seccion).getByRole("article", { name: "Lista de precios vigente" });
    expect(await within(listaVig).findByText("Lista Julio")).toBeInTheDocument();
    expect(listaVig).toHaveTextContent("Vigencia: 15/07/2026 · Moneda Bs");
    expect(within(listaVig).getByRole("link", { name: "Ver precios" })).toHaveAttribute("href", "/precios/catalogo");

    const partidas = within(seccion).getByRole("article", { name: "Partidas del catálogo" });
    expect(await within(partidas).findByText("2")).toBeInTheDocument();
    expect(partidas).toHaveTextContent("2 partidas guardadas para armar");

    const insumos = within(seccion).getByRole("article", { name: "Insumos del catálogo" });
    expect(await within(insumos).findByText("2")).toBeInTheDocument();
    expect(insumos).toHaveTextContent("1 insumo sin precio vigente");

    const prod = within(seccion).getByRole("article", { name: "Producción de la arenera" });
    expect(await within(prod).findByText("1")).toBeInTheDocument();
    expect(prod).toHaveTextContent("1 material registrado · Todo sobre el mínimo");
    expect(within(prod).getByRole("link", { name: "Ver todas las existencias" })).toHaveAttribute("href", "/produccion/existencias");
  });

  test("en la tarjeta de producción las alertas de existencia negativa o poca existencia dicen su palabra de gravedad", async () => {
    areneraResp = () =>
      json([
        { codigo: "GRA-01", nombre: "Granzón", unidad_venta: "m3", existencia: "-2", minima: "10", queda_poco: true, negativa: true },
        { codigo: "ARE-01", nombre: "Arena", unidad_venta: "t", existencia: "20", minima: "40", queda_poco: true, negativa: false },
      ]);
    montar();
    const seccion = await bloque("Lo que hay cargado");
    const prod = within(seccion).getByRole("article", { name: "Producción de la arenera" });
    expect(await within(prod).findByText("Error · 1 con existencia negativa")).toBeInTheDocument();
    expect(within(prod).getByText("Advertencia · 1 queda poco")).toBeInTheDocument();
  });

  test("quien no opera la arenera no ve la tarjeta de producción ni pide existencias", async () => {
    montar({ sesion: sesionDe("rita") });
    const seccion = await bloque("Lo que hay cargado");
    await within(seccion).findByText("Lista Julio");
    expect(within(seccion).queryByRole("article", { name: "Producción de la arenera" })).toBeNull();
    expect(pedidas(RUTA_ARENERA)).toBe(0);
  });

  test("con la especialidad de producción apagada no se ve la tarjeta de producción ni se pide", async () => {
    apagados = ["produccion"];
    montar();
    const seccion = await bloque("Lo que hay cargado");
    await within(seccion).findByText("Lista Julio");
    await waitFor(() => expect(within(seccion).queryByRole("article", { name: "Producción de la arenera" })).toBeNull());
  });

  test("quien administra y no lee obras no pide cartera, auditorías ni catálogo, pero ve lista de precios, producción y herramientas", async () => {
    montar({ sesion: sesionDe("admin") });
    const seccion = await bloque("Lo que hay cargado");
    expect(await within(seccion).findByRole("article", { name: "Lista de precios vigente" })).toBeInTheDocument();
    expect(within(seccion).getByRole("article", { name: "Producción de la arenera" })).toBeInTheDocument();
    expect(within(seccion).queryByRole("article", { name: "Libros auditados" })).toBeNull();
    expect(within(seccion).queryByRole("article", { name: "Partidas del catálogo" })).toBeNull();
    expect(pedidas(RUTA_CARTERA)).toBe(0);
    expect(pedidas(RUTA_AUDITORIAS)).toBe(0);
    expect(pedidas(RUTA_PARTIDAS)).toBe(0);
    expect(pedidas(RUTA_INSUMOS)).toBe(0);
    expect(await bloque("Herramientas de la empresa")).toBeInTheDocument();
  });
});

describe("Inicio › Resumen: sin obras y aislamiento de errores", () => {
  test("sin obras: quien revisa ve el vacío informativo y quien arma ve «Crear la primera obra»", async () => {
    cartera = () => json(SIN_OBRAS);
    pendientes = lista();
    const revisa = montar({ sesion: sesionDe("rita") });
    expect(await screen.findByRole("heading", { level: 1, name: "Sin obras en la cartera" })).toBeInTheDocument();
    const bRevisa = await bloque("La cartera de obras");
    expect(await within(bRevisa).findByText("No hay obras que su cuenta pueda ver")).toBeInTheDocument();
    expect(within(bRevisa).queryByRole("button", { name: "Crear la primera obra" })).toBeNull();
    revisa.unmount();

    montar();
    const bArma = await bloque("La cartera de obras");
    const boton = await within(bArma).findByRole("button", { name: "Crear la primera obra" });
    expect(boton).toHaveClass("cds--btn--primary");
  });

  test("un bloque o tarjeta que responde 500 muestra su error y no tumba a los demás", async () => {
    cartera = () => json({ detalle: "La base de la carpeta no responde. Intente de nuevo." }, 500);
    auditorias = () => json({ detalle: "El historial no respondió. Intente de nuevo." }, 500);
    montar();

    const bCartera = await bloque("La cartera de obras");
    expect(await within(bCartera).findByRole("alert")).toHaveTextContent("La base de la carpeta no responde. Intente de nuevo.");

    const bCargado = await bloque("Lo que hay cargado");
    const libros = within(bCargado).getByRole("article", { name: "Libros auditados" });
    expect(await within(libros).findByRole("alert")).toHaveTextContent("El historial no respondió. Intente de nuevo.");
    expect(await within(bCargado).findByText("Lista Julio")).toBeInTheDocument();

    const bProblemas = await bloque("Problemas abiertos por obra");
    // Hay más de una obra con un problema que bloquea: basta con que el bloque siga en pie con sus cifras.
    expect((await within(bProblemas).findAllByText("1 bloquea")).length).toBeGreaterThan(0);
  });
});

describe("Inicio: rutas y «Empiece aquí»", () => {
  test.each(["/", "/inicio", "/inicio/no-existe", "/no-existe", "/pendientes"])("%s acaba en #/inicio/general", async (de) => {
    montar({ en: de });
    await bloque("La cartera de obras");
    expect(ruta()).toBe("/inicio/general");
  });

  test("la pestaña «Pendientes» abre la bandeja y el título de la ventana en Inicio es «Vista general · Sílice»", async () => {
    const u = userEvent.setup();
    montar();
    await bloque("La cartera de obras");
    await waitFor(() => expect(document.title).toBe("Vista general · Sílice"));
    await u.click(within(screen.getByRole("navigation", { name: "Inicio" })).getByRole("link", { name: "Pendientes" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Pendientes" })).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
  });

  test("«Empiece aquí» aparece sin obras para quien arma y con una sola cuenta activa para quien administra", async () => {
    cartera = () => json(SIN_OBRAS);
    pendientes = lista();
    const arma = montar();
    const bArma = await bloque("Empiece aquí");
    expect(within(bArma).getAllByRole("listitem")).toHaveLength(3);
    arma.unmount();

    montar({ sesion: sesionDe("admin") });
    const bAdmin = await bloque("Empiece aquí");
    expect(within(bAdmin).getAllByRole("listitem")).toHaveLength(2);
  });

  // Restauradas tras C8: el bloque sigue en Inicio y estas reglas lo vigilan (ancla nueva: «Lo que hay cargado»).
  test("con otra cuenta activa ya no aparece", async () => {
    cuentas = () => json({ cuentas: [CUENTA_ADMIN, CUENTA_ANA], aviso_arma_y_revisa: "" });
    montar({ sesion: sesionDe("admin") });
    await bloque("Lo que hay cargado");
    await waitFor(() => expect(pedidas(RUTA_CUENTAS)).toBe(1));
    await new Promise((r) => setTimeout(r, 30));
    expect(screen.queryByRole("region", { name: "Empiece aquí" })).toBeNull();
  });

  test("una cuenta desactivada no cuenta: con el administrador y una desactivada sigue apareciendo", async () => {
    cuentas = () => json({ cuentas: [CUENTA_ADMIN, { ...CUENTA_ANA, activa: false }], aviso_arma_y_revisa: "" });
    montar({ sesion: sesionDe("admin") });
    expect(await bloque("Empiece aquí")).toBeInTheDocument();
  });

  test("si la lista de cuentas falla, no se inventa nada: no aparece", async () => {
    cuentas = () => json({ detalle: "La base no responde." }, 503);
    montar({ sesion: sesionDe("admin") });
    await bloque("Lo que hay cargado");
    await waitFor(() => expect(pedidas(RUTA_CUENTAS)).toBe(1));
    await new Promise((r) => setTimeout(r, 30));
    expect(screen.queryByRole("region", { name: "Empiece aquí" })).toBeNull();
  });
});

describe("Últimas auditorías: sin permiso dice a quién pedirlo", () => {
  test("un 403 nombra los papeles que ven las auditorías guardadas", () => {
    render(<UltimasAuditorias carga={{ estado: "sin_permiso", error: null }} desde="vista-general" />);
    expect(screen.getByText("Sin historial de auditorías para su cuenta")).toBeInTheDocument();
  });
});
