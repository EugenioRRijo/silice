import type { CausaRaizRespuesta, HallazgoLibroRespuesta, LibroAuditadoRespuesta } from "../../api/tipos";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { gravedad, normalizarSeveridad } from "../../severidad/severidad";
import type { CatalogoQueHacer } from "../../comun/catalogoQueHacer";

// Lógica pura de «Auditar un libro» (B2, ficha-b2 §1.5 y §1.10). Solo cuenta, agrupa y escribe frases: los montos, el
// veredicto (`cumple`) y las causas los da el servidor, y nada aquí los recalcula.

// Una alerta de precio de `POST /v1/libros/auditoria` (`alertas`). Ninguna pantalla las mostraba antes de B2.
export interface AlertaDePrecio {
  codigo: string;
  descripcion: string;
  // «sin fuente», «base de la empresa», «otra versión» o «USD-Bs» (`fusion/alertas.py`).
  tipo: string;
  moneda: string;
  precio: string;
  fecha: string;
  fuente: string;
  tasa?: string | null;
  precio_bs?: string | null;
  variacion?: string | null;
  mensaje: string;
}

export type AuditoriaDelLibro = LibroAuditadoRespuesta & { alertas?: AlertaDePrecio[] };

export interface CuentaDeHallazgos {
  critico: number;
  error: number;
  advertencia: number;
  info: number;
  total: number;
}

// Posiciones de los avisos de «regla no aplicable» que existen en la lista (una API anterior no las manda).
function posicionesNoAplicables(a: Pick<LibroAuditadoRespuesta, "hallazgos" | "no_aplicables">): Set<number> {
  const validas = (a.no_aplicables ?? []).filter((i) => Number.isInteger(i) && i >= 0 && i < a.hallazgos.length);
  return new Set(validas);
}

// Los hallazgos del libro: todos menos los avisos de regla no aplicable (R2 y R7 sin curva ni plan), que no son errores.
export function cuentaDeHallazgos(a: AuditoriaDelLibro): CuentaDeHallazgos {
  const fuera = posicionesNoAplicables(a);
  const cuenta: CuentaDeHallazgos = { critico: 0, error: 0, advertencia: 0, info: 0, total: 0 };
  a.hallazgos.forEach((h, i) => {
    if (fuera.has(i)) return;
    const clave = { CRITICO: "critico", ERROR: "error", ADVERTENCIA: "advertencia", INFO: "info" } as const;
    cuenta[clave[normalizarSeveridad(h.severidad)]] += 1;
    cuenta.total += 1;
  });
  return cuenta;
}

const cifra = (n: number): string => formatoEsVe(String(n));

export function fraseDeRespuesta(c: CuentaDeHallazgos): string {
  if (c.total === 0) return "El libro no tiene hallazgos";
  return c.total === 1 ? "1 hallazgo en el libro" : `${cifra(c.total)} hallazgos en el libro`;
}

// «1 crítico», «3 errores»…: cada severidad con su palabra, de la más a la menos grave, sin las que no hay.
export function desgloseDeSeveridad(c: CuentaDeHallazgos): string[] {
  const filas: [number, string, string][] = [
    [c.critico, "crítico", "críticos"],
    [c.error, "error", "errores"],
    [c.advertencia, "advertencia", "advertencias"],
    [c.info, "informativo", "informativos"],
  ];
  return filas.filter(([n]) => n > 0).map(([n, uno, varios]) => (n === 1 ? `1 ${uno}` : `${cifra(n)} ${varios}`));
}

function unir(partes: readonly string[]): string {
  if (partes.length <= 1) return partes[0] ?? "";
  return `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`;
}

// Lo que el anunciador dice, una vez, al terminar de auditar.
export function anuncioDeResultado(c: CuentaDeHallazgos): string {
  const partes = desgloseDeSeveridad(c);
  return partes.length === 0 ? "Auditoría lista: el libro no tiene hallazgos." : `Auditoría lista: ${unir(partes)}.`;
}

export interface Veredicto {
  cumple: boolean;
  titulo: string;
  detalle: string;
}

// La palabra «cumple» es la del servidor (`cumple`): la pantalla solo la acompaña con la cuenta.
export function veredictoDelLibro(cumple: boolean, c: CuentaDeHallazgos): Veredicto {
  if (cumple) {
    const detalle =
      c.total === 0
        ? "Sílice no halló nada que corregir."
        : `Sílice no halló errores; quedan ${unir(desgloseDeSeveridad(c))} por confirmar.`;
    return { cumple: true, titulo: "El libro cumple", detalle };
  }
  const partes = desgloseDeSeveridad(c);
  const que = partes.length > 0 ? `Tiene ${unir(partes)}. Corríjalos en su Excel y suba` : "Revise lo que se encontró y suba";
  return { cumple: false, titulo: "El libro no cumple", detalle: `${que} el libro de nuevo para comprobarlo.` };
}

