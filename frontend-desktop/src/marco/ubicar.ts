import { paginaPorId, type PaginaDef } from "../shell/rutas";
import { ESPACIOS, SECCIONES_DE_CUENTA, SUBVISTAS, esEspacio } from "./espacios";
import { RUTA_DE_PENDIENTES, RUTA_DE_VISTA_GENERAL, carpetaDeLaRuta, seccionPorId } from "./secciones";
import type { ObraDeCarpeta } from "./useObras";

export interface Ubicada {
  // El título de la pestaña del navegador (sin «Sílice», lo agrega useTituloDelDocumento); null sin pantalla.
  titulo: string | null;
}

// `#/obra/<carpeta>/<obra>/<sección>` y, con subvista, `…/<sección>/<subvista>` (F6, T5).
const OBRA = /^\/obra\/([^/]+)\/([1-9]\d*)\/([^/]+)(?:\/([^/]+))?$/;
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

// Dónde está la persona, dicho en el título de la pestaña («Presupuesto · Clínica», «Reajuste · Control de obra · Clínica»,
// «Existencias · Costos de producción», «Cuentas y permisos», «Pendientes»). Las obras dan el nombre de la de la ruta;
// mientras llegan, «Obra». Desde F6, T6 la barra de arriba no lleva migas: el título del documento es lo único que queda
// de ellas, y la cabecera y la barra de cada espacio dicen dónde se está.
export function ubicar(pathname: string, obras: readonly ObraDeCarpeta[], paginas: readonly PaginaDef[]): Ubicada {
  if (pathname === RUTA_DE_PENDIENTES) return { titulo: "Pendientes" };
  if (pathname === RUTA_DE_VISTA_GENERAL) return { titulo: "Vista general" };
  const deObra = OBRA.exec(pathname);
  if (deObra) {
    const carpeta = carpetaDelDestino(pathname) ?? null;
    const obraId = Number(deObra[2]);
    const nombre = obras.find((o) => o.carpeta === carpeta && o.obra_id === obraId)?.obra ?? "Obra";
    const seccion = seccionPorId(deObra[3]);
    // Una subvista que no existe se ubica como su sección (la ruta la lleva a la primera subvista usable de la sección, según `vistaDeLaSeccion`).
    const subvista = seccion && deObra[4] !== undefined ? SUBVISTAS[seccion.id]?.find((v) => v.id !== "" && v.id === deObra[4]) : undefined;
    if (seccion && subvista) return { titulo: `${subvista.titulo} · ${seccion.titulo} · ${nombre}` };
    return { titulo: seccion ? `${seccion.titulo} · ${nombre}` : nombre };
  }
  // Producción, Auditoría y Precios (F6, T4): «Existencias · Costos de producción»; la Cuenta (F6, T6): el de la sección.
  const deEspacio = ESPACIO.exec(pathname);
  if (deEspacio && esEspacio(deEspacio[1])) {
    const espacio = ESPACIOS[deEspacio[1]];
    const herramienta = espacio.herramientas.find((h) => h.id === deEspacio[2]);
    if (herramienta) return { titulo: `${herramienta.titulo} · ${espacio.titulo}` };
  }
  if (deEspacio && deEspacio[1] === "cuenta") {
    const cuenta = SECCIONES_DE_CUENTA.find((c) => c.id === deEspacio[2]);
    if (cuenta) return { titulo: cuenta.titulo };
  }
  const pagina = paginaPorId(pathname.slice(1), paginas);
  return { titulo: pagina ? pagina.titulo : null };
}
