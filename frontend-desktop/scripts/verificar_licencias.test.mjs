import { describe, expect, test } from "vitest";
import { verificarLock } from "./verificar_licencias.mjs";

const lock = (paquetes) => ({ lockfileVersion: 3, packages: { "": { name: "raiz" }, ...paquetes } });

describe("verificarLock", () => {
  test("un paquete @univerjs-pro falla", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/@univerjs-pro/sheets": { version: "1.0.0", license: "MIT" } }),
    );
    expect(problemas).toHaveLength(1);
    expect(problemas[0]).toContain("@univerjs-pro/sheets");
  });

  test("una licencia GPL-3.0 falla", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/algo": { version: "1.0.0", license: "GPL-3.0" } }),
    );
    expect(problemas).toHaveLength(1);
    expect(problemas[0]).toContain("GPL-3.0");
  });

  test("(MIT OR Apache-2.0) pasa", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/algo": { version: "1.0.0", license: "(MIT OR Apache-2.0)" } }),
    );
    expect(problemas).toEqual([]);
  });

  test("una combinacion OR con una licencia no permitida falla", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/algo": { version: "1.0.0", license: "(MIT OR GPL-3.0)" } }),
    );
    expect(problemas).toHaveLength(1);
  });

  test("un paquete sin licencia declarada falla", () => {
    const { problemas } = verificarLock(lock({ "node_modules/algo": { version: "1.0.0" } }));
    expect(problemas).toHaveLength(1);
  });

  test("cuenta los paquetes por licencia y omite la raiz", () => {
    const { cuentas } = verificarLock(
      lock({
        "node_modules/a": { version: "1.0.0", license: "MIT" },
        "node_modules/b": { version: "1.0.0", license: "MIT" },
        "node_modules/c": { version: "1.0.0", license: "Apache-2.0" },
      }),
    );
    expect(cuentas).toEqual({ MIT: 2, "Apache-2.0": 1 });
  });

  test("MIT-0 pasa", () => {
    const { problemas } = verificarLock(lock({ "node_modules/a": { version: "1.0.0", license: "MIT-0" } }));
    expect(problemas).toEqual([]);
  });

  test("MPL-2.0 pasa solo en desarrollo", () => {
    const dev = verificarLock(lock({ "node_modules/a": { version: "1.0.0", license: "MPL-2.0", dev: true } }));
    expect(dev.problemas).toEqual([]);
    const prod = verificarLock(lock({ "node_modules/a": { version: "1.0.0", license: "MPL-2.0" } }));
    expect(prod.problemas).toHaveLength(1);
  });

  test("CC-BY-4.0 pasa solo en desarrollo", () => {
    const dev = verificarLock(lock({ "node_modules/a": { version: "1.0.0", license: "CC-BY-4.0", dev: true } }));
    expect(dev.problemas).toEqual([]);
    const prod = verificarLock(lock({ "node_modules/a": { version: "1.0.0", license: "CC-BY-4.0" } }));
    expect(prod.problemas).toHaveLength(1);
  });

  test("las dependencias anidadas tambien se revisan", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/a/node_modules/@univerjs-pro/x": { version: "1.0.0", license: "MIT" } }),
    );
    expect(problemas).toHaveLength(1);
  });

  test("Unlicense (dominio publico) pasa", () => {
    const { problemas } = verificarLock(lock({ "node_modules/a": { version: "1.0.0", license: "Unlicense" } }));
    expect(problemas).toEqual([]);
  });

  test("dompurify con (MPL-2.0 OR Apache-2.0) pasa porque se elige Apache-2.0 (ruling RS2B-1)", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/dompurify": { version: "3.4.17", license: "(MPL-2.0 OR Apache-2.0)" } }),
    );
    expect(problemas).toEqual([]);
  });

  test("la misma expresion en otro paquete sigue fallando: la eleccion es por paquete", () => {
    const { problemas } = verificarLock(
      lock({ "node_modules/otro": { version: "1.0.0", license: "(MPL-2.0 OR Apache-2.0)" } }),
    );
    expect(problemas).toHaveLength(1);
  });
});
