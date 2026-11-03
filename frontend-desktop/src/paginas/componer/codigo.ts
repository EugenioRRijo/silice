// La forma del código de una partida (pulido F5, Tarea 1). Eugenio no es experto y el «Código» de texto libre le resultaba
// ambiguo (2026-10-21): el campo se busca por la descripción y lo que se escribe a mano tiene que tener forma de código.
// Es el `PATRON_CODIGO` de `api/esquemas_ola2.py` sin el espacio: letras sin tilde, cifras, punto, guion y guion bajo,
// sin empezar por un signo y hasta 64 caracteres (el código acaba en nombres de descarga).
const FORMA_DEL_CODIGO = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const CON_CIFRA = /[0-9]/;

export function esCodigoValido(texto: string): boolean {
  return FORMA_DEL_CODIGO.test(texto.trim());
}

// En «Agregar partida», lo escrito en «Partida» se toma como código solo si tiene su forma y lleva alguna cifra: «Z-99» es
// un código; «zanja» y «excavación de zanja», descripciones.
export function pareceCodigo(texto: string): boolean {
  return esCodigoValido(texto) && CON_CIFRA.test(texto);
}

export const AYUDA_DEL_CODIGO =
  "Escriba una palabra de la descripción o el código y elija de la lista, por ejemplo «zanja» o «E-411»; también puede escribir uno propio. Con este código la partida queda en el catálogo de la empresa; si ya existe, se cargan sus tablas.";

export const CODIGO_MAL_FORMADO =
  "Un código lleva letras sin tilde, cifras, punto, guion o guion bajo, sin espacios y hasta 64 caracteres, por ejemplo «E-411». Si escribió una descripción, póngala en «Descripción» y busque aquí el código por sus palabras.";
