// Estado de las tres tablas de insumos. Todo es texto, tal como se teclea y tal como lo manda la API: el
// navegador no convierte ni calcula montos (plan de la ola 3 B, RB-2).

export type TipoTabla = "materiales" | "equipos" | "mano_obra";
export type Fila = Record<string, string>;
export interface Tablas {
  materiales: Fila[];
  equipos: Fila[];
  mano_obra: Fila[];
}

export interface ColumnaInsumo {
  clave: string;
  titulo: string;
  numerica?: boolean;
}

export const TIPOS: readonly TipoTabla[] = ["materiales", "equipos", "mano_obra"];

export const TITULOS: Record<TipoTabla, string> = {
  materiales: "Materiales",
  equipos: "Equipos",
  mano_obra: "Mano de obra",
};

// Las claves son las del contrato de la API; los titulos, los de la pagina clasica. En materiales `cantidad` se
// rotula «Consumo por unidad»: nunca la misma palabra que el rendimiento de la cuadrilla (spec §3.2).
export const COLUMNAS: Record<TipoTabla, readonly ColumnaInsumo[]> = {
  materiales: [
    { clave: "descripcion", titulo: "Descripción" },
    { clave: "unidad", titulo: "Unidad" },
    { clave: "cantidad", titulo: "Consumo por unidad", numerica: true },
    { clave: "precio", titulo: "Precio", numerica: true },
  ],
  equipos: [
    { clave: "descripcion", titulo: "Descripción" },
    { clave: "cantidad", titulo: "Cantidad", numerica: true },
    { clave: "precio", titulo: "Precio", numerica: true },
    { clave: "depreciacion", titulo: "Depreciación", numerica: true },
  ],
  mano_obra: [
    { clave: "descripcion", titulo: "Descripción" },
    { clave: "cantidad", titulo: "Cantidad", numerica: true },
    { clave: "sueldo", titulo: "Sueldo", numerica: true },
    { clave: "modalidad", titulo: "Modalidad" },
  ],
};

export function tablasVacias(): Tablas {
  return { materiales: [], equipos: [], mano_obra: [] };
}

export function filaVacia(tipo: TipoTabla): Fila {
  return Object.fromEntries(COLUMNAS[tipo].map((c) => [c.clave, ""]));
}

export function hayFilas(tablas: Tablas): boolean {
  return TIPOS.some((t) => tablas[t].length > 0);
}

// Convierte lo que llega de la API (o de la referencia) en una fila de texto con exactamente las columnas de la tabla.
export function normalizarFila(tipo: TipoTabla, origen: Record<string, unknown>): Fila {
  const fila = filaVacia(tipo);
  for (const clave of Object.keys(fila)) {
    const valor = origen[clave];
    fila[clave] = valor === null || valor === undefined ? "" : String(valor);
  }
  return fila;
}

export function normalizarTablas(origen: Partial<Record<TipoTabla, Record<string, unknown>[]>>): Tablas {
  return {
    materiales: (origen.materiales ?? []).map((f) => normalizarFila("materiales", f)),
    equipos: (origen.equipos ?? []).map((f) => normalizarFila("equipos", f)),
    mano_obra: (origen.mano_obra ?? []).map((f) => normalizarFila("mano_obra", f)),
  };
}

export function agregarFila(tablas: Tablas, tipo: TipoTabla, fila?: Record<string, unknown>): Tablas {
  return { ...tablas, [tipo]: [...tablas[tipo], normalizarFila(tipo, fila ?? {})] };
}

export function borrarFila(tablas: Tablas, tipo: TipoTabla, indice: number): Tablas {
  return { ...tablas, [tipo]: tablas[tipo].filter((_, i) => i !== indice) };
}

export function editarCelda(tablas: Tablas, tipo: TipoTabla, indice: number, clave: string, valor: string): Tablas {
  return {
    ...tablas,
    [tipo]: tablas[tipo].map((f, i) => (i === indice ? { ...f, [clave]: valor } : f)),
  };
}
