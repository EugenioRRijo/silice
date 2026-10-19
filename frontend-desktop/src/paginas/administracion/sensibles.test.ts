import { describe, expect, test } from "vitest";
import { avisoDeRevocacion, bytesDeBase64, contrasenasCoinciden, textoDeApi, textoDeRed } from "./sensibles";
import type { InstalacionEstado } from "./sensibles";

const BASE: InstalacionEstado = {
  red_local: false,
  direccion: "",
  puerto: 8501,
  api_activa: false,
  puerto_api: 8000,
  avisos: [],
  respaldos: [],
  pendientes: [],
  sensible: { permitida: true, motivo: "" },
};

describe("lógica de las pestañas sensibles", () => {
  test("las contraseñas coinciden solo si son idénticas", () => {
    expect(contrasenasCoinciden("abc", "abc")).toBe(true);
    expect(contrasenasCoinciden("abc", "abc ")).toBe(false);
    expect(contrasenasCoinciden("ABC", "abc")).toBe(false);
  });

  test("el aviso de revocación cambia según haya aviso firmado", () => {
    expect(avisoDeRevocacion(true)).toBe("Clave revocada: los paquetes firmados con ella dejan de verificar.");
    expect(avisoDeRevocacion(false)).toContain("avise por teléfono");
  });

  test("decodifica base64 a los mismos octetos", () => {
    expect(Array.from(bytesDeBase64("AAECAw=="))).toEqual([0, 1, 2, 3]);
    expect(Array.from(bytesDeBase64(""))).toEqual([]);
  });

  test("dice la red y la API como la página clásica", () => {
    expect(textoDeRed(BASE)).toBe("Red local: apagada (solo http://127.0.0.1:8501)");
    expect(textoDeRed({ ...BASE, red_local: true, direccion: "192.168.1.20" })).toBe(
      "Red local: encendida en http://192.168.1.20:8501",
    );
    expect(textoDeApi(BASE)).toBe("API: apagada (puerto 8000)");
    expect(textoDeApi({ ...BASE, api_activa: true })).toBe("API: activa (puerto 8000)");
  });
});
