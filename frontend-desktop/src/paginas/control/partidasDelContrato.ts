// Las partidas de una version del contrato para los campos «Partida» con autocompletado (AC2, pedido de Eugenio del
// 2026-10-21). La lista llega entera de la API (GET /v1/control/partidas o /v1/reajuste/partidas: son las de UNA version,
// no el catalogo) y se filtra aqui, en el navegador, sin una peticion por tecla (modo local del diseno §5.4). La pagina
// no calcula nada: solo busca texto.
import type { Carga } from "../inicio/useCarga";
import type { GrupoDeResultados } from "../../comun/logicaBusqueda";

export interface PartidaDelContrato {
  codigo: string;
  descripcion: string;
  unidad: string;
}

export interface PartidasDelContrato {
  version: string;
  aviso: string;
  partidas: PartidaDelContrato[];
}

export const ROTULO_DEL_CONTRATO = "Partidas del contrato";

const plano = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

// La lista que ofrece el campo, o null si no hay con que guiar (no cargo, fallo o vino vacia): entonces el campo sigue
// siendo de texto libre y la API dice lo que falte al guardar.
export function partidasOfrecidas(carga: Carga<PartidasDelContrato>): PartidaDelContrato[] | null {
  return carga.estado === "listo" && Array.isArray(carga.datos.partidas) && carga.datos.partidas.length > 0 ? carga.datos.partidas : null;
}

// La funcion `buscar` de CampoConBusqueda sobre una lista ya cargada: todas las palabras escritas, sin tildes ni
// mayusculas, en el codigo o en la descripcion; el codigo que empieza por lo escrito va primero. Sin texto, todas.
export function buscadorDePartidasDelContrato(partidas: PartidaDelContrato[]) {
  return async (q: string, _senal: AbortSignal, limite: number): Promise<GrupoDeResultados<PartidaDelContrato>[]> => {
    const palabras = plano(q).split(/\s+/).filter(Boolean);
    const halladas = partidas.filter((p) => {
      const campo = plano(`${p.codigo} ${p.descripcion}`);
      return palabras.every((palabra) => campo.includes(palabra));
    });
    if (halladas.length === 0) return [];
    const inicio = plano(q).trim();
    const empiezan = inicio === "" ? [] : halladas.filter((p) => plano(p.codigo).startsWith(inicio));
    const ordenadas = [...empiezan, ...halladas.filter((p) => !empiezan.includes(p))];
    return [
      {
        rotulo: ROTULO_DEL_CONTRATO,
        hayMas: ordenadas.length > limite,
        opciones: ordenadas.slice(0, limite).map((p) => ({
          clave: `partida:${p.codigo}`,
          principal: p.descripcion,
          secundaria: [p.codigo, p.unidad],
          valor: p,
        })),
      },
    ];
  };
}

// La partida del contrato que el texto nombra por su codigo (sin importar mayusculas ni espacios de los bordes), o null.
export function partidaDelContrato(partidas: PartidaDelContrato[], texto: string): PartidaDelContrato | null {
  const codigo = texto.trim().toLowerCase();
  if (codigo === "") return null;
  return partidas.find((p) => p.codigo.toLowerCase() === codigo) ?? null;
}
