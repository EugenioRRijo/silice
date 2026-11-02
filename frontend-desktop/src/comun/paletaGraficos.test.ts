import { describe, expect, test } from "vitest";
import { PALETA_GRAFICOS, colorPorGrupo } from "./paletaGraficos";

function matiz(hex: string): number | null {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255) as [number, number, number];
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max - min < 0.05) return null; // gris
  const d = max - min;
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}

describe("paleta de los graficos (DESIGN.md)", () => {
  test("ningun color cae en el morado, reservado para los atipicos", () => {
    for (const hex of PALETA_GRAFICOS) {
      const h = matiz(hex);
      if (h !== null) expect(h < 255 || h > 330, `${hex} (matiz ${h})`).toBe(true);
    }
  });

  test("cada grupo recibe un color y se reparten en orden, volviendo al inicio si son muchos", () => {
    const grupos = Array.from({ length: PALETA_GRAFICOS.length + 2 }, (_, i) => `g${i}`);
    const escala = colorPorGrupo(grupos).scale;
    expect(Object.keys(escala)).toEqual(grupos);
    expect(escala["g0"]).toBe(PALETA_GRAFICOS[0]);
    expect(escala[`g${PALETA_GRAFICOS.length}`]).toBe(PALETA_GRAFICOS[0]);
  });
});
