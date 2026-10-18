// Adaptador delgado entre HojaVisor (interfaz propia) y Univer 1.0. Es el unico archivo que importa Univer en
// tiempo de ejecucion; Visor.tsx lo carga con import() para que Univer viaje en su propio archivo.
//
// Univer en SOLO LECTURA: sin barra de herramientas, de formulas, de pie ni menu contextual; edicion bloqueada
// (permiso de libro y `disableEdit`); sin workers (no se pasa `workerURL`: las formulas, que no se usan, correrian
// en el hilo principal); la telemetria de Univer es solo un identificador sin implementacion (no envia nada).
//
// API de Univer usada para ubicar los halos (ruling RS2.4-1): la Facade no da el rectangulo de una celda en
// pantalla (FRange.getCellRect devuelve coordenadas de la hoja, sin desplazamiento ni zoom), asi que se hace lo
// mismo que hace Univer para sus propios popups (transformBound2OffsetBound en sheets-ui):
//   skeleton.getCellWithCoordByIndex(fila, columna)    -> rectangulo en coordenadas de la hoja
//   escena.getViewport(VIEW_MAIN).viewportScrollX/Y    -> desplazamiento
//   escena.getAncestorScale()                          -> acercamiento
//   canvas.getBoundingClientRect()                     -> origen en pantalla
// Eventos: viewport VIEW_MAIN .onScrollAfter$ (desplazamiento), ICommandService.onCommandExecuted (zoom, cambio de
// hoja, congelado, alto/ancho) y un ResizeObserver sobre el contenedor (cambio de tamano).
import "@univerjs/preset-sheets-core/lib/index.css";
import esES from "@univerjs/preset-sheets-core/locales/es-ES";
import {
  IRenderManagerService,
  SHEET_VIEWPORT_KEY,
  SHEETS_UI_PLUGIN_CONFIG_KEY,
  UniverSheetsCorePreset,
} from "@univerjs/preset-sheets-core";
import type { FWorkbook, FWorksheet } from "@univerjs/preset-sheets-core";
import { createUniver, ICommandService, IConfigService, LocaleType, mergeLocales } from "@univerjs/presets";
import type { LibroVisualRespuesta } from "../api/tipos";
import { aUniver } from "../replica/aUniver";
import type { CeldaRef, HojaVisor, RectanguloPx } from "./hojaVisor";

const ESPERA_MAXIMA_MS = 8000;
const PASO_MS = 40;

function esperar(ms: number): Promise<void> {
  return new Promise((resolver) => setTimeout(resolver, ms));
}

