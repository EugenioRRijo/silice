// Adaptador de GET /v1/consulta/{tabla} (plan vial, Tarea 20) para CampoConBusqueda: el autocompletado con las tablas
// venezolanas (partidas viales, insumos del catalogo, tasa del BCV, salarios del CCT). No hay un componente nuevo: el
// campo con busqueda (combobox ARIA, flechas, Enter, Esc y region viva) ya existe y es el que se reutiliza.
import { pedir } from "../api/cliente";
import type { GrupoDeResultados } from "./logicaBusqueda";

export type TablaDeConsulta = "partidas_viales" | "insumos" | "tasa_bcv" | "salarios_cct";

export interface SugerenciaDeConsulta {
  valor: string; // lo que se guarda al elegir
  etiqueta: string; // lo que se lee
  fuente: string; // de donde sale
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

export function rutaDeConsulta(tabla: TablaDeConsulta, q: string, limite: number): string {
  return `/v1/consulta/${tabla}?${new URLSearchParams({ q, limite: String(limite) }).toString()}`;
}

// Un grupo con una opcion por sugerencia: la etiqueta arriba; abajo el valor (el codigo, en Plex Mono) y la fuente.
export function gruposDeConsulta(respuesta: SugerenciasHalladas): GrupoDeResultados<SugerenciaDeConsulta>[] {
  const tabla = respuesta.tabla as TablaDeConsulta;
  return [
    {
      rotulo: ROTULO[tabla] ?? respuesta.tabla,
      hayMas: respuesta.hay_mas,
      opciones: respuesta.resultados.map((s) => ({
        clave: `${respuesta.tabla}:${s.valor}`,
        principal: s.etiqueta,
        secundaria: [s.valor, s.fuente],
        valor: s,
      })),
    },
  ];
}

// La funcion `buscar` de CampoConBusqueda para una tabla de consulta.
export function buscadorDeConsulta(tabla: TablaDeConsulta) {
  return (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<SugerenciaDeConsulta>[]> =>
    pedir<SugerenciasHalladas>(rutaDeConsulta(tabla, q, limite), { senal }).then(gruposDeConsulta);
}
