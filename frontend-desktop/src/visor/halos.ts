// Hallazgos -> halos. Pura, sin DOM ni Univer. La severidad se dice con color (token), icono y texto: el color
// nunca va solo. El morado es solo para los atipicos del detector (codigo ATIPICO), sea cual sea su severidad.
import type { HallazgoLibroRespuesta, HojaVisualRespuesta } from "../api/tipos";
import type { Severidad } from "../indicadores/tipos";
import { estiloDeSeveridad, gravedad, normalizarSeveridad } from "../severidad/severidad";
import type { EstiloDeSeveridad } from "../severidad/severidad";
import { aFilaExcel, columna0ALetras } from "../replica/coordenadas";
import { parsearCelda } from "./celdas";

export type EstiloDeHallazgo = EstiloDeSeveridad;

export const CODIGO_ATIPICO = "ATIPICO";

export function estiloDeHallazgo(h: HallazgoLibroRespuesta): EstiloDeHallazgo {
  const base = estiloDeSeveridad(normalizarSeveridad(h.severidad));
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

export interface Oculto {
  indice: number;
  // Que esta oculto, dicho como lo ve el auditor: "hoja AUX oculta", "fila 19 oculta", "columna C oculta".
  motivo: string;
}

export interface ResultadoHalos {
  halos: Halo[];
  // Posiciones de los hallazgos que no se pueden marcar en la hoja porque no hay celda ubicable: sin celda, celda
  // que no es A1, u hoja que el libro no tiene.
  sinCelda: number[];
  // Hallazgos con celda, pero en una hoja, fila o columna oculta del libro: no se ven, y se dice por que.
  ocultos: Oculto[];
}

export function construirHalos(hallazgos: HallazgoLibroRespuesta[], hojas?: HojaVisualRespuesta[]): ResultadoHalos {
  const porCelda = new Map<string, Halo>();
  const sinCelda: number[] = [];
  const ocultos: Oculto[] = [];
  const porNombre = hojas ? new Map(hojas.map((h) => [h.nombre, h])) : null;

  hallazgos.forEach((h, indice) => {
    const celda = parsearCelda(h.celda);
    const hoja = celda ? porNombre?.get(celda.hoja) : undefined;
    if (!celda || (porNombre && !hoja)) {
      sinCelda.push(indice);
      return;
    }
    if (hoja) {
      const motivos: string[] = [];
      if (!hoja.visible) motivos.push(`hoja ${hoja.nombre} oculta`);
      else {
        if (hoja.ocultas_filas.includes(aFilaExcel(celda.fila0))) motivos.push(`fila ${aFilaExcel(celda.fila0)} oculta`);
        if (hoja.ocultas_columnas.includes(aFilaExcel(celda.columna0))) {
          motivos.push(`columna ${columna0ALetras(celda.columna0)} oculta`);
        }
      }
      if (motivos.length > 0) {
        ocultos.push({ indice, motivo: motivos.join(" y ") });
        return;
      }
    }
    const clave = `${celda.hoja}!${celda.fila0},${celda.columna0}`;
    const severidad = normalizarSeveridad(h.severidad);
    const actual = porCelda.get(clave);
    if (!actual) {
      porCelda.set(clave, { clave, ...celda, indices: [indice], estilo: estiloDeHallazgo(h), severidad });
      return;
    }
    actual.indices.push(indice);
    const mas = gravedad(severidad) - gravedad(actual.severidad);
    const desempate = mas === 0 && h.codigo === CODIGO_ATIPICO;
    if (mas > 0 || desempate) {
      actual.estilo = estiloDeHallazgo(h);
      actual.severidad = severidad;
    }
  });

  return { halos: [...porCelda.values()], sinCelda, ocultos };
}
