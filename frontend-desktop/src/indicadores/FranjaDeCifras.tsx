export interface CifraDeFranja {
  id: string;
  titulo: string;
  // La cifra ya formateada (es-VE): la franja no calcula ni formatea.
  valor: string;
}

interface Props {
  etiqueta: string;
  cifras: readonly CifraDeFranja[];
}

// La misma franja Fiori de `FranjaIndicadores` (divisores de 1 px, título pequeño y cifra grande), para cifras que no tienen
// meta ni variación: la cartera por moneda (total vigente, obras, en ejecución). `IndicadorFiori` exige una meta y su
// diferencia, y inventarlas para llenar el molde sería mostrar una cifra que el servidor no dio. Reusa sus clases: no hay
// estilos aparte.
export function FranjaDeCifras({ etiqueta, cifras }: Props) {
  return (
    <div className="franja-indicadores franja-indicadores--cifras" role="group" aria-label={etiqueta}>
      <div className="franja-indicadores__lista">
        {cifras.map((c) => (
          <div key={c.id} className="fiori-kpi" role="group" aria-label={c.titulo}>
            <div className="fiori-kpi__fila">
              <span className="fiori-kpi__titulo cds--type-label-01">{c.titulo}</span>
            </div>
            <div className="fiori-kpi__fila">
              <span className="fiori-kpi__actual cds--type-heading-03 silice-cifra">{c.valor}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
