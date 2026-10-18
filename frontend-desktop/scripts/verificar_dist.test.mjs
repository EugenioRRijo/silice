import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { LIMITE_BYTES, verificarDist } from "./verificar_dist.mjs";

let dir;

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "silice-dist-"));
});

afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe("verificarDist", () => {
  test("un anfitrion externo hace fallar", () => {
    writeFileSync(join(dir, "a.js"), 'fetch("https://cdn.example.com/x.woff2")');
    const { problemas } = verificarDist(dir);
    expect(problemas).toHaveLength(1);
    expect(problemas[0]).toContain("cdn.example.com");
  });

  test("http sin tls tambien hace fallar", () => {
    writeFileSync(join(dir, "a.css"), "@import url(http://fonts.example.org/x.css);");
    expect(verificarDist(dir).problemas).toHaveLength(1);
  });

  test("el espacio de nombres SVG de w3.org pasa", () => {
    writeFileSync(join(dir, "a.js"), 'const ns = "http://www.w3.org/2000/svg";');
    expect(verificarDist(dir).problemas).toEqual([]);
  });

  test("los enlaces de texto de error de React pasan", () => {
    writeFileSync(
      join(dir, "a.js"),
      'throw Error("ver https://react.dev/errors/418 y http://fb.me/use-check-prop-types")',
    );
    expect(verificarDist(dir).problemas).toEqual([]);
  });

  test("w3.org con otro subdominio no pasa", () => {
    writeFileSync(join(dir, "a.js"), 'const ns = "http://evil.w3.org.example.net/x";');
    expect(verificarDist(dir).problemas).toHaveLength(1);
  });

  test("los textos de Univer pasan solo dentro del archivo de Univer", () => {
    const texto = 'const ayuda = "https://support.google.com/docs/answer/1"; const e = `https://${x}`;';
    writeFileSync(join(dir, "adaptadorUniver-AbC123.js"), texto);
    expect(verificarDist(dir).problemas).toEqual([]);
    writeFileSync(join(dir, "index-AbC123.js"), 'const ayuda = "https://support.google.com/docs/answer/1";');
    const { problemas } = verificarDist(dir);
    expect(problemas).toHaveLength(1);
    expect(problemas[0]).toContain("support.google.com");
  });

  test("un anfitrion que no esta en la lista falla tambien dentro del archivo de Univer", () => {
    writeFileSync(join(dir, "adaptadorUniver-AbC123.js"), 'fetch("https://telemetria.example.net/e")');
    expect(verificarDist(dir).problemas).toHaveLength(1);
  });

  test("los textos del enrutador pasan solo dentro del bundle principal (index-*.js)", () => {
    const texto = 'throw Error("See https://reactrouter.com/en/main/routers/picking-a-router."); new URL(p, `http://localhost`);';
    writeFileSync(join(dir, "index-AbC123.js"), texto);
    expect(verificarDist(dir).problemas).toEqual([]);
    writeFileSync(join(dir, "otro-AbC123.js"), 'new URL(p, `http://localhost`);');
    const { problemas } = verificarDist(dir);
    expect(problemas).toHaveLength(1);
    expect(problemas[0]).toContain("localhost");
  });

  test("el bundle principal tampoco puede hablar con otro anfitrion", () => {
    writeFileSync(join(dir, "index-AbC123.js"), 'fetch("https://telemetria.example.net/e")');
    expect(verificarDist(dir).problemas).toHaveLength(1);
  });

  test("15 000 001 bytes hacen fallar", () => {
    writeFileSync(join(dir, "grande.bin"), Buffer.alloc(LIMITE_BYTES + 1));
    const { problemas, bytes } = verificarDist(dir);
    expect(bytes).toBe(15_000_001);
    expect(problemas.some((p) => p.includes("15000000"))).toBe(true);
  });

  test("15 000 000 bytes justos pasan", () => {
    writeFileSync(join(dir, "justo.bin"), Buffer.alloc(LIMITE_BYTES));
    expect(verificarDist(dir).problemas).toEqual([]);
  });

  test("revisa los archivos de subcarpetas", () => {
    writeFileSync(join(dir, "x.js"), "ok");
    const sub = join(dir, "assets");
    // mkdtemp no crea subcarpetas: se usa writeFileSync tras crearla.
    return import("node:fs").then(({ mkdirSync }) => {
      mkdirSync(sub);
      writeFileSync(join(sub, "y.js"), 'import("https://unpkg.com/z")');
      expect(verificarDist(dir).problemas).toHaveLength(1);
    });
  });

  test("una carpeta que no existe es un problema", () => {
    expect(verificarDist(join(dir, "no-existe")).problemas).toHaveLength(1);
  });
});
