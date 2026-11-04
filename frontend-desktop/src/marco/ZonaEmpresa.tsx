import { ChevronDown, ChevronRight } from "@carbon/icons-react";
import { useState } from "react";
import { Link } from "react-router";
import type { TamanoDeLetra } from "../comun/preferenciaDeLetra";
import { useTamanoDeLetra } from "../comun/useTamanoDeLetra";
import type { EspacioOfrecido } from "./oferta";
import { rutaDeEmpresa } from "./secciones";
import type { EntradaDef } from "./secciones";

interface Props {
  entradas: readonly EntradaDef[];
  // La entrada de Empresa de la ruta, o null si la ruta no es de Empresa.
  entradaActiva: string | null;
  // Los espacios de «Costos y producción» que la cuenta puede usar, en el orden de la barra, y el de la ruta (o null).
  espacios: readonly EspacioOfrecido[];
  espacioActivo: string | null;
  // Prefijo para el `id` de la lista (el `useId` de la barra), que `aria-controls` señala.
  idBase: string;
}

// La zona Empresa de la barra lateral, aparte de BarraLateral (Tarea 0 del plan F4, menor del árbitro): lleva su propio
// estado de plegado y su hook de letra, que no tienen nada que ver con el del árbol. Con letra normal es un h2 sin botón;
// con Grande o Muy grande, un desplegable de WAI-ARIA que arranca plegado (abierto si la ruta es una entrada de Empresa)
// para darle su alto al árbol. La decisión de la persona vale para el tamaño de letra con que se tomó. F6, T4: arriba lleva
// el grupo «Costos y producción» (Auditar, Precios, Costos de producción) y la zona también arranca abierta si la ruta es de
// uno de esos espacios; «Empresa y personas» y «Ayuda» pasan a la Cuenta con T6.
export function ZonaEmpresa({ entradas, entradaActiva, espacios, espacioActivo, idBase }: Props) {
  const tamanoDeLetra = useTamanoDeLetra();
  const plegable = tamanoDeLetra !== "normal";
  const [decision, setDecision] = useState<{ tamano: TamanoDeLetra; abierta: boolean } | null>(null);
  const manual = decision?.tamano === tamanoDeLetra ? decision.abierta : null;
  const abierta = !plegable || (manual ?? (entradaActiva !== null || espacioActivo !== null));
  const idDeLista = `${idBase}-empresa`;
  const idDelGrupo = `${idBase}-costos-y-produccion`;

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
          {espacios.length > 0 && (
            <li>
              <h3 id={idDelGrupo} className="silice-marco-lateral__subtitulo">
                Costos y producción
              </h3>
              <ul aria-labelledby={idDelGrupo}>
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
            </li>
          )}
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
