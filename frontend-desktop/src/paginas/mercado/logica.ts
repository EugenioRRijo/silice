// Logica pura del «Estudio de mercado» (plan de montar un presupuesto, Tarea 15; diseno §5.1 y §10): los tipos del
// contrato de `api/rutas/mercado.py`, los textos que dependen de una cuenta, la ruta del estudio y el buscador de
// insumos. Sin React. Ningun monto se convierte en numero: llegan como texto con punto y se formatean al pintarlos
// (`formatoEsVe`), y lo que la persona teclea se envia tal cual (lo interpreta `aplicacion/cifras.py`).
import { pedir } from "../../api/cliente";
import type { GrupoDeResultados } from "../../comun/logicaBusqueda";

export type Lado = "compra" | "cobro";

export interface Estadisticas {
  n: number;
  minimo: string | null;
  q1: string | null;
  mediana: string | null;
  promedio: string | null;
  maximo: string | null;
  ids: number[]; // las observaciones de las que salen las cifras
  otras_monedas: number; // observaciones de la ventana en otra moneda (no entran)
  dias: number;
}

export interface Observacion {
  id: number;
  fuente_tipo: string;
  fuente: string;
  fecha: string;
  moneda: string;
  precio: string;
  nota: string;
  responsable: string;
  cuenta: boolean; // esta en la moneda de la carpeta y entra en las cifras
}

export interface Estudio {
  lado: Lado;
  codigo: string;
  moneda: string;
  estadisticas: Estadisticas;
  propuesta: { precio: string | null; razon: string };
  piso: string | null; // cobro: costo directo + administracion
  precio_unitario: string | null; // cobro: con utilidad, sin IVA
  observaciones: Observacion[];
}

// Los tipos de fuente de la API (`FuenteTipo`), en el orden del selector, con su nombre visible.
export const FUENTES: readonly (readonly [string, string])[] = [
  ["proveedor", "Proveedor"],
  ["competidor", "Competidor"],
  ["cotizacion", "Cotización"],
  ["maprex", "MaPreX"],
  ["compra", "Compra hecha"],
];

export function nombreDeFuente(tipo: string): string {
  return FUENTES.find(([valor]) => valor === tipo)?.[1] ?? tipo;
}

// La fuente que se propone al anotar: en compra, un proveedor; en cobro, un competidor.
export function fuenteInicial(lado: Lado): string {
  return lado === "compra" ? "proveedor" : "competidor";
}

export const DIAS_POR_OMISION = "90";

// La razon con que la API dice que el primer cuartil quedo por debajo del piso (`RAZON_POR_DEBAJO` de
// aplicacion/mercado.py, que compara los montos exactos). La pagina no recalcula la regla: reconoce la razon.
export const RAZON_POR_DEBAJO = "La competencia cobra menos que su costo: se propone su costo.";

// De 1 a 3.650 dias, entero, sin signos ni ceros a la izquierda (el limite de la API). Se compara como texto: un numero
// de dias no es un monto, pero asi la pagina no convierte nada.
export function diasValidos(texto: string): boolean {
  if (!/^[1-9][0-9]{0,3}$/.test(texto)) return false;
  return texto.length < 4 || texto <= "3650";
}

export function rutaDelEstudio(lado: Lado, codigo: string, dias: string, proyecto: string | null): string {
  const consulta = new URLSearchParams({ dias });
  if (proyecto) consulta.set("proyecto", proyecto);
  return `/v1/mercado/${lado}/${encodeURIComponent(codigo)}?${consulta.toString()}`;
}

export function rutaDeAfectados(codigo: string): string {
  return `/v1/mercado/compra/${encodeURIComponent(codigo)}/afectados`;
}

// Dos rutas distintas en la API (`/compra/{codigo}/usar` y `/cobro/{codigo}/usar`), escritas enteras para que la prueba
// de rutas del front (tests/unit/test_front_rutas_api.py) las reconozca.
export function rutaDeUsar(lado: Lado, codigo: string): string {
  const cual = encodeURIComponent(codigo);
  return lado === "compra" ? `/v1/mercado/compra/${cual}/usar` : `/v1/mercado/cobro/${cual}/usar`;
}

export function rutaDeAnular(id: number): string {
  return `/v1/mercado/observaciones/${id}/anular`;
}

