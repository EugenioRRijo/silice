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

export function rutaDeInsumos(id: string, tipo: string, texto: string, limite = LIMITE_DE_INSUMOS + 1): string {
  const consulta = new URLSearchParams({ tipo });
  if (texto.trim() !== "") consulta.set("texto", texto.trim());
  consulta.set("limite", String(limite));
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
  // Uno por fila de Materiales en orden; "" = sin desperdicio.
  desperdicios: string[];
}

// En Materiales, las filas con desperdicio siembran la neta (no `f.cantidad`, que ya lo incluye) y su porcentaje.
export function sembrarApu(
  detalle: Pick<DetalleApu, "rendimiento" | "grupos"> & Partial<Pick<DetalleApu, "desperdicios">>,
): EdicionDeApu {
  const porFila = new Map((detalle.desperdicios ?? []).map((d) => [d.fila, d]));
  const materiales = detalle.grupos.find((g) => g.clave === "materiales");
  return {
    rendimiento: detalle.rendimiento,
    cantidades: Object.fromEntries(
      detalle.grupos.map((g) => [
        g.clave,
        g.filas.map((f, i) =>
          g.clave === "materiales" ? (porFila.get(i + 1)?.neta ?? f.cantidad ?? "") : (f.cantidad ?? ""),
        ),
      ]),
    ),
    desperdicios: (materiales?.filas ?? []).map((_, i) => porFila.get(i + 1)?.porcentaje ?? ""),
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

export function cambiarDesperdicioDeLinea(edicion: EdicionDeApu, indice: number, texto: string): EdicionDeApu {
  return {
    ...edicion,
    desperdicios: edicion.desperdicios.map((d, i) => (i === indice ? texto : d)),
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
  desperdicios: string[];
}

export function cuerpoDeApu(rev: number, edicion: EdicionDeApu): CuerpoDeApu {
  return {
    rev,
    rendimiento: edicion.rendimiento,
    materiales: edicion.cantidades["materiales"] ?? [],
    equipos: edicion.cantidades["equipos"] ?? [],
    mano_obra: edicion.cantidades["mano de obra"] ?? [],
    desperdicios: edicion.desperdicios,
  };
}

export type UbicacionDeApu =
  | { campo: "rendimiento" }
  | { campo: "linea"; grupo: string; fila: number }
  | { campo: "desperdicio"; fila: number };

// «{rubro}, fila {n}: …» (ui/hoja.py:937-955) o «rendimiento…» (ui/hoja.py:972). El desperdicio de materiales se revisa
// antes que la línea para marcar el porcentaje y no la cantidad neta. Otro mensaje no se ubica.
export function ubicarErrorDeApu(detalle: string): UbicacionDeApu | null {
  const desperdicio = /^materiales, fila (\d+): el desperdicio/.exec(detalle);
  if (desperdicio) return { campo: "desperdicio", fila: enteroDeDigitos(desperdicio[1]!) };
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

// E2E-3: el Estado de la partida trae uno por renglón, y con la misma partida en varios renglones el servidor da a cada
// uno los mismos avisos en otro orden (primero el suyo). Se muestra cada conjunto una vez, el primero tal como llega: dos
// estados son el mismo si tienen los mismos avisos por severidad, sin importar el orden. Solo texto; nada se calcula.
export function estadosDeLaPartida(estados: readonly string[]): string[] {
  const forma = (texto: string) =>
    texto
      .split(" | ")
      .map((segmento) => {
        const m = /^([A-ZÁÉÍÓÚÑ]+): (.*)$/.exec(segmento);
        return m ? `${m[1]}: ${m[2]!.split("; ").sort().join("; ")}` : segmento;
      })
      .sort()
      .join(" | ");
  const vistos = new Set<string>();
  const unicos: string[] = [];
  for (const estado of estados) {
    const texto = textoDeEstado(estado);
    const clave = forma(texto);
    if (vistos.has(clave)) continue;
    vistos.add(clave);
    unicos.push(texto);
  }
  return unicos;
}

// --- agregar y quitar líneas (Tarea 26) ---

export const rutaDeLineas = (id: string, partida: string) => `${rutaDeApu(id, partida)}/lineas`;
export const rutaDeQuitarLinea = (id: string, partida: string) => `${rutaDeLineas(id, partida)}/quitar`;

export type TipoDeLinea = (typeof TIPOS_DE_LINEA)[number]["valor"];

// El rubro de la tabla (clave del servidor) con su tipo de línea y cómo se nombra en una frase.
export const RUBROS: Record<string, { tipo: TipoDeLinea; enFrase: string }> = {
  materiales: { tipo: "material", enFrase: "los materiales" },
  equipos: { tipo: "equipo", enFrase: "los equipos" },
  "mano de obra": { tipo: "mano_obra", enFrase: "la mano de obra" },
};

export const grupoDelTipo = (tipo: TipoDeLinea): string => TIPOS_DE_LINEA.find((t) => t.valor === tipo)!.grupo;

// Una línea del APU a la que se le pide algo (quitarla o cambiarle el insumo): su rubro, su índice desde 0, cómo se llama y
// el id de su botón, al que vuelve el foco al cerrar el diálogo.
export interface LineaApu {
  grupo: string;
  indice: number;
  descripcion: string;
  boton: string;
}

// Lo que viaja al agregar una línea: todo como texto tal cual. Con `insumo` (su código) los demás datos del insumo los pone
// la lista de la versión; sin él, es uno nuevo con su descripción, su unidad y su precio.
export interface LineaNueva {
  tipo: TipoDeLinea;
  insumo: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  precio: string;
  depreciacion: string;
  modalidad: "jornal" | "destajo";
}

export function cuerpoDeLinea(rev: number, linea: LineaNueva): LineaNueva & { rev: number } {
  return { rev, ...linea };
}

export type CampoDeLinea = "insumo" | "unidad" | "cantidad" | "precio" | "depreciacion";

// El campo del diálogo al que va un 422 al agregar una línea: los textos de la hoja empiezan por el campo
// (aplicacion/hoja_lineas_apu.py y hoja_edicion.agregar_linea_apu). Otro texto no se ubica: va al aviso del diálogo.
export function campoDelErrorDeLinea(detalle: string): CampoDeLinea | null {
  const inicios: [CampoDeLinea, string[]][] = [
    ["cantidad", ["La cantidad", "Escriba la cantidad"]],
    ["precio", ["El precio", "Escriba el precio"]],
    ["depreciacion", ["La depreciación", "Escriba la depreciación"]],
    ["unidad", ["La unidad", "Escriba la unidad"]],
    ["insumo", ["Ese insumo", "La descripción", "Escriba la descripción"]],
  ];
  for (const [campo, prefijos] of inicios) {
    if (prefijos.some((p) => detalle.startsWith(p))) return campo;
  }
  return null;
}

// Tras agregar o quitar una línea, lo que se edita cambia de forma: se agrega (al final de su rubro) o se quita la cantidad
// de esa línea, en lo escrito y en lo aceptado, sin tocar lo demás (lo tocado y no aceptado se conserva).
export function conLineaAgregada(edicion: EdicionDeApu, grupo: string, cantidad: string): EdicionDeApu {
  return {
    ...edicion,
    cantidades: { ...edicion.cantidades, [grupo]: [...(edicion.cantidades[grupo] ?? []), cantidad] },
    desperdicios: grupo === "materiales" ? [...edicion.desperdicios, ""] : edicion.desperdicios,
  };
}

export function conLineaQuitada(edicion: EdicionDeApu, grupo: string, indice: number): EdicionDeApu {
  return {
    ...edicion,
    cantidades: { ...edicion.cantidades, [grupo]: (edicion.cantidades[grupo] ?? []).filter((_, i) => i !== indice) },
    desperdicios: grupo === "materiales" ? edicion.desperdicios.filter((_, i) => i !== indice) : edicion.desperdicios,
  };
}
