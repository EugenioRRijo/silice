import { useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { buscadorDeConsulta } from "../../comun/consulta";
import { buscadorDePartidas, esAborto } from "../../comun/logicaBusqueda";
import type { GrupoDeResultados, PartidaHallada } from "../../comun/logicaBusqueda";
import { AYUDA_DEL_CODIGO, CODIGO_MAL_FORMADO, esCodigoValido } from "./codigo";

// Lo que se elige: el código y, si sale del catálogo, su partida (para llenar la descripción y la unidad vacías).
interface CodigoHallado {
  codigo: string;
  partida: PartidaHallada | null;
}

type Grupos = GrupoDeResultados<CodigoHallado>[];

// Un error que no se puede dejar pasar en silencio: la sesión venció (401) o la búsqueda se canceló.
const debeSubir = (e: unknown) => esAborto(e) || (e instanceof ErrorDeApi && e.estado === 401);

// Las partidas del catálogo (la búsqueda de «Partida» en «Agregar partida») y las partidas viales de Sílice
// (`GET /v1/consulta/partidas_viales`), en dos grupos. Si una de las dos falla, la otra se sigue ofreciendo.
function buscadorDeCodigos() {
  const delCatalogo = buscadorDePartidas();
  const viales = buscadorDeConsulta("partidas_viales");
  return async (q: string, senal: AbortSignal, limite: number): Promise<Grupos> => {
    const [catalogo, vial] = await Promise.allSettled([delCatalogo(q, senal, limite), viales(q, senal, limite)]);
    const fallas = [catalogo, vial].filter((r) => r.status === "rejected").map((r) => r.reason as unknown);
    const grave = fallas.find(debeSubir);
    if (grave !== undefined) throw grave;
    if (fallas.length === 2) throw fallas[0];
    const grupos: Grupos = [];
    if (catalogo.status === "fulfilled") {
      for (const g of catalogo.value) {
        grupos.push({ ...g, opciones: g.opciones.map((o) => ({ ...o, valor: { codigo: o.valor.codigo, partida: o.valor } })) });
      }
    }
    if (vial.status === "fulfilled") {
      for (const g of vial.value) {
        grupos.push({ ...g, opciones: g.opciones.map((o) => ({ ...o, valor: { codigo: o.valor.valor, partida: null } })) });
      }
    }
    return grupos;
  };
}

interface Props {
  texto: string;
  alCambiar: (codigo: string) => void;
  // Se eligió una partida del catálogo: quien compone pone su código, su descripción y su unidad (avisando de lo que reemplaza).
  alElegirDelCatalogo: (partida: PartidaHallada) => void;
  alExpirar: () => void;
}

// Por qué existe (pulido F5, Tarea 1): el «Código» de Componer era texto libre y a quien no es experto le resultaba ambiguo
// (Eugenio pidió el 2026-10-21 un autocompletado guiado, como el de MaPreX). Es el campo con búsqueda de siempre
// (`CampoConBusqueda`): se busca por la descripción o el código y se elige; uno propio se puede usar tal cual solo si
// tiene forma de código. Mientras se escribe es una búsqueda, así que el formato se reclama al dejar el campo.
export function CampoDelCodigo({ texto, alCambiar, alElegirDelCatalogo, alExpirar }: Props): JSX.Element {
  const [buscar] = useState(buscadorDeCodigos);
  const [revisado, setRevisado] = useState(false);
  // El último código confirmado (D16): elegir una opción de la lista llena la descripción, la unidad y las tablas de esa partida,
  // así que es la base del Esc del panel (`data-valor-confirmado`): lo tecleado después vuelve al código elegido y la partida
  // no queda mezclada. Al dejar el campo se olvida: la próxima vez la base es el valor con que recibe el foco.
  const [confirmado, setConfirmado] = useState<string | undefined>(undefined);
  const bienFormado = esCodigoValido(texto);
  const malFormado = revisado && texto.trim() !== "" && !bienFormado;
  return (
    <CampoConBusqueda<CodigoHallado>
      id="componer-codigo"
      etiqueta="Código"
      ayuda={AYUDA_DEL_CODIGO}
      texto={texto}
      alCambiarTexto={(t) => {
        setRevisado(false);
        alCambiar(t);
      }}
      buscar={buscar}
      valorConfirmado={confirmado}
      alElegir={(opcion) => {
        setConfirmado(opcion.valor.codigo);
        // Del catálogo: quien compone pone el código junto con la descripción y la unidad; si no, es un cambio de código más.
        if (opcion.valor.partida !== null) alElegirDelCatalogo(opcion.valor.partida);
        else alCambiar(opcion.valor.codigo);
      }}
      valorPropio={bienFormado ? { rotulo: (t) => `Usar «${t}» como código`, alUsar: (t) => { setConfirmado(t); alCambiar(t); } } : undefined}
      vacio={{
        titulo: "¿No lo encuentra?",
        pasos: "Pruebe con otra palabra de la descripción o escriba un código propio, por ejemplo «E-411».",
      }}
      alSalir={() => {
        setRevisado(true);
        setConfirmado(undefined);
      }}
      alExpirar={alExpirar}
      invalido={malFormado}
      textoInvalido={CODIGO_MAL_FORMADO}
    />
  );
}
