import type { JSX } from "react";
import type { CantidadDeTramo, TramoGuardado } from "../../api/vial";
import { unidadEscrita } from "../../comun/unidades";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";


const COLUMNAS: ColumnaDensa[] = [
  { clave: "descripcion", titulo: "Partida", ordenable: false },
  { clave: "unidad", titulo: "Unidad", ordenable: false, presentar: unidadEscrita },
  { clave: "cantidad", titulo: "Cantidad", numerica: true, ordenable: false, presentar: formatoEsVe },
];

// «De 0 a 1,2 km · ancho 7,3 m · planta a 15 km»: lo que se declaró del tramo, con coma decimal.
export function resumenDelTramo(t: TramoGuardado): string {
  const partes = [`De ${formatoEsVe(t.progresiva_ini_km)} a ${formatoEsVe(t.progresiva_fin_km)} km`, `ancho ${formatoEsVe(t.ancho_m)} m`];
  if (t.distancia_planta_km !== null) partes.push(`planta a ${formatoEsVe(t.distancia_planta_km)} km`);
  return partes.join(" · ");
}

interface Props {
  tramo: TramoGuardado;
  cantidades: readonly CantidadDeTramo[];
}

// Un tramo con sus cantidades de obra (m2, m3, l, t, t·km y m). La pantalla no calcula nada: las manda el servidor y aquí
// solo se les da formato.
export function TramoConCantidades({ tramo, cantidades }: Props): JSX.Element {
  const filas = cantidades
    .filter((c) => c.tramo === tramo.id)
    .map((c, i) => ({ id: `${c.origen_id}-${i}`, descripcion: c.descripcion, unidad: c.unidad, cantidad: c.cantidad }));
  return (
    <section className="vial-tramo" aria-label={`Tramo ${tramo.id}`}>
      <h2 className="cds--type-heading-compact-02">{`Tramo ${tramo.id}`}</h2>
      <p className="vial-nota cds--type-body-compact-01">{resumenDelTramo(tramo)}</p>
      <TablaDensa etiqueta={`Cantidades del tramo ${tramo.id}`} columnas={COLUMNAS} filas={filas} />
    </section>
  );
}
