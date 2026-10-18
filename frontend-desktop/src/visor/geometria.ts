// Aritmetica pura del visor, sin Univer ni DOM: donde cae una celda en pantalla y a donde hay que desplazar para
// verla. El adaptador de Univer solo le pasa los numeros que lee de la hoja.

export interface CeldaEnHoja {
  fila0: number;
  columna0: number;
  // Rectangulo en coordenadas de la hoja (cabeceras incluidas), sin desplazamiento ni zoom.
  startX: number;
  endX: number;
  startY: number;
  endY: number;
}

export interface EntradaRectangulo {
  celda: CeldaEnHoja;
  // Desplazamiento de la zona principal (viewportScrollX/Y de Univer).
  scroll: { x: number; y: number };
  // Esquina de la zona principal en coordenadas de la hoja (despues de las cabeceras y de lo fijo).
  principal: { left: number; top: number };
  // Filas y columnas fijas: de la primera no fija hacia abajo todo se desplaza; `ancho` y `alto` es lo que ocupan.
  congelado: { xSplit: number; ySplit: number; startRow: number; startColumn: number; ancho: number; alto: number };
  cabecera: { ancho: number; alto: number };
  escala: { x: number; y: number };
}

export interface RectanguloEnLienzo {
  izquierda: number;
  arriba: number;
  derecha: number;
  abajo: number;
}

// Mismo calculo que transformPosition2Offset de sheets-ui (lo que Univer usa para sus popups): lo fijo no se
// desplaza, lo demas si. Ademas, lo que se desplazo por debajo de lo fijo se recorta en su borde. En pixeles del
// lienzo; null si no queda nada (columna o fila oculta, o tapada por lo fijo).
export function rectanguloEnPantalla(e: EntradaRectangulo): RectanguloEnLienzo | null {
  const { celda, scroll, principal, congelado, cabecera, escala } = e;
  const aX = (x: number) =>
    (x > principal.left ? x - scroll.x : congelado.ancho + cabecera.ancho - (principal.left - x)) * escala.x;
  const aY = (y: number) =>
    (y > principal.top ? y - scroll.y : congelado.alto + cabecera.alto - (principal.top - y)) * escala.y;

  if (celda.endX - celda.startX <= 0 || celda.endY - celda.startY <= 0) return null;

  let izquierda = aX(celda.startX);
  const derecha = aX(celda.endX);
  let arriba = aY(celda.startY);
  const abajo = aY(celda.endY);

  if (celda.columna0 >= congelado.startColumn && congelado.xSplit > 0) {
    izquierda = Math.max(izquierda, (congelado.ancho + cabecera.ancho) * escala.x);
  }
  if (celda.fila0 >= congelado.startRow && congelado.ySplit > 0) {
    arriba = Math.max(arriba, (congelado.alto + cabecera.alto) * escala.y);
  }
  if (derecha <= izquierda || abajo <= arriba) return null;
  return { izquierda, arriba, derecha, abajo };
}

export interface EntradaPlan {
  celda: { fila0: number; columna0: number };
  // Ancho de una columna y alto de una fila en pixeles de la hoja, sin zoom (0 si esta oculta).
  ancho: (columna0: number) => number;
  alto: (fila0: number) => number;
  // Zona de celdas visible, sin zoom.
  area: { ancho: number; alto: number };
  // Primera fila y columna no fijas, y lo que ocupan las fijas.
  congelado: { startRow: number; startColumn: number; ancho: number; alto: number };
  // Primera fila y columna de la zona principal ahora mismo.
  primeraVisible: { fila0: number; columna0: number };
  // Si la celda se ve entera en cada eje.
  visible: { horizontal: boolean; vertical: boolean };
}

const FILAS_DE_CONTEXTO = 3;

// A que fila y columna desplazar para ver la celda sin perder el contexto; null si ya se ve entera.
//  - Si ya se ve en horizontal, solo se desplaza en vertical.
//  - Si no, y desde la primera columna hasta la celda cabe en el ancho, se vuelve a la primera (para no esconder
//    las columnas de descripcion); si no cabe, la celda queda a un tercio del ancho desde la izquierda.
//  - En vertical se dejan filas de contexto arriba, menos las que hagan falta para que la celda (aunque la fila sea
//    alta) se vea entera; una fila mas alta que la zona se deja arriba del todo.
export function planDeDesplazamiento(e: EntradaPlan): { fila0: number; columna0: number } | null {
  const { celda, congelado, area, primeraVisible, visible } = e;
  if (visible.horizontal && visible.vertical) return null;

  let columna0 = primeraVisible.columna0;
  if (!visible.horizontal) {
    const disponible = area.ancho - congelado.ancho;
    let desdeElInicio = 0;
    for (let c = congelado.startColumn; c <= celda.columna0; c++) desdeElInicio += e.ancho(c);
    if (desdeElInicio <= disponible) {
      columna0 = congelado.startColumn;
    } else {
      const tercio = area.ancho / 3;
      let acumulado = 0;
      columna0 = celda.columna0;
      while (columna0 > congelado.startColumn && acumulado < tercio) {
        columna0 -= 1;
        acumulado += e.ancho(columna0);
      }
    }
  }

  let fila0 = primeraVisible.fila0;
  if (!visible.vertical) {
    const disponible = area.alto - congelado.alto;
    fila0 = Math.max(congelado.startRow, celda.fila0 - FILAS_DE_CONTEXTO);
    const altura = () => {
      let suma = 0;
      for (let f = fila0; f <= celda.fila0; f++) suma += e.alto(f);
      return suma;
    };
    while (fila0 < celda.fila0 && altura() > disponible) fila0 += 1;
  }
  return { fila0, columna0 };
}
