// Logica pura de «Reajuste de precios»: arma lo que se manda a la API con el texto que escribe la persona y lo que
// se muestra con el texto que devuelve. No calcula ni redondea nada (RB-2): el estudio lo hace el servidor.
import { leerCifra } from "../../indicadores/cifraEscrita";
import { formatoMontoEsVe } from "../../indicadores/formatoEsVe";
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

// VB-5: los valores internos de los desplegables y de los componentes (los del nucleo, que la API espera tal cual)
// con su rotulo en español. El valor que se manda no cambia; uno que no esta aqui se muestra tal cual.
const ROTULOS_DE_OPCION: Record<string, string> = {
  mensual: "Mensual",
  trimestral: "Trimestral",
  escalatoria: "Escalatoria",
  comprobacion: "Comprobación directa",
  ambos: "Ambos (escalatoria y comprobación)",
  por_partida: "Por partida",
  declarada: "Declarada",
  materiales: "Materiales",
  equipos: "Equipos",
  mano_obra: "Mano de obra",
};

export function rotuloDeOpcion(valor: string): string {
  return ROTULOS_DE_OPCION[valor] ?? valor;
}

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

// --- cifras tecleadas (regla de Eugenio, 2026-10-25: coma decimal, punto de miles) ----------------
// R, el peso de cada componente y la cantidad ejecutada se escriben con coma; la API los recibe con punto. Los enteros
// (duracion en meses, numero de periodo) y las fechas no son cifras decimales y van tal cual. Un campo en blanco no se
// juzga aqui: va tal cual y la API dice lo que falta (un peso en blanco es «sin peso»).

export const ROTULO_R = "R (fracción no reajustable)";

// El error de una cifra escrita, o null si se lee o esta en blanco.
export function errorDeCifra(texto: string): string | null {
  if (texto.trim() === "") return null;
  const lectura = leerCifra(texto);
  return "error" in lectura ? lectura.error : null;
}

function cifraParaApi(texto: string): string {
  const lectura = leerCifra(texto);
  return "valor" in lectura ? lectura.valor : texto;
}

// Cada cifra mal escrita del formulario, con el nombre del campo delante («Peso, Componentes fila 2: ...»), en el
// orden en que aparecen. Lo ejecutado a mano no se revisa si sale de las valuaciones (no se manda).
export function erroresDeCifras(f: Formulario): string[] {
  const errores: string[] = [];
  const revisar = (rotulo: string, texto: string) => {
    const error = errorDeCifra(texto);
    if (error) errores.push(`${rotulo}: ${error}`);
  };
  revisar(ROTULO_R, f.clausula.r);
  f.componentes.forEach((c, i) => revisar(`Peso, Componentes fila ${i + 1}`, c.peso ?? ""));
  if (!f.con_valuaciones) f.ejecutado.forEach((e, i) => revisar(`Cantidad, Ejecutado fila ${i + 1}`, e.cantidad ?? ""));
  return errores;
}

// El cuerpo de calcular, guardar y excel. Las filas en blanco de periodos y ejecutado no se mandan; los tres
// componentes si, como la pantalla de Streamlit (el servidor dice cual serie falta). Con las valuaciones, lo
// ejecutado sale de ellas y no se manda. Las cifras van con punto (la pagina las revisa antes con `erroresDeCifras`).
export function armarCuerpo(proyecto: string, f: Formulario): CuerpoEstudio {
  return {
    proyecto,
    version: f.version,
    clausula: { ...clausulaParaEnviar(f.clausula), r: cifraParaApi(f.clausula.r) },
    componentes: f.componentes.map((c) => ({ ...c, peso: cifraParaApi(c.peso ?? "") })),
    periodos: f.periodos.filter(hayFilaConDatos),
    ejecutado: f.con_valuaciones
      ? []
      : f.ejecutado.filter(ejecutadoConDatos).map((e) => ({ ...e, cantidad: cifraParaApi(e.cantidad ?? "") })),
    con_valuaciones: f.con_valuaciones,
  };
}

const FECHA_ISO = /^(\d{4}-\d{2})-\d{2}$/;

// Como Streamlit: el primer anio corre desde el inicio del contrato si no se escribe otra fecha, y el mes base de
// los indices se declara con su dia 1 (se escribe cualquier dia del mes). Lo que no parece fecha pasa tal cual y
// la API dice que esta mal.
function clausulaParaEnviar(c: ClausulaTextos): ClausulaTextos {
  const base = FECHA_ISO.exec(c.fecha_base_indices.trim());
  return {
    ...c,
    fecha_referencia_primer_anio: c.fecha_referencia_primer_anio.trim() || c.fecha_inicio,
    fecha_base_indices: base ? `${base[1]}-01` : c.fecha_base_indices,
  };
}

// El «1» que trae la primera fila de lo ejecutado no cuenta como dato: sin partida, cantidad ni fuente es una fila
// en blanco (en Streamlit obligaba a borrarla).
function ejecutadoConDatos(fila: Fila): boolean {
  return hayFilaConDatos({ partida: fila.partida ?? "", cantidad: fila.cantidad ?? "", fuente: fila.fuente ?? "" });
}

export function columnasDeResultado(columnas: string[]): ColumnaDensa[] {
  return columnas.map((titulo) => ({ clave: titulo, titulo, numerica: !COLUMNAS_DE_TEXTO.has(titulo),
    // Montos y tasas en es-VE; el texto exacto de la API queda en el title de la celda.
    presentar: COLUMNAS_DE_TEXTO.has(titulo) ? undefined : formatoMontoEsVe,
    // El mecanismo, con su rotulo y sin el valor interno en el title (VD-5: `presentar` lo pondria).
    celda: titulo === "Mecanismo" ? (fila: FilaDensa) => (fila.Mecanismo ? rotuloDeOpcion(fila.Mecanismo) : "") : undefined,
  }));
}

// VB-10: las 12 columnas de la API no caben a 1366 px. La tabla principal lleva la moneda del estudio; la segunda,
// el período con la otra moneda y la tasa (sus titulos sin «(otra)», la tabla ya lo dice). «Marcas» sale de las
// tablas y se lee como nota por período (`marcasPorPeriodo`). Las cifras no cambian: son las mismas celdas.
const OTRA = " (otra)";

export function partirResultado(columnas: string[]): { principal: ColumnaDensa[]; otra: ColumnaDensa[] } {
  // Sin orden: la fila Total va siempre al final.
  const todas = columnasDeResultado(columnas.filter((c) => c !== "Marcas")).map((c) => ({ ...c, ordenable: false }));
  const enOtra = (c: ColumnaDensa) => c.clave.endsWith(OTRA) || c.clave === "Tasa";
  return {
    principal: todas.filter((c) => !enOtra(c)),
    otra: todas
      .filter((c) => c.clave === "Período" || enOtra(c))
      .map((c) => ({ ...c, titulo: c.clave.endsWith(OTRA) ? c.clave.slice(0, -OTRA.length) : c.titulo })),
  };
}

// Las marcas de cada período («Período: marcas»). Las de la fila Total son el estado y los avisos, que la pagina ya
// muestra aparte.
export function marcasPorPeriodo(filas: Fila[]): string[] {
  return filas
    .filter((f) => f["Período"] !== "Total" && (f.Marcas ?? "").trim() !== "")
    .map((f) => `${f["Período"]}: ${f.Marcas}`);
}

export function filasDeResultado(filas: Fila[]): FilaDensa[] {
  return filas.map((fila, i) => ({ id: String(i), ...fila }));
}
