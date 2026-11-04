// La calculadora del FCAS por componentes (`/v1/fcas`). La pantalla no calcula nada: lee lo escrito con coma decimal,
// manda decimales con punto y escribe lo que devuelve el servidor con coma y punto de miles.
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { leerCifra, textoParaEscribir } from "../../indicadores/cifraEscrita";

export interface ComponenteFcas {
  id: string;
  nombre: string;
  base: string; // "dias" o "porcentaje"
  valor: string; // decimal con punto
  fuente: string;
  a_cotejar: boolean;
}

export interface PorDefectoFcas {
  dias_calendario: string;
  fcas_version: string;
  componentes: ComponenteFcas[];
}

export interface DeLaVersionFcas {
  fcas: string;
  porcentaje: string;
  multiplicador: string;
}

export interface ResultadoFcas {
  fcas: string; // fracción con punto
  fcas_por_dias: string;
  dias_pagados: string;
  porcentaje: string;
  multiplicador: string;
  desglose: { id: string; nombre: string; aporte: string }[];
  a_cotejar: { id: string; nombre: string }[];
  version: DeLaVersionFcas | null;
}

// Lo que la persona ve y puede cambiar de cada componente: si cuenta y su valor escrito con coma.
export interface FilaFcas {
  activo: boolean;
  valor: string;
}

export type Escrito = { dias_calendario: string; dias_trabajados: string; fcas_version: string };

export const RUTA_COMPONENTES = "/v1/fcas/componentes";
export const RUTA_CALCULAR = "/v1/fcas/calcular";
export const ETIQUETA_CALENDARIO = "Días calendario del período";
export const ETIQUETA_TRABAJADOS = "Días trabajados";
export const ETIQUETA_VERSION = "FCAS de la versión";
export const AYUDA_VERSION =
  "Fracción: 6,00 es 600 % y multiplica el sueldo por 7. Déjelo vacío para no compararlo.";
export const AYUDA_TRABAJADOS =
  "Días calendario menos descansos, feriados, vacaciones, permisos y lluvia. Ejemplo publicado por Dodi y Salas (2019): 217,28.";

export const porcentajeEsVe = (porcentaje: string): string => `${formatoEsVe(porcentaje)} %`;
export const multiplicadorEsVe = (multiplicador: string): string => `× ${formatoEsVe(multiplicador)}`;
export const unidadDe = (base: string): string => (base === "dias" ? "días de salario" : "% del salario pagado");

export function filasIniciales(componentes: ComponenteFcas[]): Record<string, FilaFcas> {
  return Object.fromEntries(componentes.map((c) => [c.id, { activo: true, valor: textoParaEscribir(c.valor) }]));
}

export type Peticion = { cuerpo: Record<string, unknown> } | { errores: Record<string, string> };

// Lo escrito (coma decimal) a la petición (punto decimal); si alguna cifra no se lee, el mensaje de cada campo.
export function armarPeticion(
  escrito: Escrito,
  componentes: ComponenteFcas[],
  filas: Record<string, FilaFcas>,
): Peticion {
  const errores: Record<string, string> = {};
  const leer = (clave: string, texto: string, opcional = false): string | undefined => {
    if (opcional && texto.trim() === "") return undefined;
    const lectura = leerCifra(texto);
    if ("error" in lectura) {
      errores[clave] = lectura.error;
      return undefined;
    }
    return lectura.valor;
  };
  const dias_calendario = leer("dias_calendario", escrito.dias_calendario);
  const dias_trabajados = leer("dias_trabajados", escrito.dias_trabajados);
  const fcas_version = leer("fcas_version", escrito.fcas_version, true);
  const activos = componentes.filter((c) => filas[c.id]?.activo);
  const enviados = activos.map((c) => ({
    id: c.id,
    nombre: c.nombre,
    base: c.base,
    valor: leer(c.id, filas[c.id]!.valor),
    fuente: c.fuente,
  }));
  if (Object.keys(errores).length > 0) return { errores };
  const cuerpo: Record<string, unknown> = { dias_calendario, dias_trabajados, componentes: enviados };
  if (fcas_version !== undefined) cuerpo["fcas_version"] = fcas_version;
  return { cuerpo };
}
