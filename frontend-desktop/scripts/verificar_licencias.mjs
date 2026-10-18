// Control de licencias (RNF-22): recorre package-lock.json y falla ante @univerjs-pro/* o una licencia
// fuera de la lista permisiva. Uso: node scripts/verificar_licencias.mjs [ruta/al/package-lock.json]
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const LICENCIAS_PERMITIDAS = new Set([
  "MIT",
  "Apache-2.0",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "ISC",
  "0BSD",
  "OFL-1.1",
  "BlueOak-1.0.0",
  "CC0-1.0",
  "Python-2.0",
  "MIT-0", // MIT sin atribucion: mas permisiva que MIT (ruling RS2.1-1)
]);

// Ruling RS2.1-1: solo para paquetes de DESARROLLO (marcados `dev: true` en el lock), que no viajan en el dist:
// MPL-2.0 (lightningcss, de vite 8; copyleft por archivo, aplica a quien distribuye esos archivos) y
// CC-BY-4.0 (caniuse-lite, datos de navegadores para browserslist). En una dependencia de produccion fallan.
export const LICENCIAS_SOLO_DESARROLLO = new Set(["MPL-2.0", "CC-BY-4.0"]);

function nombreDe(ruta) {
  const i = ruta.lastIndexOf("node_modules/");
  return i === -1 ? ruta : ruta.slice(i + "node_modules/".length);
}

// "(MIT OR Apache-2.0)" es valida si TODAS sus alternativas estan permitidas (criterio estricto).
export function licenciaPermitida(expresion, esDesarrollo = false) {
  const permitidas = (p) => LICENCIAS_PERMITIDAS.has(p) || (esDesarrollo && LICENCIAS_SOLO_DESARROLLO.has(p));
  const partes = expresion
    .replace(/[()]/g, " ")
    .split(/\s+OR\s+/i)
    .map((p) => p.trim())
    .filter(Boolean);
  return partes.length > 0 && partes.every(permitidas);
}

export function verificarLock(lock) {
  const problemas = [];
  const cuentas = {};
  for (const [ruta, datos] of Object.entries(lock.packages ?? {})) {
    if (ruta === "") continue;
    const nombre = nombreDe(ruta);
    if (nombre.startsWith("@univerjs-pro/")) {
      problemas.push(`${nombre}: paquete prohibido (@univerjs-pro/* no es Apache-2.0)`);
      continue;
    }
    const licencia = typeof datos.license === "string" ? datos.license : undefined;
    if (!licencia) {
      problemas.push(`${nombre}@${datos.version ?? "?"}: sin licencia declarada en el lock`);
      continue;
    }
    cuentas[licencia] = (cuentas[licencia] ?? 0) + 1;
    if (!licenciaPermitida(licencia, datos.dev === true)) {
      problemas.push(`${nombre}@${datos.version ?? "?"}: licencia no permitida (${licencia})`);
    }
  }
  return { problemas, cuentas };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const raiz = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const ruta = resolve(process.argv[2] ?? join(raiz, "package-lock.json"));
  const { problemas, cuentas } = verificarLock(JSON.parse(readFileSync(ruta, "utf8")));
  console.log("Paquetes por licencia:");
  for (const [licencia, n] of Object.entries(cuentas).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${licencia}: ${n}`);
  }
  if (problemas.length > 0) {
    for (const p of problemas) console.error(`ERROR ${p}`);
    process.exit(1);
  }
  console.log("licencias: todas permitidas, sin @univerjs-pro");
}
