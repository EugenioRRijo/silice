import { describe, expect, test } from "vitest";
import { buscadorDePartidasDelContrato, partidaDelContrato } from "./partidasDelContrato";
import type { PartidaDelContrato } from "./partidasDelContrato";

// Oráculo a mano: las tres partidas de la obra ficticia OB-S2 (tests/fixtures/control_ob_s2.py).
const PARTIDAS: PartidaDelContrato[] = [
  { codigo: "OB-A", descripcion: "Excavacion de zanja", unidad: "m3" },
  { codigo: "OB-B", descripcion: "Tuberia de drenaje", unidad: "m" },
  { codigo: "OB-C", descripcion: "Relleno compactado", unidad: "m3" },
];
const senal = new AbortController().signal;

describe("buscador local de las partidas del contrato", () => {
  test("una opción por partida: la descripción arriba y el código y la unidad debajo", async () => {
    const grupos = await buscadorDePartidasDelContrato(PARTIDAS)("zanja", senal, 8);
    expect(grupos).toHaveLength(1);
    expect(grupos[0]?.rotulo).toBe("Partidas del contrato");
    expect(grupos[0]?.hayMas).toBe(false);
    expect(grupos[0]?.opciones).toEqual([
      { clave: "partida:OB-A", principal: "Excavacion de zanja", secundaria: ["OB-A", "m3"], valor: PARTIDAS[0] },
    ]);
  });

  test("ignora tildes y mayúsculas y exige todas las palabras, en el código o en la descripción", async () => {
    const buscar = buscadorDePartidasDelContrato(PARTIDAS);
    const codigos = async (q: string) => (await buscar(q, senal, 8)).flatMap((g) => g.opciones.map((o) => o.valor.codigo));
    expect(await codigos("EXCAVACIÓN")).toEqual(["OB-A"]);
    expect(await codigos("relleno comp")).toEqual(["OB-C"]);
    expect(await codigos("ob-b")).toEqual(["OB-B"]);
    expect(await codigos("relleno tuberia")).toEqual([]);
  });

  test("con el texto vacío ofrece todas las del contrato", async () => {
    const grupos = await buscadorDePartidasDelContrato(PARTIDAS)("", senal, 8);
    expect(grupos[0]?.opciones.map((o) => o.valor.codigo)).toEqual(["OB-A", "OB-B", "OB-C"]);
  });

  test("respeta el límite por grupo y dice que hay más", async () => {
    const grupos = await buscadorDePartidasDelContrato(PARTIDAS)("", senal, 2);
    expect(grupos[0]?.opciones.map((o) => o.valor.codigo)).toEqual(["OB-A", "OB-B"]);
    expect(grupos[0]?.hayMas).toBe(true);
  });

  test("sin coincidencias no devuelve ningún grupo", async () => {
    expect(await buscadorDePartidasDelContrato(PARTIDAS)("pavimento", senal, 8)).toEqual([]);
  });
});

describe("partidaDelContrato (lo escrito es una partida del contrato)", () => {
  test("coincide con el código sin importar mayúsculas ni espacios de los bordes", () => {
    expect(partidaDelContrato(PARTIDAS, "  ob-a ")).toBe(PARTIDAS[0]);
    expect(partidaDelContrato(PARTIDAS, "OB-C")).toBe(PARTIDAS[2]);
  });

  test("lo que no está en el contrato, y el texto vacío, no coinciden", () => {
    expect(partidaDelContrato(PARTIDAS, "OB-D")).toBeNull();
    expect(partidaDelContrato(PARTIDAS, "")).toBeNull();
    expect(partidaDelContrato(PARTIDAS, "zanja")).toBeNull();
  });
});
