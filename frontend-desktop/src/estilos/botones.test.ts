import { describe, expect, test } from "vitest";

const leerBotonesScss = (): string => {
  const proc = (
    globalThis as unknown as {
      process: { cwd(): string; getBuiltinModule(m: "node:fs"): { readFileSync(p: string, c: string): string } };
    }
  ).process;
  return proc.getBuiltinModule("node:fs").readFileSync(`${proc.cwd()}/src/estilos/botones.scss`, "utf-8");
};

describe("botones «contorno de papel» sobre Carbon (botones.scss)", () => {
  const scss = leerBotonesScss();

  test("aplica radio de 6 px, peso 500 y botón principal en tinta complementaria con hover y bajada de 1 px", () => {
    expect(scss).toMatch(/border-radius:\s*6px/);
    expect(scss).toMatch(/font-weight:\s*500/);
    expect(scss).toMatch(/\.cds--btn--primary[\s\S]*?background-color:\s*var\(--silice-complementario\)/);
    expect(scss).toMatch(/\.cds--btn--primary[\s\S]*?background-color:\s*var\(--silice-hover-tinta\)/);
    expect(scss).toMatch(/transform:\s*translateY\(1px\)/);
  });

  test("el secundario y el terciario de Carbon llevan trazo interior de 1,5 px en t1 y al pasar encima se rellenan", () => {
    expect(scss).toMatch(
      /\.cds--btn--secondary,\s*:root\s+\.cds--btn\.cds--btn--tertiary\s*\{[\s\S]*?background-color:\s*transparent/,
    );
    expect(scss).toMatch(/box-shadow:\s*inset 0 0 0 1\.5px var\(--silice-t1\)/);
    expect(scss).toMatch(
      /\.cds--btn--secondary[\s\S]*?&:hover[^{]*\{[\s\S]*?background-color:\s*var\(--silice-t1\);[\s\S]*?color:\s*var\(--silice-hoja\)/,
    );
  });

  test("el fantasma subraya con desfase de 4 px y los destructivos separan trazo de confirmación primaria", () => {
    expect(scss).toMatch(/\.cds--btn--ghost[\s\S]*?text-decoration:\s*underline/);
    expect(scss).toMatch(/\.cds--btn--ghost[\s\S]*?text-underline-offset:\s*4px/);
    expect(scss).toMatch(
      /\.cds--btn--danger--tertiary,\s*:root\s+\.cds--btn\.cds--btn--danger--ghost[\s\S]*?box-shadow:\s*inset 0 0 0 1\.5px var\(--silice-gravedad-error\)/,
    );
    expect(scss).toMatch(
      /\.cds--btn--danger,\s*:root\s+\.cds--btn\.cds--btn--danger--primary\s*\{[\s\S]*?background-color:\s*var\(--silice-gravedad-error\)/,
    );
  });

  test("el foco usa anillo dorado de 2 px con :focus-visible y quita el box-shadow de foco de Carbon", () => {
    expect(scss).toMatch(/:focus\s*\{[\s\S]*?box-shadow:\s*none/);
    expect(scss).toMatch(
      /:focus-visible\s*\{[\s\S]*?outline:\s*2px solid var\(--silice-foco\);[\s\S]*?outline-offset:\s*2px/,
    );
  });

  test("las alturas, rellenos horizontales y ancho mínimo van en rem y ningún font-size usa px ni pt", () => {
    expect(scss).toMatch(/min-inline-size:\s*4\.5rem/);
    expect(scss).toMatch(/\.cds--btn--sm\s*\{[\s\S]*?block-size:\s*1\.75rem;[\s\S]*?padding-inline:\s*0\.75rem/);
    expect(scss).toMatch(/\.cds--btn--md\s*\{[\s\S]*?block-size:\s*2rem;[\s\S]*?padding-inline:\s*0\.875rem/);
    expect(scss).toMatch(/\.cds--btn--xl[\s\S]*?block-size:\s*2\.5rem;[\s\S]*?padding-inline:\s*1\.125rem/);
    expect(scss).not.toMatch(/(?:^|[\s;{])(?:min-)?(?:height|block-size):\s*[\d.]+px/);
    expect(scss).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(scss).not.toMatch(/[^-]font:\s*[^;]*\d+px/);
  });

  test("la transición es solo de color y fondo (120 ms) y vive únicamente dentro de prefers-reduced-motion: no-preference", () => {
    const inicioMedia = scss.indexOf("@media (prefers-reduced-motion: no-preference)");
    expect(inicioMedia).toBeGreaterThan(-1);
    const antes = scss.slice(0, inicioMedia);
    // El lookahead va antes del espacio: con «\s*(?!none)» el motor podía no consumir el espacio y aceptar « none».
    expect(antes).not.toMatch(/transition:(?!\s*none\b)/);

    const bloqueMedia = scss.slice(inicioMedia);
    expect(bloqueMedia).toMatch(
      /transition:\s*background-color 120ms cubic-bezier\(\.22,\s*1,\s*\.36,\s*1\),\s*color 120ms cubic-bezier\(\.22,\s*1,\s*\.36,\s*1\)/,
    );
  });

  test("define la clase .silice-boton-nueva-obra con fondo acento, texto #1F1B16 y borde #C9A227", () => {
    expect(scss).toMatch(
      /\.silice-boton-nueva-obra[\s\S]*?background-color:\s*var\(--silice-acento\);[\s\S]*?color:\s*#1F1B16;[\s\S]*?border:\s*1px solid #C9A227/,
    );
  });
});
