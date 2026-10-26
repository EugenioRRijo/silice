// Logica pura de la navegacion por modulos: que areas ve la cuenta en la barra del modulo abierto, a que area y a que
// modulo pertenece la ruta actual, y en que modulo entra la cuenta. La visibilidad la decide `visible` (rutas.ts).
import { MODULOS, PAGINAS, modulosVisibles, paginaPorId, visible, type ModuloId, type PaginaDef } from "./rutas";

export interface GrupoNav {
  titulo: string | null;
  paginas: PaginaDef[];
}

export type EntradaNav =
  | { tipo: "enlace"; area: string; titulo: string; pagina: PaginaDef }
  | { tipo: "panel"; area: string; titulo: string; grupos: GrupoNav[] };

// Las areas del modulo, en su orden. Un area con una sola pantalla visible es un enlace directo que lleva el titulo del
// AREA (decision 2 de Eugenio: rita ve «Obras» y abre el Tablero; el titulo de la pantalla queda en su h1); con varias,
// un panel con un solo grupo sin titulo; sin ninguna, no aparece.
export function navegacion(
  modulo: ModuloId,
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): EntradaNav[] {
  const def = MODULOS.find((m) => m.id === modulo);
  if (!def) return [];
  return def.areas.flatMap((area): EntradaNav[] => {
    const delArea = paginas.filter(
      (p) => p.ubicacion?.modulo === modulo && p.ubicacion.area === area.id && visible(p, acciones, modoEntrega, paginas),
    );
    if (delArea.length === 0) return [];
    if (delArea.length === 1) return [{ tipo: "enlace", area: area.id, titulo: area.titulo, pagina: delArea[0] }];
    return [{ tipo: "panel", area: area.id, titulo: area.titulo, grupos: [{ titulo: null, paginas: delArea }] }];
  });
}

// Solo el primer segmento: sin consulta ni ancla (la barra recibe `useLocation().pathname`, pero no se fia).
function idDeRuta(pathname: string): string {
  return pathname.split(/[?#]/)[0].split("/")[1] ?? "";
}

export function areaActual(pathname: string, entradas: readonly EntradaNav[]): string | null {
  const id = idDeRuta(pathname);
  if (!id) return null;
  for (const e of entradas) {
    if (e.tipo === "enlace" ? e.pagina.id === id : e.grupos.some((g) => g.paginas.some((p) => p.id === id))) return e.area;
  }
  return null;
}

// El modulo sale de la pantalla (un marcador a /componer abre Presupuestos y obras aunque el ultimo fuera Auditoria).
// Fuera de los modulos (Administracion, Acerca) o en una ruta sin pantalla, queda el ultimo usado.
export function moduloDeRuta(
  pathname: string,
  ultimo: ModuloId | null,
  paginas: readonly PaginaDef[] = PAGINAS,
): ModuloId | null {
  const pagina = paginaPorId(idDeRuta(pathname), paginas);
  return pagina?.ubicacion?.modulo ?? ultimo;
}

// Modulo de entrada por rol (decision 3 de Eugenio, ratificada el 2026-10-25): quien arma y quien administra entran en
// Presupuestos y obras; quien revisa, en Auditoria. El rol se lee por una accion que solo tiene ese rol
// (seguridad/permisos.py); el primer renglon que la cuenta tenga y cuyo modulo vea es el que manda. Que cada una siga
// siendo exclusiva de su rol en la matriz lo vigila tests/unit/test_front_entrada_por_rol.py.
export const ENTRADA_POR_ROL: readonly { accion: string; modulo: ModuloId }[] = [
  { accion: "editar_hoja", modulo: "obras" },
  { accion: "revisar_paquete", modulo: "auditoria" },
  { accion: "administrar_precios", modulo: "obras" },
];

// El modulo guardado si la cuenta todavia lo puede usar; si no, el de su rol; si no, el primero visible; null si la
// cuenta no ve ningun modulo.
export function moduloAlEntrar(
  preferido: ModuloId | null,
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): ModuloId | null {
  const visibles = modulosVisibles(acciones, modoEntrega, paginas).map((m) => m.id);
  if (preferido !== null && visibles.includes(preferido)) return preferido;
  const porRol = ENTRADA_POR_ROL.find((e) => acciones.includes(e.accion) && visibles.includes(e.modulo));
  return porRol?.modulo ?? visibles[0] ?? null;
}
