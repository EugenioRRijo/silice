import { EstadoVacio } from "../../comun/EstadoVacio";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { deObservaciones, enOtraMoneda } from "./logica";
import type { Estudio } from "./logica";

// Un monto de la API (texto con punto, ya en centimos) como se lee: «140,00 Bs». Se formatea una sola vez y nunca se
// convierte en numero; el texto con punto decimal no se muestra en ninguna parte (ni en un `title`).
export function Monto({ valor, moneda }: { valor: string; moneda: string }) {
  return (
    <>
      <span>{formatoEsVe(valor)}</span> {moneda}
    </>
  );
}

interface Props {
  estudio: Estudio;
  // Cobro: el nombre de la obra abierta cuyos parametros dan el piso; null sin obra o en compra.
  obra: string | null;
}

// Las cifras del mercado (n, minimo, primer cuartil, mediana, promedio y maximo, cada monto «de n observaciones») y,
// en cobro, su costo (piso) y el precio con utilidad. Todo viene calculado por la API.
export function Cifras({ estudio, obra }: Props) {
  const { estadisticas: est, moneda, lado } = estudio;
  const id = `mercado-${lado}-cifras`;
  const montos: [string, string | null][] = [
    ["Mínimo", est.minimo],
    ["Primer cuartil", est.q1],
    ["Mediana", est.mediana],
    ["Promedio", est.promedio],
    ["Máximo", est.maximo],
  ];

  return (
    <>
      <section className="silice-mercado__bloque" aria-labelledby={id}>
        <h2 id={id} className="cds--type-heading-compact-02">
          {`Cifras de los últimos ${est.dias} días, en ${moneda}`}
        </h2>
        {est.n === 0 ? (
          <EstadoVacio
            titulo={`Sin observaciones en los últimos ${est.dias} días.`}
            descripcion="Anote el primer precio que vea en «Anotar una observación», más abajo, o amplíe los días hacia atrás."
          />
        ) : (
          <dl className="silice-mercado__cifras">
            <div className="silice-mercado__cifra">
              <dt className="cds--type-label-01">Observaciones</dt>
              <dd className="silice-mercado__valor">{est.n}</dd>
            </div>
            {montos.map(([titulo, valor]) => (
              <div key={titulo} className="silice-mercado__cifra">
                <dt className="cds--type-label-01">{titulo}</dt>
                <dd className="silice-mercado__valor">{valor === null ? "—" : <Monto valor={valor} moneda={moneda} />}</dd>
                <dd className="silice-mercado__de cds--type-helper-text-01">{deObservaciones(est.n)}</dd>
              </div>
            ))}
          </dl>
        )}
        {est.otras_monedas > 0 && (
          <p className="silice-mercado__nota cds--type-helper-text-01">{enOtraMoneda(est.otras_monedas)}</p>
        )}
      </section>

      {lado === "cobro" && estudio.piso !== null && estudio.precio_unitario !== null && (
        <section className="silice-mercado__bloque" aria-labelledby={`mercado-${lado}-costo`}>
          <h2 id={`mercado-${lado}-costo`} className="cds--type-heading-compact-02">
            Su costo
          </h2>
          <dl className="silice-mercado__cifras">
            <div className="silice-mercado__cifra">
              <dt className="cds--type-label-01">Su costo (piso)</dt>
              <dd className="silice-mercado__valor">
                <Monto valor={estudio.piso} moneda={moneda} />
              </dd>
              <dd className="silice-mercado__de cds--type-helper-text-01">costo directo más administración</dd>
            </div>
            <div className="silice-mercado__cifra">
              <dt className="cds--type-label-01">Precio con utilidad</dt>
              <dd className="silice-mercado__valor">
                <Monto valor={estudio.precio_unitario} moneda={moneda} />
              </dd>
              <dd className="silice-mercado__de cds--type-helper-text-01">el de su análisis de precio, sin IVA</dd>
            </div>
          </dl>
          <p className="silice-mercado__nota cds--type-helper-text-01">
            {obra === null
              ? "Calculado con la lista para armar de la carpeta y los parámetros por omisión: no hay una obra abierta."
              : `Calculado con la lista para armar de la carpeta y los parámetros de la versión vigente de la obra «${obra}» (sin versión guardada, los por omisión).`}
          </p>
        </section>
      )}
    </>
  );
}
