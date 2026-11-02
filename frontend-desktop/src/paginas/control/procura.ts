// MP-7, Tarea 24: el contrato de `/v1/procura` (Tarea 23) y las funciones puras de la pestaña «Procura».
// Las cantidades llegan exactas con punto y se leen con `formatoEsVe` una sola vez; las fechas, aaaa-mm-dd, con
// `fechaDeRanura`. Lo que la persona teclea (cantidad, precio, plazo) viaja tal cual: lo interpreta el servidor con la
// regla de la coma decimal (`aplicacion/cifras.py`); aqui solo se revisa antes, para decir el error en su campo.

export interface NecesidadDeMaterial {
  descripcion: string;
  unidad: string;
  cantidad: string;
  partidas: string[];
  se_necesita: string | null;
  pedir_a_mas_tardar: string | null;
  plazo: number;
  pedida: string | null;
  recibida: string | null;
}

export interface AlertaDeCompra {
  severidad: "AVISO" | "ERROR";
  texto: string;
}

// Por partida, la causa de retraso que sugiere la procura al corte (la clave de las causas de Valuaciones).
export interface CausaSugerida {
  partida: string;
  causa: string;
}

export interface Procura {
  necesidades: NecesidadDeMaterial[];
  alertas: AlertaDeCompra[];
  aviso: string | null;
  causas_sugeridas: CausaSugerida[];
}

// Las claves de cada fila de la tabla de materiales (son tambien sus titulos).
export const COLUMNAS_PROCURA = [
  "Insumo",
  "Cantidad",
  "Partidas",
  "Se necesita",
  "Pedir a más tardar",
  "Plazo (días hábiles)",
  "Pedida",
  "Recibida",
] as const;

export const COLUMNAS_ALERTAS_DE_COMPRA = ["Severidad", "Qué pasa"] as const;

// La severidad de la procura en el nombre del componente comun (`Severidad`: icono y nombre, nunca solo color). El
// AVISO de la procura es una advertencia: aun hay tiempo de pedir.
export function severidadDeCompra(severidad: string): string {
  return severidad === "AVISO" ? "ADVERTENCIA" : severidad;
}

// «1 día hábil», «5 días hábiles».
export function diasHabiles(dias: string): string {
  return dias === "1" ? "1 día hábil" : `${dias} días hábiles`;
}

// El material en el nombre accesible de un boton de una fila: «Pedida hoy: Cemento gris (saco)» (empieza por lo visible).
export function delMaterial(n: Pick<NecesidadDeMaterial, "descripcion" | "unidad">): string {
  return n.unidad ? `${n.descripcion} (${n.unidad})` : n.descripcion;
}

// Los campos del dialogo «Recibida…».
export type CampoDeRecepcion = "fecha" | "cantidad" | "precio";

// El campo al que pertenece un mensaje de regla de la API (`aplicacion/procura.py`: «La cantidad debe ser…», «El precio
// debe ser…», «La fecha de la compra…»); null si no es de ningun campo (se dice en el dialogo).
export function campoDelError(detalle: string): CampoDeRecepcion | null {
  if (detalle.startsWith("La cantidad")) return "cantidad";
  if (detalle.startsWith("El precio")) return "precio";
  if (detalle.startsWith("La fecha")) return "fecha";
  return null;
}

// Las causas sugeridas por partida, solo las que estan en la lista de causas de Valuaciones (una clave desconocida
// no se preelige: el selector no tendria esa opcion).
export function sugeridasPorPartida(sugeridas: CausaSugerida[], claves: string[]): Record<string, string> {
  const validas = new Set(claves);
  return Object.fromEntries(sugeridas.filter((s) => validas.has(s.causa)).map((s) => [s.partida, s.causa]));
}

// La ayuda del selector de causa mientras muestra la sugerida (la procura solo sugiere «Compra tardía», Tarea 23).
export const AYUDA_CAUSA_SUGERIDA = "Sugerida por la procura: un material de esta partida llegó tarde. Puede cambiarla.";

// La causa de una linea de valuacion: la que eligio la persona o, si no ha tocado el selector, la que sugiere la
// procura para su partida («» = sin causa).
export function causaDeLinea(
  linea: { partida: string; causa: string },
  elegida: boolean,
  sugeridas: Record<string, string>,
): string {
  return elegida ? linea.causa : (sugeridas[linea.partida.trim()] ?? "");
}
