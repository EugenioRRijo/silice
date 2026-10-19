// Logica pura de «Reajuste de precios»: arma lo que se manda a la API con el texto que escribe la persona y lo que
// se muestra con el texto que devuelve. No calcula ni redondea nada (RB-2): el estudio lo hace el servidor.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";

export type Fila = Record<string, string>;

export interface ClausulaTextos {
  fecha_inicio: string;
  duracion_meses: string;
  fecha_referencia_primer_anio: string;
  periodicidad: string;
  mecanismo: string;
  mecanismo_pagadero: string;
  fuente_pagadero: string;
  estructura: string;
  fecha_base_indices: string;
  r: string;
  fuente_r: string;
  r_en_comprobacion: "si" | "no";
  fuente: string;
  responsable: string;
}

export interface Formulario {
  version: string;
  clausula: ClausulaTextos;
  componentes: Fila[];
  periodos: Fila[];
  ejecutado: Fila[];
  con_valuaciones: boolean;
}

export interface CuerpoEstudio {
  proyecto: string;
  version: string;
  clausula: ClausulaTextos;
  componentes: Fila[];
  periodos: Fila[];
  ejecutado: Fila[];
  con_valuaciones: boolean;
}

export const CLAVES_COMPONENTE = ["componente", "serie", "peso"];
export const CLAVES_PERIODO = ["desde", "hasta", "version_comprobacion", "excepcion"];
export const CLAVES_EJECUTADO = ["periodo", "partida", "cantidad", "fuente"];
// Columnas del resultado que son texto y no cifra (el resto se alinea a la derecha como monto o tasa).
const COLUMNAS_DE_TEXTO = new Set(["Período", "Mecanismo", "Moneda", "Marcas"]);

export function filasVacias(claves: string[], cantidad: number): Fila[] {
  return Array.from({ length: cantidad }, () => Object.fromEntries(claves.map((c) => [c, ""])));
}

export function hayFilaConDatos(fila: Fila): boolean {
  return Object.values(fila).some((valor) => valor.trim() !== "");
}

// Quita la fila `indice`; si era la unica deja una en blanco (la tabla nunca queda sin donde escribir).
export function quitarFilaVacia(filas: Fila[], indice: number): Fila[] {
  const resto = filas.filter((_, i) => i !== indice);
  return resto.length > 0 ? resto : filasVacias(Object.keys(filas[0] ?? {}), 1);
}

export function formularioInicial(): Formulario {
  const componentes = ["materiales", "equipos", "mano_obra"].map((c) => ({ componente: c, serie: "", peso: "" }));
  return {
    version: "",
    clausula: {
      fecha_inicio: "",
      duracion_meses: "",
      fecha_referencia_primer_anio: "",
      periodicidad: "mensual",
      mecanismo: "escalatoria",
      mecanismo_pagadero: "",
      fuente_pagadero: "",
      estructura: "por_partida",
      fecha_base_indices: "",
      r: "",
      fuente_r: "",
      r_en_comprobacion: "no",
      fuente: "",
      responsable: "",
    },
    componentes,
    periodos: filasVacias(CLAVES_PERIODO, 1),
    ejecutado: [{ periodo: "1", partida: "", cantidad: "", fuente: "" }],
    con_valuaciones: false,
  };
}

// El cuerpo de calcular, guardar y excel. Las filas en blanco de periodos y ejecutado no se mandan; los tres
// componentes si, como la pantalla de Streamlit (el servidor dice cual serie falta). Con las valuaciones, lo
// ejecutado sale de ellas y no se manda.
export function armarCuerpo(proyecto: string, f: Formulario): CuerpoEstudio {
  return {
    proyecto,
    version: f.version,
    clausula: f.clausula,
    componentes: f.componentes,
    periodos: f.periodos.filter(hayFilaConDatos),
    ejecutado: f.con_valuaciones ? [] : f.ejecutado.filter(ejecutadoConDatos),
    con_valuaciones: f.con_valuaciones,
  };
}

// El «1» que trae la primera fila de lo ejecutado no cuenta como dato: sin partida, cantidad ni fuente es una fila
// en blanco (en Streamlit obligaba a borrarla).
function ejecutadoConDatos(fila: Fila): boolean {
  return hayFilaConDatos({ partida: fila.partida ?? "", cantidad: fila.cantidad ?? "", fuente: fila.fuente ?? "" });
}

export function columnasDeResultado(columnas: string[]): ColumnaDensa[] {
  return columnas.map((titulo) => ({ clave: titulo, titulo, numerica: !COLUMNAS_DE_TEXTO.has(titulo) }));
}

export function filasDeResultado(filas: Fila[]): FilaDensa[] {
  return filas.map((fila, i) => ({ id: String(i), ...fila }));
}
