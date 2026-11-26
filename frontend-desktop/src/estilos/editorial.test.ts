import { describe, expect, test } from "vitest";

interface LecturaFs {
  readFileSync(ruta: string, codificacion: string): string;
}

const proc = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(modulo: "node:fs"): LecturaFs };
  }
).process;

const leer = (relativa: string): string =>
  proc.getBuiltinModule("node:fs").readFileSync(`${proc.cwd()}/src/${relativa}`, "utf-8");

const sinComentarios = (scss: string): string =>
  scss.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

function bloquesConSelector(scss: string, patronSelector: RegExp): string[] {
  const limpio = sinComentarios(scss);
  const hallados: string[] = [];
  let pos = 0;
  while (pos < limpio.length) {
    const abre = limpio.indexOf("{", pos);
    if (abre < 0) break;
    const cabecera = limpio.slice(pos, abre).trim();
    let nivel = 1;
    let i = abre + 1;
    while (i < limpio.length && nivel > 0) {
      if (limpio[i] === "{") nivel++;
      else if (limpio[i] === "}") nivel--;
      i++;
    }
    const cuerpo = limpio.slice(abre + 1, i - 1);
    const selectorFinal = cabecera.split("}").pop()?.trim() ?? cabecera;
    if (patronSelector.test(selectorFinal)) {
      hallados.push(cuerpo);
    }
    pos = i;
  }
  return hallados;
}

const ALIAS_EDITORIAL: Record<string, string> = {
  "--silice-stone": "--silice-fondo",
  "--silice-surface": "--silice-hoja",
  "--silice-surface-muted": "--silice-alzado",
  "--silice-surface-warm": "--silice-alzado",
  "--silice-rail": "--silice-lateral",
  "--silice-rail-hover": "--silice-alzado",
  "--silice-rail-band": "--silice-alzado",
  "--silice-border": "--silice-linea",
  "--silice-border-strong": "--silice-borde-fuerte",
  "--silice-hairline": "--silice-linea",
  "--silice-charcoal": "--silice-marco",
  "--silice-charcoal-btn": "--silice-complementario",
  "--silice-charcoal-hover": "--silice-hover-tinta",
  "--silice-charcoal-deep": "--silice-carbon-profundo",
  "--silice-charcoal-ink": "--silice-tinta-sobre-acento",
  "--silice-gold": "--silice-acento",
  "--silice-gold-strong": "--silice-resaltador-borde",
  "--silice-gold-soft": "--silice-resaltador",
  "--silice-gold-ink": "--silice-gravedad-advertencia",
  "--silice-ink": "--silice-t1",
  "--silice-muted": "--silice-t2",
  "--silice-muted-soft": "--silice-t2",
  "--silice-ok": "--silice-gravedad-ok",
  "--silice-ok-ink": "--silice-gravedad-ok",
  "--silice-ok-bg": "--silice-gravedad-ok-fondo",
  "--silice-ok-border": "--silice-gravedad-ok-borde",
  "--silice-warn": "--silice-gravedad-advertencia",
  "--silice-warn-bg": "--silice-gravedad-advertencia-fondo",
  "--silice-warn-border": "--silice-gravedad-advertencia-borde",
  "--silice-err": "--silice-gravedad-error",
  "--silice-err-bg": "--silice-gravedad-error-fondo",
  "--silice-err-border": "--silice-gravedad-error-borde",
};

const escapar = (s: string): string => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function luminanciaRelativa(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const lineal = (c: number): number => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b);
}

function razonContraste(a: string, b: string): number {
  const la = luminanciaRelativa(a);
  const lb = luminanciaRelativa(b);
  const mayor = Math.max(la, lb);
  const menor = Math.min(la, lb);
  return (mayor + 0.05) / (menor + 0.05);
}

function parDeToken(fuenteTokens: string, nombre: string): [string, string] {
  const m = new RegExp(
    `${escapar(nombre)}:\\s*light-dark\\(\\s*(#[0-9a-fA-F]{6})\\s*,\\s*(#[0-9a-fA-F]{6})\\s*\\)`,
  ).exec(fuenteTokens);
  if (!m || !m[1] || !m[2]) {
    throw new Error(`Falta par light-dark hexadecimal para ${nombre} en tokens.scss`);
  }
  return [m[1], m[2]];
}

