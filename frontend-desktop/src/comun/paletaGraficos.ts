import { formatoEsVe } from "../indicadores/formatoEsVe";

// Paleta de los graficos (DESIGN.md): grises y un verde azulado; nunca el morado (reservado para los atipicos) ni el
// azul de interaccion. Carbon Charts trae su propia paleta categorica (con morado), por eso se pasa siempre una escala.
export const PALETA_GRAFICOS = ["#525252", "#007d79", "#8d8d8d", "#161616", "#198038", "#a8a8a8"] as const;

// `color.scale` de Carbon Charts: un color por grupo, en orden.
export function colorPorGrupo(grupos: string[]): { scale: Record<string, string> } {
  const scale: Record<string, string> = {};
  grupos.forEach((g, i) => {
    scale[g] = PALETA_GRAFICOS[i % PALETA_GRAFICOS.length]!;
  });
  return { scale };
}

// Numero de un eje o de un tooltip a es-VE, solo por operaciones de cadena sobre su representacion decimal.
export function formatoNumeroEsVe(valor: unknown): string {
  return formatoEsVe(String(valor));
}

// Colores de las series de una curva por su rol (DESIGN.md: real = oscuro y grueso, plan = gris claro, pronostico =
// gris medio discontinuo). Una segunda serie real toma el verde azulado para distinguirse de la primera.
export function colorPorSerie(series: { nombre: string; rol: "plan" | "real" | "pronostico" }[]): {
  scale: Record<string, string>;
} {
  const scale: Record<string, string> = {};
  let reales = 0;
  for (const s of series) {
    if (s.rol === "plan") scale[s.nombre] = "#8d8d8d";
    else if (s.rol === "pronostico") scale[s.nombre] = "#525252";
    else scale[s.nombre] = ["#161616", "#007d79", "#198038"][reales++ % 3]!;
  }
  return { scale };
}
