// @vitest-environment jsdom
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { compile, Logger } from "sass";

// Dirección de diseño «Instrumento de auditoría y control» (enmienda de DESIGN.md del 2026-11-22, aprobada por Eugenio):
// Atkinson Hyperlegible Next alojada (RNF-08), marco en azul petróleo, neutros del concreto, radio 0, sin sombras y
// movimiento que respeta prefers-reduced-motion. Estas guardias leen el código de estilos; no miran píxeles.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = nodo.cwd();
const leer = (ruta: string) => fs.readFileSync(`${raiz}/src/${ruta}`, "utf-8");

const luminancia = (hex: string) => {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
};
const contraste = (a: string, b: string) => {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x! + 0.05) / (y! + 0.05);
};
// Sin comentarios: los textos que explican («antes IBM Plex») no cuentan como código.
const sinComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

describe("tipografía: Atkinson Hyperlegible Next alojada en el propio servidor", () => {
  const fuentes = sinComentarios(leer("estilos/fuentes.scss"));

  test("fuentes.scss declara Atkinson Hyperlegible Next variable (200 a 800) desde el paquete de Fontsource", () => {
    expect(fuentes).toMatch(/font-family:\s*["']?Atkinson Hyperlegible Next["']?/);
    expect(fuentes).toMatch(/font-weight:\s*200 800/);
    expect(fuentes).toContain("@fontsource-variable/atkinson-hyperlegible-next/files/");
    expect(fuentes).toMatch(/latin-wght-normal\.woff2/);
    expect(fuentes).toMatch(/latin-ext-wght-normal\.woff2/);
    expect(fuentes).toMatch(/font-display:\s*swap/);
  });

  test("sin URLs externas (RNF-08) y sin IBM Plex ni cursiva en las fuentes propias", () => {
    expect(fuentes).not.toMatch(/https?:\/\//);
    expect(fuentes).not.toMatch(/\/\/fonts\./);
    expect(fuentes).not.toMatch(/IBM Plex|@ibm\/plex/i);
    expect(fuentes).not.toMatch(/font-style:\s*italic/);
  });

  test("package.json fija la fuente con versión exacta y retira los paquetes de IBM Plex", () => {
    const paquete = JSON.parse(fs.readFileSync(`${raiz}/package.json`, "utf-8")) as { dependencies: Record<string, string> };
    expect(paquete.dependencies["@fontsource-variable/atkinson-hyperlegible-next"]).toBe("5.3.0");
    expect(Object.keys(paquete.dependencies).filter((n) => n.startsWith("@ibm/plex"))).toEqual([]);
  });

  test("el CSS propio de los estilos base no nombra IBM Plex ni monoespaciadas", () => {
    for (const archivo of ["estilos/tokens.scss", "estilos/editorial.scss", "estilos/app.scss"]) {
      expect(sinComentarios(leer(archivo)), archivo).not.toMatch(/IBM Plex|monospace/);
    }
  });

  test(".silice-cifra y .silice-codigo llevan cifras tabulares", () => {
    const app = sinComentarios(leer("estilos/app.scss"));
    expect(app).toMatch(/\.silice-cifra\s*\{[^}]*font-variant-numeric:\s*tabular-nums/);
    expect(app).toMatch(/\.silice-codigo\s*\{[^}]*font-variant-numeric:\s*tabular-nums/);
  });
});

describe("tokens del instrumento de auditoría", () => {
  let css = "";
  beforeAll(() => {
    css = compile(`${raiz}/src/estilos/tokens.scss`, { quietDeps: true, logger: Logger.silent, loadPaths: [`${raiz}/node_modules`] }).css;
    const estilo = document.createElement("style");
    estilo.textContent = css;
    document.head.append(estilo);
    document.body.innerHTML = `<div class="cds--g10" id="tema"></div>`;
  }, 60_000);
  afterAll(() => {
    document.head.innerHTML = "";
    document.body.innerHTML = "";
  });
  const token = (nombre: string) => getComputedStyle(document.documentElement).getPropertyValue(nombre).trim().toLowerCase();

  test("el marco y la marca por omisión son petróleo y arena sílice", () => {
    expect(token("--silice-petroleo")).toBe("#15333a");
    expect(token("--silice-arena")).toBe("#d3c49a");
    expect(token("--silice-marco")).toBe("var(--silice-petroleo)");
    expect(token("--silice-acento")).toBe("var(--silice-arena)");
    expect(token("--silice-complementario")).toBe("var(--silice-marco)");
  });

  test("la familia de la interfaz es Atkinson y Carbon la toma en el tema", () => {
    expect(token("--silice-fuente")).toMatch(/^["']?atkinson hyperlegible next["']?,/);
    expect(css).toMatch(/font-family:\s*var\(--silice-fuente\)/);
  });

  test("los neutros y los semánticos de la propuesta están tal cual", () => {
    const esperado: Record<string, string> = {
      "--silice-tinta": "#1b2120",
      "--silice-grafito": "#4a5451",
      "--silice-gris-obra": "#5f6966",
      "--silice-borde-campo": "#7f8a86",
      "--silice-borde": "#c9d0cd",
      "--silice-hilo": "#dde2df",
      "--silice-lateral-base": "#e7ebe9",
      "--silice-concreto": "#f2f4f2",
      "--silice-seleccion": "#dde9e6",
      "--silice-real": "#3b4542",
      "--silice-ibcs-favorable-texto": "#198038",
      "--silice-ibcs-desfavorable": "#da1e28",
      "--silice-sev-critico": "#da1e28",
      "--silice-sev-error": "#eb6200",
      "--silice-atipico": "#8a3ffc",
    };
    for (const [nombre, valor] of Object.entries(esperado)) expect(token(nombre), nombre).toBe(valor);
  });

  test("contrastes AA de la propuesta", () => {
    expect(contraste("#ffffff", "#15333a")).toBeGreaterThanOrEqual(13);
    expect(contraste("#d3c49a", "#15333a")).toBeGreaterThanOrEqual(7.5);
    expect(contraste("#1b2120", "#ffffff")).toBeGreaterThanOrEqual(16);
    expect(contraste("#4a5451", "#e7ebe9")).toBeGreaterThanOrEqual(6.5);
    expect(contraste("#5f6966", "#e7ebe9")).toBeGreaterThanOrEqual(4.5);
    expect(contraste("#7f8a86", "#ffffff")).toBeGreaterThanOrEqual(3);
    expect(contraste("#198038", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contraste("#3b4542", "#ffffff")).toBeGreaterThanOrEqual(9);
  });

  test("el botón «Demostración» lee un texto oscuro (≥ 4,5:1) sobre el fondo de aviso", () => {
    // Fondo yellow-10 de Carbon (V-16) y tinta del proyecto.
    expect(contraste(token("--silice-tinta"), "#fcf4d6")).toBeGreaterThanOrEqual(4.5);
    const app = sinComentarios(leer("estilos/app.scss"));
    const regla = /\.silice-marco-barra \.silice-demo \.silice-demo__boton[^{]*\{([^}]*)\}/.exec(app)?.[1] ?? "";
    expect(regla).toMatch(/background(-color)?:\s*var\(--silice-aviso-fondo\)/);
    expect(regla).toMatch(/color:\s*var\(--silice-tinta\)/);
    for (const estado of [":hover", ":active", ":focus-visible", '[aria-expanded="true"]']) {
      expect(app, estado).toContain(`.silice-demo__boton${estado}`);
    }
  });

  test("las variables --silice-* que ya usan los demás archivos siguen existiendo", () => {
    for (const nombre of [
      "--silice-stone", "--silice-surface", "--silice-surface-muted", "--silice-surface-warm", "--silice-rail", "--silice-rail-hover",
      "--silice-rail-band", "--silice-border", "--silice-border-strong", "--silice-hairline", "--silice-charcoal", "--silice-charcoal-btn",
      "--silice-charcoal-hover", "--silice-charcoal-deep", "--silice-charcoal-ink", "--silice-gold", "--silice-gold-strong",
      "--silice-gold-soft", "--silice-gold-ink", "--silice-ink", "--silice-muted", "--silice-muted-soft", "--silice-ok", "--silice-ok-ink",
      "--silice-ok-bg", "--silice-ok-border", "--silice-warn", "--silice-warn-bg", "--silice-warn-border", "--silice-err",
      "--silice-err-bg", "--silice-err-border", "--silice-texto", "--silice-texto-secundario", "--silice-divisor", "--silice-fondo",
    ]) {
      expect(leer("estilos/editorial.scss") + leer("estilos/tokens.scss"), nombre).toContain(`${nombre}:`);
    }
  });
});

describe("forma y movimiento (editorial.scss y app.scss)", () => {
  const editorial = sinComentarios(leer("estilos/editorial.scss"));
  const app = sinComentarios(leer("estilos/app.scss"));

  test("radio 0: se retiran --silice-radio-sm/md/lg y no queda border-radius salvo el círculo y la píldora", () => {
    expect(editorial).not.toMatch(/--silice-radio-(sm|md|lg)\s*:/);
    for (const [nombre, texto] of [["editorial", editorial], ["app", app]] as const) {
      const radios = [...texto.matchAll(/border-radius:\s*([^;]+);/g)].map((m) => m[1]!.trim());
      expect(radios.filter((r) => !["0", "50%", "9999px", "0.625rem"].includes(r)), nombre).toEqual([]);
    }
  });

  test("sin sombras propias ni vidrio en estos estilos", () => {
    expect(editorial).not.toMatch(/box-shadow:\s*(?!none)/);
    expect(app).not.toMatch(/box-shadow:\s*(?!none)/);
    expect(editorial + app).not.toMatch(/backdrop-filter/);
  });

  test("editorial.scss ya no pisa el error, el foco ni lo deshabilitado de Carbon", () => {
    expect(editorial).not.toMatch(/\.cds--(text-input|password-input|select-input|text-area)/);
    expect(editorial).not.toMatch(/&:focus\b|:focus-visible/);
    expect(editorial).not.toMatch(/--invalid|--disabled|:disabled|\[disabled\]/);
    expect(editorial).not.toMatch(/\.cds--(inline-notification|tile)\b/);
  });

  test("las pantallas de trabajo no llevan el tope de 74 rem", () => {
    expect(editorial).not.toMatch(/74rem/);
  });

  test("ninguna transición usa «all» ni anima propiedades de maquetación", () => {
    for (const [nombre, texto] of [["editorial", editorial], ["app", app]] as const) {
      expect(texto, nombre).not.toMatch(/transition:\s*all\b/);
      expect(texto, nombre).not.toMatch(/transition[^;]*(inline-size|block-size|width|height|margin)/);
    }
  });

  test("prefers-reduced-motion deja los cambios de color y no quita todo con !important", () => {
    const bloque = /@media \(prefers-reduced-motion: reduce\)\s*\{([\s\S]*?)\n\}/.exec(app)?.[1] ?? "";
    expect(bloque).not.toMatch(/transition:\s*none\s*!important/);
    expect(bloque).toMatch(/animation-duration|animation:\s*none/);
    expect(bloque).toMatch(/scroll-behavior:\s*auto/);
  });

  test("la curva y las duraciones de movimiento son tokens", () => {
    const tokens = leer("estilos/tokens.scss");
    expect(tokens).toMatch(/--silice-curva:\s*cubic-bezier\(0\.16,\s*1,\s*0\.3,\s*1\)/);
    for (const [n, v] of [["respuesta", "120ms"], ["estado", "200ms"], ["panel", "320ms"], ["trazo", "560ms"]]) {
      expect(tokens).toMatch(new RegExp(`--silice-t-${n}:\\s*${v}`));
    }
  });
});
