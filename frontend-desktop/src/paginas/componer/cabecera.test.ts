import { describe, expect, test } from "vitest";
import { mismoDatoDeCabecera } from "./cabecera";

// N4 de la tanda (árbitro, ronda 4): el aviso «Se cambió la unidad…» al elegir una partida del catálogo no debe saltar por
// diferencias que el servidor no ve: espacios de borde y las grafías que la pantalla escribe de otra forma («m³» es «m3»,
// «día» es «dia»; `unidadEscrita`). El servidor compara las unidades con `unidades_equivalentes` y la descripción sin los
// espacios de borde (`aplicacion/composicion.py`, `motivo_para_no_reemplazar`).
describe("mismoDatoDeCabecera", () => {
  test("la descripción se compara sin los espacios de borde", () => {
    expect(mismoDatoDeCabecera("descripcion", "Relleno ficticio ", "Relleno ficticio")).toBe(true);
    expect(mismoDatoDeCabecera("descripcion", "Relleno ficticio", "Relleno compactado ficticio")).toBe(false);
  });

  test("la unidad se compara por su grafía escrita y sin bordes", () => {
    expect(mismoDatoDeCabecera("unidad", "m³", "m3")).toBe(true);
    expect(mismoDatoDeCabecera("unidad", " m3", "m3")).toBe(true);
    expect(mismoDatoDeCabecera("unidad", "día", "dia")).toBe(true);
    expect(mismoDatoDeCabecera("unidad", "M3", "m3")).toBe(true);
    expect(mismoDatoDeCabecera("unidad", "m2", "m3")).toBe(false);
  });
});
