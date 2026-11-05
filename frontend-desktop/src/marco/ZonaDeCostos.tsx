import { ChevronDown, ChevronRight } from "@carbon/icons-react";
import { useState } from "react";
import { Link } from "react-router";
import type { TamanoDeLetra } from "../comun/preferenciaDeLetra";
import { useTamanoDeLetra } from "../comun/useTamanoDeLetra";
import type { EspacioOfrecido } from "./oferta";

interface Props {
  // Los espacios de «Costos y producción» que la cuenta puede usar, en el orden de la barra, y el de la ruta (o null).
  espacios: readonly EspacioOfrecido[];
  espacioActivo: string | null;
  // Prefijo para el `id` de la lista (el `useId` de la barra), que `aria-controls` señala.
  idBase: string;
}

// La zona «Costos y producción» de la barra lateral (Auditar un presupuesto, Precios y catálogo, Costos de producción), aparte
// de BarraLateral: lleva su propio estado de plegado y su hook de letra, que no tienen nada que ver con el de las obras.
// Antes era la zona Empresa (Tarea 0 del plan F4); en F6, T6 «Empresa y personas» y «Ayuda» pasaron a la Cuenta y quedó solo
// este grupo, con su título (diseño visual 3.1). Con letra normal es un h2 sin botón; con Grande o Muy grande, un
// desplegable de WAI-ARIA que arranca plegado (abierto si la ruta es de uno de los tres espacios) para darle su alto a la
// lista de obras. La decisión de la persona vale para el tamaño de letra con que se tomó.
export function ZonaDeCostos({ espacios, espacioActivo, idBase }: Props) {
  const tamanoDeLetra = useTamanoDeLetra();
  const plegable = tamanoDeLetra !== "normal";
  const [decision, setDecision] = useState<{ tamano: TamanoDeLetra; abierta: boolean } | null>(null);
  const manual = decision?.tamano === tamanoDeLetra ? decision.abierta : null;
  const abierta = !plegable || (manual ?? espacioActivo !== null);
  const idDeLista = `${idBase}-costos`;
  // Sin ningún espacio que la cuenta pueda usar no hay zona que ofrecer.
  if (espacios.length === 0) return null;

  return (
    <nav aria-label="Costos y producción" className="silice-marco-lateral__costos">
      <h2 className="silice-marco-lateral__titulo">
        {plegable ? (
          <button
            type="button"
            className="silice-marco-lateral__costos-boton"
            aria-expanded={abierta}
            aria-controls={idDeLista}
            onClick={() => setDecision({ tamano: tamanoDeLetra, abierta: !abierta })}
          >
            {abierta ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
            Costos y producción
          </button>
        ) : (
          "Costos y producción"
        )}
      </h2>
      {abierta && (
        <ul id={idDeLista}>
          {espacios.map((e) => (
            <li key={e.id}>
              <Link
                to={e.ruta}
                aria-current={espacioActivo === e.id ? "page" : undefined}
                className="silice-marco-lateral__fila"
              >
                {e.titulo}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
