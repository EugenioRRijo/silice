import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { describe, expect, test } from "vitest";

// D15 de la tanda de detalles (el árbitro del autocompletado señaló importaciones entre páginas y MONEDAS en tres sitios).
// Lo que dos páginas comparten va en `src/comun/`. Esta prueba lee el código fuente (no las pruebas) y no deja crecer la deuda:
//  - ninguna página importa de otra que no esté en `CONOCIDAS` (la lista solo puede achicarse: una entrada que ya no
//    se cumple también falla, para que se borre);
//  - `MONEDAS` se define una sola vez, en `comun/monedas.ts`.

const SRC = resolve(__dirname, "..");
const PAGINAS = join(SRC, "paginas");

function archivos(carpeta: string): string[] {
  return readdirSync(carpeta).flatMap((nombre) => {
    const ruta = join(carpeta, nombre);
    if (statSync(ruta).isDirectory()) return archivos(ruta);
    return /\.tsx?$/.test(nombre) && !/\.test\.tsx?$/.test(nombre) ? [ruta] : [];
  });
}

// «pagina -> otra/modulo» por cada importación relativa que sale de la carpeta de su página hacia otra página.
function importacionesEntrePaginas(): string[] {
  const halladas = new Set<string>();
  for (const ruta of archivos(PAGINAS)) {
    const propia = relative(PAGINAS, ruta).split(sep)[0];
    for (const m of readFileSync(ruta, "utf8").matchAll(/from\s+"(\.[^"]+)"/g)) {
      const destino = relative(PAGINAS, resolve(dirname(ruta), m[1])).split(sep);
      if (destino[0].startsWith("..") || destino[0] === propia) continue;
      halladas.add(`${propia} -> ${destino.join("/")}`);
    }
  }
  return [...halladas].sort();
}

// Deuda conocida al 2026-11-06, sin las que D15 movió a `comun/` (useCarga, CampoDeUnidad, CampoDePartida y sus datos).
// «archivos», «mercado» y «versiones» son pestañas de la Hoja y usan sus piezas; las demás se mueven cuando se toquen.
const CONOCIDAS = [
  "archivos -> hoja/AvisoDeEdicion",
  "archivos -> hoja/ProveedorDeLaHoja",
  "archivos -> hoja/logica",
  "archivos -> hoja/logicaSecciones",
  "archivos -> hoja/useDialogo",
  "archivos -> hoja/useDialogoDeOperacion",
  "auditoria -> inicio/UltimasAuditorias",
  "auditoria -> inicio/archivoPendiente",
  "control -> mercado/logica",
  "historial -> inicio/UltimasAuditorias",
  "hoja -> archivos/textos",
  "hoja -> componer/ComponerPartida",
  "hoja -> componer/codigo",
  "hoja -> control/logica",
  "inicio -> pendientes/logica",
  "inicio -> pendientes/textos",
  "mercado -> hoja/ContextoDeDialogos",
  "mercado -> hoja/DialogoDeOperacion",
  "mercado -> hoja/logica",
  "mercado -> hoja/logicaGuardar",
  "mercado -> hoja/logicaVersiones",
  "mercado -> hoja/useDialogoDeOperacion",
  "mercado -> hoja/useOfertas",
  "mercado -> hoja/useOperacion",
  "obras -> pendientes/logica",
  "produccion -> existencias/formato",
  "produccion -> inicio/PanelArenera",
  "riesgo -> hoja/logica",
  "versiones -> hoja/DialogoDeOperacion",
  "versiones -> hoja/ProveedorDeLaHoja",
  "versiones -> hoja/TablaPaginada",
  "versiones -> hoja/VistaCarga",
  "versiones -> hoja/logica",
  "versiones -> hoja/logicaGuardar",
  "versiones -> hoja/logicaVersiones",
  "versiones -> hoja/puedeEditar",
  "versiones -> hoja/textos",
  "versiones -> hoja/useAprobacionDeVersion",
  "versiones -> hoja/useDialogoDeOperacion",
  "versiones -> hoja/useGuardadoDeLaPagina",
  "versiones -> hoja/useOperacion",
  "vial -> hoja/logica",
  "vial -> produccion/AvisoConFoco",
];

describe("arquitectura del front", () => {
  test("ninguna página importa de otra salvo la deuda conocida, y la deuda conocida solo se achica", () => {
    const halladas = importacionesEntrePaginas();
    expect(halladas.filter((h) => !CONOCIDAS.includes(h))).toEqual([]);
    expect(CONOCIDAS.filter((c) => !halladas.includes(c))).toEqual([]);
  });

  test("MONEDAS se define una sola vez, en comun/monedas.ts", () => {
    const definiciones = archivos(SRC)
      .filter((ruta) => /\b(const|let|var)\s+MONEDAS\b/.test(readFileSync(ruta, "utf8")))
      .map((ruta) => relative(SRC, ruta).split(sep).join("/"));
    expect(definiciones).toEqual(["comun/monedas.ts"]);
  });
});
