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

// F6, T8: la Vista general (`#/inicio/general`), dentro del marco de verdad y con la API de mentira. Las respuestas
// tienen la forma de `GET /v1/obras/resumen/todas` (T7) y de `GET /v1/obras/pendientes/todas`; la interfaz solo las
// formatea. Oráculos escritos a mano: obras, carpetas y cifras ficticias, y los textos que fijan el plan y el diseño visual.

const RUTA_CARTERA = "/v1/obras/resumen/todas";
const RUTA_PENDIENTES = "/v1/obras/pendientes/todas";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";
const RUTA_ARENERA = "/v1/produccion/existencias";
const SUR = "Carpeta Sur.db";

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

// Una cartera con las dos monedas. Los montos llegan como texto, y uno llega sin el cero final: la pantalla los lee
// en centésimas y no recalcula nada (la suma de Bs con USD sería 429.637,10: no debe aparecer jamás).
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
  por_moneda: [DOS_MONEDAS.por_moneda[0]],
  obras: DOS_MONEDAS.obras.slice(0, 2),
};
const SIN_OBRAS = { hoy: "2026-11-05", por_moneda: [], obras: [], carpetas_omitidas: 0 };

const AUDITORIA = { id: 1, archivo: "presupuesto-1.xlsx", fecha: "2026-10-18T14:32:00", tipo: "libro", errores: 2, advertencias: 5 };

