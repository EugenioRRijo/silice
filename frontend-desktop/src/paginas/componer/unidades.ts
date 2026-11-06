// AC4 (pedido de Eugenio del 2026-10-21): la unidad se elige de las que ya usa el catalogo de la carpeta, o se escribe una
// propia. `GET /v1/consulta/unidades` las da agrupadas con la tabla de alias del nucleo (`m3`, `m³` y `M3` son `m3`), con
// sus grafias y en orden de uso. Es una lista corta: se pide una vez por campo y se filtra en el navegador, asi que basta
// una letra («m») para ver sugerencias. Lo usan Componer (cabecera y materiales) y la Hoja (insumo nuevo).
import { pedir } from "../../api/cliente";
import type { GrupoDeResultados } from "../../comun/logicaBusqueda";

export const RUTA_DE_UNIDADES = "/v1/consulta/unidades";
const ROTULO = "Unidades del catálogo";

export interface UnidadUsada {
  unidad: string; // la forma canonica: lo que se guarda al elegir
  usos: number; // cuantas partidas e insumos del catalogo la usan
  grafias: string[]; // como esta escrita en el catalogo
}

interface UnidadesRespuesta {
  unidades: UnidadUsada[];
}

const comparable = (texto: string) =>
  texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();

// 0: igual a lo escrito; 1: empieza asi; 2: lo contiene; null: no coincide. Cuenta la unidad y cualquiera de sus grafias.
function cercania(u: UnidadUsada, q: string): number | null {
  const formas = [u.unidad, ...u.grafias].map(comparable);
  if (formas.includes(q)) return 0;
  if (formas.some((f) => f.startsWith(q))) return 1;
  if (formas.some((f) => f.includes(q))) return 2;
  return null;
}

// Las unidades que coinciden con lo escrito: la exacta, luego las que empiezan asi y luego las que lo contienen; dentro de
// cada grupo, en el orden del servidor (las mas usadas primero).
export function filtrarUnidades(unidades: readonly UnidadUsada[], q: string): UnidadUsada[] {
  const buscado = comparable(q);
  return unidades
    .map((u, orden) => ({ u, orden, cerca: cercania(u, buscado) }))
    .filter((c): c is { u: UnidadUsada; orden: number; cerca: number } => c.cerca !== null)
    .sort((a, b) => a.cerca - b.cerca || a.orden - b.orden)
    .map((c) => c.u);
}

const vecesEnElCatalogo = (usos: number) => `${usos} ${usos === 1 ? "vez" : "veces"} en el catálogo`;

// Un grupo con la unidad arriba y, abajo, sus grafias y cuantas veces la usa el catalogo. Sin unidades, ningun grupo: el
// campo dice que no hay y ofrece usar lo escrito tal cual.
export function gruposDeUnidades(halladas: readonly UnidadUsada[], limite: number): GrupoDeResultados<UnidadUsada>[] {
  if (halladas.length === 0) return [];
  return [
    {
      rotulo: ROTULO,
      hayMas: halladas.length > limite,
      opciones: halladas.slice(0, limite).map((u) => ({
        clave: `unidad:${u.unidad}`,
        principal: u.unidad,
        secundaria: [u.grafias.join(", "), vecesEnElCatalogo(u.usos)],
        valor: u,
      })),
    },
  ];
}

// La funcion `buscar` de CampoConBusqueda: pide la lista la primera vez y la reutiliza. Si no llega, esa busqueda falla
// (el campo lo dice) y la siguiente la vuelve a pedir. La respuesta de una busqueda vieja la descarta el propio campo.
export function buscadorDeUnidades() {
  let lista: Promise<UnidadUsada[]> | null = null;
  return async (q: string, _senal: AbortSignal, limite: number): Promise<GrupoDeResultados<UnidadUsada>[]> => {
    lista ??= pedir<UnidadesRespuesta | undefined>(RUTA_DE_UNIDADES).then((r) => r?.unidades ?? []);
    const pedida = lista;
    try {
      return gruposDeUnidades(filtrarUnidades(await pedida, q), limite);
    } catch (error) {
      if (lista === pedida) lista = null;
      throw error;
    }
  };
}
