import { periodoLegible } from "../../comun/CurvaPlanAvance";
import { Cifra } from "./Cifra";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { VistaEquilibrio } from "./logica";

interface Props {
  id: string;
  moneda: string;
  alAusente: () => void;
}

function Metrica({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="cds--type-helper-text-01">{rotulo}</dt>
      <dd className="cds--type-heading-compact-02">{children}</dd>
    </div>
  );
}

function ContenidoEquilibrio({ vista, moneda }: { vista: VistaEquilibrio; moneda: string }) {
  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        No se edita: se mueve con las cantidades, los precios, los parámetros y el plan.
      </p>
      <dl className="silice-hoja__metricas">
        <Metrica rotulo="Ventas (contrato)">
          <Cifra monto={vista.venta} unidad={moneda} />
        </Metrica>
        <Metrica rotulo="Costo variable">
          <Cifra monto={vista.costo_variable} unidad={moneda} />
        </Metrica>
        <Metrica rotulo="Costo fijo">
          <Cifra monto={vista.costo_fijo} unidad={moneda} />
        </Metrica>
        <Metrica rotulo="Utilidad">
          <Cifra monto={vista.utilidad} unidad={moneda} />
        </Metrica>
        {vista.punto !== null && (
          <Metrica rotulo="Punto de equilibrio">
            <Cifra monto={vista.punto} unidad={moneda} />
          </Metrica>
        )}
        {vista.punto !== null && vista.porcentaje !== null && (
          <Metrica rotulo="Como % de las ventas">
            <Cifra monto={vista.porcentaje} unidad="%" />
          </Metrica>
        )}
        {vista.punto !== null && vista.periodo !== null && (
          <Metrica rotulo="Se alcanza en">{periodoLegible(vista.periodo)}</Metrica>
        )}
      </dl>
      <p className="cds--type-body-compact-01" role="status">
        {vista.mensaje}
      </p>
    </div>
  );
}

// Pestaña «Punto de equilibrio»: solo lectura (se mueve con las cantidades, los precios, los parámetros y el plan).
export function PestanaEquilibrio({ id, moneda, alAusente }: Props) {
  return (
    <VistaCarga<VistaEquilibrio> ruta={rutaDeVista(id, "equilibrio")} etiqueta="Punto de equilibrio" alAusente={alAusente}>
      {(vista) => <ContenidoEquilibrio vista={vista} moneda={moneda} />}
    </VistaCarga>
  );
}
