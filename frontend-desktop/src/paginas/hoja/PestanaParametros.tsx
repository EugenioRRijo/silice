import { Cifra } from "./Cifra";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { VistaParametros } from "./logica";

interface Props {
  id: string;
  moneda: string;
  alAusente: () => void;
}

function ContenidoParametros({ vista, moneda }: { vista: VistaParametros; moneda: string }) {
  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        Los parámetros de costo del borrador. Aquí solo se leen; editarlos llega en una entrega posterior.
      </p>
      <dl className="silice-hoja__metricas">
        {vista.campos.map((c) => (
          <div key={c.clave}>
            <dt className="cds--type-helper-text-01">{c.rotulo}</dt>
            <dd className="cds--type-heading-compact-02">
              <Cifra monto={{ texto: c.valor, exacto: c.valor }} />
            </dd>
          </div>
        ))}
      </dl>
      {vista.moneda_proyecto !== null && (
        <p className="cds--type-body-compact-01">Moneda del proyecto: {vista.moneda_proyecto}</p>
      )}
      <p className="silice-hoja__total cds--type-heading-03">
        Total del presupuesto <Cifra monto={vista.total} unidad={moneda} />
      </p>
    </div>
  );
}

// Pestaña «Parámetros» en lectura (editar los cuatro y convertir la moneda llegan en las rebanadas 3c y 3d).
export function PestanaParametros({ id, moneda, alAusente }: Props) {
  return (
    <VistaCarga<VistaParametros> ruta={rutaDeVista(id, "parametros")} etiqueta="Parámetros" alAusente={alAusente}>
      {(vista) => <ContenidoParametros vista={vista} moneda={moneda} />}
    </VistaCarga>
  );
}