// El TextInput de Carbon no enlaza su mensaje de error con el campo (solo la ayuda, y solo sin error): con error, el
// campo se describe con el mensaje, como hace CampoConBusqueda. Sin error no se pasa nada (queda la ayuda de Carbon).
export function describirError(id: string, invalido: boolean): { "aria-describedby"?: string } {
  return invalido ? { "aria-describedby": `${id}-error-msg` } : {};
}

// «A», «A y B», «A, B y C».
export function enumeracion(elementos: readonly string[]): string {
  if (elementos.length <= 1) return elementos.join("");
  return `${elementos.slice(0, -1).join(", ")} y ${elementos[elementos.length - 1]}`;
}

// Lo que se dice antes de confirmar un precio de compra (D-MP2: antes muestra que APU se moveran).
export function textoDeAfectados(apus: readonly string[]): string {
  if (apus.length === 0) return "Ninguna partida del catálogo usa este insumo: no cambiará el precio de ninguna.";
  return `Cambiará el precio en ${enumeracion(apus)}.`;
}

export function deObservaciones(n: number): string {
  return n === 1 ? "de 1 observación" : `de ${n} observaciones`;
}

export function enOtraMoneda(n: number): string {
  return n === 1
    ? "1 observación en otra moneda no entra en las cifras."
    : `${n} observaciones en otra moneda no entran en las cifras.`;
}

// Hoy, como lo da el selector de fecha (AAAA-MM-DD), en la hora local de quien usa la pagina.
export function hoyIso(ahora: Date = new Date()): string {
  const dos = (v: number) => String(v).padStart(2, "0");
  return `${ahora.getFullYear()}-${dos(ahora.getMonth() + 1)}-${dos(ahora.getDate())}`;
}

// --- Insumos del catalogo -------------------------------------------------------------------------------------------
// No hay una busqueda de insumos en el servidor (la de T10 es de partidas): se pide una vez `GET /insumos` (la lista del
// catalogo de la carpeta, la misma del «Catálogo de partidas e insumos») y se filtra en el navegador con la misma regla
// de palabras sin tildes ni mayusculas. Sirve para catalogos de cientos de insumos; con miles conviene la ruta propia.

export interface InsumoDelCatalogo {
  codigo: string;
  descripcion: string;
  tipo: string;
  unidad: string | null;
  precio_vigente: string | null;
}

const TIPO_DE_INSUMO: Record<string, string> = {
  material: "material",
  equipo: "equipo",
  mano_obra: "mano de obra",
};

function plano(texto: string): string {
  return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

function abortado(): Error {
  const error = new Error("Búsqueda cancelada");
  error.name = "AbortError";
  return error;
}

export function gruposDeInsumos(
  insumos: readonly InsumoDelCatalogo[],
  q: string,
  limite: number,
): GrupoDeResultados<InsumoDelCatalogo>[] {
  const palabras = plano(q).split(/\s+/).filter(Boolean);
  const hallados = insumos.filter((i) => {
    const texto = plano(`${i.codigo} ${i.descripcion}`);
    return palabras.every((p) => texto.includes(p));
  });
  return [
    {
      rotulo: "Insumos del catálogo",
      hayMas: hallados.length > limite,
      opciones: hallados.slice(0, limite).map((i) => ({
        clave: `insumo:${i.codigo}`,
        principal: i.descripcion,
        secundaria: [i.codigo, ...(i.unidad ? [i.unidad] : []), TIPO_DE_INSUMO[i.tipo] ?? i.tipo],
        valor: i,
      })),
    },
  ];
}

// La funcion `buscar` de CampoConBusqueda para los insumos. La lista se pide una vez por buscador; si falla, la
// siguiente busqueda la vuelve a pedir.
export function buscadorDeInsumos() {
  let lista: Promise<InsumoDelCatalogo[]> | null = null;
  return async (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<InsumoDelCatalogo>[]> => {
    if (senal.aborted) throw abortado();
    const pedida = lista ?? pedir<InsumoDelCatalogo[]>("/insumos");
    lista = pedida;
    let insumos: InsumoDelCatalogo[];
    try {
      insumos = await pedida;
    } catch (error) {
      if (lista === pedida) lista = null;
      throw error;
    }
    if (senal.aborted) throw abortado();
    return gruposDeInsumos(insumos, q, limite);
  };
}
