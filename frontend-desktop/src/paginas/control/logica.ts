// Control de obra (UC-19, UC-20): contrato de `/v1/control/*` y las funciones puras de la pagina.
// Los textos de las tablas ya vienen presentados por la API; aqui no se recalcula ningun monto.
import { useCallback, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { useCarga } from "../inicio/useCarga";
import type { Carga } from "../inicio/useCarga";

export type Fila = Record<string, string>;

export interface ParametroDeControl {
  parametro: string;
  que_es: string;
  valor: string;
  naturaleza: string;
}

export interface LineaBase {
  tiene_linea_base: boolean;
  descripcion: string | null;
  versiones: string[];
  hay_valuaciones: boolean;
  parametros: ParametroDeControl[];
}

export interface Valuaciones {
  tiene_linea_base: boolean;
  filas: Fila[];
  aviso: string;
  anulables: { id: number; rotulo: string }[];
  corte_por_defecto: string | null;
}

export interface PuntoDeCurva {
  periodo: string;
  pv: string;
  ev: string;
  ac: string | null;
}

export interface Calculo {
  estado: "sin_linea_base" | "sin_valuaciones" | "listo";
  corte: string | null;
  dia: number | null;
  moneda: string | null;
  indicadores: Fila[];
  costos_sin_tasa: string[];
  curva: PuntoDeCurva[];
  spi_no_aplica: boolean;
  alertas: Fila[];
  terminos: { indice: string; reproyectado: string; plan_base: string; eac_sistema: string } | null;
  motivo_termino: string;
  equilibrio: { punto: string; mensaje: string } | null;
  estudios: string;
  reproyeccion: Fila[];
  plan: { columnas: string[]; filas: Fila[] } | null;
  decisiones: Fila[];
  versiones_revaloradas: string[];
}

export interface OpcionDeRecuperacion {
  clave: string;
  titulo: string;
  aplica: boolean;
  motivo: string;
  requisitos: string[];
  requiere_declaracion: boolean;
  fila: Fila;
}

export type MetodoDePrecios = "ninguno" | "comprobacion" | "escalatoria";

export interface Precios {
  metodo: MetodoDePrecios;
  version: string;
  km: string;
  r: string;
  fuente: string;
}

export interface Filtros {
  corte: string;
  precios: Precios;
}

export const PRECIOS_INICIALES: Precios = { metodo: "ninguno", version: "", km: "", r: "0", fuente: "" };
export const FILTROS_INICIALES: Filtros = { corte: "", precios: PRECIOS_INICIALES };

export const ROTULO_DE_METODO: Record<MetodoDePrecios, string> = {
  ninguno: "Sin precios del corte",
  comprobacion: "Comprobacion directa (version revalorada)",
  escalatoria: "Escalatoria (un Km declarado)",
};

export const PESTANAS = ["Línea base", "Valuaciones", "Valor ganado", "Alertas y reproyección", "Recuperación"] as const;

export const COLUMNAS_VALUACIONES = ["Numero", "Periodo", "Fecha", "Inspector", "Registrada", "Estado"];
export const COLUMNAS_INDICADORES = ["Indicador", "Valor", "En la otra moneda", "Nota"];
export const COLUMNAS_ALERTAS = ["Alerta", "Severidad", "Descripcion", "Observado", "Umbral"];
export const COLUMNAS_REPROYECCION = ["Partida", "Indice", "Fin (dia habil)", "Nota"];
export const COLUMNAS_DECISIONES = ["Version", "Opcion", "Corte", "Termino", "Fuente", "Responsable"];
export const COLUMNAS_OPCIONES = [
  "Opcion",
  "Termino",
  "Retraso (dias)",
  "Costo directo adicional",
  "Costo indirecto",
  "Penalizacion",
  "Punto de equilibrio",
  "Nota",
];

// Las columnas de una tabla de la API: la clave es el titulo, que es tambien la clave de cada fila.
export function columnasDe(titulos: string[], numericas: string[] = []) {
  return titulos.map((t) => ({ clave: t, titulo: t, numerica: numericas.includes(t), ordenable: false }));
}

// Las filas con el `id` que pide la tabla (el lugar que ocupan).
export function conId(filas: Fila[]): ({ id: string } & Fila)[] {
  return filas.map((f, i) => ({ id: String(i), ...f }));
}

export function rutaDe(base: string, proyecto: string, extra: Record<string, string> = {}): string {
  const p = new URLSearchParams({ proyecto, ...extra });
  return `${base}?${p.toString()}`;
}

// Los parametros de la consulta del calculo: solo lo que la persona eligio.
export function consultaDeCalculo(proyecto: string, filtros: Filtros): string {
  const extra: Record<string, string> = {};
  if (filtros.corte.trim()) extra.corte = filtros.corte.trim();
  const { metodo, version, km, r, fuente } = filtros.precios;
  if (metodo !== "ninguno") {
    extra.metodo = metodo;
    if (metodo === "comprobacion") extra.version = version;
    if (metodo === "escalatoria") Object.assign(extra, { km, r, fuente });
  }
  return rutaDe("/v1/control/calculo", proyecto, extra);
}

// El cuerpo comun de las opciones y de la eleccion: el servidor no guarda estado, asi que se repite todo.
export function cuerpoDeOpciones(proyecto: string, filtros: Filtros, objetivo: string, horasPrevias: string) {
  return {
    proyecto,
    corte: filtros.corte.trim() || null,
    precios: filtros.precios,
    objetivo,
    horas_previas: horasPrevias,
  };
}

// Las filas de una valuacion tal como las pide la API: las vacias se ignoran alla.
export interface LineaEditable {
  partida: string;
  cantidad: string;
  fecha_medicion: string;
  observacion: string;
}

export const LINEA_VACIA: LineaEditable = { partida: "", cantidad: "", fecha_medicion: "", observacion: "" };

export function sinLineasVacias(lineas: LineaEditable[]): LineaEditable[] {
  return lineas.filter((l) => l.partida.trim() !== "" || l.cantidad.trim() !== "");
}

// Resultado de una accion que escribe: en curso, con su mensaje de exito o con su error.
export interface EstadoDeAccion {
  enviando: boolean;
  error: unknown;
  exito: string;
}

export function useAccion(alExpirar: () => void, alTerminar?: () => void) {
  const [estado, setEstado] = useState<EstadoDeAccion>({ enviando: false, error: null, exito: "" });
  const ejecutar = useCallback(
    async (tarea: () => Promise<string>) => {
      setEstado({ enviando: true, error: null, exito: "" });
      try {
        const exito = await tarea();
        setEstado({ enviando: false, error: null, exito });
        alTerminar?.();
      } catch (error) {
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setEstado({ enviando: false, error, exito: "" });
      }
    },
    [alExpirar, alTerminar],
  );
  return { estado, ejecutar };
}

// Como `useCarga`, pero mientras vuelve a pedir tras una escritura deja a la vista lo ultimo que llego: asi el
// formulario que acaba de escribir no se desmonta (y su aviso de exito no se pierde) detras de un esqueleto.
export function useCargaSuave<T>(ruta: string, alExpirar: () => void): Carga<T> {
  const carga = useCarga<T>(ruta, alExpirar);
  const [ultimo, setUltimo] = useState<T | null>(null);
  if (carga.estado === "listo" && carga.datos !== ultimo) setUltimo(carga.datos);
  if (carga.estado === "cargando" && ultimo !== null) return { estado: "listo", datos: ultimo };
  return carga;
}
