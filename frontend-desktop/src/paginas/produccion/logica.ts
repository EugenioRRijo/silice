// Lógica pura de «Costos del período»: leer lo que escribe la persona, sumar y decir en español. Los montos se
// manejan como texto decimal y se suman con enteros grandes: nunca pasan por Number.
import { ErrorDeApi } from "../../api/cliente";
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

interface FilaSumable {
  centro: string;
  monto: string;
  moneda: string;
  anulado: boolean;
  anula_id: number | null;
}

export interface TotalDeCentro {
  centro: string;
  moneda: string;
  total: string; // decimal con punto
}

// Los costos vigentes sumados por centro y moneda. Los anulados y sus filas de anulación no suman.
export function totalesPorCentro(filas: readonly FilaSumable[]): TotalDeCentro[] {
  const grupos = new Map<string, { centro: string; moneda: string; montos: [string, string][] }>();
  for (const f of filas) {
    const m = DECIMAL.exec(f.monto);
    if (f.anulado || f.anula_id !== null || !m) continue;
    const clave = `${f.centro}|${f.moneda}`;
    const grupo = grupos.get(clave) ?? { centro: f.centro, moneda: f.moneda, montos: [] };
    grupo.montos.push([m[1]!, m[2] ?? ""]);
    grupos.set(clave, grupo);
  }
  return [...grupos.values()]
    .map(({ centro, moneda, montos }) => {
      const decimales = Math.max(2, ...montos.map(([, d]) => d.length));
      const suma = montos.reduce((acc, [e, d]) => acc + BigInt(e + d.padEnd(decimales, "0")), 0n);
      const texto = suma.toString().padStart(decimales + 1, "0");
      return { centro, moneda, total: `${texto.slice(0, -decimales)}.${texto.slice(-decimales)}` };
    })
    .sort((a, b) => a.centro.localeCompare(b.centro) || a.moneda.localeCompare(b.moneda));
}

const SIN_DETALLE = /respondió con el estado \d+/;

// Lo que se le dice a la persona cuando la API rechaza una acción de costos: nunca el nombre de un estado ni el
// cuerpo técnico de una validación. El `detalle` que escribe el servidor en español se muestra tal cual.
export function mensajeDeCostos(error: unknown): string {
  if (!(error instanceof ErrorDeApi)) return "Ocurrió un error inesperado. Inténtelo de nuevo.";
  if (error.estado === 403) return "Su cuenta no tiene permiso para registrar costos.";
  if (error.estado === 404) return "Ese costo ya no existe.";
  if (error.estado === 422 && SIN_DETALLE.test(error.detalle)) return "Revise los datos: alguno no es válido.";
  if (error.estado === 409 && SIN_DETALLE.test(error.detalle)) return "Ese costo ya fue anulado.";
  return error.detalle;
}
