import type { JSX, ReactNode, Ref } from "react";
import type { CalculoDeCosto } from "../../api/produccionPlanta";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { fechaEsVe, mostrarMonto, nombreDelMes } from "./logica";
import { fuenteDelPrecio, resumenDeCalculo } from "./logicaPlanta";

interface Props {
  calculo: CalculoDeCosto;
  region: Ref<HTMLElement>;
  // Lo que va debajo de la tabla (la publicación, si la cuenta puede).
  children?: ReactNode;
}

// El cálculo tal como lo guardó el servidor: costo por tonelada de cada producto (presentado con dos decimales y el
// valor exacto aparte, en su propia columna), los totales de cada centro y la fuente con que quedará el precio. Nada
// de esto se calcula aquí: solo se escribe con coma decimal y punto de miles.
export function ResultadoDelCalculo({ calculo, region, children }: Props): JSX.Element {
  const resumen = resumenDeCalculo(calculo.instantanea);
  const columnas: ColumnaDensa[] = [
    { clave: "codigo", titulo: "Producto" },
    { clave: "tipo", titulo: "Tipo" },
    { clave: "presentado", titulo: `Costo por tonelada (${calculo.moneda})`, numerica: true, presentar: mostrarMonto },
    { clave: "exacto", titulo: `Valor exacto (${calculo.moneda})`, numerica: true, presentar: formatoEsVe },
  ];
  const filas: FilaDensa[] = calculo.productos.map((p) => ({
    id: p.codigo,
    codigo: p.codigo,
    tipo: resumen.agregados.includes(p.codigo) ? "Agregado" : "Mezcla",
    presentado: p.presentado,
    exacto: p.por_tonelada,
  }));
  return (
    <section ref={region} tabIndex={-1} aria-label="Resultado del cálculo" className="planta-resultado">
      <h2 className="cds--type-heading-compact-02">Cálculo n.º {calculo.id}</h2>
      <p className="cds--type-body-compact-01">
        Período {nombreDelMes(calculo.periodo)}, en {calculo.moneda}. Calculado por {calculo.usuario}
        {calculo.registrado ? ` el ${fechaEsVe(calculo.registrado.slice(0, 10))}` : ""}. Fuente:{" "}
        <span className="silice-cifra">{fuenteDelPrecio(calculo.periodo, calculo.id)}</span>
      </p>
      <TablaDensa etiqueta={`Costo por tonelada de ${nombreDelMes(calculo.periodo)}`} columnas={columnas} filas={filas} />
      <ul className="planta-lista cds--type-body-compact-01" aria-label="Totales del período">
        {resumen.totalCantera !== null && (
          <li>
            Total de la cantera: {mostrarMonto(resumen.totalCantera)} {calculo.moneda}
          </li>
        )}
        {resumen.totalPlanta !== null && (
          <li>
            Total de la planta: {mostrarMonto(resumen.totalPlanta)} {calculo.moneda}
          </li>
        )}
      </ul>
      <p className="planta-nota cds--type-body-compact-01">
        Huella del cálculo: <span className="silice-cifra">{calculo.huella}</span>. Recalcular crea otro cálculo; el anterior queda intacto.
      </p>
      {children}
    </section>
  );
}
