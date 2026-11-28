import { describe, expect, test } from "vitest";
import { extraerPersona, nombreDeResponsable } from "./responsable";

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

  // T4 (mutante R1): el corte solo vale si queda algún nombre antes del « <».
  test("si el texto empieza por « <» no se queda sin nombre", () => {
    expect(nombreDeResponsable(" <ana>")).toBe(" <ana>");
  });
});

// T4 (mutantes R2 y R4): bordes de `extraerPersona` que la lógica de Versiones no recorre.
describe("extraerPersona: bordes", () => {
  test("la clave va en minúsculas aunque el usuario venga con mayúsculas, y el usuario se conserva tal cual", () => {
    expect(extraerPersona("Ana Pérez <Ana>")).toEqual({ clave: "u:ana", nombre: "Ana Pérez", usuario: "Ana" });
  });

  test("un texto que empieza por el usuario entre ángulos usa el usuario como nombre", () => {
    expect(extraerPersona("<ana>")).toEqual({ clave: "u:ana", nombre: "ana", usuario: "ana" });
  });
});
