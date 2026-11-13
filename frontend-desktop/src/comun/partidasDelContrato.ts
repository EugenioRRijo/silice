// Las partidas de una version del contrato para los campos «Partida» con autocompletado (AC2, pedido de Eugenio del
// 2026-10-21). La lista llega entera de la API (GET /v1/control/partidas o /v1/reajuste/partidas: son las de UNA version,
// no el catalogo) y se filtra aqui, en el navegador, sin una peticion por tecla (modo local del diseno §5.4). La pagina
// no calcula nada: solo busca texto.
import type { Carga } from "./useCarga";
import { buscadorLocal } from "./normalizar";
import { unidadEscrita } from "../comun/unidades";

export interface PartidaDelContrato {
  codigo: string;
  descripcion: string;
  unidad: string;
  // Control (ola 2, 2026-11-13): la lista trae cada renglón del presupuesto, con su número y cuántos renglones tiene su
  // código; Reajuste no los trae (una por código).
  renglon?: number;
  renglones?: number;
}

// true si el código de `p` está en más de un renglón del presupuesto.
export function codigoRepetido(p: PartidaDelContrato): boolean {
  return (p.renglones ?? 1) > 1;
}

export interface PartidasDelContrato {
  version: string;
  aviso: string;
  partidas: PartidaDelContrato[];
  // La API recorto la lista a su tope: que una partida no este en ella no dice que no este en el contrato.
  truncada?: boolean;
}

export const AVISO_LISTA_RECORTADA =
  "La lista muestra solo parte de las partidas del contrato: si la suya no aparece, escriba su código.";

// true si la lista que llego esta recortada (entonces no se juzga con ella: decide el servidor).
export function listaRecortada(carga: Carga<PartidasDelContrato>): boolean {
  return carga.estado === "listo" && carga.datos.truncada === true;
}

export const ROTULO_DEL_CONTRATO = "Partidas del contrato";

// La lista que ofrece el campo, o null si no hay con que guiar (no cargo, fallo o vino vacia): entonces el campo sigue
// siendo de texto libre y la API dice lo que falte al guardar.
export function partidasOfrecidas(carga: Carga<PartidasDelContrato>): PartidaDelContrato[] | null {
  return carga.estado === "listo" && Array.isArray(carga.datos.partidas) && carga.datos.partidas.length > 0 ? carga.datos.partidas : null;
}

// La funcion `buscar` de CampoConBusqueda sobre una lista ya cargada: todas las palabras escritas, sin tildes ni
// mayusculas, en el codigo o en la descripcion; el codigo que empieza por lo escrito va primero. Sin texto, todas.
export function buscadorDePartidasDelContrato(partidas: PartidaDelContrato[]) {
  return buscadorLocal(partidas, {
    rotulo: ROTULO_DEL_CONTRATO,
    textoDe: (p) => `${p.codigo} ${p.descripcion}`,
    codigoDe: (p) => p.codigo,
    opcionDe: (p) => ({
      clave: p.renglon === undefined ? `partida:${p.codigo}` : `partida:${p.codigo}:${p.renglon}`,
      principal: p.descripcion,
      secundaria: [
        p.codigo,
        unidadEscrita(p.unidad),
        ...(codigoRepetido(p) && p.renglon !== undefined ? [`renglón ${p.renglon} del presupuesto`] : []),
      ],
      valor: p,
    }),
  });
}

// La partida del contrato que el texto nombra por su codigo (sin importar mayusculas ni espacios de los bordes), o null.
export function partidaDelContrato(partidas: PartidaDelContrato[], texto: string): PartidaDelContrato | null {
  const codigo = texto.trim().toLowerCase();
  if (codigo === "") return null;
  return partidas.find((p) => p.codigo.toLowerCase() === codigo) ?? null;
}
