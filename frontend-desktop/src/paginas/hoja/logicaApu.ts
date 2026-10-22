// Lógica pura de la edición del APU y del cambio de insumo (rebanada 3c-3: E6, E7 y E8 del diseño §4.4). Todo lo que
// escribe la persona viaja como texto, tal cual; el servidor valida con los mensajes de la clásica. Aquí no se convierte
// nada a número.
import { enteroDeDigitos } from "./logica";
import type { DetalleApu, Monto } from "./logica";

const rutaDelBorrador = (id: string) => `/v1/hoja/borradores/${id}`;

// El código de una partida puede traer «/» (AF-CODO-1/2): va codificado para que sea un solo trozo de la ruta.
export const rutaDeApu = (id: string, partida: string) => `${rutaDelBorrador(id)}/apu/${encodeURIComponent(partida)}`;
export const rutaDeInsumo = (id: string, partida: string) => `${rutaDeApu(id, partida)}/insumo`;

// La clásica muestra a lo sumo 300 candidatos y pide uno más (301) para saber si hay más (ui/paginas/hoja.py:1515).
export const LIMITE_DE_INSUMOS = 300;

export function rutaDeInsumos(id: string, tipo: string, texto: string): string {
  const consulta = new URLSearchParams({ tipo });
  if (texto.trim() !== "") consulta.set("texto", texto.trim());
  consulta.set("limite", String(LIMITE_DE_INSUMOS + 1));
  return `${rutaDelBorrador(id)}/insumos?${consulta.toString()}`;
}

// Lo que la clásica agrega tras el error del APU (ui/paginas/hoja.py:1674).
export const FRASE_DE_APU = "La hoja sigue con el último APU válido.";

// --- cantidades y rendimiento (E6) ---

// Los tres rubros de un APU, con la clave con que los nombra el servidor.
export type RubroDeApu = "materiales" | "equipos" | "mano de obra";

export interface EdicionDeApu {
  rendimiento: string;
  cantidades: Record<string, string[]>;
}

export function sembrarApu(detalle: Pick<DetalleApu, "rendimiento" | "grupos">): EdicionDeApu {
  return {
    rendimiento: detalle.rendimiento,
    cantidades: Object.fromEntries(detalle.grupos.map((g) => [g.clave, g.filas.map((f) => f.cantidad ?? "")])),
  };
}

export function cambiarCantidadDeLinea(edicion: EdicionDeApu, rubro: string, indice: number, texto: string): EdicionDeApu {
  return {
    ...edicion,
    cantidades: {
      ...edicion.cantidades,
      [rubro]: (edicion.cantidades[rubro] ?? []).map((c, i) => (i === indice ? texto : c)),
    },
  };
}

export function cambiarRendimiento(edicion: EdicionDeApu, texto: string): EdicionDeApu {
  return { ...edicion, rendimiento: texto };
}

export interface CuerpoDeApu {
  rev: number;
  rendimiento: string;
  materiales: string[];
  equipos: string[];
  mano_obra: string[];
}

export function cuerpoDeApu(rev: number, edicion: EdicionDeApu): CuerpoDeApu {
  return {
    rev,
    rendimiento: edicion.rendimiento,
    materiales: edicion.cantidades["materiales"] ?? [],
    equipos: edicion.cantidades["equipos"] ?? [],
    mano_obra: edicion.cantidades["mano de obra"] ?? [],
  };
}

export type UbicacionDeApu = { campo: "rendimiento" } | { campo: "linea"; grupo: string; fila: number };

// «{rubro}, fila {n}: …» (ui/hoja.py:937-955) o «rendimiento…» (ui/hoja.py:972). Otro mensaje no se ubica.
export function ubicarErrorDeApu(detalle: string): UbicacionDeApu | null {
  const linea = /^(materiales|equipos|mano de obra), fila (\d+): /.exec(detalle);
  if (linea) return { campo: "linea", grupo: linea[1]!, fila: enteroDeDigitos(linea[2]!) };
  if (/^rendimiento\b/.test(detalle)) return { campo: "rendimiento" };
  return null;
}

// --- cambio de insumo (E7, E8) ---

export const TIPOS_DE_LINEA = [
  { valor: "material", rotulo: "Material", grupo: "materiales" },
  { valor: "equipo", rotulo: "Equipo", grupo: "equipos" },
  { valor: "mano_obra", rotulo: "Mano de obra", grupo: "mano de obra" },
] as const;

export function cuerpoDeInsumo(
  rev: number,
  tipo: string,
  indice: number,
  insumo: string,
): { rev: number; tipo: string; indice: number; insumo: string } {
  return { rev, tipo, indice, insumo };
}

export interface InsumoCandidato {
  codigo: string;
  descripcion: string;
  unidad: string;
  precio: Monto;
}

export interface InsumosRespuesta {
  insumos: InsumoCandidato[];
  hay_mas: boolean;
}

// A lo sumo 300; si hay más (el servidor lo dice o vino el 301) se pide acotar por descripción.
export function insumosVisibles(respuesta: InsumosRespuesta): { insumos: InsumoCandidato[]; hayMas: boolean } {
  return {
    insumos: respuesta.insumos.slice(0, LIMITE_DE_INSUMOS),
    hayMas: respuesta.hay_mas || respuesta.insumos.length > LIMITE_DE_INSUMOS,
  };
}

// El servidor arma «Estado de {clave}: {estado}» (ui/paginas/hoja.py:1738); a la persona solo le sirve el estado. La clave
// trae «:» pero no «: », así que el estado empieza donde sigue una palabra en mayúsculas con dos puntos (ERROR:, PENDIENTE:…).
export function textoDeEstado(estado: string): string {
  return estado.replace(/^Estado de .*?: (?=[A-ZÁÉÍÓÚÑ]+(?::| \|))/, "");
}
