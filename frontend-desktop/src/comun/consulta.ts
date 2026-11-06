// Adaptador de GET /v1/consulta/{tabla} (plan vial, Tarea 20) para CampoConBusqueda: el autocompletado con las tablas
// venezolanas (partidas viales, insumos del catalogo, tasa del BCV, salarios del CCT). No hay un componente nuevo: el
// campo con busqueda (combobox ARIA, flechas, Enter, Esc y region viva) ya existe y es el que se reutiliza.
import { pedir } from "../api/cliente";
import { fechaEsVe, formatoEsVe } from "../indicadores/formatoEsVe";
import { materialesDeArenera } from "../api/produccionPlanta";
import type { GrupoDeResultados } from "./logicaBusqueda";

export type TablaDeConsulta = "partidas_viales" | "insumos" | "tasa_bcv" | "salarios_cct";

export interface SugerenciaDeConsulta {
  valor: string; // lo que se guarda al elegir
  etiqueta: string; // lo que se lee
  fuente: string; // de donde sale
  // Solo con `detalle` o `paraArmarAl` (insumos y salarios, AC1b); lo que no viene, no llega.
  descripcion?: string | null;
  unidad?: string | null;
  // El precio de la lista para armar a esa fecha, decimal con punto, en `moneda`; rige desde `fecha_precio`. Si esa lista
  // esta en otra moneda que la de la carpeta no llega el precio y si `aviso_precio`.
  precio?: string | null;
  moneda?: string | null;
  fecha_precio?: string | null;
  aviso_precio?: string | null;
  // «material», «equipo» o «mano de obra» (con `detalle`): en la lista de Equipos el catálogo mezcla los dos tipos.
  tipo?: string | null;
}

// Lo que se le pide de mas a la consulta (AC1b): la descripcion y la unidad de cada insumo y, con una fecha ISO, el precio
// de la lista para armar a esa fecha. Sin opciones la ruta es la de siempre.
export interface OpcionesDeConsulta {
  detalle?: boolean;
  paraArmarAl?: string;
  // Solo de presentacion (no viaja en la ruta): la linea de cada resultado dice el precio, la moneda y la fecha de su lista, o
  // que no hay precio en la lista para armar (dictamen del autocompletado, MAYOR). Se pone con `paraArmarAl`; sin ella la
  // linea es la de siempre, [valor, fuente].
  mostrarPrecio?: boolean;
}

export interface SugerenciasHalladas {
  tabla: string;
  resultados: SugerenciaDeConsulta[];
  hay_mas: boolean;
}

const ROTULO: Record<TablaDeConsulta, string> = {
  partidas_viales: "Partidas viales",
  insumos: "Insumos del catálogo",
  tasa_bcv: "Tasas del BCV",
  salarios_cct: "Oficios de mano de obra del catálogo",
};

export function rutaDeConsulta(tabla: TablaDeConsulta, q: string, limite: number, opciones: OpcionesDeConsulta = {}): string {
  const params = new URLSearchParams({ q, limite: String(limite) });
  if (opciones.detalle) params.set("detalle", "true");
  if (opciones.paraArmarAl) params.set("para_armar_al", opciones.paraArmarAl);
  return `/v1/consulta/${tabla}?${params.toString()}`;
}

const SIN_PRECIO_EN_LA_LISTA = "sin precio en la lista para armar";

// Lo que se lee debajo de un insumo cuando se ofrece con su precio: la unidad (si la trae), el precio con su moneda y la fecha
// de su lista. El precio llega como decimal con punto y solo se reescribe con la coma; en otra moneda que la de la carpeta el
// servidor no lo manda y si su aviso, que es lo que se lee. Sin nada de eso, «sin precio en la lista para armar».
function lineaConPrecio(s: SugerenciaDeConsulta): string[] {
  const partes = [s.valor];
  if (s.unidad) partes.push(s.unidad);
  if (s.precio && s.moneda) {
    partes.push(`${formatoEsVe(s.precio)} ${s.moneda}`);
    if (s.fecha_precio) partes.push(`lista del ${fechaEsVe(s.fecha_precio)}`);
  } else {
    partes.push(s.aviso_precio || SIN_PRECIO_EN_LA_LISTA);
  }
  if (s.tipo) partes.push(s.tipo);
  return partes;
}

