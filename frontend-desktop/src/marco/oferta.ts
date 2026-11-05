import { useContext } from "react";
import { ContextoAplicacion } from "../shell/contexto";
import { PAGINAS, paginaPorId, usable, type PaginaDef } from "../shell/rutas";
import { ESPACIOS, ESPACIOS_EN_LA_BARRA, SECCIONES_DE_CUENTA, SUBVISTAS, cuentaUsable, primeraUsable, rutaDeHerramienta } from "./espacios";
import type { CuentaDef, EspacioId } from "./espacios";
import { SECCIONES_DE_OBRA, type SeccionDef } from "./secciones";
import type { ObraDeCarpeta } from "./useObras";

// Un espacio de la empresa que la cuenta puede usar: lleva a su primera herramienta usable.
export interface EspacioOfrecido {
  id: EspacioId;
  titulo: string;
  ruta: string;
}

// Lo que una cuenta puede ofrecerse en el marco: la barra lateral y el buscador comparten estas reglas para que ninguna
// de las dos muestre algo que la cuenta no puede usar (la API vuelve a exigirlo, pero aquí no se ofrece).
export interface Oferta {
  // Las de toda obra (incluida «Tramos» mientras el módulo vial esté encendido).
  secciones: readonly SeccionDef[];
  // Las secciones de la Cuenta que la cuenta puede usar (F6, T6; contrato 3), en el orden de su barra.
  cuenta: readonly CuentaDef[];
  // Los espacios de la empresa con al menos una herramienta usable, en el orden de la barra lateral (F6, T4).
  espacios: readonly EspacioOfrecido[];
  // Desde F6 (contrato de rutas) toda pantalla tiene sitio: queda vacío. Se conserva hasta que se retire a quien lo lee (busqueda.ts).
  sueltas: readonly PaginaDef[];
  // Las pantallas usables de los espacios de la empresa y de las subvistas de la obra que no son sección ni entrada del
  // árbol (libros, historial, simulador, tablero, reajuste…): el buscador las ofrece por su ruta canónica.
  herramientas: readonly PaginaDef[];
}

function usableLa(pagina: string | null, acciones: readonly string[], modoEntrega: boolean, apagados: readonly string[]): boolean {
  const def = pagina === null ? undefined : paginaPorId(pagina);
  return def !== undefined && usable(def, acciones, modoEntrega, apagados);
}

// `apagados` son los módulos que la instalación apagó (plan vial, Tarea 19): sus secciones, entradas y pantallas no se ofrecen.
export function ofertaDe(acciones: readonly string[], modoEntrega: boolean, apagados: readonly string[] = []): Oferta {
  // Una sección con `pagina: null` aún no tiene pantalla: no se ofrece. Una cuya pantalla principal no es usable pero que
  // tiene una subvista usable sí se ofrece y abre en ella (contrato 2.1: Aprobaciones para quien solo revisa paquetes).
  const secciones = SECCIONES_DE_OBRA.filter(
    (s) =>
      usableLa(s.pagina, acciones, modoEntrega, apagados) ||
      (SUBVISTAS[s.id] ?? []).some((v) => usableLa(v.pagina, acciones, modoEntrega, apagados)),
  );
  const cuenta = SECCIONES_DE_CUENTA.filter((c) => cuentaUsable(c, acciones, modoEntrega, apagados));
  const deLasSecciones = new Set<string | null>(SECCIONES_DE_OBRA.map((s) => s.pagina));
  const deLasHerramientas = new Set<string | null>([
    ...Object.values(ESPACIOS).flatMap((e) => e.herramientas.map((h) => h.pagina)),
    ...Object.values(SUBVISTAS).flatMap((vs) => (vs ?? []).map((v) => v.pagina)),
  ]);
  // Contrato de rutas §2.3: la Cuenta (Administración repartida y Acerca) completa las 31 pantallas.
  // La Vista general («inicio», F6 T8) es la entrada de la app: tiene sitio en Inicio y no es una pantalla suelta.
  const conSitio = new Set<string | null>([...deLasSecciones, ...deLasHerramientas, ...SECCIONES_DE_CUENTA.map((c) => c.pagina), "inicio"]);
  const sueltas = PAGINAS.filter((p) => !conSitio.has(p.id) && usable(p, acciones, modoEntrega, apagados));
  const herramientas = PAGINAS.filter(
    (p) => deLasHerramientas.has(p.id) && !deLasSecciones.has(p.id) && usable(p, acciones, modoEntrega, apagados),
  );
  const espacios = ESPACIOS_EN_LA_BARRA.flatMap((id): EspacioOfrecido[] => {
    const primera = primeraUsable(ESPACIOS[id].herramientas, acciones, modoEntrega, apagados);
    return primera === null ? [] : [{ id, titulo: ESPACIOS[id].titulo, ruta: rutaDeHerramienta(id, primera.id) }];
  });
  return { secciones, cuenta, espacios, sueltas, herramientas };
}

// Las secciones de una obra, en el orden del marco.
export function seccionesDeLaObra(oferta: Oferta): readonly SeccionDef[] {
  return SECCIONES_DE_OBRA.filter((s) => oferta.secciones.includes(s));
}

// Nunca se ofrece una obra que al abrirla daría 403: sin permiso para cambiar de carpeta, solo las de la abierta.
// Siempre devuelve una lista nueva (copia o filtro), nunca `obras`: quien la reciba puede ordenarla sin mutar la fuente.
export function obrasAlcanzables(
  obras: readonly ObraDeCarpeta[],
  carpetaActual: string | null,
  puedeCambiarDeCarpeta: boolean,
): ObraDeCarpeta[] {
  return puedeCambiarDeCarpeta ? [...obras] : obras.filter((o) => o.carpeta === carpetaActual);
}

export function useOferta() {
  const aplicacion = useContext(ContextoAplicacion);
  const sesion = aplicacion?.sesion;
  const acciones = sesion?.acciones ?? [];
  return {
    acciones,
    puedeCambiarDeCarpeta: acciones.includes("abrir_carpeta"),
    oferta: ofertaDe(acciones, sesion?.modo_entrega ?? false, aplicacion?.modulosApagados),
  };
}
