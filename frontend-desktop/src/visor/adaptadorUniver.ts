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
import { columnaDeDescripcion } from "./celdas";
import { planDeDesplazamiento, rectanguloEnPantalla } from "./geometria";
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

  // Lo que hace falta de Univer para ubicar una celda: la cuadricula y el viewport principal de la hoja activa.
  function contexto(celda: CeldaRef) {
    const hoja = hojaActual();
    if (hoja.getSheetName() !== celda.hoja) return null;
    const r = render();
    const sk = hoja.getSkeleton();
    const principal = viewportPrincipal();
    const canvas = r?.engine.getCanvasElement();
    const zona = area();
    if (!r || !sk || !principal || !canvas || !zona) return null;
    const { scaleX, scaleY } = r.scene.getAncestorScale();
    const congelado = hoja.getFreeze();
    // Lo que ocupan las filas y columnas fijas (sin cabeceras).
    const inicioVista = sk.getNoMergeCellWithCoordByIndex(congelado.startRow - congelado.ySplit, congelado.startColumn - congelado.xSplit, false);
    const finVista = sk.getNoMergeCellWithCoordByIndex(congelado.startRow, congelado.startColumn, false);
    const cajaCanvas = canvas.getBoundingClientRect();
    const cajaContenedor = contenedor.getBoundingClientRect();
    const anchoCss = Number.parseFloat(canvas.style.width);
    return {
      hoja,
      sk,
      principal,
      zona,
      escala: { x: scaleX, y: scaleY },
      congelado: {
        xSplit: congelado.xSplit,
        ySplit: congelado.ySplit,
        startRow: congelado.startRow,
        startColumn: congelado.startColumn,
        ancho: finVista.startX - inicioVista.startX,
        alto: finVista.startY - inicioVista.startY,
      },
      // El canvas puede estar escalado por CSS; su origen en pantalla se pasa al contenedor del visor.
      ajuste: anchoCss > 0 ? cajaCanvas.width / anchoCss : 1,
      origen: { x: cajaCanvas.left - cajaContenedor.left, y: cajaCanvas.top - cajaContenedor.top },
    };
  }

  function rectanguloDe(celda: CeldaRef): RectanguloPx | null {
    const c = contexto(celda);
    if (!c) return null;
    const hoja = c.sk.getCellWithCoordByIndex(celda.fila0, celda.columna0);
    const r = rectanguloEnPantalla({
      celda: { fila0: celda.fila0, columna0: celda.columna0, startX: hoja.startX, endX: hoja.endX, startY: hoja.startY, endY: hoja.endY },
      scroll: { x: c.principal.viewportScrollX, y: c.principal.viewportScrollY },
      principal: { left: c.principal.left, top: c.principal.top },
      congelado: c.congelado,
      cabecera: { ancho: c.sk.rowHeaderWidth, alto: c.sk.columnHeaderHeight },
      escala: c.escala,
    });
    if (!r) return null;
    const x = r.izquierda * c.ajuste + c.origen.x;
    const y = r.arriba * c.ajuste + c.origen.y;
    const ancho = (r.derecha - r.izquierda) * c.ajuste;
    const alto = (r.abajo - r.arriba) * c.ajuste;
    const { zona } = c;
    // Fuera de la zona de celdas: no esta a la vista.
    if (x + ancho <= zona.x || x >= zona.x + zona.ancho) return null;
    if (y + alto <= zona.y || y >= zona.y + zona.alto) return null;
    return { x, y, ancho, alto };
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

  // Se ve entera en cada eje (dentro de la zona de celdas y sin recortes por lo fijo).
  function visibilidad(celda: CeldaRef, c: NonNullable<ReturnType<typeof contexto>>) {
    const r = rectanguloDe(celda);
    const g = c.sk.getCellWithCoordByIndex(celda.fila0, celda.columna0);
    if (!r) return { horizontal: false, vertical: false };
    const margen = 0.75;
    const completaX = Math.abs(r.ancho - (g.endX - g.startX) * c.escala.x * c.ajuste) < margen;
    const completaY = Math.abs(r.alto - (g.endY - g.startY) * c.escala.y * c.ajuste) < margen;
    const { zona } = c;
    return {
      horizontal: completaX && r.x >= zona.x - margen && r.x + r.ancho <= zona.x + zona.ancho + margen,
      vertical: completaY && r.y >= zona.y - margen && r.y + r.alto <= zona.y + zona.alto + margen,
    };
  }

  function desplazarA(celda: CeldaRef): void {
    const c = contexto(celda);
    if (!c) return;
    // La descripcion de la fila (texto largo a la izquierda de la celda) no debe perderse de vista: sin ella la
    // celda "P5" no dice de que partida habla.
    const hojaDelLibro = libro.hojas.find((h) => h.nombre === celda.hoja);
    const descripcion = hojaDelLibro ? columnaDeDescripcion(hojaDelLibro, celda.fila0, celda.columna0) : null;
    const visibleCelda = visibilidad(celda, c);
    const visibleDescripcion =
      descripcion === null ? true : visibilidad({ hoja: celda.hoja, fila0: celda.fila0, columna0: descripcion }, c).horizontal;
    const estado = c.hoja.getScrollState();
    const plan = planDeDesplazamiento({
      celda,
      ancho: (col) => {
        const k = c.sk.getNoMergeCellWithCoordByIndex(0, col, false);
        return k.endX - k.startX;
      },
      alto: (fila) => {
        const k = c.sk.getNoMergeCellWithCoordByIndex(fila, 0, false);
        return k.endY - k.startY;
      },
      area: { ancho: c.zona.ancho / (c.escala.x * c.ajuste), alto: c.zona.alto / (c.escala.y * c.ajuste) },
      congelado: { startRow: c.congelado.startRow, startColumn: c.congelado.startColumn, ancho: c.congelado.ancho, alto: c.congelado.alto },
      primeraVisible: {
        fila0: estado.sheetViewStartRow + c.congelado.ySplit,
        columna0: estado.sheetViewStartColumn + c.congelado.xSplit,
      },
      visible: { ...visibleCelda, descripcion: visibleDescripcion },
      descripcion: descripcion ?? undefined,
    });
    // Sin animacion (duracion 0).
    if (plan) c.hoja.scrollToCell(plan.fila0, plan.columna0, 0);
  }

  function irA(celda: CeldaRef): void {
    const cambio = hojaActual().getSheetName() !== celda.hoja;
    irAHoja(celda.hoja);
    const colocar = () => {
      const hoja = hojaActual();
      if (hoja.getSheetName() !== celda.hoja) return;
      desplazarA(celda);
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
