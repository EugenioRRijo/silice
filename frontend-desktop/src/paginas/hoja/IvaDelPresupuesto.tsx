import type { JSX } from "react";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { porcentajeDeAlicuota } from "../control/logica";
import type { Impuestos } from "../control/logica";
import { TEXTOS_DEL_IVA as T } from "./textos";

// Tarea 5b del plan F4 (plan vial, Tarea 18): el subtotal, el IVA y el total con IVA debajo de «Total del presupuesto». Las
// tres cifras las calcula el servidor (`aplicacion/impuestos.con_iva`); aquí solo se leen, con coma decimal y la moneda de
// la obra. Es lectura: lo ve igual quien arma y quien revisa. La alícuota y su fuente («a cotejar con la Gaceta vigente»)
// van en el «¿Qué es esto?» de la pestaña (`parrafosDeAyudaDelIva`), no en un segundo botón con el mismo nombre.
export function parrafosDeAyudaDelIva(impuestos: Impuestos): string[] {
  return [T.explicacion, T.fuente(porcentajeDeAlicuota(impuestos.alicuota), impuestos.fuente_alicuota)];
}

export function IvaDelPresupuesto({ impuestos, moneda }: { impuestos: Impuestos; moneda: string }): JSX.Element {
  const porcentaje = porcentajeDeAlicuota(impuestos.alicuota);
  const cifra = (valor: string) => `${formatoEsVe(valor)} ${moneda}`;
  return (
    <section className="silice-hoja__iva" aria-label={T.region}>
      <p className="silice-hoja__iva-linea">
        {T.subtotal} <span>{cifra(impuestos.subtotal)}</span>
      </p>
      <p className="silice-hoja__iva-linea">
        {T.iva(porcentaje)} <span>{cifra(impuestos.iva)}</span>
      </p>
      <p className="silice-hoja__iva-linea silice-hoja__iva-total cds--type-heading-03">
        {T.totalConIva} <span>{cifra(impuestos.total)}</span>
      </p>
    </section>
  );
}
