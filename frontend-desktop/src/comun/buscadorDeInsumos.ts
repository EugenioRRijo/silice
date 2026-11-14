// Buscador de la DESCRIPCION EXACTA de un insumo (AC3): lo usan los campos que piden esa descripcion tal cual para
// emparejarla con las lineas de una composicion (los precios de ensayo de Escenarios y la lista del Simulador). Esas
// lineas pueden ser material, equipo o mano de obra, y las dos tablas de consulta las separan (`insumos` y
// `salarios_cct`), asi que se ofrecen las dos, una por grupo.
//
// Se pide siempre con `detalle`: sin el, la sugerencia trae solo el codigo (`valor`) y una etiqueta con codigo y unidad
// que no es la descripcion. No cambia `consulta.ts`: lo compone.
import type { OpcionDeBusqueda } from "./CampoConBusqueda";
import { buscadorDeConsulta } from "./consulta";
import type { SugerenciaDeConsulta } from "./consulta";
import type { GrupoDeResultados } from "./logicaBusqueda";

export function buscadorDeInsumosYOficios() {
  const insumos = buscadorDeConsulta("insumos", { detalle: true });
  const oficios = buscadorDeConsulta("salarios_cct", { detalle: true });
  return async (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<SugerenciaDeConsulta>[]> => {
    // Un fallo de cualquiera de las dos (un 401, por ejemplo) es el fallo de la busqueda: no se oculta media lista.
    const [deInsumos, deOficios] = await Promise.all([insumos(q, senal, limite), oficios(q, senal, limite)]);
    return [...deInsumos, ...deOficios];
  };
}

// La descripcion exacta del catalogo, o null si la sugerencia no la trae (no se inventa a partir de la etiqueta).
export function descripcionDeInsumo(opcion: OpcionDeBusqueda<SugerenciaDeConsulta>): string | null {
  const descripcion = opcion.valor.descripcion?.trim();
  return descripcion ? descripcion : null;
}
