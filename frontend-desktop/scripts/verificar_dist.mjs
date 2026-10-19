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
// Solo en el bundle de los graficos (GraficoCarbon-*.js, Carbon Charts): enlaces de documentacion dentro de avisos de
// consola y de mensajes de error (charts.carbondesignsystem.com, el de date-fns en github.com). Nunca se piden a la red.
export const ANFITRIONES_DE_GRAFICOS = new Set(["charts.carbondesignsystem.com", "github.com"]);
const ARCHIVO_DE_GRAFICOS = /(^|[\\/])GraficoCarbon-[^\\/]*\.js$/;
// Solo en el bundle de Administracion (administracion-*.js): el texto «solo http://127.0.0.1:PUERTO» que describe la red
// local. Es la direccion de este mismo equipo, escrita en un mensaje, no una peticion.
export const ANFITRIONES_DE_ADMINISTRACION = new Set(["127.0.0.1"]);
const ARCHIVO_DE_ADMINISTRACION = /(^|[\\/])administracion-[^\\/]*\.js$/;
const ARCHIVO_PRINCIPAL = /(^|[\\/])index-[^\\/]*\.js$/;

// "reactjs.org" es un enlace de un mensaje de advertencia de React (como react.dev); "${...}" es un fragmento
// de plantilla de texto (`https://${direccion}`), no un anfitrion.
const ARCHIVO_DE_UNIVER = /(^|[\\/])adaptadorUniver-[^\\/]*\.(js|css)$/;

// http, https, ws y wss con anfitrion.
const URL_EXTERNA = /(?:https?|wss?):\/\/([^\s/'"`)\\<>?#:]+)/gi;
// URLs sin esquema que el navegador completa con el del sitio y mandan a otro anfitrion: url(//host/...) y
// @import "//host/..." en CSS, y src="//host/..." o href="//host/..." en HTML. Una ruta propia (/app/...) lleva una
// sola barra y no coincide.
const URL_SIN_ESQUEMA_CSS = /(?:url\(\s*|@import\s+)['"]?\/\/([^\s/'")\\<>?#:]+)/gi;
const URL_SIN_ESQUEMA_HTML = /\b(?:src|href)\s*=\s*['"]\/\/([^\s/'">\\<?#:]+)/gi;

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
    const extension = ruta.slice(ruta.lastIndexOf(".")).toLowerCase();
    const candidatas = [...texto.matchAll(URL_EXTERNA)];
    if (extension === ".css") candidatas.push(...texto.matchAll(URL_SIN_ESQUEMA_CSS));
    if (extension === ".html") candidatas.push(...texto.matchAll(URL_SIN_ESQUEMA_HTML));
    for (const m of candidatas) {
      const anfitrion = m[1].toLowerCase();
      if (anfitrion.startsWith("${")) continue; // fragmento de plantilla de texto
      if (ANFITRIONES_PERMITIDOS.has(anfitrion) || vistos.has(anfitrion)) continue;
      if (ARCHIVO_DE_UNIVER.test(ruta) && ANFITRIONES_DE_UNIVER.has(anfitrion)) continue;
      if (ARCHIVO_PRINCIPAL.test(ruta) && ANFITRIONES_DEL_ENRUTADOR.has(anfitrion)) continue;
      if (ARCHIVO_DE_ADMINISTRACION.test(ruta) && ANFITRIONES_DE_ADMINISTRACION.has(anfitrion)) continue;
      if (ARCHIVO_DE_GRAFICOS.test(ruta) && ANFITRIONES_DE_GRAFICOS.has(anfitrion)) continue;
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