// El principal de la conclusión: con algo que entregar, el informe; sin nada, auditar otro libro.
export function pasoSiguiente(c: CuentaDeHallazgos): "informe" | "otro" {
  return c.total > 0 ? "informe" : "otro";
}

// Las causas con varios casos: corregir una arregla todos sus casos. Una causa de un solo caso se lee mejor suelta.
export function causasMultiples(a: AuditoriaDelLibro): CausaRaizRespuesta[] {
  return (a.causas ?? []).filter((c) => c.ocurrencias >= 2);
}

export interface HallazgoSuelto {
  // Su posición en `hallazgos` (la misma que usan `causas` y `no_aplicables`).
  indice: number;
  hallazgo: HallazgoLibroRespuesta;
}

// Los hallazgos que no están en una causa de varios casos ni son avisos de regla no aplicable, de más a menos graves
// y, a igual gravedad, en el orden en que los dio el servidor.
export function hallazgosSueltos(a: AuditoriaDelLibro): HallazgoSuelto[] {
  const agrupados = new Set(causasMultiples(a).flatMap((c) => c.indices));
  const fuera = posicionesNoAplicables(a);
  return a.hallazgos
    .map((hallazgo, indice) => ({ indice, hallazgo }))
    .filter(({ indice }) => !agrupados.has(indice) && !fuera.has(indice))
    .sort((x, y) => gravedad(normalizarSeveridad(y.hallazgo.severidad)) - gravedad(normalizarSeveridad(x.hallazgo.severidad)));
}

export function noAplicables(a: AuditoriaDelLibro): HallazgoLibroRespuesta[] {
  return a.hallazgos.filter((_, i) => posicionesNoAplicables(a).has(i));
}

export interface AvisoDePrecio {
  tipo: string;
  codigos: string[];
  mensaje: string;
  // Cuántos precios dicen exactamente lo mismo.
  cantidad: number;
}

// Las alertas que de verdad avisan: se callan las que el servidor declara sin aviso (USD-Bs dentro del umbral) y las que
// dicen exactamente lo mismo se agrupan en una línea con su cuenta. Sin catálogo no se calla nada.
export function avisosDePrecio(alertas: readonly AlertaDePrecio[] | undefined, catalogo: CatalogoQueHacer | null): AvisoDePrecio[] {
  const grupos = new Map<string, AvisoDePrecio>();
  for (const alerta of alertas ?? []) {
    const frases = catalogo?.alertas[alerta.tipo]?.sin_aviso_si ?? [];
    if (frases.some((f) => alerta.mensaje.includes(f))) continue;
    const clave = `${alerta.tipo}\u0000${alerta.mensaje}`;
    const grupo = grupos.get(clave);
    if (grupo === undefined) {
      grupos.set(clave, { tipo: alerta.tipo, codigos: [alerta.codigo], mensaje: alerta.mensaje, cantidad: 1 });
    } else if (!grupo.codigos.includes(alerta.codigo)) {
      grupo.codigos.push(alerta.codigo);
      grupo.cantidad = grupo.codigos.length;
    }
  }
  return [...grupos.values()];
}

// «A1, A2, A3, A4 y 2 más»: hasta cuatro celdas a la vista.
export function celdasResumidas(celdas: readonly string[], maximo = 4): string {
  if (celdas.length <= maximo) return unir(celdas);
  const resto = celdas.length - maximo;
  return `${celdas.slice(0, maximo).join(", ")} y ${cifra(resto)} más`;
}

// La fecha de hoy en la zona de la persona (no en UTC: a las 8 p. m. en Caracas ya sería mañana).
export function fechaDeHoy(ahora: Date = new Date()): string {
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${ahora.getFullYear()}-${dos(ahora.getMonth() + 1)}-${dos(ahora.getDate())}`;
}

// La causa de un hallazgo agrupado se lee hasta su primer «;»: lo que sigue es detalle del caso.
export function fraseDeLaCausa(descripcion: string): string {
  const corte = descripcion.indexOf(";");
  return (corte >= 0 ? descripcion.slice(0, corte) : descripcion).trim();
}

export function textoDeCasos(n: number): string {
  return n === 1 ? "1 caso" : `${cifra(n)} casos`;
}

// El cuerpo de las rutas de libros (`POST /v1/libros/auditoria`, `/replica` y `/auditoria/pdf`): el `.xlsx` y, si hay, la
// fecha de la revisión (la API nunca lee el reloj: con la misma fecha, el mismo libro da siempre el mismo resultado).
export function cuerpoDeLibro(archivo: File, fecha?: string): FormData {
  const cuerpo = new FormData();
  cuerpo.append("libro", archivo, archivo.name);
  if (fecha) cuerpo.append("fecha_devolucion", fecha);
  return cuerpo;
}
