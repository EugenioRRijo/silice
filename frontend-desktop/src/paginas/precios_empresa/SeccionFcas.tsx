import { Button } from "@carbon/react";
import { useState } from "react";
import type { JSX } from "react";
import { CalculadoraFCAS } from "./CalculadoraFCAS";

// La calculadora del FCAS se abre a pedido: mientras no se abre no consulta nada ni suma ruido a la página.
export function SeccionFcas({ alExpirar }: { alExpirar: (error: unknown) => void }): JSX.Element {
  const [abierta, setAbierta] = useState(false);
  return (
    <section className="silice-precios-empresa__seccion" aria-labelledby="precios-empresa-fcas">
      <h2 id="precios-empresa-fcas" className="cds--type-heading-compact-02">
        FCAS por componentes
      </h2>
      <p className="silice-precios-empresa__nota cds--type-label-01">
        El factor de costos asociados al salario que sale de los días pagados y de los aportes patronales, con su base
        legal. Se compara con el de la versión y no se aplica solo.
      </p>
      {abierta ? (
        <CalculadoraFCAS alExpirar={alExpirar} />
      ) : (
        <div className="silice-precios-empresa__acciones">
          <Button kind="tertiary" size="md" onClick={() => setAbierta(true)}>
            Abrir la calculadora del FCAS
          </Button>
        </div>
      )}
    </section>
  );
}
