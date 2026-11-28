// Analizadores de frontera para las respuestas del servidor que lee la Hoja (`pedir(ruta, { leer })`).
// Validan la forma del JSON al entrar para que los componentes y la lógica pura confíen en los tipos.
import type { HallazgoInformeRespuesta, InformeAuditoriaRespuesta } from "../../api/tipos";
import type { Impuestos } from "../control/logica";
import type { EstadoFila, FilaPresupuesto, Hallazgos, Monto, Resumen, VistaPresupuesto } from "./logica";

function comoObjeto(valor: unknown, ruta: string): Record<string, unknown> {
  if (typeof valor !== "object" || valor === null || Array.isArray(valor)) {
    throw new Error(`Se esperaba un objeto en ${ruta}.`);
  }
  return valor as Record<string, unknown>;
}

function leerTexto(valor: unknown, ruta: string): string {
  if (typeof valor !== "string") {
    throw new Error(`Se esperaba un texto en ${ruta}.`);
  }
  return valor;
}

function leerTextoNoVacio(valor: unknown, ruta: string): string {
  const texto = leerTexto(valor, ruta);
  if (texto.trim() === "") {
    throw new Error(`Falta un texto no vacío en ${ruta}.`);
  }
  return texto;
}

function leerTextoONulo(valor: unknown, ruta: string): string | null {
  if (valor === null) return null;
  if (typeof valor !== "string") {
    throw new Error(`Se esperaba un texto o nulo en ${ruta}.`);
  }
  return valor;
}

function leerBooleano(valor: unknown, ruta: string): boolean {
  if (typeof valor !== "boolean") {
    throw new Error(`Se esperaba un booleano en ${ruta}.`);
  }
  return valor;
}

function leerNumero(valor: unknown, ruta: string): number {
  if (typeof valor !== "number" || !Number.isFinite(valor)) {
    throw new Error(`Se esperaba un número finito en ${ruta}.`);
  }
  return valor;
}

function leerArreglo<T>(valor: unknown, ruta: string, leerElemento: (item: unknown, rutaItem: string) => T): T[] {
  if (!Array.isArray(valor)) {
    throw new Error(`Se esperaba una lista en ${ruta}.`);
  }
  return valor.map((item, indice) => leerElemento(item, `${ruta}[${indice}]`));
}

function leerMonto(valor: unknown, ruta: string): Monto {
  const o = comoObjeto(valor, ruta);
  return {
    texto: leerTexto(o.texto, `${ruta}.texto`),
    exacto: leerTexto(o.exacto, `${ruta}.exacto`),
  };
}

function leerImpuestos(valor: unknown, ruta: string): Impuestos {
  const o = comoObjeto(valor, ruta);
  return {
    subtotal: leerTexto(o.subtotal, `${ruta}.subtotal`),
    iva: leerTexto(o.iva, `${ruta}.iva`),
    total: leerTexto(o.total, `${ruta}.total`),
    alicuota: leerTexto(o.alicuota, `${ruta}.alicuota`),
    fuente_alicuota: leerTexto(o.fuente_alicuota, `${ruta}.fuente_alicuota`),
  };
}

function leerEstadoFila(valor: unknown, ruta: string): EstadoFila {
  const o = comoObjeto(valor, ruta);
  return {
    severidad: leerTextoONulo(o.severidad, `${ruta}.severidad`),
    texto: leerTexto(o.texto, `${ruta}.texto`),
  };
}

function leerFilaPresupuesto(valor: unknown, ruta: string): FilaPresupuesto {
  const o = comoObjeto(valor, ruta);
  const fila: FilaPresupuesto = {
    clave: leerTextoNoVacio(o.clave, `${ruta}.clave`),
    partida: leerTexto(o.partida, `${ruta}.partida`),
    descripcion: leerTexto(o.descripcion, `${ruta}.descripcion`),
    unidad: leerTexto(o.unidad, `${ruta}.unidad`),
    cantidad: leerTexto(o.cantidad, `${ruta}.cantidad`),
    cantidad_calculada: leerTexto(o.cantidad_calculada, `${ruta}.cantidad_calculada`),
    escrita: leerBooleano(o.escrita, `${ruta}.escrita`),
    pu: o.pu === null ? null : leerMonto(o.pu, `${ruta}.pu`),
    total: o.total === null ? null : leerMonto(o.total, `${ruta}.total`),
    estado: leerEstadoFila(o.estado, `${ruta}.estado`),
    quitable: leerBooleano(o.quitable, `${ruta}.quitable`),
    nota: leerTextoONulo(o.nota, `${ruta}.nota`),
    calculo: leerTextoONulo(o.calculo, `${ruta}.calculo`),
  };
  if (o.de_tramo !== undefined) {
    fila.de_tramo = leerBooleano(o.de_tramo, `${ruta}.de_tramo`);
  }
  return fila;
}

