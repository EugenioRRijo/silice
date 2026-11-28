import { describe, expect, test } from "vitest";

// Lote C0 de la cara «Papel y resaltador» (docs/especificaciones/2026-11-26-cara-papel-y-resaltador/README.md):
// tokens claro y oscuro con color-scheme y light-dark(), Carbon apuntando a ellos, y las letras nuevas empaquetadas.

interface Fs {
  readdirSync(carpeta: string, o: { withFileTypes: true }): { name: string; isDirectory(): boolean }[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src`;
const leer = (ruta: string) => fs.readFileSync(ruta, "utf-8");
const tokens = () => leer(`${raiz}/estilos/tokens.scss`);
const fuentes = () => leer(`${raiz}/estilos/fuentes.scss`);

function archivos(carpeta: string, ext: RegExp): string[] {
  return fs.readdirSync(carpeta, { withFileTypes: true }).flatMap((e) => {
    const ruta = `${carpeta}/${e.name}`;
    return e.isDirectory() ? archivos(ruta, ext) : ext.test(e.name) && !/\.test\./.test(e.name) ? [ruta] : [];
  });
}

// El par claro/oscuro de cada token, tal como lo fija la especificación.
const PARES: Record<string, [string, string]> = {
  "--silice-fondo": ["#F7F4EE", "#161513"],
  "--silice-hoja": ["#FDFBF7", "#1C1A18"],
  "--silice-alzado": ["#EFE9DF", "#262421"],
  "--silice-lateral": ["#EFE9DF", "#12110F"],
  "--silice-marco": ["#1F1B16", "#12110F"],
  "--silice-complementario": ["#1F1B16", "#EFE9DE"],
  "--silice-t1": ["#1F1B16", "#EFE9DE"],
  "--silice-t2": ["#5E554A", "#AAA398"],
  "--silice-t3": ["#9A9184", "#8A847A"],
  "--silice-resaltador": ["#FFF4C2", "#2E2919"],
  "--silice-gravedad-error": ["#B42318", "#F0857C"],
  "--silice-gravedad-advertencia": ["#8A5A00", "#DDB25E"],
  "--silice-gravedad-ok": ["#2F6B3F", "#7FBF8E"],
  "--silice-gravedad-ok-fondo": ["#EAF4EC", "#17261C"],
  "--silice-gravedad-ok-borde": ["#568A65", "#4D8B5E"],
  "--silice-gravedad-advertencia-fondo": ["#FDF3DC", "#2B2212"],
  "--silice-gravedad-advertencia-borde": ["#A67308", "#B08428"],
  "--silice-gravedad-error-fondo": ["#FDF0EE", "#2D1917"],
  "--silice-gravedad-error-borde": ["#C65347", "#C86057"],
  "--silice-borde-fuerte": ["#766D61", "#8A847A"],
  "--silice-carbon-profundo": ["#171410", "#0E0D0B"],
  "--silice-tinta-sobre-acento": ["#1F1B16", "#1F1B16"],
  "--silice-serie-1": ["#2A78D6", "#3987E5"],
  "--silice-serie-2": ["#1BAF7A", "#199E70"],
  "--silice-serie-3": ["#EB6834", "#D95926"],
};

const escapar = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

describe("tokens de la cara en claro y oscuro", () => {
  test("la raíz admite los dos esquemas", () => {
    expect(tokens()).toMatch(/:root\s*\{[^}]*color-scheme:\s*light dark/);
  });

  test.each(Object.entries(PARES))("%s lleva su par claro y oscuro con light-dark()", (nombre, [claro, oscuro]) => {
    const patron = new RegExp(`${escapar(nombre)}:\\s*light-dark\\(\\s*${claro}\\s*,\\s*${oscuro}\\s*\\)`, "i");
    expect(tokens()).toMatch(patron);
  });

  test("el amarillo de la marca y el borde del resaltador son los mismos en los dos modos", () => {
    expect(tokens()).toMatch(/--silice-acento:\s*#F6D55C/i);
    expect(tokens()).toMatch(/--silice-resaltador-borde:\s*#C9A227/i);
  });

  test("la elección de la persona fija el esquema sobre el del sistema", () => {
    expect(tokens()).toMatch(/:root\[data-modo="claro"\]\s*\{[^}]*color-scheme:\s*light\b/);
    expect(tokens()).toMatch(/:root\[data-modo="oscuro"\]\s*\{[^}]*color-scheme:\s*dark\b/);
  });

  test.each([
    ["--cds-background", "--silice-fondo"],
    ["--cds-layer-01", "--silice-hoja"],
    ["--cds-text-primary", "--silice-t1"],
    ["--cds-text-secondary", "--silice-t2"],
    ["--cds-focus", "--silice-foco"],
    ["--cds-button-primary", "--silice-complementario"],
  ])("Carbon lee %s de %s", (carbon, silice) => {
    expect(tokens()).toMatch(new RegExp(`${escapar(carbon)}:\\s*var\\(${escapar(silice)}\\)`));
  });
});

describe("letras de la cara", () => {
  test("Instrument Sans (400, 500, 600) y Newsreader (400) se sirven desde el propio paquete", () => {
    const f = fuentes();
    for (const peso of [400, 500, 600]) {
      expect(f).toMatch(new RegExp(`"Instrument Sans"[^;]*${peso}|cara\\("Instrument Sans"[^)]*${peso}`));
    }
    expect(f).toMatch(/"Newsreader"[^;]*400|cara\("Newsreader"[^)]*400/);
    expect(f).toMatch(/@fontsource\/instrument-sans/);
    expect(f).toMatch(/@fontsource\/newsreader/);
    expect(f).not.toMatch(/https?:\/\//);
  });

  test("ninguna hoja de estilos ni componente propio usa ya IBM Plex", () => {
    const malos = archivos(raiz, /\.(scss|tsx?)$/)
      .filter((f) => /IBM Plex/.test(leer(f)))
      .map((f) => f.slice(raiz.length));
    expect(malos).toEqual([]);
  });

  test("la interfaz hereda Instrument Sans desde el cuerpo", () => {
    expect(leer(`${raiz}/estilos/app.scss`)).toMatch(/body[^{]*\{[^}]*font-family:[^;]*"Instrument Sans"/);
  });

  test("las versiones de las letras están fijadas", () => {
    const pkg = JSON.parse(leer(`${nodo.cwd()}/package.json`)) as { dependencies: Record<string, string> };
    expect(pkg.dependencies["@fontsource/instrument-sans"]).toBe("5.3.0");
    expect(pkg.dependencies["@fontsource/newsreader"]).toBe("5.3.0");
  });
});

// WCAG 1.4.11: el anillo de foco llega a 3:1 sobre las superficies de la cara en los dos modos. El dorado del
// resaltador (#C9A227) da 2,0-2,3:1 sobre el papel claro: el foco tiene su propio token, más oscuro solo en claro.
describe("el foco del teclado se ve en claro y en oscuro", () => {
  const SUPERFICIES = ["--silice-fondo", "--silice-hoja", "--silice-alzado", "--silice-lateral", "--silice-resaltador"];
  const par = (token: string): [string, string] => {
    const m = new RegExp(`${escapar(token)}:\\s*light-dark\\((#[0-9a-fA-F]{6}),\\s*(#[0-9a-fA-F]{6})\\)`).exec(tokens());
    expect(m, `${token} no es un light-dark(#claro, #oscuro)`).not.toBeNull();
    return [m![1]!, m![2]!];
  };
  const lum = (hex: string) => {
    const c = [0, 1, 2].map((i) => parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0]! + 0.7152 * c[1]! + 0.0722 * c[2]!;
  };
  const contraste = (a: string, b: string) => {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x! + 0.05) / (y! + 0.05);
  };
  test.each(SUPERFICIES)("--silice-foco llega a 3:1 sobre %s en los dos modos", (superficie) => {
    const [focoClaro, focoOscuro] = par("--silice-foco");
    const [fondoClaro, fondoOscuro] = par(superficie);
    expect(contraste(focoClaro, fondoClaro)).toBeGreaterThanOrEqual(3);
    expect(contraste(focoOscuro, fondoOscuro)).toBeGreaterThanOrEqual(3);
  });
});

