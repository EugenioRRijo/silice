// Vigila lo que jsdom no dibuja: reglas de CSS que, si se pierden, rompen la pantalla sin que ninguna otra prueba
// lo note (los halos tapados por el lienzo, la franja que crece, el triangulo amarillo ilegible). Compila el SCSS
// real y lee las reglas.
import { fileURLToPath } from "node:url";
import * as sass from "sass";
import { describe, expect, test } from "vitest";

const compilar = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;
const css = compilar("./visor.scss") + compilar("../indicadores/indicadores.scss");

// Cuerpo de la regla cuyo selector es exactamente `selector`.
function regla(selector: string): string {
  const escapado = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|\\})\\s*${escapado}\\s*\\{([^}]*)\\}`, "m").exec(css);
  if (!m) throw new Error(`No hay una regla para ${selector}`);
  return m[1];
}

// El lienzo de Univer (su capa de contenido) tiene z-index 8; verificado en el navegador (tarea 2.4b).
const Z_INDEX_LIENZO_DE_UNIVER = 8;
// Los menus y popups de Univer y de Carbon empiezan en 1000.
const Z_INDEX_DE_LOS_POPUPS = 1000;

describe("estilos del visor", () => {
  test("la capa de halos queda por encima del lienzo de Univer y por debajo de los popups", () => {
    const z = Number(/z-index:\s*(\d+)/.exec(regla(".capa-halos"))?.[1]);
    expect(z).toBeGreaterThan(Z_INDEX_LIENZO_DE_UNIVER);
    expect(z).toBeLessThan(Z_INDEX_DE_LOS_POPUPS);
  });

  test("el lienzo de Univer es un solo plano apilado (isolation), para que la capa de halos lo compare entero", () => {
    expect(regla(".hoja-lienzo")).toMatch(/isolation:\s*isolate/);
  });

  test("la capa de halos no recibe el puntero (la hoja sigue siendo clicable) y recorta a su zona", () => {
    expect(regla(".capa-halos")).toMatch(/pointer-events:\s*none/);
    expect(regla(".capa-halos")).toMatch(/overflow:\s*hidden/);
  });

  test("la franja de indicadores mide 64 px, no envuelve y no crece", () => {
    const franja = regla(".franja-indicadores");
    expect(franja).toMatch(/block-size:\s*4rem/);
    expect(franja).toMatch(/flex-wrap:\s*nowrap/);
    // Dentro de la columna de la pantalla no debe encogerse (la franja se comia sus 64 px).
    expect(franja).toMatch(/flex:\s*none/);
  });

  test("nada de la franja recorta: el tooltip de las cifras exactas se abre por debajo de ella (B1)", () => {
    for (const selector of [".franja-indicadores", ".franja-indicadores__lista", ".fiori-kpi", ".visor"]) {
      expect(regla(selector), selector).not.toMatch(/overflow(-x|-y)?:\s*(hidden|clip|auto|scroll)/);
    }
  });

  test("el contenedor del tooltip tampoco recorta, aunque comparta la clase de los textos con elipsis", () => {
    expect(regla(".fiori-kpi__tooltip")).toMatch(/overflow:\s*visible/);
  });

  test("el valor con cifras exactas no se pinta como boton nativo y senala que revela algo (B2)", () => {
    const valor = regla(".fiori-kpi__valor");
    expect(valor).toMatch(/appearance:\s*none/);
    expect(valor).toMatch(/background:\s*transparent/);
    expect(valor).toMatch(/border:\s*0/);
    expect(valor).toMatch(/padding:\s*0/);
    expect(valor).toMatch(/margin:\s*0/);
    expect(valor).toMatch(/font:\s*inherit/);
    expect(valor).toMatch(/color:\s*inherit/);
    expect(valor).toMatch(/text-align:\s*start/);
    expect(valor).toMatch(/text-decoration:\s*underline dotted/);
    expect(valor).toMatch(/cursor:\s*help/);
    const foco = regla(".fiori-kpi__valor:focus-visible");
    expect(foco).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    expect(foco).toMatch(/outline-offset:\s*2px/);
  });

  test("los indicadores recortan con elipsis cada texto", () => {
    expect(regla(".fiori-kpi")).toMatch(/min-inline-size:\s*0/);
    const textos = regla(".fiori-kpi__titulo,\n.fiori-kpi__meta,\n.fiori-kpi__actual,\n.fiori-kpi__delta");
    expect(textos).toMatch(/text-overflow:\s*ellipsis/);
  });

  test("la barra de fecha y archivo es una sola de 48 px", () => {
    const barra = regla(".visor__barra");
    expect(barra).toMatch(/block-size:\s*3rem/);
    expect(barra).toMatch(/flex-wrap:\s*nowrap/);
    expect(barra).toMatch(/align-items:\s*center/);
  });

  test("solo el cuerpo de la lista desplaza: el encabezado y los filtros quedan fijos", () => {
    expect(regla(".visor__lista")).toMatch(/overflow:\s*hidden/);
    expect(regla(".lista-hallazgos__cuerpo")).toMatch(/overflow-y:\s*auto/);
    expect(regla(".lista-hallazgos__cabecera")).toMatch(/flex:\s*none/);
  });

  test("el halo amarillo lleva un segundo contorno oscuro de 1 px (m1)", () => {
    const r = regla(".halo--advertencia");
    expect(r).toMatch(/box-shadow:\s*inset 0 0 0 3px var\(--cds-text-primary\)/);
    expect(regla(".halo--advertencia.halo--elegido")).toMatch(/box-shadow:\s*inset 0 0 0 4px var\(--cds-text-primary\)/);
  });

  test("la descripcion de la lista se recorta a 3 lineas y solo la fila elegida la muestra completa (M5)", () => {
    expect(regla(".hallazgo__descripcion")).toMatch(/-webkit-line-clamp:\s*3/);
    expect(regla(".lista-hallazgos__fila--elegida .hallazgo__descripcion")).toMatch(/-webkit-line-clamp:\s*unset/);
  });

  test("las pestanas con conteo, el cargando y la ranura de la cabecera tienen estilo (M2, m4, M3)", () => {
    expect(regla(".pestana__conteo")).toMatch(/display:\s*inline-flex/);
    expect(regla(".visor__esqueleto-lienzo")).toMatch(/background:\s*var\(--cds-skeleton-background\)/);
    expect(regla(".silice-cabecera__libro")).toMatch(/flex:\s*1 1 0/);
  });

  test("el signo del triangulo amarillo va con la tinta principal", () => {
    const r = regla('.icono-sev[data-icono=WarningAltFilled] [data-icon-path=inner-path]');
    expect(r).toMatch(/fill:\s*var\(--cds-text-primary\)/);
    expect(r).toMatch(/opacity:\s*1/);
  });
});

// Contraste WCAG 2.1 entre dos colores #rrggbb.
function luminancia(hex: string): number {
  const canales = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2];
}
function contraste(a: string, b: string): number {
  const [claro, oscuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (oscuro + 0.05);
}

describe("contraste del triangulo amarillo (DESIGN.md)", () => {
  // yellow-30 de Carbon (#f1c21b) y gray-100 (#161616), los valores que fija DESIGN.md.
  test("el signo oscuro sobre el amarillo pasa 4,5:1 y el amarillo solo sobre blanco no pasa ni 3:1", () => {
    expect(contraste("#161616", "#f1c21b")).toBeGreaterThan(4.5);
    expect(contraste("#f1c21b", "#ffffff")).toBeLessThan(3);
    expect(contraste("#f1c21b", "#f4f4f4")).toBeLessThan(3);
  });
});
