import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { Monto } from "./logica";

// Una cifra tal como la manda la API: el texto a dos decimales en es-VE a la vista y el valor exacto (también en es-VE,
// con todos sus dígitos) en el `title` y en un texto accesible. La interfaz no calcula ni redondea.
export function Cifra({ monto, unidad }: { monto: Monto; unidad?: string }) {
  return (
    <span title={formatoEsVe(monto.exacto)}>
      {formatoEsVe(monto.texto)}
      {unidad ? ` ${unidad}` : ""}
      <span className="cds--visually-hidden"> Valor exacto {formatoEsVe(monto.exacto)}</span>
    </span>
  );
}
