import type { JSX } from "react";
import type { CalculoDeCosto } from "../../api/produccionPlanta";
import { fechaEsVe, mostrarMonto, nombreDelMes, rotulo, CENTROS } from "./logica";
import { constanciasDe } from "./logicaMezcla";

interface Props {
  calculo: CalculoDeCosto;
}

// Lo que el servidor dejó anotado en la instantánea (Tarea 4b) y que cambia cómo se lee el cálculo: costos que llegaron
// del mes anterior, costos que no tuvieron a quién repartirse y pasan al siguiente, y agregados que no se produjeron
// este mes y toman el costo de un cálculo anterior. Solo se escribe lo guardado; un cálculo viejo no trae nada de esto.
export function ConstanciasDelCalculo({ calculo }: Props): JSX.Element | null {
  const { vieneDelMesAnterior, pasaAlMesSiguiente, deOtroCalculo } = constanciasDe(calculo.instantanea);
  if (vieneDelMesAnterior.length + pasaAlMesSiguiente.length + deOtroCalculo.length === 0) return null;
  const moneda = calculo.moneda;
  return (
    <>
      {vieneDelMesAnterior.length > 0 && (
        <section aria-label="Viene del mes anterior" className="planta-constancia">
          <h3 className="cds--type-heading-compact-01">Viene del mes anterior</h3>
          <ul className="cds--type-body-compact-01">
            {vieneDelMesAnterior.map((d) => (
              <li key={d.centro}>
                {rotulo(CENTROS, d.centro)}: {mostrarMonto(d.total)} {moneda} (cálculo n.º {d.calculo} de {nombreDelMes(d.periodo)}
                {d.tasa ? `; convertido con la tasa del cierre de ${nombreDelMes(d.periodo)}: ${mostrarMonto(d.tasa.valor)} del ${fechaEsVe(d.tasa.fecha)}` : ""})
              </li>
            ))}
          </ul>
        </section>
      )}
      {pasaAlMesSiguiente.length > 0 && (
        <section aria-label="Pasa al mes siguiente" className="planta-constancia">
          <h3 className="cds--type-heading-compact-01">Pasa al mes siguiente</h3>
          <p className="planta-nota cds--type-body-compact-01">Costos que este mes no tuvieron a quién repartirse.</p>
          <ul className="cds--type-body-compact-01">
            {pasaAlMesSiguiente.map((d) => (
              <li key={d.centro}>
                {rotulo(CENTROS, d.centro)}: {mostrarMonto(d.total)} {moneda}
              </li>
            ))}
          </ul>
        </section>
      )}
      {deOtroCalculo.length > 0 && (
        <section aria-label="Costos tomados de otro cálculo" className="planta-constancia">
          <h3 className="cds--type-heading-compact-01">Costos tomados de otro cálculo</h3>
          <p className="planta-nota cds--type-body-compact-01">Agregados que no se produjeron este mes.</p>
          <ul className="cds--type-body-compact-01">
            {deOtroCalculo.map((d) => (
              <li key={d.codigo}>
                {d.codigo}: {mostrarMonto(d.costo)} {moneda} por tonelada, del cálculo n.º {d.calculo} de {nombreDelMes(d.periodo)}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
