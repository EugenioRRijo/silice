// Las series de indices para el campo «Serie» de los componentes (AC2). La lista llega entera de GET /v1/reajuste/series
// (solo la definicion de cada serie, ningun valor) y se filtra aqui, sin una peticion por tecla. La pagina no calcula nada.
import type { Carga } from "../inicio/useCarga";
import type { GrupoDeResultados } from "../../comun/logicaBusqueda";

export interface SerieDeIndice {
  clave: string;
  nombre: string;
  organismo: string;
  unidad: string;
  periodicidad: string;
}

export const ROTULO_DE_SERIES = "Series de índices importadas";

const plano = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

// La lista que ofrece el campo, o null si no hay con que guiar (no cargo, fallo o no hay series importadas): entonces el
// campo sigue siendo de texto libre y el calculo dice «las series X no estan importadas».
export function seriesOfrecidas(carga: Carga<SerieDeIndice[]>): SerieDeIndice[] | null {
  return carga.estado === "listo" && Array.isArray(carga.datos) && carga.datos.length > 0 ? carga.datos : null;
}

// La funcion `buscar` de CampoConBusqueda sobre las series ya cargadas: todas las palabras escritas, sin tildes ni
// mayusculas, en la clave, el nombre o el organismo; la clave que empieza por lo escrito va primero. Sin texto, todas.
export function buscadorDeSeries(series: SerieDeIndice[]) {
  return async (q: string, _senal: AbortSignal, limite: number): Promise<GrupoDeResultados<SerieDeIndice>[]> => {
    const palabras = plano(q).split(/\s+/).filter(Boolean);
    const halladas = series.filter((s) => {
      const campo = plano(`${s.clave} ${s.nombre} ${s.organismo}`);
      return palabras.every((palabra) => campo.includes(palabra));
    });
    if (halladas.length === 0) return [];
    const inicio = plano(q).trim();
    const empiezan = inicio === "" ? [] : halladas.filter((s) => plano(s.clave).startsWith(inicio));
    const ordenadas = [...empiezan, ...halladas.filter((s) => !empiezan.includes(s))];
    return [
      {
        rotulo: ROTULO_DE_SERIES,
        hayMas: ordenadas.length > limite,
        opciones: ordenadas.slice(0, limite).map((s) => ({
          clave: `serie:${s.clave}`,
          principal: s.nombre,
          secundaria: [s.clave, s.organismo, s.unidad, s.periodicidad],
          valor: s,
        })),
      },
    ];
  };
}
