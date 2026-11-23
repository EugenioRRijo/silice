import { unidadEscrita } from "../../comun/unidades";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

// El Estado de una fila llega del servidor como «SEVERIDAD: mensaje | SEVERIDAD: mensaje», con los mensajes que escriben
// las reglas del núcleo (que no se tocan). Eugenio (2026-11-23) vio en el Presupuesto «⚠ Advertencia» y debajo
// «ADVERTENCIA: la cantidad … es manual y no declara la regla que la produjo: no es derivable ni reproducible». Aquí se
// lee para la persona: la severidad del primer aviso ya la dice el ícono, las demás van sin mayúsculas sostenidas, y los
// mensajes del núcleo que se conocen se dicen en español llano. Solo texto: nada se decide aquí.

const SEVERIDADES: Record<string, string> = {
  CRITICO: "Crítico",
  ERROR: "Error",
  ADVERTENCIA: "Advertencia",
  INFO: "Información",
  PENDIENTE: "Pendiente",
};

// La advertencia de R1 para una cantidad manual (`core/verification/reglas.py`; la reconoce también
// `aplicacion/hoja_partidas.py`, `_R1_MANUAL`).
const R1_MANUAL =
  /^la cantidad de (?<codigo>.+) \((?<cifra>[\d.,]+) (?<unidad>[^()]*)\) es manual y no declara la regla que la produjo: no es derivable ni reproducible$/;

function mensajeLlano(mensaje: string): string {
  const r1 = R1_MANUAL.exec(mensaje);
  if (r1?.groups) {
    const { codigo, cifra, unidad } = r1.groups;
    return `La cantidad de ${codigo} (${cifra!.includes(",") ? cifra : formatoEsVe(cifra!)} ${unidadEscrita(unidad!)}) se escribió a mano, sin el cálculo que la produce: Sílice no puede comprobar de dónde sale.`;
  }
  return mensaje.charAt(0).toUpperCase() + mensaje.slice(1);
}

export function estadoLlano(texto: string, severidad: string | null): string {
  return texto
    .split(" | ")
    .map((segmento, i) => {
      const m = /^([A-ZÁÉÍÓÚÑ]+): (.*)$/s.exec(segmento);
      if (m === null || !(m[1]! in SEVERIDADES)) return segmento;
      const llano = mensajeLlano(m[2]!);
      // El primer aviso es el de la severidad que muestra el ícono: no se repite. «Pendiente» no es una severidad.
      if (i === 0 && m[1] === severidad && m[1] !== "PENDIENTE") return llano;
      return `${SEVERIDADES[m[1]!]}: ${llano.charAt(0).toLowerCase()}${llano.slice(1)}`;
    })
    .join(" · ");
}
