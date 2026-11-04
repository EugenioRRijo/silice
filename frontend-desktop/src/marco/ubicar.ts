import { paginaPorId, type PaginaDef } from "../shell/rutas";
import { ESPACIOS, SUBVISTAS, esEspacio } from "./espacios";
import type { Miga } from "./Migas";
import {
  ENTRADAS_DE_EMPRESA,
  RUTA_DE_PENDIENTES,
  carpetaDeLaRuta,
  rutaDeObra,
  seccionPorId,
} from "./secciones";
import type { ObraDeCarpeta } from "./useObras";

export interface Ubicada {
  migas: Miga[];
  // El título de la pestaña del navegador (sin «Sílice», lo agrega useTituloDelDocumento); null sin pantalla.
  titulo: string | null;
}

// `#/obra/<carpeta>/<obra>/<sección>` y, con subvista, `…/<sección>/<subvista>` (F6, T5).
const OBRA = /^\/obra\/([^/]+)\/([1-9]\d*)\/([^/]+)(?:\/([^/]+))?$/;
const EMPRESA = /^\/empresa\/([^/]+)$/;
const ESPACIO = /^\/([^/]+)\/([^/]+)$/;

// La carpeta de una ruta `#/obra/<carpeta>/<obra>/<sección>[/<subvista>]` (null = la de la empresa), o undefined si la ruta no es de
// una obra. La consulta (`?…`) no cuenta.
export function carpetaDelDestino(destino: string): string | null | undefined {
  const m = OBRA.exec(destino.split("?")[0]);
  if (!m) return undefined;
  try {
    return carpetaDeLaRuta(decodeURIComponent(m[1]));
  } catch {
    return undefined;
  }
}

// Dónde está la persona, dicho en migas («Mis obras / Clínica / Presupuesto», «Mis obras / Clínica / Control de obra /
// Reajuste», «Empresa / Ayuda», «Pendientes») y en el título de la pestaña. Las obras dan el nombre de la de la ruta; mientras llegan, «Obra».
export function ubicar(pathname: string, obras: readonly ObraDeCarpeta[], paginas: readonly PaginaDef[]): Ubicada {
  if (pathname === RUTA_DE_PENDIENTES) return { migas: [{ texto: "Pendientes" }], titulo: "Pendientes" };
  const deObra = OBRA.exec(pathname);
  if (deObra) {
    const carpeta = carpetaDelDestino(pathname) ?? null;
    const obraId = Number(deObra[2]);
    const nombre = obras.find((o) => o.carpeta === carpeta && o.obra_id === obraId)?.obra ?? "Obra";
    const seccion = seccionPorId(deObra[3]);
    const migas: Miga[] = [
      { texto: "Mis obras", ruta: RUTA_DE_PENDIENTES },
      { texto: nombre, ruta: rutaDeObra(carpeta, obraId, "resumen") },
    ];
    // Una subvista que no existe se ubica como su sección (la ruta la lleva a la pantalla principal).
    const subvista = seccion && deObra[4] !== undefined ? SUBVISTAS[seccion.id]?.find((v) => v.id !== "" && v.id === deObra[4]) : undefined;
    if (seccion && subvista) {
      migas.push({ texto: seccion.titulo, ruta: rutaDeObra(carpeta, obraId, seccion.id) }, { texto: subvista.titulo });
      return { migas, titulo: `${subvista.titulo} · ${seccion.titulo} · ${nombre}` };
    }
    if (seccion) migas.push({ texto: seccion.titulo });
    return { migas, titulo: seccion ? `${seccion.titulo} · ${nombre}` : nombre };
  }
  // Producción, Auditoría y Precios (F6, T4): «Existencias · Costos de producción».
  const deEspacio = ESPACIO.exec(pathname);
  if (deEspacio && esEspacio(deEspacio[1])) {
    const espacio = ESPACIOS[deEspacio[1]];
    const herramienta = espacio.herramientas.find((h) => h.id === deEspacio[2]);
    if (herramienta) {
      return {
        migas: [{ texto: espacio.titulo }, { texto: herramienta.titulo }],
        titulo: `${herramienta.titulo} · ${espacio.titulo}`,
      };
    }
  }
  const deEmpresa = EMPRESA.exec(pathname);
  const entrada = deEmpresa ? ENTRADAS_DE_EMPRESA.find((e) => e.id === deEmpresa[1]) : undefined;
  if (entrada) return { migas: [{ texto: "Empresa" }, { texto: entrada.titulo }], titulo: entrada.titulo };
  const pagina = paginaPorId(pathname.slice(1), paginas);
  return pagina ? { migas: [{ texto: pagina.titulo }], titulo: pagina.titulo } : { migas: [], titulo: null };
}
