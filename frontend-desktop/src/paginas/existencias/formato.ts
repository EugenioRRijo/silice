// Formato de cantidades y fechas. Nada aqui calcula: solo cambia como se escribe un texto decimal y se lee lo que
// escribe la persona (coma o punto) para mandarlo a la API con punto.

const DECIMAL_DE_API = /^([+-]?)(\d+)(?:\.(\d*))?$/;

// «24.5000» -> «24,5»; «20.000» -> «20»; «-0.000» -> «0». Sin separador de miles (igual que lo que se acepta al
// escribir). Un texto que no es decimal se devuelve como llego.
export function mostrarCantidad(texto: string): string {
  const m = DECIMAL_DE_API.exec(texto.trim());
  if (!m) return texto;
  const fraccion = (m[3] ?? "").replace(/0+$/, "");
  const esCero = /^0*$/.test(m[2]) && fraccion === "";
  const signo = m[1] === "-" && !esCero ? "-" : "";
  return `${signo}${m[2]}${fraccion ? `,${fraccion}` : ""}`;
}

export type LecturaDeCantidad = { valor: string } | { error: string };

interface OpcionesDeCantidad {
  // Conteo fisico y existencia minima aceptan 0.
  permiteCero?: boolean;
}

// Lo que escribe la persona: «24,5» y «24.5» valen lo mismo y salen con punto. Con coma y punto a la vez («1.234,5»)
// no se adivina cual es el decimal: se pide escribirlo sin separador de miles. Sin signo ni exponentes. `deQue` es la
// frase completa que sigue a «la cantidad» («de la entrada», «del conteo»).
export function leerCantidad(texto: string, deQue: string, opciones: OpcionesDeCantidad = {}): LecturaDeCantidad {
  const limpio = texto.trim();
  if (limpio === "") return { error: `Escriba la cantidad ${deQue}.` };
  if (limpio.includes(",") && limpio.includes(".")) {
    return { error: `La cantidad ${deQue} no debe llevar separador de miles: escriba, por ejemplo, 1234,5.` };
  }
  if (!/^\d+(?:[.,]\d+)?$/.test(limpio)) {
    return {
      error: opciones.permiteCero
        ? `La cantidad ${deQue} debe ser un número, cero o mayor.`
        : `La cantidad ${deQue} debe ser un número mayor que cero.`,
    };
  }
  const valor = limpio.replace(",", ".");
  if (!opciones.permiteCero && /^0+(?:\.0*)?$/.test(valor)) {
    return { error: `La cantidad ${deQue} debe ser un número mayor que cero.` };
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