let servidor: ReturnType<typeof servidorFalso>;
let cartera: Respondedor;
let pendientes: Respondedor;
let auditorias: Respondedor;
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
    if (ruta === RUTA_ARENERA) return json([]);
    if (ruta === "/v1/modulos") {
      const claves = ["produccion", "vial", "riesgo", "edificacion"];
      return json({ modulos: claves.map((clave) => ({ clave, nombre: clave, activo: !apagados.includes(clave), cambiado_por: null, cambiado_el: null })) });
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

// El registro de pantallas ligeras, pero con la Vista general de verdad: la que `shell/rutas.ts` registra como «inicio».
function conVistaGeneral(): PaginaDef[] {
  const real = PAGINAS.find((p) => p.id === "inicio");
  if (!real) throw new Error("Falta la pantalla «inicio» (la Vista general) en el registro de shell/rutas.ts.");
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

describe("Vista general: el orden de los bloques", () => {
  test("lo que bloquea va primero, después la cartera, el avance, las auditorías y la arenera", async () => {
    montar();
    await bloque("Cartera por moneda");
    await screen.findByText("presupuesto-1.xlsx");
    await bloque("Arenera: lo que requiere atención");
    const titulos = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    const propios = titulos.filter((t) =>
      ["Lo que requiere atención", "Cartera por moneda", "Obras y avance contra el plan", "Últimas auditorías", "Arenera: lo que requiere atención"].includes(t ?? ""),
    );
    expect(propios).toEqual([
      "Lo que requiere atención",
      "Cartera por moneda",
      "Obras y avance contra el plan",
      "Últimas auditorías",
      "Arenera: lo que requiere atención",
    ]);
  });

  test("un solo h1 «Vista general», y la barra del espacio ofrece Vista general (actual) y Pendientes", async () => {
    montar();
    await bloque("Cartera por moneda");
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1).toHaveLength(1);
    expect(h1[0]).toHaveTextContent("Vista general");
    expect(h1[0]).toHaveClass("cds--type-heading-04");
    const barra = screen.getByRole("navigation", { name: "Inicio" });
    expect(within(barra).getByRole("link", { name: "Vista general" })).toHaveAttribute("aria-current", "page");
    expect(within(barra).getByRole("link", { name: "Pendientes" })).not.toHaveAttribute("aria-current");
  });
});

describe("Vista general: lo que bloquea", () => {
  test("cada pendiente dice su urgencia con palabras, su obra y el paso que lleva a hacerlo", async () => {
    montar();
    const b = await bloque("Lo que requiere atención");
    await within(b).findByText("Falta pedir el cemento");
    expect(within(b).getByText("2 bloquean · 1 aviso")).toBeInTheDocument();
    expect(within(b).getAllByText("Bloquea")).toHaveLength(2);
    expect(within(b).getAllByText("Aviso")).toHaveLength(1);
    expect(within(b).getByText("Casa Demo")).toBeInTheDocument();
    expect(within(b).getByRole("link", { name: "Abrir el presupuesto" })).toHaveAttribute("href", "/obra/empresa/7/presupuesto");
    // Una acción de otra carpeta lleva a la obra de esa carpeta.
    expect(within(b).getByRole("link", { name: "Hacer una versión nueva" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/presupuesto");
    expect(within(b).getByRole("link", { name: "Actualizar precios" })).toHaveAttribute("href", "/obra/empresa/8/mercado/actualizar");
  });

  test("solo los primeros cinco; el pie lleva a la bandeja con el total", async () => {
    const seis = [CEMENTO, DEVUELTA, { ...CEMENTO, texto: "Falta pedir la cabilla" }, PRECIOS, { ...PRECIOS, texto: "Faltan 2 cotizaciones" }, { ...PRECIOS, texto: "Revisar el flete" }];
    pendientes = lista(...seis);
    montar();
    const b = await bloque("Lo que requiere atención");
    await within(b).findByText("Falta pedir el cemento");
    expect(within(b).queryByText("Revisar el flete")).toBeNull();
    expect(within(b).getByText("Faltan 2 cotizaciones")).toBeInTheDocument();
    expect(within(b).getByRole("link", { name: "Ir a la bandeja de pendientes (6)" })).toHaveAttribute("href", "/inicio/pendientes");
  });

  test("sin pendientes dice, en una línea, que no hay nada por hacer", async () => {
    pendientes = lista();
    montar();
    const b = await bloque("Lo que requiere atención");
    expect(await within(b).findByText("No tiene pendientes por hacer.")).toBeInTheDocument();
    expect(within(b).queryByRole("link", { name: /bandeja/ })).toBeNull();
  });
});

describe("Vista general: la cartera por moneda, sin recalcular y sin mezclar", () => {
  test("cada cifra sale de la respuesta tal cual: «334570.5» se ve como 334.570,50", async () => {
    montar();
    const bs = await bloque("Cartera en Bs");
    expect(within(bs).getByText("Obras en Bs")).toBeInTheDocument();
    expect(within(bs).getByText("334.570,50 Bs")).toBeInTheDocument();
    expect(within(bs).getByText("2")).toBeInTheDocument(); // obras
    expect(within(bs).getByText("1")).toBeInTheDocument(); // en ejecución
    const usd = await bloque("Cartera en USD");
    expect(within(usd).getByText("Obras en USD")).toBeInTheDocument();
    expect(within(usd).getByText("95.066,60 USD")).toBeInTheDocument();
  });

  test("con dos monedas no aparece ninguna suma de Bs con USD, ni una moneda dentro de la otra", async () => {
    montar();
    const bs = await bloque("Cartera en Bs");
    const usd = await bloque("Cartera en USD");
    // 334.570,50 + 95.066,60 = 429.637,10: esa cifra no existe en ninguna parte.
    expect(document.body.textContent).not.toContain("429.637");
    expect(document.body.textContent).not.toContain("429637");
    expect(bs.textContent).not.toContain("USD");
    expect(usd.textContent).not.toContain("Bs");
    // Y no hay una tarjeta «Total» que mezcle las dos.
    expect(screen.queryByRole("region", { name: /^Cartera en (?!Bs$|USD$)/ })).toBeNull();
  });

  test("con una sola moneda se pinta solo esa: ni tarjeta vacía ni ceros para la otra", async () => {
    cartera = () => json(SOLO_BS);
    montar();
    await bloque("Cartera en Bs");
    expect(screen.queryByRole("region", { name: "Cartera en USD" })).toBeNull();
    expect(document.body.textContent).not.toContain("0,00");
  });

  test("carpetas_omitidas > 0 se le dice a la persona en español llano", async () => {
    cartera = () => json({ ...DOS_MONEDAS, carpetas_omitidas: 2 });
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("No se pudieron leer 2 carpetas; sus obras no aparecen en la cartera.")).toBeInTheDocument();
  });

  test("una carpeta omitida se dice en singular", async () => {
    cartera = () => json({ ...DOS_MONEDAS, carpetas_omitidas: 1 });
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("No se pudo leer 1 carpeta; sus obras no aparecen en la cartera.")).toBeInTheDocument();
  });

  test("sin carpetas omitidas no hay aviso", async () => {
    montar();
    await bloque("Cartera en Bs");
    expect(screen.queryByText(/No se pudo(ieron)? leer/)).toBeNull();
  });
});

describe("Vista general: el avance ejecutado contra el plan, por obra", () => {
  const tabla = async () => within(await bloque("Obras y avance contra el plan"));

  test("cada obra dice su etapa, su total y el avance real contra el plan", async () => {
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa).toHaveTextContent("En ejecución");
    expect(casa).toHaveTextContent("334.570,50 Bs");
    expect(casa).toHaveTextContent("Real 62,5 % · Plan 70,0 %");
    const galpon = t.getByRole("link", { name: "Galpón Sur" }).closest("tr")!;
    expect(galpon).toHaveTextContent("Atrasada");
    expect(galpon).toHaveTextContent("95.066,60 USD");
    expect(galpon).toHaveTextContent("Real 10,0 % · Plan 25,5 %");
  });

  test("el texto de la etapa sale del servidor (etapa_texto), no de una tabla de la interfaz", async () => {
    const obras = DOS_MONEDAS.obras.map((o) => (o.obra_id === 7 ? { ...o, etapa_texto: "En ejecución desde octubre" } : o));
    cartera = () => json({ ...DOS_MONEDAS, obras });
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa).toHaveTextContent("En ejecución desde octubre");
  });

  test("la obra sin avance dice «Sin avance» y la sin versión, «Sin versión»", async () => {
    montar();
    const t = await tabla();
    const torre = (await t.findByRole("link", { name: "Torre B" })).closest("tr")!;
    expect(within(torre).getByText("Sin avance")).toBeInTheDocument();
    expect(within(torre).getByText("Sin versión")).toBeInTheDocument();
    expect(torre).not.toHaveTextContent("Real");
  });

  test("con avance, la barra IBCS dibuja el real relleno y el plan en contorno; sin avance no hay barra", async () => {
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa.querySelector(".fiori-kpi__barra-real")).toHaveStyle({ inlineSize: "62.5%" });
    expect(casa.querySelector(".fiori-kpi__barra-meta")).toHaveStyle({ inlineSize: "70%" });
    const torre = t.getByRole("link", { name: "Torre B" }).closest("tr")!;
    expect(torre.querySelector(".fiori-kpi__barra")).toBeNull();
  });

  // Pasada en el navegador (H5): con letra Muy grande el «%» caía solo en la línea siguiente. Entre la cifra y el «%» va un
  // espacio duro (U+00A0, como en `ObjetivoDeMercado`): se lee igual, «62,5 %», pero no se parte.
  test("el «%» no se separa de su cifra: espacio duro entre la cifra y el signo", async () => {
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa.querySelector(".silice-inicio__avance .silice-cifra")?.textContent).toBe("Real 62,5\u00a0% · Plan 70,0\u00a0%");
    expect(casa).toHaveTextContent("Real 62,5 % · Plan 70,0 %");
  });

  // Pasada en el navegador (H2): con letra Grande o Muy grande la tabla se desplazaba por dentro y escondía la columna de
  // avance, en una región que el teclado no podía enfocar. jsdom no dibuja: aquí se fija lo que sí se ve (la región
  // nombrada y enfocable, la etiqueta de cada celda) y, sobre el SCSS real compilado, la regla que apila las filas cuando
  // la caja no cabe, medida en rem (crece con la letra). Que la columna de avance quede a la vista solo se ve en el navegador.
  test("la tabla va en una región enfocable y con nombre, por si aun así hay que desplazarla", async () => {
    montar();
    const t = await tabla();
    const tablaDeObras = await t.findByRole("table", { name: "Obras de la cartera y su avance contra el plan" });
    const region = tablaDeObras.closest<HTMLElement>('[role="region"]');
    expect(region, "la tabla va dentro de una región").not.toBeNull();
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region).toHaveAccessibleName("Obras de la cartera y su avance contra el plan: desplazar horizontalmente");
    expect(region).toHaveClass("silice-tabla", "silice-inicio__obras");
  });

  test("cada celda lleva la etiqueta de su columna, para leerse apilada sin la cabecera", async () => {
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    const celdas = Array.from(casa.querySelectorAll("td")).map((c) => c.getAttribute("data-etiqueta"));
    expect(celdas).toEqual([null, "Estado", "Total", "Avance ejecutado vs. plan"]);
  });

  describe("la hoja de estilos de la tabla de obras", () => {
    // La ruta va en una variable: con el literal, Vite reescribe el `new URL` como recurso (como en `ApuEnPanel.test.tsx`).
    const ESTILOS = "./inicio.scss";
    const css = sass.compile(fileURLToPath(new URL(ESTILOS, import.meta.url))).css;
    // El texto de un bloque `{ ... }` que empieza en `inicio` (con las llaves anidadas).
    const bloqueDesde = (inicio: number): string => {
      const abre = css.indexOf("{", inicio);
      let nivel = 0;
      for (let i = abre; i < css.length; i++) {
        if (css[i] === "{") nivel++;
        if (css[i] === "}" && --nivel === 0) return css.slice(abre + 1, i);
      }
      return "";
    };

    test("la caja es un contenedor de ancho y no deja que Carbon desplace por su cuenta", () => {
      expect(css).toMatch(/\.silice-inicio__obras\s*\{[^}]*container-type:\s*inline-size/);
      expect(css).toMatch(/\.silice-inicio__obras\s+\.cds--data-table-content\s*\{[^}]*overflow-x:\s*visible/);
    });

    test("cuando la caja mide menos de unos rem, las filas se apilan; el umbral es en rem y no en px", () => {
      const i = css.search(/@container\s*\(max-inline-size:\s*[\d.]+rem\)/);
      expect(i, "falta un @container con max-inline-size en rem").toBeGreaterThanOrEqual(0);
      const apilada = bloqueDesde(i);
      expect(apilada).toMatch(/\.silice-inicio__obras[^{]*\btd\b[^{]*\{[^}]*display:\s*block/);
      expect(apilada).toMatch(/\.silice-inicio__obras[^{]*\btr\b/);
      expect(apilada).toMatch(/td\[data-etiqueta\]::before\s*\{[^}]*content:\s*attr\(data-etiqueta\)/);
      // La cabecera sigue para los lectores de pantalla: solo se saca de la vista.
      expect(apilada).toMatch(/thead\s*\{[^}]*clip-path:\s*inset\(50%\)/);
      expect(css).not.toMatch(/@container\s*\(max-(inline-size|width):\s*[\d.]+px/);
    });

    test("el ancho mínimo del avance baja de 10 rem y, apilado, es cero", () => {
      expect(css).toMatch(/\.silice-inicio__avance\s*\{[^}]*min-inline-size:\s*(?:[1-8](?:\.\d+)?|0\.\d+)rem/);
      const apilada = bloqueDesde(css.search(/@container\s*\(max-inline-size/));
      expect(apilada).toMatch(/\.silice-inicio__avance\s*\{[^}]*min-inline-size:\s*0/);
    });
  });

  test("el nombre de la obra lleva a su Resumen, en la carpeta de la obra", async () => {
    montar();
    const t = await tabla();
    expect(await t.findByRole("link", { name: "Galpón Sur" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/resumen");
    expect(t.getByRole("link", { name: "Casa Demo" })).toHaveAttribute("href", "/obra/empresa/7/resumen");
  });
});

describe("Vista general: sin auditorías guardadas", () => {
  // Pasada en el navegador (H7): decía «Suelte arriba el Excel…» y en la Vista general no hay nada arriba. Aquí remite a
  // Auditoría, con el enlace «Ir a Auditoría» que ya está debajo. En la propia Auditoría el texto de siempre no cambia
  // (`paginas/auditoria/Auditoria.test.tsx`).
  test("el vacío manda a Auditoría y no habla de soltar un Excel arriba", async () => {
    auditorias = () => json([]);
    montar();
    const b = await bloque("Últimas auditorías");
    expect(await within(b).findByText("Todavía no hay auditorías guardadas")).toBeInTheDocument();
    expect(b).not.toHaveTextContent(/arriba|suelte/i);
    expect(b).toHaveTextContent(/Auditoría/);
    expect(within(b).getByRole("link", { name: "Ir a Auditoría" })).toHaveAttribute("href", "/auditoria");
  });
});

describe("Vista general: sin obras", () => {
  test("quien revisa ve el estado vacío, sin crear nada", async () => {
    cartera = () => json(SIN_OBRAS);
    pendientes = lista();
    montar({ sesion: sesionDe("rita") });
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("No hay obras que su cuenta pueda ver")).toBeInTheDocument();
    // La Vista general reúne todas las carpetas que la cuenta puede ver: no habla de «esta carpeta».
    expect(b).not.toHaveTextContent("en esta carpeta");
    expect(within(b).getByText("Cuando haya una obra registrada en las carpetas a las que tiene acceso, aparecerá aquí.")).toBeInTheDocument();
    expect(within(b).queryByRole("button", { name: "Nueva obra" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Obras y avance contra el plan" })).toBeNull();
    expect(document.querySelector(".silice-vacio")).not.toBeNull();
  });

  test("quien arma ve cómo empezar y el botón «Nueva obra»", async () => {
    cartera = () => json(SIN_OBRAS);
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("Aún no hay obras")).toBeInTheDocument();
    expect(within(b).getByText("Cree la primera obra para armar su presupuesto y seguir su avance.")).toBeInTheDocument();
    expect(within(b).getByRole("button", { name: "Nueva obra" })).toBeInTheDocument();
  });
});

describe("Vista general: un bloque que falla no tumba a los demás", () => {
  test("la cartera con un 500 dice su error y los demás bloques se ven", async () => {
    cartera = () => json({ detalle: "La base de la carpeta no responde. Intente de nuevo." }, 500);
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByRole("alert")).toHaveTextContent("La base de la carpeta no responde. Intente de nuevo.");
    // Lo demás sigue en pie.
    const bloquea = await bloque("Lo que requiere atención");
    expect(await within(bloquea).findByText("Falta pedir el cemento")).toBeInTheDocument();
    expect(await screen.findByText("presupuesto-1.xlsx")).toBeInTheDocument();
    expect(await bloque("Arenera: lo que requiere atención")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Vista general" })).toBeInTheDocument();
  });

  test("los pendientes con un 500 dicen su error y la cartera se ve", async () => {
    pendientes = () => json({ detalle: "Sílice no respondió a tiempo. Intente de nuevo." }, 500);
    montar();
    const b = await bloque("Lo que requiere atención");
    expect(await within(b).findByRole("alert")).toHaveTextContent("Sílice no respondió a tiempo. Intente de nuevo.");
    expect(await bloque("Cartera en Bs")).toBeInTheDocument();
    // (la barra lateral también lista la obra: se mira la tabla de avance)
    expect(within(await bloque("Obras y avance contra el plan")).getByRole("link", { name: "Casa Demo" })).toBeInTheDocument();
  });

  test("las auditorías con un 500 dicen su error y la cartera y lo que bloquea se ven", async () => {
    auditorias = () => json({ detalle: "El historial no respondió. Intente de nuevo." }, 500);
    montar();
    expect(await screen.findByText("El historial no respondió. Intente de nuevo.")).toBeInTheDocument();
    expect(await bloque("Cartera en Bs")).toBeInTheDocument();
    expect(await within(await bloque("Lo que requiere atención")).findByText("Falta pedir el cemento")).toBeInTheDocument();
  });
});

describe("Vista general: la arenera y los permisos", () => {
  test("quien opera la arenera con su especialidad encendida ve la arenera", async () => {
    montar();
    expect(await bloque("Arenera: lo que requiere atención")).toBeInTheDocument();
    expect(pedidas(RUTA_ARENERA)).toBe(1);
  });

  test("quien no opera la arenera no la ve ni la pide", async () => {
    montar({ sesion: sesionDe("rita") });
    await bloque("Cartera por moneda");
    expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).toBeNull();
    expect(pedidas(RUTA_ARENERA)).toBe(0);
  });

  test("con la especialidad de producción apagada, la arenera no se ve ni se pide", async () => {
    apagados = ["produccion"];
    montar();
    await bloque("Cartera por moneda");
    // `GET /v1/modulos` llega después del primer dibujo: se espera a que la arenera desaparezca o nunca aparezca.
    await waitFor(() => expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).toBeNull());
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).toBeNull();
  });

  test("quien administra y no lee obras no recibe cartera ni auditorías (no se piden), pero sí la arenera", async () => {
    montar({ sesion: sesionDe("admin") });
    expect(await bloque("Arenera: lo que requiere atención")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Vista general" })).toBeInTheDocument();
    expect(pedidas(RUTA_CARTERA)).toBe(0);
    expect(pedidas(RUTA_AUDITORIAS)).toBe(0);
    expect(screen.queryByRole("region", { name: "Cartera por moneda" })).toBeNull();
  });
});

describe("Vista general: los pendientes se vuelven a pedir al volver", () => {
  test("al volver de una obra a la Vista general se piden otra vez y lo resuelto ya no está", async () => {
    const u = userEvent.setup();
    let actuales = [CEMENTO, PRECIOS];
    pendientes = () => json({ pendientes: actuales, carpetas_omitidas: 0 });
    montar({ ir: "/obra/empresa/7/presupuesto" });
    const antes = await bloque("Lo que requiere atención");
    await within(antes).findByText("Falta pedir el cemento");
    expect(pedidas(RUTA_PENDIENTES)).toBe(1);

    await u.click(screen.getByRole("button", { name: "Ir a /obra/empresa/7/presupuesto" }));
    await screen.findByRole("heading", { level: 1, name: "Presupuesto" }, { timeout: 3000 });
    // En la Hoja se resolvió lo del cemento.
    actuales = [PRECIOS];
    await u.click(within(screen.getByRole("banner")).getByRole("link", { name: "Sílice" }));

    const despues = await bloque("Lo que requiere atención");
    await within(despues).findByText("3 precios con más de 90 días");
    expect(ruta()).toBe("/inicio/general");
    expect(pedidas(RUTA_PENDIENTES)).toBe(2);
    expect(screen.queryByText("Falta pedir el cemento")).toBeNull();
  });

  test("al arrancar en «/» (que redirige a la Vista general) se piden una sola vez", async () => {
    montar({ en: "/" });
    const b = await bloque("Lo que requiere atención");
    await within(b).findByText("Falta pedir el cemento");
    await waitFor(() => expect(ruta()).toBe("/inicio/general"));
    expect(pedidas(RUTA_PENDIENTES)).toBe(1);
  });
});

describe("Inicio: las rutas", () => {
  const titulo = (nombre: string) => screen.findByRole("heading", { level: 1, name: nombre }, { timeout: 3000 });

  test.each(["/", "/inicio", "/inicio/no-existe", "/no-existe"])("%s acaba en #/inicio/general, la Vista general", async (de) => {
    montar({ en: de });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general");
  });

  test("#/pendientes redirige a #/inicio/pendientes y muestra la bandeja", async () => {
    montar({ en: "/pendientes" });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
  });

  test("#/pendientes?proyecto=OF-001 conserva la consulta", async () => {
    montar({ en: "/pendientes?proyecto=OF-001" });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes?proyecto=OF-001");
  });

  test("#/inicio/general?x=1 y #/inicio?x=1 conservan la consulta", async () => {
    montar({ en: "/inicio?x=1" });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general?x=1");
  });

  test("la pestaña «Pendientes» de la barra abre la bandeja, con su barra y su cabecera", async () => {
    const u = userEvent.setup();
    montar();
    await bloque("Cartera por moneda");
    await u.click(within(screen.getByRole("navigation", { name: "Inicio" })).getByRole("link", { name: "Pendientes" }));
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
    expect(screen.getByRole("region", { name: "Vista general" })).toBeInTheDocument(); // la cabecera del espacio
    expect(within(screen.getByRole("navigation", { name: "Inicio" })).getByRole("link", { name: "Pendientes" })).toHaveAttribute("aria-current", "page");
  });

  test("el título de la pestaña del navegador dice «Vista general · Sílice»", async () => {
    montar();
    await titulo("Vista general");
    await waitFor(() => expect(document.title).toBe("Vista general · Sílice"));
  });
});
