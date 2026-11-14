// Formato de cantidades y fechas. Nada aqui calcula: solo cambia como se escribe un texto decimal y se lee lo que
// escribe la persona (coma decimal y punto de miles, regla de Eugenio del 2026-10-25) para mandarlo a la API con punto.
import { MENSAJE_CIFRA, leerCifra } from "../../indicadores/cifraEscrita";
import { cantidadEsVe } from "../../indicadores/formatoEsVe";

// «24.5000» -> «24,5»; «20.000» -> «20»; «1234.5» -> «1.234,5»; «-0.000» -> «0». Coma decimal y punto de miles, como
// se escribe al registrar. Un texto que no es decimal se devuelve como llego. Es `cantidadEsVe`, la de toda la interfaz.
export const mostrarCantidad = cantidadEsVe;

export type LecturaDeCantidad = { valor: string } | { error: string };

interface OpcionesDeCantidad {
  // Conteo fisico y existencia minima aceptan 0.
  permiteCero?: boolean;
}

// Lo que escribe la persona con la regla de `leerCifra`: «24,5» y «1.234,5» salen con punto («24.5», «1234.5»); «2.5» o
// «1,234.5» se rechazan con la regla, sin adivinar. Sin signo: una cantidad es positiva (o cero si se permite). `deQue`
// es la frase completa que sigue a «la cantidad» («de la entrada», «del conteo»).
export function leerCantidad(texto: string, deQue: string, opciones: OpcionesDeCantidad = {}): LecturaDeCantidad {
  if (texto.trim() === "") return { error: `Escriba la cantidad ${deQue}.` };
  const lectura = leerCifra(texto);
  if ("error" in lectura) return { error: `La cantidad ${deQue} está mal escrita. ${MENSAJE_CIFRA}` };
  const { valor } = lectura;
  const esCero = /^0(?:\.0*)?$/.test(valor);
  if (valor.startsWith("-") || (!opciones.permiteCero && esCero)) {
    return {
      error: opciones.permiteCero
        ? `La cantidad ${deQue} debe ser un número, cero o mayor.`
        : `La cantidad ${deQue} debe ser un número mayor que cero.`,
    };
  }
  return { valor };
}

function dos(n: number): string {
  return String(n).padStart(2, "0");
}

// El dia local (no el UTC): a las 11 de la noche en Venezuela sigue siendo el mismo dia.
export function hoyISO(ahora: Date = new Date()): string {
  return `${ahora.getFullYear()}-${dos(ahora.getMonth() + 1)}-${dos(ahora.getDate())}`;
}

// Fecha y hora local sin zona (AAAA-MM-DDThh:mm:ss): lo que pide la API en `ahora`.
export function ahoraLocalISO(ahora: Date = new Date()): string {
  return `${hoyISO(ahora)}T${dos(ahora.getHours())}:${dos(ahora.getMinutes())}:${dos(ahora.getSeconds())}`;
}

export function rotuloUnidad(unidad: string): string {
  return unidad === "m3" ? "m³" : unidad;
}

const FECHA_ISO = /^\d{4}-\d{2}-\d{2}$/;

// La fecha de un pesaje de la bandeja si es AAAA-MM-DD valida (los primeros 10 caracteres, como la hora del reporte
// «2026-10-15 08:30»); si no, vacia: no se adivina.
export function fechaIsoDe(texto: string): string {
  const diez = texto.trim().slice(0, 10);
  if (!FECHA_ISO.test(diez)) return "";
  const fecha = new Date(`${diez}T00:00:00Z`);
  return Number.isNaN(fecha.getTime()) || fecha.toISOString().slice(0, 10) !== diez ? "" : diez;
}
