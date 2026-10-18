// Conversion del contrato neutro de la replica (coordenadas de Excel en base 1, anchos en caracteres, altos en
// puntos, estilos de la hoja de calculo) a la instantanea de Univer (base 0, pixeles, IStyleData). Es el unico
// modulo que arma esa instantanea; la unica resta de uno vive en coordenadas.aBase0 (RS2-1). Si cambia la
// version de Univer, solo cambia este archivo.
//
// Decisiones de fidelidad (ver la bitacora de la tarea 2.4):
//  - RS2-14: los numeros y las fechas van como NUMERO (v numerico, t = 2) con el codigo de formato del libro como
//    patron (s.n.pattern); el motor de formatos de Univer (sheets-numfmt, que ya viene en el preset) los muestra,
//    con los separadores de la localizacion del libro (esES: miles con punto, coma decimal). Las fechas ISO del
//    contrato pasan al numero de serie de Excel (fechaSerial.ts). Number() se usa SOLO para que Univer dibuje la
//    celda; el valor exacto guardado y la formula van en `custom`, y ningun monto se calcula con ese numero.
//  - Sin `f`: Univer no recalcula nada.
//  - Las celdas cubiertas por una combinada no vienen en el contrato (RS2-10) y no se crean.
//  - La alineacion General (numero a la derecha, texto a la izquierda) la da Univer por el tipo de la celda.
import type { ICellData, IStyleData, IWorkbookData, IWorksheetData } from "@univerjs/presets";
import type { EstiloVisualRespuesta, HojaVisualRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { aBase0, parsearA1, parsearRango } from "./coordenadas";
import { serialDeExcel } from "./fechaSerial";
import { tipoDeValor } from "./tipoDeValor";

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

// El patron de formato va solo en las celdas que son numero o fecha: un texto no lo necesita.
type Variante = "base" | "conPatron";

function estiloUniver(e: EstiloVisualRespuesta, variante: Variante): IStyleData {
  const s: Record<string, unknown> = {};
  if (e.relleno) s.bg = { rgb: e.relleno };
  if (e.fuente) s.ff = e.fuente;
  if (e.tamano) s.fs = Number(e.tamano);
  if (e.negrita) s.bl = 1;
  if (e.cursiva) s.it = 1;
  if (e.subrayado) s.ul = { s: 1 };
  if (e.color) s.cl = { rgb: e.color };

  if (e.alineacion_h && H[e.alineacion_h] !== undefined) s.ht = H[e.alineacion_h];
  if (e.alineacion_v && V[e.alineacion_v] !== undefined) s.vt = V[e.alineacion_v];
  if (e.ajustar_texto) s.tb = ENVOLVER;
  if (variante === "conPatron") s.n = { pattern: e.formato_numero };

  const lados = ["t", "r", "b", "l"] as const;
  const bd: Record<string, { s: number; cl: { rgb: string } }> = {};
  lados.forEach((lado, i) => {
    const estilo = e.bordes[i];
    if (estilo) bd[lado] = { s: BORDE[estilo] ?? 1, cl: { rgb: NEGRO } };
  });
  if (Object.keys(bd).length > 0) s.bd = bd;
  return s as IStyleData;
}

const GENERAL = "General";
const NUMERO_UNIVER = 2; // CellValueType.NUMBER
const BOOLEANO_UNIVER = 3; // CellValueType.BOOLEAN

interface Valor {
  v: string | number | boolean;
  t?: number;
  conPatron: boolean;
}

// Que le damos a Univer segun lo que parece ser el valor guardado (el contrato lo trae como texto).
function valorDeUniver(mostrado: string, formato: string): Valor {
  const texto: Valor = { v: mostrado, conPatron: false };
  if (formato === "@") return texto; // formato Texto: lo que parece numero es texto
  const conFormato = formato !== GENERAL && formato !== "";
  switch (tipoDeValor(mostrado)) {
    case "numero":
      return { v: Number(mostrado), t: NUMERO_UNIVER, conPatron: conFormato };
    case "fecha": {
      const serial = conFormato ? serialDeExcel(mostrado) : null;
      return serial === null ? texto : { v: serial, t: NUMERO_UNIVER, conPatron: true };
    }
    case "booleano":
      return { v: mostrado === "TRUE", t: BOOLEANO_UNIVER, conPatron: false };
    default:
      return texto;
  }
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
    const valor = valorDeUniver(c.mostrado, estilo?.formato_numero ?? GENERAL);
    const fila = (cellData[aBase0(c.fila)] ??= {});
    fila[aBase0(c.columna)] = {
      v: valor.v,
      ...(valor.t !== undefined ? { t: valor.t } : {}),
      s: estilo ? idDeEstilo(c.estilo, valor.conPatron ? "conPatron" : "base") : undefined,
      custom: { mostrado: c.mostrado, formula: c.formula },
    } as ICellData;
  }

  const columnData: Record<number, { w?: number; hd?: number }> = {};
  for (const [columna, ancho] of Object.entries(hoja.anchos)) {
    columnData[aBase0(Number(columna))] = { w: pxDeAncho(ancho) };
  }
  for (const columna of hoja.ocultas_columnas) {
    columnData[aBase0(columna)] = { ...columnData[aBase0(columna)], hd: 1 };
  }

  const rowData: Record<number, { h?: number; ia?: number; hd?: number }> = {};
  for (const [fila, alto] of Object.entries(hoja.altos)) {
    rowData[aBase0(Number(fila))] = { h: pxDeAlto(alto), ia: 0 };
  }
  for (const fila of hoja.ocultas_filas) {
    rowData[aBase0(fila)] = { ...rowData[aBase0(fila)], hd: 1 };
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
    const id = `e${indice}${variante === "base" ? "" : "n"}`;
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
