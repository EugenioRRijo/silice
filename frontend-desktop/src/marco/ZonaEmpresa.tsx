import { ChevronDown, ChevronRight } from "@carbon/icons-react";
import { useState } from "react";
import { Link } from "react-router";
import type { TamanoDeLetra } from "../comun/preferenciaDeLetra";
import { useTamanoDeLetra } from "../comun/useTamanoDeLetra";
import { rutaDeEmpresa } from "./secciones";
import type { EntradaDef } from "./secciones";

interface Props {
  entradas: readonly EntradaDef[];
  // La entrada de Empresa de la ruta, o null si la ruta no es de Empresa.
  entradaActiva: string | null;
  // Prefijo para el `id` de la lista (el `useId` de la barra), que `aria-controls` señala.
  idBase: string;
}

// La zona Empresa de la barra lateral, aparte de BarraLateral (Tarea 0 del plan F4, menor del árbitro): lleva su propio
// estado de plegado y su hook de letra, que no tienen nada que ver con el del árbol. Con letra normal es un h2 sin botón;
// con Grande o Muy grande, un desplegable de WAI-ARIA que arranca plegado (abierto si la ruta es una entrada de Empresa)
// para darle su alto al árbol. La decisión de la persona vale para el tamaño de letra con que se tomó.
export function ZonaEmpresa({ entradas, entradaActiva, idBase }: Props) {
  const tamanoDeLetra = useTamanoDeLetra();
  const plegable = tamanoDeLetra !== "normal";
  const [decision, setDecision] = useState<{ tamano: TamanoDeLetra; abierta: boolean } | null>(null);
  const manual = decision?.tamano === tamanoDeLetra ? decision.abierta : null;
  const abierta = !plegable || (manual ?? entradaActiva !== null);
  const idDeLista = `${idBase}-empresa`;

  return (
    <nav aria-label="Empresa" className="silice-marco-lateral__empresa">
      <h2 className="silice-marco-lateral__titulo">
        {plegable ? (
          <button
            type="button"
            className="silice-marco-lateral__empresa-boton"
            aria-expanded={abierta}
            aria-controls={idDeLista}
            onClick={() => setDecision({ tamano: tamanoDeLetra, abierta: !abierta })}
          >
            {abierta ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
            Empresa
          </button>
        ) : (
          "Empresa"
        )}
      </h2>
      {abierta && (
        <ul id={idDeLista}>
          {entradas.map((e) => (
            <li key={e.id}>
              <Link
                to={rutaDeEmpresa(e.id)}
                aria-current={entradaActiva === e.id ? "page" : undefined}
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
