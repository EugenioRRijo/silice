// El presentador único de las filas del registro de cambios: lo comparten «Guardar versión», Versiones y Revisar › «Quién
// cambió qué». El servidor guarda claves técnicas («parametro», «control|spi_error», «largo=4.5; ancho=3.2»): forman parte
// de la huella y no se tocan; aquí solo se presentan en español llano, con coma decimal y punto de miles.

import { cifraSiLoEs } from "../indicadores/formatoEsVe";
import { rotuloDeOrigen } from "../paginas/hoja/logica";
import { rotuloDeCampo, rotuloDeParametro, valorDeCambio } from "./rotulos";

// La clave de la fila del registro: un parámetro tiene su rótulo; lo demás es un renglón o una fila del metraje.
export function presentarClave(objeto: string, clave: string): string {
  return objeto === "parametro" ? rotuloDeParametro(clave) : rotuloDeOrigen(clave);
}

// El alta o la baja de una fila de metraje lleva el resumen «clave=valor; clave=valor» (`_resumen_de_fila`, aplicacion/hoja.py).
const CLAVE_DE_RESUMEN = /^[a-z][a-z0-9_]*$/;

function resumenCompuesto(valor: string): string | null {
  const partes = valor.split("; ");
  const pares: [string, string][] = [];
  for (const parte of partes) {
    const i = parte.indexOf("=");
    if (i <= 0 || !CLAVE_DE_RESUMEN.test(parte.slice(0, i))) return null;
    pares.push([parte.slice(0, i), parte.slice(i + 1)]);
  }
  return pares.map(([k, v]) => `${rotuloDeCampo(k)}=${cifraSiLoEs(v)}`).join("; ");
}

// El antes o el después de un cambio de ese campo.
export function presentarValor(campo: string, valor: string): string {
  if (campo === "fila") {
    const compuesto = resumenCompuesto(valor);
    if (compuesto !== null) return compuesto;
  }
  return valorDeCambio(campo, valor);
}