// Revisión visual en claro y oscuro (T3 del plan de cierre, 2026-11-28): Carbon trae grises y pasteles fijos para sus
// cabeceras de tabla, pestañas con fondo, filas elegidas, avisos y textos de ayuda. En oscuro daban texto claro sobre
// #e0e0e0 (1,1:1) o sobre un pastel (1,1:1). Cada uno sigue ahora a un token de la cara, que tiene su par claro y oscuro.
describe("Carbon no deja grises ni pasteles fijos en el modo oscuro", () => {
  test.each([
    ["--cds-layer-accent-01", "--silice-alzado"],
    ["--cds-layer-selected-01", "--silice-resaltador"],
    ["--cds-link-secondary", "--silice-complementario"],
    ["--cds-text-helper", "--silice-t2"],
    ["--cds-notification-background-error", "--silice-gravedad-error-fondo"],
    ["--cds-notification-background-success", "--silice-gravedad-ok-fondo"],
    ["--cds-notification-background-warning", "--silice-gravedad-advertencia-fondo"],
    ["--cds-notification-background-info", "--silice-gravedad-info-fondo"],
  ])("Carbon lee %s de %s", (carbon, silice) => {
    expect(tokens()).toMatch(new RegExp(`${escapar(carbon)}:\\s*var\\(${escapar(silice)}\\)`));
  });

  // En una capa de nivel dos (la Cuenta, los diálogos) Carbon lee el sufijo -02 y -03: sin ellos las cabeceras de tabla y las
  // pestañas con fondo de Cuentas y permisos, Empresa y Carpetas seguían en #e0e0e0.
  test.each(["--cds-layer-accent-02", "--cds-layer-accent-03", "--cds-layer-selected-02", "--cds-layer-selected-03"])(
    "%s también sigue a la cara (capas anidadas)",
    (carbon) => {
      expect(tokens()).toMatch(new RegExp(`${escapar(carbon)}:\\s*color-mix\\(in srgb, var\\(--silice-(alzado|resaltador)\\)`));
    },
  );

  test("el texto desactivado tiene su par claro y oscuro (el rgba(22,22,22,.25) de Carbon no se lee sobre el papel oscuro)", () => {
    expect(tokens()).toMatch(/--cds-text-disabled:\s*light-dark\(/);
  });

  test("el número del contador de la barra lateral es la tinta del texto, no el marco (que en oscuro es el color del lateral)", () => {
    expect(tokens()).toMatch(/--silice-contador-numero:\s*var\(--silice-t1\)/);
  });

  describe("contraste del texto sobre esas superficies (WCAG 1.4.3, 4,5:1)", () => {
    const par = (token: string): [string, string] => {
      const m = new RegExp(`${escapar(token)}:\\s*light-dark\\((#[0-9a-fA-F]{6}),\\s*(#[0-9a-fA-F]{6})\\)`).exec(tokens());
      expect(m, `${token} no es un light-dark(#claro, #oscuro)`).not.toBeNull();
      return [m![1]!, m![2]!];
    };
    const lum = (hex: string) => {
      const c = [0, 1, 2].map((i) => parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
      return 0.2126 * c[0]! + 0.7152 * c[1]! + 0.0722 * c[2]!;
    };
    const contraste = (a: string, b: string) => {
      const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
      return (x! + 0.05) / (y! + 0.05);
    };
    test.each([
      "--silice-gravedad-info-fondo",
      "--silice-gravedad-error-fondo",
      "--silice-gravedad-ok-fondo",
      "--silice-gravedad-advertencia-fondo",
      "--silice-alzado",
      "--silice-resaltador",
    ])("la tinta (--silice-t1) se lee sobre %s en claro y en oscuro", (fondo) => {
      const [t1Claro, t1Oscuro] = par("--silice-t1");
      const [fClaro, fOscuro] = par(fondo);
      expect(contraste(t1Claro, fClaro)).toBeGreaterThanOrEqual(4.5);
      expect(contraste(t1Oscuro, fOscuro)).toBeGreaterThanOrEqual(4.5);
    });

    test.each(["--silice-hoja", "--silice-alzado", "--silice-resaltador"])(
      "el texto de ayuda (--silice-t2) se lee sobre %s en claro y en oscuro",
      (fondo) => {
        const [t2Claro, t2Oscuro] = par("--silice-t2");
        const [fClaro, fOscuro] = par(fondo);
        expect(contraste(t2Claro, fClaro)).toBeGreaterThanOrEqual(4.5);
        expect(contraste(t2Oscuro, fOscuro)).toBeGreaterThanOrEqual(4.5);
      },
    );
  });
});
