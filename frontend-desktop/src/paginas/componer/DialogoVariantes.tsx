import { Button } from "@carbon/react";
import { useRef } from "react";
import { centesimasEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import type { Prevision } from "./cliente";

interface Props {
  prevision: Prevision;
  alVolver: () => void;
  alGuardar: () => void;
}

// D-MP2: un precio tecleado distinto del que ya tiene el insumo en la lista no lo cambia; crea una variante solo para
// este APU. Antes de guardar se dice cuales, con los dos precios en la moneda de la lista (la API los da con punto: se
// formatean una sola vez). El dialogo es el del armazon (modal, Tab atrapado, Esc = «Volver»); el foco empieza en
// «Volver», la opcion que no cambia nada.
// 2026-11-13 (D-8): un precio convertido de Bs trae 28 cifras. Los dos se leen con dos decimales; si asi se leen iguales
// (5,04 y 5,0411…), van exactos, porque lo que el dialogo dice es justamente que son distintos.
function losDosPrecios(enLista: string, tecleado: string): [string, string] {
  const [a, b] = [centesimasEsVe(enLista), centesimasEsVe(tecleado)];
  return a === b ? [formatoEsVe(enLista), formatoEsVe(tecleado)] : [a, b];
}

export function DialogoVariantes({ prevision, alVolver, alGuardar }: Props) {
  const volver = useRef<HTMLButtonElement>(null);
  const moneda = prevision.lista.moneda;
  return (
    <MarcoDeDialogo
      titulo="Precios distintos a los de la lista"
      alCerrar={alVolver}
      inicial={() => volver.current}
      pie={
        <>
          <Button ref={volver} kind="secondary" onClick={alVolver}>
            Volver
          </Button>
          <Button kind="primary" onClick={alGuardar}>
            Guardar así
          </Button>
        </>
      }
    >
      <ul className="silice-componer__variantes cds--type-body-compact-01">
        {prevision.variantes.map((v) => {
          const [enLista, tecleado] = losDosPrecios(v.precio_en_lista, v.precio_tecleado);
          return (
            <li key={v.codigo_variante}>
              {`“${v.descripcion}” ya está a ${enLista} ${moneda}; con ${tecleado} ${moneda} se creará una variante solo para este APU.`}
            </li>
          );
        })}
      </ul>
      <p className="silice-componer__nota cds--type-body-compact-01">
        {`Los insumos nuevos se guardan en la lista «${prevision.lista.nombre}». Si prefiere el precio que ya tiene la lista, vuelva y corrija el suyo.`}
      </p>
    </MarcoDeDialogo>
  );
}