describe("compatibilidad de editorial.scss con el modo oscuro de Papel y resaltador", () => {
  test("editorial.scss no define colores fijos: cada --silice-* de color es var(--silice-…) o light-dark(…)", () => {
    const editorial = sinComentarios(leer("estilos/editorial.scss"));
    const tokens = sinComentarios(leer("estilos/tokens.scss"));

    expect(editorial).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(editorial).not.toMatch(/\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\s*\(/i);

    const declaraciones = [...editorial.matchAll(/(--silice-[a-z0-9-]+)\s*:\s*([^;]+);/g)];
    const deColor = declaraciones.filter(([, nombre]) => !/^--silice-radio-(sm|md|lg)$/.test(nombre ?? ""));

    expect(deColor.length).toBe(Object.keys(ALIAS_EDITORIAL).length);

    for (const [, nombre, valorBruto] of deColor) {
      const valor = (valorBruto ?? "").trim();
      expect(valor, nombre).toMatch(/^(?:var\(--silice-[a-z0-9-]+\)|light-dark\(.+\))$/);
      const ref = /^var\((--silice-[a-z0-9-]+)\)$/.exec(valor)?.[1];
      if (ref) {
        expect(ref in ALIAS_EDITORIAL, `${nombre} no debe apuntar a otro alias viejo (${ref})`).toBe(false);
        expect(
          tokens,
          `${ref} debe existir como token primario en tokens.scss`,
        ).toMatch(new RegExp(`${escapar(ref)}:\\s*(?:light-dark\\(|#[0-9a-fA-F]{6}\\b)`));
      }
    }
  });

  test.each(Object.entries(ALIAS_EDITORIAL))("%s apunta al token nuevo %s", (viejo, nuevo) => {
    const editorial = sinComentarios(leer("estilos/editorial.scss"));
    expect(editorial).toMatch(new RegExp(`${escapar(viejo)}:\\s*var\\(${escapar(nuevo)}\\)\\s*;`));
  });

  test(".cds--g10 no fija --cds-* con colores sueltos", () => {
    const editorial = leer("estilos/editorial.scss");
    const bloquesG10 = bloquesConSelector(editorial, /(?:^|,)\s*\.cds--g10\b/);
    const tokens = sinComentarios(leer("estilos/tokens.scss"));

    for (const bloque of bloquesG10) {
      expect(bloque).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(bloque).not.toMatch(/\b(?:rgba?|hsla?|white|black)\b/i);

      const propiedades = [...bloque.matchAll(/([a-z0-9-]+)\s*:\s*([^;]+);/gi)];
      for (const [, prop, valorBruto] of propiedades) {
        const valor = (valorBruto ?? "").trim();
        const destino = /^var\((--silice-[a-z0-9-]+)\)$/.exec(valor)?.[1];
        expect(destino, `${prop} en .cds--g10 debe apuntar a var(--silice-*) de tokens.scss`).toBeDefined();
        expect(
          destino !== undefined && destino in ALIAS_EDITORIAL,
          `${prop} en .cds--g10 no debe apuntar al token viejo ${destino ?? ""}`,
        ).toBe(false);
        if (destino) {
          expect(tokens).toMatch(new RegExp(`${escapar(destino)}:\\s*(?:light-dark\\(|#[0-9a-fA-F]{6}\\b)`));
        }
      }
    }
  });
});

describe("contraste WCAG AA en claro y oscuro de los pares nuevos de tokens.scss", () => {
  test("las tintas de estado (ok, advertencia, error) alcanzan al menos 4,5:1 sobre hoja, fondo, alzado y su propio fondo", () => {
    const tokens = leer("estilos/tokens.scss");
    const hoja = parDeToken(tokens, "--silice-hoja");
    const fondo = parDeToken(tokens, "--silice-fondo");
    const alzado = parDeToken(tokens, "--silice-alzado");
    const t1 = parDeToken(tokens, "--silice-t1");

    const familias = [
      ["--silice-gravedad-ok", "--silice-gravedad-ok-fondo"],
      ["--silice-gravedad-advertencia", "--silice-gravedad-advertencia-fondo"],
      ["--silice-gravedad-error", "--silice-gravedad-error-fondo"],
    ] as const;

    for (const [tintaNombre, fondoEstadoNombre] of familias) {
      const tinta = parDeToken(tokens, tintaNombre);
      const fondoEstado = parDeToken(tokens, fondoEstadoNombre);
      for (const idx of [0, 1] as const) {
        const modo = idx === 0 ? "claro" : "oscuro";
        expect(razonContraste(tinta[idx], hoja[idx]), `${tintaNombre} sobre hoja (${modo})`).toBeGreaterThanOrEqual(4.5);
        expect(razonContraste(tinta[idx], fondo[idx]), `${tintaNombre} sobre fondo (${modo})`).toBeGreaterThanOrEqual(4.5);
        expect(razonContraste(tinta[idx], alzado[idx]), `${tintaNombre} sobre alzado (${modo})`).toBeGreaterThanOrEqual(4.5);
        expect(
          razonContraste(tinta[idx], fondoEstado[idx]),
          `${tintaNombre} sobre ${fondoEstadoNombre} (${modo})`,
        ).toBeGreaterThanOrEqual(4.5);
        expect(
          razonContraste(t1[idx], fondoEstado[idx]),
          `t1 sobre ${fondoEstadoNombre} (${modo})`,
        ).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  test("los bordes fuertes y de estado alcanzan al menos 3:1 y las tintas sobre acento o carbón profundo alcanzan 4,5:1", () => {
    const tokens = leer("estilos/tokens.scss");
    const hoja = parDeToken(tokens, "--silice-hoja");
    const fondo = parDeToken(tokens, "--silice-fondo");
    const alzado = parDeToken(tokens, "--silice-alzado");
    const marco = parDeToken(tokens, "--silice-marco");
    const bordeFuerte = parDeToken(tokens, "--silice-borde-fuerte");

    const bordesEstado = [
      ["--silice-gravedad-ok-borde", "--silice-gravedad-ok-fondo"],
      ["--silice-gravedad-advertencia-borde", "--silice-gravedad-advertencia-fondo"],
      ["--silice-gravedad-error-borde", "--silice-gravedad-error-fondo"],
    ] as const;

    for (const idx of [0, 1] as const) {
      const modo = idx === 0 ? "claro" : "oscuro";
      expect(razonContraste(bordeFuerte[idx], hoja[idx]), `borde-fuerte sobre hoja (${modo})`).toBeGreaterThanOrEqual(3);
      expect(razonContraste(bordeFuerte[idx], fondo[idx]), `borde-fuerte sobre fondo (${modo})`).toBeGreaterThanOrEqual(3);
      expect(razonContraste(bordeFuerte[idx], alzado[idx]), `borde-fuerte sobre alzado (${modo})`).toBeGreaterThanOrEqual(3);
      expect(razonContraste(bordeFuerte[idx], marco[idx]), `borde-fuerte sobre marco (${modo})`).toBeGreaterThanOrEqual(3);

      for (const [bordeNombre, fondoEstadoNombre] of bordesEstado) {
        const borde = parDeToken(tokens, bordeNombre);
        const fondoEstado = parDeToken(tokens, fondoEstadoNombre);
        expect(razonContraste(borde[idx], hoja[idx]), `${bordeNombre} sobre hoja (${modo})`).toBeGreaterThanOrEqual(3);
        expect(razonContraste(borde[idx], fondo[idx]), `${bordeNombre} sobre fondo (${modo})`).toBeGreaterThanOrEqual(3);
        expect(
          razonContraste(borde[idx], fondoEstado[idx]),
          `${bordeNombre} sobre ${fondoEstadoNombre} (${modo})`,
        ).toBeGreaterThanOrEqual(3);
      }
    }

    const acento = /--silice-acento:\s*(#[0-9a-fA-F]{6})/.exec(tokens)?.[1] ?? "";
    expect(acento).not.toBe("");
    const tintaSobreAcento = parDeToken(tokens, "--silice-tinta-sobre-acento");
    const carbonProfundo = parDeToken(tokens, "--silice-carbon-profundo");
    for (const idx of [0, 1] as const) {
      expect(razonContraste(tintaSobreAcento[idx], acento)).toBeGreaterThanOrEqual(4.5);
      expect(razonContraste("#FFFFFF", carbonProfundo[idx])).toBeGreaterThanOrEqual(4.5);
      expect(razonContraste(acento, carbonProfundo[idx])).toBeGreaterThanOrEqual(4.5);
    }
  });
});
