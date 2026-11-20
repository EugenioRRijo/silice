// Lo que la pantalla «Riesgo de la obra» lee de lo tecleado y cómo escribe lo que llega. No calcula ningún monto: los
// percentiles, la reserva y la cobertura los manda el servidor, exactos; aquí solo se redondean a centésimas para leerlos.
import { ErrorDeApi } from "../../api/cliente";
import type { Descartado, MapaRecordado, PedidoDeProyeccion } from "../../api/riesgo";
import { leerCifra } from "../../indicadores/cifraEscrita";
import { centesimasEsVe, fechaEsVe } from "../../indicadores/formatoEsVe";

// Los insumos que más empujan que se muestran (el plan pide los tres primeros).
export const MAS_EMPUJAN = 3;

// Los parámetros tal como se escriben, con punto de miles (D-V-3: 2.000 trayectorias, 36 meses de historia, 6 de plazo).
export interface Campos {
  inicio: string;
  meses: string;
  trayectorias: string;
  semilla: string;
  ventana: string;
  porCorte: string;
}

export const CAMPOS_INICIALES: Campos = { inicio: "", meses: "6", trayectorias: "2.000", semilla: "1", ventana: "36", porCorte: "500" };

export const ROTULOS: Record<Exclude<keyof Campos, "inicio">, string> = {
  meses: "Meses del plazo",
  trayectorias: "Trayectorias",
  semilla: "Semilla",
  ventana: "Meses de historia",
  porCorte: "Trayectorias por corte",
};

export type Lectura = { valor: number } | { error: string };

// Un entero escrito con la regla de las cifras («2.000» es dos mil): el mensaje de la regla si no la cumple, y otro si
// trae decimales. Va a la API como entero JSON; los topes los dice el servidor.
export function leerEntero(texto: string): Lectura {
  const lectura = leerCifra(texto);
  if ("error" in lectura) return lectura;
  if (!/^[0-9]+$/.test(lectura.valor)) return { error: "Escriba un número entero, sin decimales ni signo." };
  return { valor: Number(lectura.valor) };
}

// Lee los campos pedidos: los valores, o el error de cada campo que no se pudo leer.
export function leerCampos<K extends keyof typeof ROTULOS>(
  campos: Campos,
  claves: readonly K[],
): { valores: Record<K, number> } | { errores: Partial<Record<K, string>> } {
  const valores = {} as Record<K, number>;
  const errores: Partial<Record<K, string>> = {};
  for (const clave of claves) {
    const lectura = leerEntero(campos[clave]);
    if ("error" in lectura) errores[clave] = lectura.error;
    else valores[clave] = lectura.valor;
  }
  return Object.keys(errores).length > 0 ? { errores } : { valores };
}

// Un monto exacto de la API en centésimas, con coma decimal, punto de miles y su moneda: «1.248,72 USD».
export function monto(exacto: string, moneda: string): string {
  return `${centesimasEsVe(exacto)} ${moneda}`;
}

// Sin línea base de control la fecha de inicio es obligatoria: el mismo texto que el 422 de la API
// (aplicacion/riesgo/obra.py, SIN_INICIO), para decirlo en el campo antes de enviar y reconocerlo si llega del servidor.
export const SIN_INICIO = "Indique la fecha de inicio de la obra: la versión no tiene línea base de control de la que tomarla.";

export function pideLaFechaDeInicio(detalle: string): boolean {
  return detalle.startsWith("Indique la fecha de inicio");
}

// Cuando a una serie le falta historia, el 422 de la API (aplicacion/riesgo/proyeccion.py, `mensaje_de_pocos_meses`) dice dónde se
// carga: en la página «Índices del BCV». Con ese texto se ofrece el enlace a esa página; es la misma frase que escribe el servidor.
export const PAGINA_DE_LAS_SERIES = "Índices del BCV";

export function faltaCargarSeries(error: unknown): boolean {
  return error instanceof ErrorDeApi && error.estado === 422 && error.detalle.includes(`«${PAGINA_DE_LAS_SERIES}»`);
}

// La ayuda del campo de la fecha de inicio: de dónde sale si se deja vacía.
export function ayudaDelInicio(inicioLineaBase: string | null): string {
  return inicioLineaBase !== null
    ? `Si la deja vacía se toma la de la línea base: ${fechaEsVe(inicioLineaBase)}.`
    : "Esta versión no tiene línea base de control: escriba la fecha de inicio.";
}

// El informe de riesgo en Excel (`GET /v1/riesgo/reportes/riesgo`) con lo mismo que se proyectó: el servidor vuelve a
// calcular con la misma semilla. El mapa viaja como JSON en la consulta; sin fecha de inicio manda la de la línea base.
export function rutaDelInformeDeRiesgo(pedido: PedidoDeProyeccion): string {
  const consulta = new URLSearchParams({
    proyecto: pedido.proyecto,
    version: pedido.version,
    meses: String(pedido.meses),
    trayectorias: String(pedido.trayectorias),
    semilla: String(pedido.semilla),
    ventana_meses: String(pedido.ventana_meses),
    mapa: JSON.stringify(pedido.mapa),
  });
  if (pedido.inicio !== null) consulta.set("inicio", pedido.inicio);
  return `/v1/riesgo/reportes/riesgo?${consulta.toString()}`;
}

// La nota bajo «Serie que mueve cada insumo» cuando el selector viene precargado con lo que Sílice recordó (DS-90).
export function notaDeLaPrecarga(recordado: MapaRecordado, version: string): string {
  return recordado.de_version === version
    ? "Precargado con las series que usó la última vez en esta versión."
    : `Precargado con las series que usó la última vez en la versión ${recordado.de_version}.`;
}

// Lo recordado que no se precargó y por qué (DS-92): el insumo ya no está en la versión o su serie ya no se ofrece.
export function avisoDeDescartados(descartados: readonly Descartado[]): string | null {
  if (descartados.length === 0) return null;
  const cuantos = descartados.length === 1 ? "1 insumo" : `${descartados.length} insumos`;
  const motivos = descartados.map((d) =>
    d.motivo === "insumo" ? `«${d.insumo}» ya no está en esta versión` : `«${d.insumo}»: la serie que tenía ya no se ofrece`,
  );
  return `No se precargó la serie de ${cuantos}: ${motivos.join("; ")}.`;
}

// Si no se pudo recordar el mapa, se dice sin estorbar: el resultado ya está y no depende de ello.
export const SIN_RECORDAR = "No se pudo recordar la serie de cada insumo para la próxima vez; el resultado no cambia.";