function leerConteoSeveridad(valor: unknown, ruta: string): Hallazgos {
  const o = comoObjeto(valor, ruta);
  return {
    severidad: leerTexto(o.severidad, `${ruta}.severidad`),
    total: leerNumero(o.total, `${ruta}.total`),
  };
}

function leerReglaEvaluada(
  valor: unknown,
  ruta: string,
): { regla: string; nombre: string; hallazgos: number } {
  const o = comoObjeto(valor, ruta);
  return {
    regla: leerTexto(o.regla, `${ruta}.regla`),
    nombre: leerTexto(o.nombre, `${ruta}.nombre`),
    hallazgos: leerNumero(o.hallazgos, `${ruta}.hallazgos`),
  };
}

function leerHallazgoInforme(valor: unknown, ruta: string): HallazgoInformeRespuesta {
  const o = comoObjeto(valor, ruta);
  return {
    numero: leerNumero(o.numero, `${ruta}.numero`),
    regla: leerTexto(o.regla, `${ruta}.regla`),
    severidad: leerTexto(o.severidad, `${ruta}.severidad`),
    partida: leerTextoONulo(o.partida, `${ruta}.partida`),
    descripcion: leerTexto(o.descripcion, `${ruta}.descripcion`),
    impacto: leerTextoONulo(o.impacto, `${ruta}.impacto`),
    observado: leerTextoONulo(o.observado, `${ruta}.observado`),
    esperado: leerTextoONulo(o.esperado, `${ruta}.esperado`),
    origen: leerArreglo(o.origen, `${ruta}.origen`, leerTexto),
  };
}

/** Valida la respuesta de la vista del presupuesto antes de entregarla a la superficie. */
export function leerVistaPresupuesto(datos: unknown): VistaPresupuesto {
  const o = comoObjeto(datos, "vistaPresupuesto");
  return {
    filas: leerArreglo(o.filas, "vistaPresupuesto.filas", leerFilaPresupuesto),
    total: leerMonto(o.total, "vistaPresupuesto.total"),
    moneda: leerTexto(o.moneda, "vistaPresupuesto.moneda"),
    vacio_mensaje: leerTextoONulo(o.vacio_mensaje, "vistaPresupuesto.vacio_mensaje"),
    impuestos: leerImpuestos(o.impuestos, "vistaPresupuesto.impuestos"),
  };
}

/** Valida la respuesta del informe de auditoría antes de entregarla a la superficie. */
export function leerInforme(datos: unknown): InformeAuditoriaRespuesta {
  const o = comoObjeto(datos, "informe");
  return {
    codigo_presupuesto: leerTexto(o.codigo_presupuesto, "informe.codigo_presupuesto"),
    cumple: leerBooleano(o.cumple, "informe.cumple"),
    veredicto: leerTexto(o.veredicto, "informe.veredicto"),
    total_hallazgos: leerNumero(o.total_hallazgos, "informe.total_hallazgos"),
    por_severidad: leerArreglo(o.por_severidad, "informe.por_severidad", leerConteoSeveridad),
    reglas_evaluadas: leerArreglo(o.reglas_evaluadas, "informe.reglas_evaluadas", leerReglaEvaluada),
    hallazgos: leerArreglo(o.hallazgos, "informe.hallazgos", leerHallazgoInforme),
    sin_hallazgos: leerTextoONulo(o.sin_hallazgos, "informe.sin_hallazgos"),
  };
}

/** Valida la respuesta del resumen de un borrador antes de entregarla a la superficie. */
export function leerResumen(datos: unknown): Resumen {
  const o = comoObjeto(datos, "resumen");
  const resumen: Resumen = {
    rev: leerNumero(o.rev, "resumen.rev"),
    moneda: leerTexto(o.moneda, "resumen.moneda"),
    total: leerMonto(o.total, "resumen.total"),
    cambios: leerNumero(o.cambios, "resumen.cambios"),
    pendientes_catalogo: leerNumero(o.pendientes_catalogo, "resumen.pendientes_catalogo"),
    hallazgos: leerArreglo(o.hallazgos, "resumen.hallazgos", leerConteoSeveridad),
    hay_plan: leerBooleano(o.hay_plan, "resumen.hay_plan"),
    version_mas_nueva: leerTextoONulo(o.version_mas_nueva, "resumen.version_mas_nueva"),
    guardado_como: leerTextoONulo(o.guardado_como, "resumen.guardado_como"),
  };
  if (o.espacio_vacio !== undefined) {
    resumen.espacio_vacio = leerBooleano(o.espacio_vacio, "resumen.espacio_vacio");
  }
  if (o.desgloses !== undefined) {
    resumen.desgloses = leerNumero(o.desgloses, "resumen.desgloses");
  }
  return resumen;
}