// Un grupo con una opcion por sugerencia: la etiqueta arriba; abajo el valor (el codigo, en Plex Mono) y la fuente (o, con
// `mostrarPrecio`, la unidad y el precio con su fecha).
export function gruposDeConsulta(
  respuesta: SugerenciasHalladas,
  opciones: Pick<OpcionesDeConsulta, "mostrarPrecio"> = {},
): GrupoDeResultados<SugerenciaDeConsulta>[] {
  const tabla = respuesta.tabla as TablaDeConsulta;
  return [
    {
      rotulo: ROTULO[tabla] ?? respuesta.tabla,
      hayMas: respuesta.hay_mas,
      opciones: respuesta.resultados.map((s) => ({
        clave: `${respuesta.tabla}:${s.valor}`,
        principal: s.etiqueta,
        secundaria: opciones.mostrarPrecio ? lineaConPrecio(s) : [s.valor, s.fuente],
        valor: s,
      })),
    },
  ];
}

// La funcion `buscar` de CampoConBusqueda para una tabla de consulta.
export function buscadorDeConsulta(tabla: TablaDeConsulta, opciones: OpcionesDeConsulta = {}) {
  return (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<SugerenciaDeConsulta>[]> =>
    pedir<SugerenciasHalladas>(rutaDeConsulta(tabla, q, limite, opciones), { senal }).then((r) => gruposDeConsulta(r, opciones));
}

// Tablas que no son del servidor de consulta: los materiales de producción de la arenera (mezclas y agregados), que
// viven en la base de la instalación y no en el catálogo de la carpeta. `GET /v1/produccion/materiales` ya los lista.
export type TablaDeBusqueda = TablaDeConsulta | "materiales_produccion" | "componentes_de_receta";

const ROTULO_MATERIALES = "Materiales de la arenera";
const sinTildes = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

// Los materiales activos de la arenera que contienen todas las palabras escritas, en su código o su nombre.
export function buscadorDeMateriales() {
  return async (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<SugerenciaDeConsulta>[]> => {
    const palabras = sinTildes(q).split(/\s+/).filter(Boolean);
    const halladas = (await materialesDeArenera(senal)).filter(
      (m) => m.activo && palabras.every((p) => sinTildes(`${m.codigo} ${m.nombre}`).includes(p)),
    );
    if (halladas.length === 0) return [];
    return [
      {
        rotulo: ROTULO_MATERIALES,
        hayMas: halladas.length > limite,
        opciones: halladas.slice(0, limite).map((m) => ({
          clave: `materiales_produccion:${m.codigo}`,
          principal: m.nombre,
          secundaria: [m.codigo, ROTULO_MATERIALES],
          valor: { valor: m.codigo, etiqueta: m.nombre, fuente: ROTULO_MATERIALES },
        })),
      },
    ];
  };
}

// Un componente de receta puede ser un material propio de la arenera o un insumo del catálogo: se ofrecen los dos grupos.
export function buscadorDeComponentes() {
  const materiales = buscadorDeMateriales();
  const insumos = buscadorDeConsulta("insumos");
  return async (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<SugerenciaDeConsulta>[]> => {
    // Si los materiales fallan (p. ej. el módulo de producción apagado), el catálogo sigue ofreciéndose.
    const [propios, delCatalogo] = await Promise.all([
      materiales(q, senal, limite).catch((error: unknown) => {
        if (senal.aborted) throw error;
        return [];
      }),
      insumos(q, senal, limite),
    ]);
    return [...propios, ...delCatalogo];
  };
}
