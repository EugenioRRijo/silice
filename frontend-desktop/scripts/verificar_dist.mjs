// Control del dist (RNF-22, RNF-23): tamano <= 15 000 000 bytes y ninguna URL a otro anfitrion.
// Uso: node scripts/verificar_dist.mjs [carpeta]   (por omision ./dist)
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const LIMITE_BYTES = 15_000_000;

// Lista blanca explicita (ruling RS2.1-2). Ninguno de estos anfitriones se consulta en ejecucion:
//  - www.w3.org: espacios de nombres XML/SVG/MathML, que son identificadores y no se descargan.
//  - react.dev, fb.me: enlaces dentro de textos de error de React y prop-types, que solo se imprimen.
export const ANFITRIONES_PERMITIDOS = new Set(["www.w3.org", "react.dev", "fb.me", "reactjs.org"]);

// Solo en el archivo de Univer (adaptadorUniver-*.js/css, el visor de la hoja; ruling RS2.4-5). Son textos y
// identificadores que Univer lleva dentro y que nunca se piden a la red:
//  - support.google.com, support.microsoft.com, www.wps.cn: enlaces "mas informacion" de la descripcion de cada
//    funcion de hoja de calculo (solo se muestran).
//  - univer.ai, github.com, example.com: ejemplos de la ayuda de HYPERLINK, IMAGE y ENCODEURL, y el URI de los
//    tipos de operacion (ot-json, text-x) que Univer usa como nombre; example.com tambien aparece en una clase
//    de Tailwind de ejemplo que ningun elemento usa.
//  - universheet.net, redi.wzhu.dev: enlaces dentro de mensajes de error de consola.
//  - sharejs.org: URI de tipo de operacion (text-unicode, json1), un identificador.
//  - localhost: base para interpretar un enlace relativo (new URL) y una comparacion de texto.
// Los datos de la hoja, las fuentes y la telemetria no usan ninguno (Univer no trae implementacion de telemetria
// y no se le da workerURL). Cualquiera de estos anfitriones fuera de ese archivo sigue siendo un error.
export const ANFITRIONES_DE_UNIVER = new Set([
  "support.google.com",
  "support.microsoft.com",
  "www.wps.cn",
  "univer.ai",
  "github.com",
  "example.com",
  "universheet.net",
  "redi.wzhu.dev",
  "sharejs.org",
  "localhost",
]);
// Solo en el bundle principal (index-*.js), donde queda react-router (ruling RS2B-2). Son textos que el enrutador
// lleva dentro y que nunca se piden a la red:
//  - reactrouter.com: enlace dentro de un mensaje de error («must be used within a data router. See ...»).
//  - localhost: base falsa de `new URL(ruta, "http://localhost")`, para interpretar rutas relativas.
export const ANFITRIONES_DEL_ENRUTADOR = new Set(["reactrouter.com", "localhost"]);
const ARCHIVO_PRINCIPAL = /(^|[\\/])index-[^\\/]*\.js$/;

// "reactjs.org" es un enlace de un mensaje de advertencia de React (como react.dev); "${...}" es un fragmento
// de plantilla de texto (`https://${direccion}`), no un anfitrion.
const ARCHIVO_DE_UNIVER = /(^|[\\/])adaptadorUniver-[^\\/]*\.(js|css)$/;

const URL_EXTERNA = /https?:\/\/([^\s/'"`)\\<>?#:]+)/gi;

function* archivos(carpeta) {
  for (const nombre of readdirSync(carpeta)) {
    const ruta = join(carpeta, nombre);
    if (statSync(ruta).isDirectory()) yield* archivos(ruta);
    else yield ruta;
  }
}

export function verificarDist(carpeta) {
  const problemas = [];
  if (!existsSync(carpeta)) {
    return { bytes: 0, archivos: 0, problemas: [`No existe la carpeta ${carpeta}; corra npm run build antes.`] };
  }
  let bytes = 0;
  let cuenta = 0;
  for (const ruta of archivos(carpeta)) {
    const contenido = readFileSync(ruta);
    bytes += contenido.length;
    cuenta += 1;
    const texto = contenido.toString("latin1");
    const vistos = new Set();
    for (const m of texto.matchAll(URL_EXTERNA)) {
      const anfitrion = m[1].toLowerCase();
      if (anfitrion.startsWith("${")) continue; // fragmento de plantilla de texto
      if (ANFITRIONES_PERMITIDOS.has(anfitrion) || vistos.has(anfitrion)) continue;
      if (ARCHIVO_DE_UNIVER.test(ruta) && ANFITRIONES_DE_UNIVER.has(anfitrion)) continue;
      if (ARCHIVO_PRINCIPAL.test(ruta) && ANFITRIONES_DEL_ENRUTADOR.has(anfitrion)) continue;
      vistos.add(anfitrion);
      problemas.push(`${ruta}: URL hacia el anfitrion externo ${anfitrion} (RNF-22)`);
    }
  }
  if (bytes > LIMITE_BYTES) {
    problemas.push(`El dist pesa ${bytes} bytes y el limite es ${LIMITE_BYTES} (RNF-23); tope 15000000.`);
  }
  return { bytes, archivos: cuenta, problemas };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const raiz = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const carpeta = resolve(process.argv[2] ?? join(raiz, "dist"));
  const { bytes, archivos: n, problemas } = verificarDist(carpeta);
  console.log(`dist: ${n} archivos, ${bytes} bytes (limite ${LIMITE_BYTES})`);
  if (problemas.length > 0) {
    for (const p of problemas) console.error(`ERROR ${p}`);
    process.exit(1);
  }
  console.log("dist: sin URLs externas y dentro del tamano permitido");
}
