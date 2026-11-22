import { Catalog, ChevronDown, ChevronRight, DocumentView, Industry } from "@carbon/icons-react";
import { useState } from "react";
import { Link } from "react-router";
import type { TamanoDeLetra } from "../comun/preferenciaDeLetra";
import { useTamanoDeLetra } from "../comun/useTamanoDeLetra";
import type { EspacioId } from "./espacios";
import type { EspacioOfrecido } from "./oferta";

interface Props {
  // Los espacios de «Costos y producción» que la cuenta puede usar, en el orden de la barra, y el de la ruta (o null).
  espacios: readonly EspacioOfrecido[];
  espacioActivo: string | null;
  // Prefijo para el `id` de la lista (el `useId` de la barra), que `aria-controls` señala.
  idBase: string;
}

const PREFIJO_ESPACIO: Record<EspacioId, string> = {
  auditoria: "01",
  precios: "02",
  produccion: "03",
};

function IconoEspacio({ id }: { id: EspacioId }) {
  if (id === "auditoria") return <DocumentView size={16} className="silice-marco-lateral__icono-oro" aria-hidden="true" />;
  if (id === "precios") return <Catalog size={16} className="silice-marco-lateral__icono-oro" aria-hidden="true" />;
  return <Industry size={16} className="silice-marco-lateral__icono-oro" aria-hidden="true" />;
}

export function ZonaDeCostos({ espacios, espacioActivo, idBase }: Props) {
  const tamanoDeLetra = useTamanoDeLetra();
  const plegable = tamanoDeLetra !== "normal";
  const [decision, setDecision] = useState<{ tamano: TamanoDeLetra; abierta: boolean } | null>(null);
  const manual = decision?.tamano === tamanoDeLetra ? decision.abierta : null;
  const abierta = !plegable || (manual ?? espacioActivo !== null);
  const idDeLista = `${idBase}-costos`;
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
                data-prefijo={PREFIJO_ESPACIO[e.id]}
                className="silice-marco-lateral__fila silice-marco-lateral__herramienta"
              >
                <IconoEspacio id={e.id} />
                <span className="silice-marco-lateral__etiqueta">{e.titulo}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