export async function crearHojaUniver(contenedor: HTMLElement, libro: LibroVisualRespuesta): Promise<HojaVisor> {
  const { univer, univerAPI } = createUniver({
    locale: LocaleType.ES_ES,
    locales: { [LocaleType.ES_ES]: mergeLocales(esES) },
    presets: [
      UniverSheetsCorePreset({
        container: contenedor,
        header: false,
        toolbar: false,
        footer: false,
        formulaBar: false,
        contextMenu: false,
        disableAutoFocus: true,
        disableTextFormatAlert: true,
        disableTextFormatMark: true,
        sheets: { disableForceStringAlert: true, disableForceStringMark: true },
      }),
    ],
  });

  const injector = univer.__getInjector();
  const renderManager = injector.get(IRenderManagerService);
  const comandos = injector.get(ICommandService);

  const datos = aUniver(libro);
  const fLibro: FWorkbook = univerAPI.createWorkbook(datos);
  const unitId = fLibro.getId();

  // Si la primera hoja esta oculta, la hoja activa debe ser la primera que se ve.
  const primeraVisible = libro.hojas.find((h) => h.visible);
  if (primeraVisible && fLibro.getActiveSheet().getSheetName() !== primeraVisible.nombre) {
    const hoja = fLibro.getSheetByName(primeraVisible.nombre);
    if (hoja) fLibro.setActiveSheet(hoja);
  }

  const render = () => renderManager.getRenderUnitById(unitId);
  const viewportPrincipal = () => render()?.scene.getViewport(SHEET_VIEWPORT_KEY.VIEW_MAIN);

  // El lienzo se arma de forma asincrona: se espera a tener escena y cuadricula antes de entregar el visor.
  const inicio = Date.now();
  for (;;) {
    const listo = viewportPrincipal() && fLibro.getActiveSheet().getSkeleton();
    if (listo) break;
    if (Date.now() - inicio > ESPERA_MAXIMA_MS) {
      univer.dispose();
      throw new Error("Univer no termino de preparar la hoja.");
    }
    await esperar(PASO_MS);
  }

  // Los plugins escriben su configuracion y sus permisos al arrancar, de forma asincrona: el bloqueo de edicion
  // (permiso del libro y `disableEdit`) se pone despues, ya con todo listo; antes se pisa.
  fLibro.setEditable(false);
  injector.get(IConfigService).setConfig(SHEETS_UI_PLUGIN_CONFIG_KEY, { disableEdit: true }, { merge: true });
  const hojaActual = (): FWorksheet => fLibro.getActiveSheet();

  function area(): RectanguloPx | null {
    const r = render();
    const sk = hojaActual().getSkeleton();
    const canvas = r?.engine.getCanvasElement();
    if (!r || !sk || !canvas) return null;
    const { scaleX, scaleY } = r.scene.getAncestorScale();
    const cajaCanvas = canvas.getBoundingClientRect();
    const cajaContenedor = contenedor.getBoundingClientRect();
    const izquierda = cajaCanvas.left - cajaContenedor.left + sk.rowHeaderWidth * scaleX;
    const arriba = cajaCanvas.top - cajaContenedor.top + sk.columnHeaderHeight * scaleY;
    return {
      x: izquierda,
      y: arriba,
      ancho: Math.max(0, cajaCanvas.width - sk.rowHeaderWidth * scaleX),
      alto: Math.max(0, cajaCanvas.height - sk.columnHeaderHeight * scaleY),
    };
  }

  function rectanguloDe(celda: CeldaRef): RectanguloPx | null {
    const hoja = hojaActual();
    if (hoja.getSheetName() !== celda.hoja) return null;
    const r = render();
    const sk = hoja.getSkeleton();
    const principal = viewportPrincipal();
    const canvas = r?.engine.getCanvasElement();
    const zona = area();
    if (!r || !sk || !principal || !canvas || !zona) return null;

    const c = sk.getCellWithCoordByIndex(celda.fila0, celda.columna0);
    if (c.endX - c.startX <= 0 || c.endY - c.startY <= 0) return null; // fila o columna oculta

    const { scaleX, scaleY } = r.scene.getAncestorScale();
    const congelado = hoja.getFreeze();
    const { startColumn, startRow, xSplit, ySplit } = congelado;

    // Mismo calculo que transformPosition2Offset de sheets-ui: las celdas de la zona congelada no se desplazan.
    const inicioVista = sk.getNoMergeCellWithCoordByIndex(startRow - ySplit, startColumn - xSplit, false);
    const finVista = sk.getNoMergeCellWithCoordByIndex(startRow, startColumn, false);
    const anchoCongelado = finVista.startX - inicioVista.startX;
    const altoCongelado = finVista.startY - inicioVista.startY;
    const aX = (x: number) =>
      (x > principal.left ? x - principal.viewportScrollX : anchoCongelado + sk.rowHeaderWidth - (principal.left - x)) *
      scaleX;
    const aY = (y: number) =>
      (y > principal.top ? y - principal.viewportScrollY : altoCongelado + sk.columnHeaderHeight - (principal.top - y)) *
      scaleY;

    let izquierda = aX(c.startX);
    let derecha = aX(c.endX);
    let arriba = aY(c.startY);
    let abajo = aY(c.endY);

    // De canvas a pantalla (el canvas puede estar escalado por CSS) y a coordenadas del contenedor.
    const cajaCanvas = canvas.getBoundingClientRect();
    const cajaContenedor = contenedor.getBoundingClientRect();
    const anchoCss = Number.parseFloat(canvas.style.width);
    const ajuste = anchoCss > 0 ? cajaCanvas.width / anchoCss : 1;
    const origenX = cajaCanvas.left - cajaContenedor.left;
    const origenY = cajaCanvas.top - cajaContenedor.top;
    izquierda = izquierda * ajuste + origenX;
    derecha = derecha * ajuste + origenX;
    arriba = arriba * ajuste + origenY;
    abajo = abajo * ajuste + origenY;

    // Una celda que se desplazo por debajo de la zona congelada no debe verse encima de ella.
    if (celda.columna0 >= startColumn && xSplit > 0) {
      const borde = (anchoCongelado + sk.rowHeaderWidth) * scaleX * ajuste + origenX;
      izquierda = Math.max(izquierda, borde);
    }
    if (celda.fila0 >= startRow && ySplit > 0) {
      const borde = (altoCongelado + sk.columnHeaderHeight) * scaleY * ajuste + origenY;
      arriba = Math.max(arriba, borde);
    }

    if (derecha <= izquierda || abajo <= arriba) return null;
    // Fuera de la zona de celdas: no esta a la vista.
    if (derecha <= zona.x || izquierda >= zona.x + zona.ancho) return null;
    if (abajo <= zona.y || arriba >= zona.y + zona.alto) return null;
    return { x: izquierda, y: arriba, ancho: derecha - izquierda, alto: abajo - arriba };
  }

  // Avisos de "cambio la vista": varios eventos de Univer pueden llegar juntos, se junta todo en un solo
  // aviso por cuadro de dibujo.
  const oyentesCambio = new Set<() => void>();
  let pendiente = false;
  const avisarCambio = () => {
    if (pendiente) return;
    pendiente = true;
    requestAnimationFrame(() => {
      pendiente = false;
      oyentesCambio.forEach((f) => f());
    });
  };

  const suscripciones: { unsubscribe?: () => void; dispose?: () => void }[] = [];
  const principal = viewportPrincipal();
  if (principal) suscripciones.push(principal.onScrollAfter$.subscribeEvent(avisarCambio));
  suscripciones.push(comandos.onCommandExecuted(avisarCambio));
  const observador = new ResizeObserver(avisarCambio);
  observador.observe(contenedor);

  const oyentesSeleccion = new Set<(c: CeldaRef) => void>();
  suscripciones.push(
    fLibro.onSelectionChange((selecciones) => {
      const primera = selecciones[0];
      if (!primera) return;
      const celda: CeldaRef = {
        hoja: hojaActual().getSheetName(),
        fila0: primera.startRow,
        columna0: primera.startColumn,
      };
      oyentesSeleccion.forEach((f) => f(celda));
    }),
  );

  function irAHoja(nombre: string): void {
    const hoja = fLibro.getSheetByName(nombre);
    if (hoja && hojaActual().getSheetName() !== nombre) fLibro.setActiveSheet(hoja);
  }

  function irA(celda: CeldaRef): void {
    const cambio = hojaActual().getSheetName() !== celda.hoja;
    irAHoja(celda.hoja);
    const colocar = () => {
      const hoja = hojaActual();
      if (hoja.getSheetName() !== celda.hoja) return;
      const zona = area();
      const r = rectanguloDe(celda);
      const dentro =
        r && zona && r.x >= zona.x && r.y >= zona.y && r.x + r.ancho <= zona.x + zona.ancho && r.y + r.alto <= zona.y + zona.alto;
      // Solo se desplaza si la celda no se ve entera, y sin animacion (duracion 0); con un par de filas de
      // contexto por encima para que no quede pegada al borde.
      if (!dentro) hoja.scrollToCell(Math.max(0, celda.fila0 - 2), Math.max(0, celda.columna0 - 1), 0);
      hoja.getRange(celda.fila0, celda.columna0).activate();
      avisarCambio();
    };
    // Tras cambiar de hoja, Univer arma su cuadricula en el cuadro siguiente.
    if (cambio) setTimeout(colocar, PASO_MS);
    else colocar();
  }

  return {
    hojaActiva: () => hojaActual().getSheetName(),
    irAHoja,
    irA,
    rectanguloDe,
    area,
    alCambiar: (devolucion) => {
      oyentesCambio.add(devolucion);
      return () => oyentesCambio.delete(devolucion);
    },
    alSeleccionar: (devolucion) => {
      oyentesSeleccion.add(devolucion);
      return () => oyentesSeleccion.delete(devolucion);
    },
    destruir: () => {
      observador.disconnect();
      for (const s of suscripciones) {
        if (typeof s.unsubscribe === "function") s.unsubscribe();
        else s.dispose?.();
      }
      oyentesCambio.clear();
      oyentesSeleccion.clear();
      univer.dispose();
    },
  };
}
