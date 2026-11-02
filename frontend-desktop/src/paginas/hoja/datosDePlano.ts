// Respuestas ficticias de las rutas del plano (P1 a P6) con la forma del contrato (docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md).
// Los conteos son los del caso OF-001 con su plano de muestra (tests/unit/test_ui_hoja_planos.py: 33 importados, 0 no reconocidos,
// 9 aproximados, 6 pendientes; 48 líneas de informe; 6 alturas pendientes y 2 circuitos supuestos), escritos a mano. Todo ficticio.
import type { ImportacionRespuesta, FilaDeInforme, ResumenDeFusionRespuesta } from "./logicaPlano";
import type { Resumen } from "./logica";

export const UNIDADES = ["m", "cm", "mm", "dm", "in", "ft"];

function filas(tipo: string, cuantas: number, desde: number, mensaje: (i: number) => string): FilaDeInforme[] {
  return Array.from({ length: cuantas }, (_, k) => ({
    tipo,
    referencia: `Capa ${tipo.toUpperCase().slice(0, 3)}`,
    fila: `F${desde + k}`,
    mensaje: mensaje(desde + k),
  }));
}

// 33 + 9 + 6 = 48 líneas, en el orden que las cuenta el servidor.
export const INFORME_OF001: FilaDeInforme[] = [
  ...filas("Importado", 33, 1, (i) => `Fila ${i} importada del plano`),
  ...filas("Aproximado", 9, 34, (i) => `La fila ${i} se aproximó al entero más cercano`),
  ...filas("Pendiente", 6, 43, (i) => `Falta la altura del ambiente de la fila ${i}`),
];

export const CONTEOS_OF001 = [
  { rotulo: "Importado", cantidad: 33 },
  { rotulo: "No reconocido", cantidad: 0 },
  { rotulo: "Aproximado", cantidad: 9 },
  { rotulo: "Pendiente", cantidad: 6 },
];

export const AVISO_PENDIENTES =
  "Si fusiona ahora, los ambientes sin altura entran con 2,5 m provisionales y los circuitos supuestos quedan marcados en la auditoría. Puede cargarlos antes o corregirlos después en las tablas.";

export const ALTURAS_OF001 = Array.from({ length: 6 }, (_, k) => ({ id: `A${k + 1}`, nombre: `Oficina ${k + 1}` }));

export const CIRCUITOS_OF001 = [
  { id: "C1", fase: "1", neutro: "1", tierra: "1", puntos: "6" },
  { id: "C2", fase: "1", neutro: "1", tierra: "1", puntos: "6" },
];

export function importada(extra: Partial<ImportacionRespuesta> = {}): ImportacionRespuesta {
  return {
    estado: "importada",
    archivo: "of001.dxf",
    mensaje: "",
    pide_unidad: false,
    unidades: [],
    conteos: CONTEOS_OF001,
    informe: INFORME_OF001,
    alturas_pendientes: ALTURAS_OF001,
    circuitos_supuestos: CIRCUITOS_OF001,
    aviso_pendientes: AVISO_PENDIENTES,
    ...extra,
  };
}

export function sinPendientes(extra: Partial<ImportacionRespuesta> = {}): ImportacionRespuesta {
  return importada({
    conteos: CONTEOS_OF001.map((c) => (c.rotulo === "Pendiente" ? { ...c, cantidad: 0 } : c)),
    alturas_pendientes: [],
    circuitos_supuestos: [],
    aviso_pendientes: null,
    ...extra,
  });
}

export function detenida(extra: Partial<ImportacionRespuesta> = {}): ImportacionRespuesta {
  return {
    estado: "detenida",
    archivo: "sin_unidad.dxf",
    mensaje: "El dibujo no declara su unidad. Elija la unidad en que está dibujado.",
    pide_unidad: true,
    unidades: UNIDADES,
    conteos: [],
    informe: [],
    alturas_pendientes: [],
    circuitos_supuestos: [],
    aviso_pendientes: null,
    ...extra,
  };
}

export function rechazada(extra: Partial<ImportacionRespuesta> = {}): ImportacionRespuesta {
  return {
    estado: "rechazada",
    archivo: "roto.dxf",
    mensaje: "el archivo no es un dibujo DXF válido",
    pide_unidad: false,
    unidades: [],
    conteos: [],
    informe: [],
    alturas_pendientes: [],
    circuitos_supuestos: [],
    aviso_pendientes: null,
    ...extra,
  };
}

export const FUSION_OF001: ResumenDeFusionRespuesta = {
  por_tipo: CONTEOS_OF001,
  filas_por_tabla: [
    { rotulo: "Ambientes", cantidad: 6 },
    { rotulo: "Fuentes", cantidad: 6 },
    { rotulo: "Puntos", cantidad: 21 },
  ],
  origenes: 33, // el backend real con OF-001 (tests/unit/test_ui_hoja_planos.py y la medición de 3e-2)
};

export const MENSAJE_DE_FUSION =
  "Se fusionó «of001.dxf» con el borrador de la hoja: 6 ambientes, 6 fuentes y 21 puntos. Revise las filas en las tablas de abajo; la auditoría las evalúa como a las demás. Todavía no se guardó ninguna versión: use Guardar versión cuando esté conforme.";

export function resumenTrasFusion(rev: number): Resumen {
  return {
    rev,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
    cambios: 3,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
  };
}

export function respuestaDeFusion(rev: number) {
  return {
    rev,
    resumen: resumenTrasFusion(rev),
    fusion: FUSION_OF001,
    informe: INFORME_OF001,
    mensaje: MENSAJE_DE_FUSION,
  };
}
