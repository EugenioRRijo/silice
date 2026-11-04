import { describe, expect, test } from "vitest";

// Prueba en vivo 2026-10-25: Componer mostraba «(UC-07, flujo 3a)». Los codigos del expediente (casos de uso,
// requisitos, secciones de la especificacion) son de quien construye Silice, no de quien lo usa: en las paginas solo
// pueden ir en comentarios. jsdom no recorre todas las pantallas en todos sus estados: se lee el fuente, sin
// comentarios. Los textos que llegan de la API los vigila `tests/unit/test_aplicacion_composicion.py`.
interface Fs {
  readdirSync(carpeta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const carpeta = `${nodo.cwd()}/src/paginas`;

const JERGA = /\b(?:UC|RF|RNF)[-‑]\d|spec\s*§/;

function sinComentarios(fuente: string): string {
  return fuente
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split(/\r?\n/)
    .map((linea) => linea.replace(/(^|[^:"'`])\/\/.*$/, "$1"))
    .join("\n");
}

const fuentes = fs
  .readdirSync(carpeta, { recursive: true })
  .map((r) => r.replaceAll("\\", "/"))
  .filter((r) => /\.tsx?$/.test(r) && !/\.test\.tsx?$/.test(r));

describe("sin jerga interna en las paginas", () => {
  test("el filtro de comentarios deja las cadenas y quita los comentarios", () => {
    expect(sinComentarios('// UC-10 comentario\nconst t = "Texto RF-33";')).toBe('\nconst t = "Texto RF-33";');
    expect(sinComentarios("{/* RNF-08 */}<p>Hola</p>")).toBe("{}<p>Hola</p>");
    expect(JERGA.test(sinComentarios('const t = "Partida nueva (UC-07, flujo 3a)";'))).toBe(true);
  });

  test("ninguna pagina tiene un codigo UC-, RF-, RNF- ni «spec §» fuera de un comentario", () => {
    expect(fuentes.length).toBeGreaterThan(50); // la guardia no recorre una lista vacia
    const conJerga = fuentes.filter((r) => JERGA.test(sinComentarios(fs.readFileSync(`${carpeta}/${r}`, "utf-8"))));
    expect(conJerga).toEqual([]);
  });
});

// Plan del rediseño del marco, Tarea 8: el marco habla con las palabras de quien usa Sílice (obra, sección, pendiente,
// empresa). Los textos del marco (marco/ y las piezas del armazón que monta) no dicen «módulo», «área», «página»,
// «carpeta de trabajo» ni «Streamlit». Los identificadores no llevan tilde («pagina», «area»): solo cuentan las palabras
// del español escrito, que son las que se ven.
const VISIBLE_CON_TILDE = /módulo|área|página|carpeta de trabajo|streamlit/i;
const raiz = `${nodo.cwd()}/src`;
const DEL_MARCO = [
  ...fs
    .readdirSync(`${raiz}/marco`, { recursive: true })
    .map((r) => `marco/${r.replaceAll("\\", "/")}`)
    .filter((r) => /\.tsx?$/.test(r) && !/\.test\.tsx?$/.test(r)),
  "shell/DialogoSalida.tsx",
  "shell/LimiteDeError.tsx",
  "shell/MarcaDemostracion.tsx",
  "shell/MenuCuenta.tsx",
  "shell/ColumnaRecorrido.tsx",
  "shell/PanelRecorrido.tsx",
  "shell/obras/DialogoNuevaObra.tsx",
  "shell/carpetas/MarcoDeDialogo.tsx",
  "comun/TamanoLetra.tsx",
];

describe("sin vocabulario interno en el marco", () => {
  test("la guardia detecta las palabras con y sin mayúscula y deja pasar los identificadores", () => {
    expect(VISIBLE_CON_TILDE.test('const t = "Recargue la página";')).toBe(true);
    expect(VISIBLE_CON_TILDE.test("<p>Áreas del Módulo</p>")).toBe(true);
    expect(VISIBLE_CON_TILDE.test('const t = "Ahora trabaja con la carpeta de trabajo";')).toBe(true);
    expect(VISIBLE_CON_TILDE.test("const pagina = paginaPorId(area);")).toBe(false);
  });

  test("ningún texto del marco dice «módulo», «área», «página», «carpeta de trabajo» ni «Streamlit»", () => {
    expect(DEL_MARCO.length).toBeGreaterThan(15); // la guardia no recorre una lista vacia
    const conJerga = DEL_MARCO.filter((r) => VISIBLE_CON_TILDE.test(sinComentarios(fs.readFileSync(`${raiz}/${r}`, "utf-8"))));
    expect(conJerga).toEqual([]);
  });
});

// Cierre de F4 (Tarea 14): las pantallas Elaborar (baja 19), Partidas similares (baja 20), el Histórico de precios suelto
// (Tarea 13) y la pestaña Trazabilidad (baja 24) ya no existen. Ningún texto visible de las páginas manda a ellas. El
// verbo («elabore el presupuesto») tampoco: era el nombre de la pantalla («Elaborar un presupuesto») y se confunde con ella.
const PANTALLA_RETIRADA = /página Elaborar|Siguiente paso: Elaborar|Elabore un presupuesto|«Partidas similares»|pestaña «Trazabilidad»/;

describe("sin pantallas retiradas en los textos de las páginas", () => {
  test("la guardia detecta los textos viejos y deja pasar los de hoy", () => {
    expect(PANTALLA_RETIRADA.test('const t = "Elabore un presupuesto en la página Elaborar y guárdelo";')).toBe(true);
    expect(PANTALLA_RETIRADA.test('const t = "Siguiente paso: Elaborar un presupuesto";')).toBe(true);
    expect(PANTALLA_RETIRADA.test('<Tab>Histórico de precios</Tab>')).toBe(false);
    expect(PANTALLA_RETIRADA.test('const t = "Partidas similares del catálogo";')).toBe(false);
  });

  test("ninguna página nombra Elaborar, «Partidas similares» ni la pestaña «Trazabilidad» fuera de un comentario", () => {
    expect(fuentes.length).toBeGreaterThan(50);
    const viejas = fuentes.filter((r) => PANTALLA_RETIRADA.test(sinComentarios(fs.readFileSync(`${carpeta}/${r}`, "utf-8"))));
    expect(viejas).toEqual([]);
  });
});
