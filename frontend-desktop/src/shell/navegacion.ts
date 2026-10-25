// Logica pura de la barra superior: que entradas se muestran y a que area pertenece la ruta actual.
// Se construye sobre `areasVisibles` (rutas.ts), que ya decide la visibilidad por permisos y modo entrega.
import { AREAS, PAGINAS, areasVisibles, type PaginaDef } from "./rutas";

export interface GrupoNav {
  titulo: string | null;
  paginas: PaginaDef[];
}

export type EntradaNav =
  | { tipo: "enlace"; area: string; titulo: string; pagina: PaginaDef }
  | { tipo: "panel"; area: string; titulo: string; grupos: GrupoNav[] };

export function navegacion(
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): EntradaNav[] {
  return areasVisibles(acciones, modoEntrega, paginas).map((area): EntradaNav => {
    if (area.paginas.length === 1) {
      const pagina = area.paginas[0];
      return { tipo: "enlace", area: area.id, titulo: pagina.titulo, pagina };
    }
    const def = AREAS.find((a) => a.id === area.id);
    if (!def?.grupos) {
      return { tipo: "panel", area: area.id, titulo: area.titulo, grupos: [{ titulo: null, paginas: area.paginas }] };
    }
    const grupos: GrupoNav[] = [];
    const usadas = new Set<string>();
    for (const g of def.grupos) {
      const delGrupo = area.paginas.filter((p) => g.paginas.includes(p.id));
      delGrupo.forEach((p) => usadas.add(p.id));
      if (delGrupo.length > 0) grupos.push({ titulo: g.titulo, paginas: delGrupo });
    }
    const otras = area.paginas.filter((p) => !usadas.has(p.id));
    if (otras.length > 0) grupos.push({ titulo: "Otras", paginas: otras });
    return { tipo: "panel", area: area.id, titulo: area.titulo, grupos };
  });
}

export function areaActual(pathname: string, entradas: readonly EntradaNav[]): string | null {
  const id = pathname.split("/")[1] ?? "";
  if (!id) return null;
  for (const e of entradas) {
    if (e.tipo === "enlace" ? e.pagina.id === id : e.grupos.some((g) => g.paginas.some((p) => p.id === id))) return e.area;
  }
  return null;
}
