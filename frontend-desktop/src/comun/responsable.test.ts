import { describe, expect, test } from "vitest";
import { nombreDeResponsable } from "./responsable";

// El responsable que guarda la API es «Nombre <login>» (RF-82, `seguridad/cuentas.py::texto_responsable`), con
// « (tras restablecimiento)» al final si aplica. En la interfaz se dice el nombre. Casos escritos a mano.
describe("nombreDeResponsable", () => {
  test("quita el login", () => {
    expect(nombreDeResponsable("Ana Pérez <ana>")).toBe("Ana Pérez");
  });

  test("quita también la marca del restablecimiento", () => {
    expect(nombreDeResponsable("Rita <rita> (tras restablecimiento)")).toBe("Rita");
  });

  test("sin login (la clave de API u otro texto) lo deja tal cual", () => {
    expect(nombreDeResponsable("API")).toBe("API");
  });
});
