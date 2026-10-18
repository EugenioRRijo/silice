// Hallazgos -> halos. Pura, sin DOM ni Univer. La severidad se dice con color (token), icono y texto: el color
// nunca va solo. El morado es solo para los atipicos del detector (codigo ATIPICO), sea cual sea su severidad.
import type { HallazgoLibroRespuesta } from "../api/tipos";
import type { Severidad } from "../indicadores/tipos";
import { parsearCelda } from "./celdas";

export type NombreDeIcono = "ErrorFilled" | "WarningFilled" | "WarningAltFilled" | "InformationFilled";

export interface EstiloDeHallazgo {
  token: string;
  icono: NombreDeIcono;
  texto: string;
}

export const CODIGO_ATIPICO = "ATIPICO";

const POR_SEVERIDAD: Record<Severidad, EstiloDeHallazgo> = {
  CRITICO: { token: "--silice-sev-critico", icono: "ErrorFilled", texto: "Crítico" },
  ERROR: { token: "--silice-sev-error", icono: "WarningFilled", texto: "Error" },
  ADVERTENCIA: { token: "--silice-sev-advertencia", icono: "WarningAltFilled", texto: "Advertencia" },
  INFO: { token: "--silice-sev-info", icono: "InformationFilled", texto: "Información" },
};

// Mas grande = mas grave.
const GRAVEDAD: Record<Severidad, number> = { INFO: 0, ADVERTENCIA: 1, ERROR: 2, CRITICO: 3 };

function severidadDe(h: HallazgoLibroRespuesta): Severidad {
  return h.severidad in POR_SEVERIDAD ? (h.severidad as Severidad) : "INFO";
}

export function estiloDeHallazgo(h: HallazgoLibroRespuesta): EstiloDeHallazgo {
  const base = POR_SEVERIDAD[severidadDe(h)];
  // El icono del atipico es el de su severidad: asi sigue diciendo "informacion", "advertencia"...
  if (h.codigo === CODIGO_ATIPICO) return { ...base, token: "--silice-atipico", texto: "Atípico" };
  return base;
}

export interface Halo {
  clave: string;
  hoja: string;
  fila0: number;
  columna0: number;
  // Posiciones en la lista de hallazgos original de todos los hallazgos de esta celda.
  indices: number[];
  // El estilo del mas grave (a igual gravedad, el atipico).
  estilo: EstiloDeHallazgo;
  severidad: Severidad;
}

export interface ResultadoHalos {
  halos: Halo[];
  // Posiciones de los hallazgos que no se pueden marcar en la hoja: sin celda, celda que no es A1, u hoja que el
  // libro no tiene.
  sinCelda: number[];
}

export function construirHalos(hallazgos: HallazgoLibroRespuesta[], hojasDelLibro?: string[]): ResultadoHalos {
  const porCelda = new Map<string, Halo>();
  const sinCelda: number[] = [];
  const hojas = hojasDelLibro ? new Set(hojasDelLibro) : null;

  hallazgos.forEach((h, indice) => {
    const celda = parsearCelda(h.celda);
    if (!celda || (hojas && !hojas.has(celda.hoja))) {
      sinCelda.push(indice);
      return;
    }
    const clave = `${celda.hoja}!${celda.fila0},${celda.columna0}`;
    const severidad = severidadDe(h);
    const actual = porCelda.get(clave);
    if (!actual) {
      porCelda.set(clave, { clave, ...celda, indices: [indice], estilo: estiloDeHallazgo(h), severidad });
      return;
    }
    actual.indices.push(indice);
    const mas = GRAVEDAD[severidad] - GRAVEDAD[actual.severidad];
    const desempate = mas === 0 && h.codigo === CODIGO_ATIPICO;
    if (mas > 0 || desempate) {
      actual.estilo = estiloDeHallazgo(h);
      actual.severidad = severidad;
    }
  });

  return { halos: [...porCelda.values()], sinCelda };
}
