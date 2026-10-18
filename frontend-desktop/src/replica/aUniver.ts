// UNICO lugar de la interfaz que convierte el contrato neutro de la replica (coordenadas de Excel en base 1,
// anchos en caracteres, altos en puntos, estilos de la hoja de calculo) a la instantanea de Univer (base 0,
// pixeles, IStyleData). Si cambia la version de Univer, solo cambia este archivo (RS2-1).
//
// Decisiones de fidelidad (ver la bitacora de la tarea 2.4):
//  - Cada celda lleva el TEXTO ya formateado (formatoNumero.ts) como cadena y sin `f`: Univer no recalcula ni
//    reinterpreta nada. El valor guardado y la formula van en `custom` por si hacen falta (tooltip, Capa Delta).
//  - Las celdas cubiertas por una combinada no vienen en el contrato (RS2-10) y no se crean.
//  - Excel alinea numeros/fechas a la derecha y booleanos al centro cuando la alineacion es General; como todo
//    llega como texto, esa alineacion se pone aqui, explicita, en una variante del estilo.
import type { ICellData, IStyleData, IWorkbookData, IWorksheetData } from "@univerjs/presets";
import type { EstiloVisualRespuesta, HojaVisualRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { parsearA1, parsearRango } from "./coordenadas";
import { formatearMostrado, tipoDeValor } from "./formatoNumero";

// Excel: ancho en pixeles a 96 dpi con la fuente por omision = ancho guardado * 7 (el guardado ya incluye los
// 5 px de relleno: trunc((caracteres * 7 + 5) / 7 * 256) / 256).
const PX_POR_UNIDAD_DE_ANCHO = 7;
const ANCHO_POR_OMISION_PX = 64; // 8,43 caracteres
const ALTO_POR_OMISION_PX = 20; // 15 pt
const ANCHO_CABECERA_FILAS_PX = 46;
const ALTO_CABECERA_COLUMNAS_PX = 20;
const FILAS_DE_SOBRA = 30;
const MINIMO_FILAS = 100;
const COLUMNAS_DE_SOBRA = 10;
const MINIMO_COLUMNAS = 26;

export function pxDeAncho(ancho: string): number {
  return Math.round(Number(ancho) * PX_POR_UNIDAD_DE_ANCHO);
}

export function pxDeAlto(puntos: string): number {
  return Math.round((Number(puntos) * 96) / 72);
}

// Valores numericos de las enumeraciones de Univer (HorizontalAlign, VerticalAlign, WrapStrategy,
// BorderStyleTypes, BooleanNumber), fijados por la prueba de aUniver.test.ts.
const H: Record<string, number> = { left: 1, center: 2, right: 3, justify: 4 };
const V: Record<string, number> = { top: 1, center: 2, bottom: 3 };
const ENVOLVER = 3;
const BORDE: Record<string, number> = { hair: 2, dotted: 3, dashed: 4, thin: 1, double: 7, medium: 8, thick: 13 };
const NEGRO = "#000000";

type Variante = "base" | "derecha" | "centro";

function estiloUniver(e: EstiloVisualRespuesta, variante: Variante): IStyleData {
  const s: Record<string, unknown> = {};
  if (e.relleno) s.bg = { rgb: e.relleno };
  if (e.fuente) s.ff = e.fuente;
  if (e.tamano) s.fs = Number(e.tamano);
  if (e.negrita) s.bl = 1;
  if (e.cursiva) s.it = 1;
  if (e.subrayado) s.ul = { s: 1 };
  if (e.color) s.cl = { rgb: e.color };

  const h = e.alineacion_h ? H[e.alineacion_h] : variante === "derecha" ? 3 : variante === "centro" ? 2 : undefined;
  if (h !== undefined) s.ht = h;
  if (e.alineacion_v && V[e.alineacion_v] !== undefined) s.vt = V[e.alineacion_v];
  if (e.ajustar_texto) s.tb = ENVOLVER;

  const lados = ["t", "r", "b", "l"] as const;
  const bd: Record<string, { s: number; cl: { rgb: string } }> = {};
  lados.forEach((lado, i) => {
    const estilo = e.bordes[i];
    if (estilo) bd[lado] = { s: BORDE[estilo] ?? 1, cl: { rgb: NEGRO } };
  });
  if (Object.keys(bd).length > 0) s.bd = bd;
  return s as IStyleData;
}

function varianteDe(e: EstiloVisualRespuesta, mostrado: string): Variante {
  if (e.alineacion_h) return "base";
  const tipo = tipoDeValor(mostrado);
  if (tipo === "numero" || tipo === "fecha") return "derecha";
  if (tipo === "booleano") return "centro";
  return "base";
}

function convertirHoja(
  hoja: HojaVisualRespuesta,
  id: string,
  estilos: EstiloVisualRespuesta[],
  idDeEstilo: (indice: number, variante: Variante) => string,
): Partial<IWorksheetData> {
  const cellData: Record<number, Record<number, ICellData>> = {};
  for (const c of hoja.celdas) {
    const estilo = estilos[c.estilo];
    const fila = (cellData[c.fila - 1] ??= {});
    fila[c.columna - 1] = {
      v: formatearMostrado(c.mostrado, estilo?.formato_numero ?? "General"),
      s: estilo ? idDeEstilo(c.estilo, varianteDe(estilo, c.mostrado)) : undefined,
      custom: { mostrado: c.mostrado, formula: c.formula },
    };
  }

  const columnData: Record<number, { w?: number; hd?: number }> = {};
  for (const [columna, ancho] of Object.entries(hoja.anchos)) {
    columnData[Number(columna) - 1] = { w: pxDeAncho(ancho) };
  }
  for (const columna of hoja.ocultas_columnas) {
    columnData[columna - 1] = { ...columnData[columna - 1], hd: 1 };
  }

  const rowData: Record<number, { h?: number; ia?: number; hd?: number }> = {};
  for (const [fila, alto] of Object.entries(hoja.altos)) {
    rowData[Number(fila) - 1] = { h: pxDeAlto(alto), ia: 0 };
  }
  for (const fila of hoja.ocultas_filas) {
    rowData[fila - 1] = { ...rowData[fila - 1], hd: 1 };
  }

  const mergeData = hoja.combinadas.flatMap((rango) => {
    const r = parsearRango(rango);
    return r ? [r] : [];
  });

  const fija = hoja.fijas ? parsearA1(hoja.fijas) : null;
  const freeze = fija
    ? { xSplit: fija.columna0, ySplit: fija.fila0, startColumn: fija.columna0, startRow: fija.fila0 }
    : { xSplit: 0, ySplit: 0, startColumn: 0, startRow: 0 };

  return {
    id,
    name: hoja.nombre,
    tabColor: "",
    hidden: hoja.visible ? 0 : 1,
    freeze,
    rowCount: Math.max(hoja.filas + FILAS_DE_SOBRA, MINIMO_FILAS),
    columnCount: Math.max(hoja.columnas + COLUMNAS_DE_SOBRA, MINIMO_COLUMNAS),
    zoomRatio: 1,
    scrollTop: 0,
    scrollLeft: 0,
    defaultColumnWidth: ANCHO_POR_OMISION_PX,
    defaultRowHeight: ALTO_POR_OMISION_PX,
    mergeData,
    cellData,
    rowData,
    columnData,
    rowHeader: { width: ANCHO_CABECERA_FILAS_PX },
    columnHeader: { height: ALTO_CABECERA_COLUMNAS_PX },
    showGridlines: 1,
    rightToLeft: 0,
  } as Partial<IWorksheetData>;
}

export function aUniver(libro: LibroVisualRespuesta): IWorkbookData {
  const styles: Record<string, IStyleData> = {};
  const idDeEstilo = (indice: number, variante: Variante): string => {
    const id = `e${indice}${variante === "base" ? "" : variante === "derecha" ? "d" : "c"}`;
    if (!(id in styles)) styles[id] = estiloUniver(libro.estilos[indice], variante);
    return id;
  };

  const sheets: Record<string, Partial<IWorksheetData>> = {};
  const sheetOrder: string[] = [];
  libro.hojas.forEach((hoja, i) => {
    const id = `hoja-${i}`;
    sheetOrder.push(id);
    sheets[id] = convertirHoja(hoja, id, libro.estilos, idDeEstilo);
  });

  return {
    id: "libro",
    name: libro.nombre,
    appVersion: "1.0.3",
    locale: "esES" as IWorkbookData["locale"],
    styles,
    sheetOrder,
    sheets,
  };
}
