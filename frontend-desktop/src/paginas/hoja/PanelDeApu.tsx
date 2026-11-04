import type { JSX } from "react";
import { PanelLateral } from "../../comun/PanelLateral";
import { unidadEscrita } from "../../comun/unidades";
import { EditorDeApu } from "./EditorDeApu";
import type { Resumen } from "./logica";
import { useHojaDeLaObra } from "./ProveedorDeLaHoja";

// La fila de «Partidas» cuyo APU se abrió: su código y lo que el panel dice en su título.
export interface PartidaDelPanel {
  partida: string;
  descripcion: string;
  unidad: string;
}

// Por qué existe (Tarea 7 del plan F4; fusión del inventario de «Buscar partida» con la tabla): el código de cada fila de
// «Partidas» abre el APU de esa partida en el panel lateral (`comun/PanelLateral`), junto a la tabla y sin cambiar de
// pestaña. El editor es el mismo de la pestaña APU (`EditorDeApu`). Lo usa solo `PestanaPresupuesto`.
export function PanelDeApu({
  abierta,
  alCerrar,
  alAceptar,
}: {
  abierta: PartidaDelPanel | null;
  alCerrar: () => void;
  alAceptar: (r: Resumen) => void;
}): JSX.Element | null {
  const { estado, refrescar } = useHojaDeLaObra();
  const borrador = estado.estado === "listo" ? estado.borrador : null;
  const titulo = abierta === null ? "" : `APU de ${abierta.partida} · ${abierta.descripcion} · ${unidadEscrita(abierta.unidad)}`;
  return (
    <PanelLateral titulo={titulo} abierto={abierta !== null && borrador !== null} alCerrar={alCerrar} ancho="ancho">
      {abierta !== null && borrador !== null && (
        // Otra partida es otro APU: se vuelve a montar y lee el suyo. Lo escrito en el anterior que esperaba la pausa sale al
        // desmontarse, como al cambiar de pestaña (`useEdicionDeSeccion`); cerrar el panel también lo manda.
        <EditorDeApu key={abierta.partida} borrador={borrador} partida={abierta.partida} alAceptar={alAceptar} alAusente={refrescar} />
      )}
    </PanelLateral>
  );
}
