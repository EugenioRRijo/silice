// Lógica pura de «Costos del período»: leer lo que escribe la persona y decir en español. La interfaz no calcula
// montos (los totales los suma el servidor): solo cambia cómo se escriben. Los montos son texto decimal y nunca
// pasan por Number.
import { ErrorDeApi } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { MENSAJE_CIFRA, leerCifra } from "../../indicadores/cifraEscrita";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

// Los de `produccion/costos.py`, con el rótulo que lee la persona.
export const CENTROS: readonly { valor: string; texto: string }[] = [
  { valor: "cantera", texto: "Cantera" },
  { valor: "planta", texto: "Planta" },
];
export const CONCEPTOS: readonly { valor: string; texto: string }[] = [
  { valor: "gasoil", texto: "Gasoil" },
  { valor: "equipo", texto: "Equipo" },
  { valor: "nomina", texto: "Nómina" },
  { valor: "mantenimiento", texto: "Mantenimiento" },
  { valor: "explosivos", texto: "Explosivos" },
  { valor: "energia", texto: "Energía" },
  { valor: "otro", texto: "Otro" },
];
export const MONEDAS: readonly { valor: string; texto: string }[] = [
  { valor: "Bs", texto: "Bolívares (Bs)" },
  { valor: "USD", texto: "Dólares (USD)" },
];

export function rotulo(lista: readonly { valor: string; texto: string }[], valor: string): string {
  return lista.find((e) => e.valor === valor)?.texto ?? valor;
}

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const PERIODO = /^(\d{4})-(0[1-9]|1[0-2])$/;

export function periodoValido(texto: string): boolean {
  return PERIODO.test(texto);
}

// «2026-11» -> «noviembre de 2026».
export function nombreDelMes(periodo: string): string {
  const m = PERIODO.exec(periodo);
  return m ? `${MESES[Number(m[2]) - 1]} de ${m[1]}` : periodo;
}

// El día local de hoy si cae en el período; si no, el primero del período.
export function fechaInicial(periodo: string, hoy: string): string {
  return hoy.startsWith(`${periodo}-`) ? hoy : `${periodo}-01`;
}

export type LecturaDeMonto = { valor: string } | { error: string };

// Lo que escribe la persona («1.250,50») al decimal con punto de la API («1250.50»). Sin signo; el cero vale.
export function leerMonto(texto: string): LecturaDeMonto {
  if (texto.trim() === "") return { error: "Escriba el monto." };
  const lectura = leerCifra(texto);
  if ("error" in lectura) return { error: `El monto está mal escrito. ${MENSAJE_CIFRA}` };
  if (lectura.valor.startsWith("-")) return { error: "El monto debe ser un número, cero o mayor." };
  return lectura;
}

const DECIMAL = /^(\d+)(?:\.(\d+))?$/;

// «1250.5» -> «1.250,50»: al menos dos decimales, coma decimal y punto de miles.
export function mostrarMonto(texto: string): string {
  const m = DECIMAL.exec(texto.trim());
  if (!m) return texto;
  return formatoEsVe(`${m[1]}.${(m[2] ?? "").padEnd(2, "0")}`);
}

// «2026-11-03» -> «03/11/2026».
export function fechaEsVe(iso: string): string {
  const [anio, mes, dia] = iso.split("-");
  return anio && mes && dia ? `${dia}/${mes}/${anio}` : iso;
}

const SIN_DETALLE = /respondió con el estado \d+/;

// Lo que se le dice a la persona cuando la API rechaza una acción de costos: nunca el nombre de un estado ni el
// cuerpo técnico de una validación. El `detalle` que escribe el servidor en español se muestra tal cual.
export function mensajeDeCostos(error: unknown): string {
  if (!(error instanceof ErrorDeApi)) return mensajeDeError(error);
  if (error.estado === 403) return "Su cuenta no tiene permiso para registrar costos.";
  if (error.estado === 404) return "Ese costo ya no existe.";
  if (error.estado === 422 && SIN_DETALLE.test(error.detalle)) return "Revise los datos: alguno no es válido.";
  if (error.estado === 409 && SIN_DETALLE.test(error.detalle)) return "Ese costo ya fue anulado.";
  return mensajeDeError(error);
}
