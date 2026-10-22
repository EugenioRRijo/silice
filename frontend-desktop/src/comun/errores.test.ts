import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { mensajeDeError } from "./errores";

describe("mensajeDeError", () => {
  test("un error de la API dice su detalle tal cual", () => {
    expect(mensajeDeError(new ErrorDeApi(409, "El presupuesto ya existe."))).toBe("El presupuesto ya existe.");
  });

  test("un 429 agrega los segundos de espera, con singular", () => {
    expect(mensajeDeError(new ErrorDeApi(429, "Demasiados intentos.", 45))).toBe(
      "Demasiados intentos. Espere 45 segundos antes de volver a intentarlo.",
    );
    expect(mensajeDeError(new ErrorDeApi(429, "Demasiados intentos.", 1))).toContain("Espere 1 segundo ");
  });

  test("un texto pasa tal cual y cualquier otra cosa da el mensaje general", () => {
    expect(mensajeDeError("Falta el archivo.")).toBe("Falta el archivo.");
    expect(mensajeDeError(new Error("interno"))).toBe("Ocurrió un error inesperado. Inténtelo de nuevo.");
    expect(mensajeDeError(undefined)).toBe("Ocurrió un error inesperado. Inténtelo de nuevo.");
  });
});
