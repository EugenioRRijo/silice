// Un solo formato numerico en la pantalla del libro: punto decimal y sin separador de miles. Solo operaciones de
// cadena (nunca se convierte a numero), de modo que el monto exacto no cambia.
// Reconoce "4 331,43", "4.331,43" y "12,5"; no toca "3, 4, 5" (coma seguida de espacio).
const SEPARADOR = "[ \\u00a0\\u202f.]";
const MONTO_LOCAL = new RegExp(`\\d{1,3}(?:${SEPARADOR}\\d{3})+,\\d+|\\d+,\\d+`, "g");
const SEPARADORES = new RegExp(SEPARADOR, "g");

export function montosEnFormatoUnico(texto: string): string {
  return texto.replace(MONTO_LOCAL, (m) => m.replace(SEPARADORES, "").replace(",", "."));
}
