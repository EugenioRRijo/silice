// F8, C4: poda de los patrones de silabeo de Univer en el dist (RNF-22: dist de 15 000 000 bytes como mucho).
//
// `@univerjs/engine-render` declara una tabla `PATTERN_LOADERS` con un `import()` por idioma (70 idiomas, unos 4,4 MB que
// Vite emite como trozos perezosos aunque nadie los pida). El motor solo silabea un párrafo con el silabeo automático de un
// documento encendido (`autoHyphenation`), que la hoja del visor no enciende; si falta el cargador de un idioma, Univer
// sigue sin silabear (`_loadPattern`: «if (!loader) return»). Se conservan el español y el inglés por si algún día se
// enciende. Sin la tabla (otra versión de Univer) la poda falla en voz alta: hay que revisar el código nuevo antes de
// compilar.

export const IDIOMAS_CONSERVADOS = new Set(["es", "en-gb", "en-us"]);

const INICIO = "const PATTERN_LOADERS = {";

// Una entrada de la tabla: `["<idioma>"]: () => …,` en su propia línea (la última puede ir sin coma).
const ENTRADA = /^\s*\["([^"]+)"\]:\s*\(\)\s*=>.*?,?\s*$/;

/** @param {string} id */
export function esCargadorDePatrones(id) {
  return /[\\/]@univerjs[\\/]engine-render[\\/]lib[\\/](?:es[\\/])?index\.js(?:\?|$)/.test(id);
}

/** @param {string} codigo @param {ReadonlySet<string>} [conservar] @returns {string} */
export function podarPatrones(codigo, conservar = IDIOMAS_CONSERVADOS) {
  const desde = codigo.indexOf(INICIO);
  if (desde < 0) throw new Error("No se encontró la tabla PATTERN_LOADERS de Univer: revise scripts/patronesDeSilabeo.mjs con la versión nueva");
  const cuerpo = desde + INICIO.length;
  const hasta = codigo.indexOf("\n};", cuerpo);
  if (hasta < 0) throw new Error("La tabla PATTERN_LOADERS de Univer no termina como se esperaba");
  const lineas = codigo.slice(cuerpo, hasta).split("\n");
  const quedan = lineas.filter((linea) => {
    const entrada = ENTRADA.exec(linea);
    return entrada === null || conservar.has(entrada[1]);
  });
  // Cada entrada conservada termina en coma: así la que era la última y la que la sigue no se juntan.
  const tabla = quedan.map((linea) => (ENTRADA.test(linea) && !linea.trimEnd().endsWith(",") ? `${linea.trimEnd()},` : linea));
  return codigo.slice(0, cuerpo) + tabla.join("\n") + codigo.slice(hasta);
}
