// Control de obra (UC-19, UC-20): contrato de `/v1/control/*` y las funciones puras de la pagina.
// Los textos de las tablas ya vienen presentados por la API; aqui no se recalcula ningun monto.
import { useCallback, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import type { FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe, formatoMontoEsVe } from "../../indicadores/formatoEsVe";
import { useCarga } from "../inicio/useCarga";
import type { Carga } from "../inicio/useCarga";

export type Fila = Record<string, string>;

// V-12: lo que se le pasa a `AvisoError` cuando una carga no llego a `listo`. Los estados `sin_permiso` y
// `no_disponible` traen el `ErrorDeApi` con su `detalle`: se conserva; si no hay detalle, una frase en español
// (nunca el codigo interno del estado).
export function errorDeCarga(carga: Carga<unknown>): unknown {
  if (carga.estado === "cargando" || carga.estado === "listo") return null;
  if (carga.estado === "error") return carga.error;
  if (carga.error instanceof ErrorDeApi && carga.error.detalle) return carga.error;
  return carga.estado === "sin_permiso" ? "Su cuenta no tiene permiso para ver esto." : "No se encontró lo pedido.";
}

// V-22: los identificadores internos que la API manda tal cual, en español llano. El codigo original se conserva en el
// `title` de la celda (trazabilidad) y un codigo que no esta aqui se muestra tal cual.
const ETIQUETAS_DE_CODIGO: Record<string, string> = {
  spi_error: "Umbral de SPI para error",
  cpi_error: "Umbral de CPI para error",
  retraso_error: "Retraso del término para error",
  precio_info: "Desvío de precio que avisa",
  equilibrio_puntos: "Subida del punto de equilibrio que advierte",
  eta_cuadrilla: "Eficiencia de la cuadrilla adicional",
  cuadrillas_max: "Cuadrillas máximas por frente",
  eta_horas_extra: "Eficiencia de la hora extra",
  horas_extra_dia: "Horas extra por día",
  recargo_horas_extra: "Recargo de las horas extra",
  fcas_en_horas_extra: "FCAS sobre las horas extra",
  penalizacion_diaria: "Penalización diaria por retraso",
  fuente_penalizacion: "Fuente de la penalización",
  SUPUESTO_DECLARADO: "Supuesto declarado",
  DATO_DEL_CONTRATO: "Dato del contrato",
  FUENTE_VERIFICADA: "Fuente verificada",
  "AL-1": "Retraso (SPI)",
  "AL-2": "Sobrecosto (CPI)",
  "AL-3": "Retraso del término",
  "AL-4": "Punto de equilibrio",
  "AL-5": "Desvío de precio",
  "AL-6": "Partida detenida",
};

export function etiquetaDeCodigo(codigo: string): string {
  return ETIQUETAS_DE_CODIGO[codigo] ?? codigo;
}

// Un texto con codigos adentro («0.8500 (SUPUESTO_DECLARADO)», «... es ERROR (AL-1)»): los de naturaleza se leen en
// minuscula y los parentesis tecnicos (AL-n, eta, eta_he) se quitan, porque el texto ya dice de que se trata.
export function textoLlano(texto: string): string {
  return texto
    .replace(/\s*\((?:AL-[0-9]+|eta|eta_he)\)/g, "")
    .replace(/\b(SUPUESTO_DECLARADO|DATO_DEL_CONTRATO)\b/g, (c) => (ETIQUETAS_DE_CODIGO[c] ?? c).toLowerCase());
}

// VB-4: las cifras de las descripciones de las alertas, en es-VE. Solo en las frases fijas del nucleo que llevan un
// numero (AL-1, AL-2, AL-4 y AL-5) y solo en el hueco de la cifra: el resto (un codigo de partida que escribio el
// usuario, «art. 133») queda tal cual. Los grupos alternan texto y cifra.
const CIFRA = "([-+]?[0-9]+(?:\\.[0-9]+)?)";
const FRASES_CON_CIFRAS = [
  new RegExp(`^(retraso: SPI )${CIFRA}$`),
  new RegExp(`^(sobrecosto: CPI )${CIFRA}$`),
  new RegExp(`^(el punto de equilibrio proyectado sube más de )${CIFRA}( puntos porcentuales .*)$`),
  new RegExp(`^(.*: el precio del corte desvía )${CIFRA}( sobre un valor ganado de )${CIFRA}$`),
];

// Mas largo que esto no es una descripcion del nucleo (la mas larga mide ~150 caracteres): vuelve intacto sin probar
// ninguna expresion ni formatear cifras (el separador de miles de formatoEsVe es cuadratico en el largo de la cifra).
const LARGO_MAXIMO_DESCRIPCION = 2_000;

export function descripcionEsVe(texto: string): string {
  if (texto.length > LARGO_MAXIMO_DESCRIPCION) return texto;
  for (const frase of FRASES_CON_CIFRAS) {
    const m = frase.exec(texto);
    if (m) return m.slice(1).map((parte, i) => (i % 2 === 1 ? formatoEsVe(parte) : parte)).join("");
  }
  return texto;
}

// La severidad que manda la API («ADVERTENCIA», «sin evaluar») para el componente comun: las del nucleo pasan tal
// cual (el componente les pone su nombre e icono) y «sin evaluar» se lee con mayuscula inicial.
export function severidadVisible(valor: string): string {
  return valor === "sin evaluar" ? "Sin evaluar" : valor;
}

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

// Un supuesto de una opcion en sus tres ranuras: nombre y valor ya con tilde, la naturaleza como codigo del nucleo.
export interface SupuestoDeOpcion {
  nombre: string;
  valor: string;
  naturaleza: string;
}

export interface OpcionDeRecuperacion {
  clave: string;
  titulo: string;
  aplica: boolean;
  motivo: string;
  requisitos: string[];
  requiere_declaracion: boolean;
  fila: Fila;
  // VD-1: los supuestos de `fila.Nota`, por ranura (vacia si la opcion no aplica).
  supuestos?: SupuestoDeOpcion[];
}

// VD-1: la «Nota» de una opcion, en español, armada ranura por ranura con la misma forma que la API
// («nombre: valor (naturaleza)», separados por «; »). Ninguna regla mira dentro de un texto armado: el nombre se
// cambia solo si es uno del catalogo fijo del nucleo (las «eta» se leen «eficiencia», como en los parametros), la
// naturaleza solo si es un codigo conocido, y la cifra se pone en es-VE solo en los supuestos numericos del nucleo y
// solo si TODA la ranura es una cifra. Lo demas (la lista de partidas del usuario, por ejemplo) sale tal cual. La
// opcion que no aplica, o una respuesta sin ranuras, muestra su nota tal cual.
const NOMBRES_DE_SUPUESTO: Record<string, string> = {
  "eta de cuadrillas": "eficiencia de la cuadrilla adicional",
  "eta de horas extra": "eficiencia de la hora extra",
  recargo: "recargo de las horas extra",
};
const SUPUESTOS_NUMERICOS = new Set([
  "eta de cuadrillas",
  "cuadrillas máximas",
  "eta de horas extra",
  "horas extra por día",
  "recargo",
  "penalización diaria",
]);
const CIFRA_SOLA = /^[-+]?[0-9]{1,30}(?:\.[0-9]{1,30})?$/;
// Una ranura numerica del nucleo mide unas decenas de caracteres: mas larga, no se prueba ninguna expresion.
const LARGO_MAXIMO_RANURA = 64;
const NATURALEZAS = new Set(["SUPUESTO_DECLARADO", "DATO_DEL_CONTRATO", "FUENTE_VERIFICADA"]);

function valorDeSupuesto(s: SupuestoDeOpcion): string {
  if (!SUPUESTOS_NUMERICOS.has(s.nombre) || s.valor.length > LARGO_MAXIMO_RANURA) return s.valor;
  return CIFRA_SOLA.test(s.valor) ? formatoEsVe(s.valor) : s.valor;
}

export function notaDeOpcion(opcion: OpcionDeRecuperacion): string {
  const supuestos = opcion.supuestos ?? [];
  if (!opcion.aplica || supuestos.length === 0) return opcion.fila.Nota ?? "";
  return supuestos
    .map((s) => {
      const nombre = NOMBRES_DE_SUPUESTO[s.nombre] ?? s.nombre;
      const naturaleza = NATURALEZAS.has(s.naturaleza) ? etiquetaDeCodigo(s.naturaleza).toLowerCase() : s.naturaleza;
      return `${nombre}: ${valorDeSupuesto(s)} (${naturaleza})`;
    })
    .join("; ");
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
  comprobacion: "Comprobación directa (versión revalorada)",
  escalatoria: "Escalatoria (un Km declarado)",
};

export const PESTANAS = ["Línea base", "Valuaciones", "Valor ganado", "Alertas y reproyección", "Recuperación"] as const;

// Son las claves de cada fila tal como las manda la API (sin tilde); el título visible sale de TITULOS_VISIBLES.
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
// Los titulos que la API manda sin tilde, tal como se leen (la clave de la fila sigue siendo el titulo original).
export const TITULOS_VISIBLES: Record<string, string> = {
  Numero: "Número",
  Descripcion: "Descripción",
  Indice: "Índice",
  "Fin (dia habil)": "Fin (día hábil)",
  Opcion: "Opción",
  Termino: "Término",
  "Retraso (dias)": "Retraso (días)",
  Penalizacion: "Penalización",
  Version: "Versión",
  Periodo: "Período",
};

// VD-5: `TablaDensa` pone el texto original en el `title` de toda celda con `presentar`. Eso es el exacto de una
// cifra, pero en un rotulo, un codigo o una fecha mostraba el valor interno al pasar el raton («spi_error», «AL-1»).
// Una columna de texto se presenta con `celda`, que no lleva `title`; el orden sigue usando el valor de la fila.
export function sinTitulo(clave: string, presentar: (valor: string) => string): (fila: FilaDensa) => string {
  return (fila) => {
    const valor = fila[clave] ?? "";
    return valor ? presentar(valor) : valor;
  };
}

export function columnasDe(
  titulos: string[],
  numericas: string[] = [],
  presentar: Record<string, (valor: string) => string> = {},
) {
  return titulos.map((t) => {
    const propio = presentar[t];
    const numerica = numericas.includes(t);
    return {
      clave: t,
      titulo: TITULOS_VISIBLES[t] ?? t,
      numerica,
      ordenable: false,
      // Las cifras se leen en es-VE (el exacto queda en el title); una columna con texto propio lo compone encima.
      presentar: numerica ? (valor: string) => formatoMontoEsVe((propio ?? ((v: string) => v))(valor)) : undefined,
      celda: !numerica && propio ? sinTitulo(t, propio) : undefined,
    };
  });
}

// VD-5: el umbral de una alerta tiene la forma fija «0.9000 (SUPUESTO_DECLARADO)» (`alertas_en_filas` de
// aplicacion/control.py; sin cifra si el umbral no aplica). Se parte solo esa forma, para que el exacto vaya en el
// title de la cifra y no el codigo de la naturaleza; otra cosa (o un texto mas largo que el tope) devuelve null.
const UMBRAL = /^([-+]?[0-9]{1,30}(?:\.[0-9]{1,30})?)? ?\(([A-Z_]{1,40})\)$/;
const LARGO_MAXIMO_UMBRAL = 128;

export function partirUmbral(texto: string): { cifra: string; naturaleza: string } | null {
  if (texto.length > LARGO_MAXIMO_UMBRAL) return null;
  const m = UMBRAL.exec(texto);
  return m ? { cifra: m[1] ?? "", naturaleza: m[2]! } : null;
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

// Como `useCarga`, pero mientras vuelve a pedir tras una escritura deja a la vista lo último que llego: asi el
// formulario que acaba de escribir no se desmonta (y su aviso de exito no se pierde) detras de un esqueleto.
export function useCargaSuave<T>(ruta: string, alExpirar: () => void): Carga<T> {
  const carga = useCarga<T>(ruta, alExpirar);
  const [ultimo, setUltimo] = useState<T | null>(null);
  if (carga.estado === "listo" && carga.datos !== ultimo) setUltimo(carga.datos);
  if (carga.estado === "cargando" && ultimo !== null) return { estado: "listo", datos: ultimo };
  return carga;
}
