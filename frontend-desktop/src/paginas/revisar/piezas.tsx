// Piezas de «Revisar un paquete» que se repiten: un monto con su exacto a la vista y una tabla de diferencias.
import type { ReactNode } from "react";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { presentador } from "./logica";
import type { TablaDeDiferencia } from "./tipos";

// Un monto como lo escribe la clasica (el texto de la API, en es-VE) con el valor exacto en el `title` y para el
// lector de pantalla. La interfaz no redondea: el texto ya viene redondeado de la API.
export function Monto({ texto, exacto }: { texto: string; exacto: string }) {
  return (
    <>
      <span className="silice-revisar__cifra" title={`Valor exacto: ${exacto}`}>
        {formatoEsVe(texto)}
      </span>
      <span className="cds--visually-hidden">{`. Valor exacto: ${exacto}`}</span>
    </>
  );
}

export function Dato({ rotulo, texto, exacto }: { rotulo: string; texto: string; exacto: string }) {
  return (
    <div>
      <dt className="cds--type-label-01">{rotulo}</dt>
      <dd className="cds--type-heading-03">
        <Monto texto={texto} exacto={exacto} />
      </dd>
    </div>
  );
}

// Una tabla de diferencias (contra la entrega anterior o contra una lista): totales antes y despues, la diferencia,
// su reparto por cantidad y por precio, y las partidas que no quedaron iguales.
export function Diferencia({ d, idTitulo, children }: { d: TablaDeDiferencia; idTitulo: string; children?: ReactNode }) {
  const ver = presentador(
    d.partidas.flatMap((p) => [
      [p.desvio_cantidad, p.desvio_cantidad_texto],
      [p.desvio_precio, p.desvio_precio_texto],
      [p.desvio_total, p.desvio_total_texto],
    ]) as [string, string][],
  );
  const columnas: ColumnaDensa[] = [
    { clave: "codigo_partida", titulo: "Partida" },
    { clave: "descripcion", titulo: "Descripción" },
    { clave: "estado", titulo: "Estado" },
    { clave: "desvio_cantidad", titulo: "Δ cantidad", numerica: true, presentar: ver },
    { clave: "desvio_precio", titulo: "Δ precio", numerica: true, presentar: ver },
    { clave: "desvio_total", titulo: "Δ total", numerica: true, presentar: ver },
  ];
  return (
    <section className="silice-revisar__seccion" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        {d.titulo}
      </h2>
      {children}
      <dl className="silice-revisar__datos">
        <Dato rotulo="Total antes" texto={d.total_antes_texto} exacto={d.total_antes} />
        <Dato rotulo="Total después" texto={d.total_despues_texto} exacto={d.total_despues} />
        <Dato rotulo="Diferencia" texto={d.diferencia_texto} exacto={d.diferencia} />
      </dl>
      <p className="silice-revisar__nota cds--type-body-compact-01">{d.por_cantidad_y_precio}</p>
      <TablaDensa
        etiqueta={`Partidas: ${d.titulo}`}
        columnas={columnas}
        filas={d.partidas.map((p, i) => ({
          id: String(i),
          codigo_partida: p.codigo_partida,
          descripcion: p.descripcion,
          estado: p.estado,
          desvio_cantidad: p.desvio_cantidad,
          desvio_precio: p.desvio_precio,
          desvio_total: p.desvio_total,
        }))}
        vacio={{ titulo: "Ninguna partida cambió." }}
      />
    </section>
  );
}
