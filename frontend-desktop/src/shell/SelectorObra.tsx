import { Add, Building, ChevronDown, Folder } from "@carbon/icons-react";
import { Button, Search } from "@carbon/react";
import { useId, useState } from "react";
import type { JSX, ReactNode } from "react";
import type { ProyectoRespuesta } from "../api/tipos";
import { coincide } from "../paginas/catalogo/filtro";
import { rotuloDeProyecto } from "./Selectores";
import { useDespliegue } from "./useDespliegue";
import "./SelectorObra.scss";

// El boton del selector lleva este id: los dialogos de carpetas y de «Nueva obra» le devuelven el foco al cerrarse.
export const ID_BOTON_OBRA = "silice-boton-obra";

interface Props {
  // Las obras de la carpeta abierta; null si la cuenta no las ve (sin `leer_proyecto`) o aun no llegan.
  obras: ProyectoRespuesta[] | null;
  // Codigo de la obra elegida, o null.
  elegida: string | null;
  // En el inicio del modulo (la mesa de control) el boton dice «Todas las obras».
  enInicio: boolean;
  // Nombre de la carpeta abierta, sin .db; null mientras no se sabe.
  carpeta: string | null;
  puedeCambiarCarpeta: boolean;
  puedeCrearObra: boolean;
  alElegir: (codigo: string) => void;
  alNuevaObra: () => void;
  alCambiarCarpeta: () => void;
  // Hueco al pie del panel (la lista de la carpeta de MP T4).
  pie?: ReactNode;
  // Si la cuenta puede ver las obras (por omision, si llega la lista). Con ella y sin lista, la lista esta cargando.
  puedeVerObras?: boolean;
}

// «Obra» en la barra de Presupuestos y obras (diseno de modulos §7 y §12.2): el boton dice la obra elegida y abre un
// panel (patron de `useDespliegue`, como la cuenta) con la busqueda, la lista de obras, «Nueva obra» y, al pie, la
// carpeta de trabajo con «Cambiar carpeta…». Quien no ve obras pero cambia de carpeta (el administrador) ve solo la
// carpeta. El texto se recorta por CSS; el nombre completo va en el nombre accesible y en `title`.
export function SelectorObra({
  obras,
  elegida,
  enInicio,
  carpeta,
  puedeCambiarCarpeta,
  puedeCrearObra,
  alElegir,
  alNuevaObra,
  alCambiarCarpeta,
  pie,
  puedeVerObras = obras !== null,
}: Props): JSX.Element | null {
  const idPanel = useId();
  const { abierto, alternar, envoltorio, boton, alTeclear } = useDespliegue();
  const [busqueda, setBusqueda] = useState("");
  // La busqueda no sobrevive al cierre del panel, se cierre como se cierre (boton, Esc, clic fuera, elegir): se ajusta
  // durante el render, sin efecto, como el aviso del armazon.
  const [abiertoAntes, setAbiertoAntes] = useState(abierto);
  if (abierto !== abiertoAntes) {
    setAbiertoAntes(abierto);
    if (!abierto) setBusqueda("");
  }
  if (!puedeVerObras && !puedeCambiarCarpeta) return null;

  const nombreCarpeta = carpeta ?? "…";
  const actual = obras?.find((o) => o.codigo === elegida) ?? null;
  const nombreObra = actual && obras ? rotuloDeProyecto(actual, obras, false) : null;
  let texto: string;
  let accion: string;
  if (!puedeVerObras) {
    texto = `Carpeta: ${nombreCarpeta}`;
    accion = "Cambiar carpeta";
  } else if (enInicio) {
    texto = "Todas las obras";
    accion = "Elegir obra";
  } else if (nombreObra !== null) {
    texto = `Obra: ${nombreObra}`;
    accion = "Cambiar obra";
  } else {
    texto = elegida !== null && obras === null ? "Obra: cargando…" : "Obra: sin elegir";
    accion = "Elegir obra";
  }

  // Cerrar el panel y llevar el foco al boton antes de lo que sigue: asi un dialogo que se abre despues (carpetas,
  // «Nueva obra») sabe a donde devolverlo, y el control pulsado, que desaparece con el panel, no deja el foco en <body>.
  function cerrarYDespues(despues: () => void) {
    alternar();
    boton.current?.focus();
    despues();
  }

  const visibles = obras?.filter((o) => coincide([o.nombre, o.cliente, o.ubicacion], busqueda)) ?? [];

  return (
    <div className="silice-obra" ref={envoltorio} onKeyDown={alTeclear}>
      <button
        type="button"
        id={ID_BOTON_OBRA}
        ref={boton}
        className="cds--header__action silice-obra__boton"
        aria-expanded={abierto}
        aria-controls={idPanel}
        aria-label={`${texto}. ${accion}`}
        title={nombreObra ?? (puedeVerObras ? texto : nombreCarpeta)}
        onClick={alternar}
      >
        {puedeVerObras ? <Building size={16} aria-hidden="true" /> : <Folder size={16} aria-hidden="true" />}
        <span className="silice-obra__texto cds--type-body-compact-01">{texto}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {abierto && (
        <div
          id={idPanel}
          role="region"
          aria-label={puedeVerObras ? "Obra" : "Carpeta de trabajo"}
          className="silice-obra__panel"
        >
          {puedeVerObras && (
            <>
              <Search
                size="sm"
                labelText="Buscar obra"
                placeholder="Nombre, cliente o ubicación"
                closeButtonLabelText="Borrar la búsqueda"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                // El Search de Carbon se queda con Esc (borra y detiene la propagacion): aqui Esc cierra el panel de una
                // vez, como en el resto de la barra, y el foco vuelve al boton.
                onKeyDown={(e) => {
                  if (e.key !== "Escape") return;
                  alternar();
                  boton.current?.focus();
                }}
              />
              <ListaDeObras
                obras={obras}
                visibles={visibles}
                elegida={elegida}
                busqueda={busqueda}
                puedeCrearObra={puedeCrearObra}
                alElegir={(codigo) => cerrarYDespues(() => alElegir(codigo))}
              />
              {puedeCrearObra && (
                <Button
                  kind="ghost"
                  size="sm"
                  renderIcon={Add}
                  className="silice-obra__nueva"
                  onClick={() => cerrarYDespues(alNuevaObra)}
                >
                  Nueva obra
                </Button>
              )}
            </>
          )}
          <div className="silice-obra__pie">
            <p className="silice-obra__carpeta cds--type-helper-text-01">
              <span>{`Carpeta: ${nombreCarpeta}`}</span>
              {puedeCambiarCarpeta && (
                <>
                  <span aria-hidden="true"> · </span>
                  <button
                    type="button"
                    className="silice-obra__cambiar cds--link"
                    onClick={() => cerrarYDespues(alCambiarCarpeta)}
                  >
                    Cambiar carpeta…
                  </button>
                </>
              )}
            </p>
            {pie}
          </div>
        </div>
      )}
    </div>
  );
}

function ListaDeObras({
  obras,
  visibles,
  elegida,
  busqueda,
  puedeCrearObra,
  alElegir,
}: {
  obras: ProyectoRespuesta[] | null;
  visibles: ProyectoRespuesta[];
  elegida: string | null;
  busqueda: string;
  puedeCrearObra: boolean;
  alElegir: (codigo: string) => void;
}) {
  if (obras === null) {
    return (
      <p className="silice-obra__estado cds--type-body-compact-01" role="status">
        Cargando las obras…
      </p>
    );
  }
  if (obras.length === 0) {
    return (
      <p className="silice-obra__estado cds--type-body-compact-01">
        {puedeCrearObra
          ? "Esta carpeta de trabajo aún no tiene obras. Cree la primera con «Nueva obra»."
          : "Esta carpeta de trabajo aún no tiene obras."}
      </p>
    );
  }
  if (visibles.length === 0) {
    return (
      <p className="silice-obra__estado cds--type-body-compact-01" role="status">
        {`Ninguna obra coincide con «${busqueda.trim()}».`}
      </p>
    );
  }
  return (
    <ul className="silice-obra__lista" aria-label="Obras de la carpeta de trabajo">
      {visibles.map((o) => {
        const detalle = [o.cliente, o.ubicacion].filter((d) => (d ?? "").trim() !== "").join(" · ");
        return (
          <li key={o.codigo}>
            <button
              type="button"
              className="silice-obra__opcion"
              aria-current={o.codigo === elegida ? "true" : undefined}
              onClick={() => alElegir(o.codigo)}
            >
              <span className="silice-obra__nombre cds--type-body-compact-01">{rotuloDeProyecto(o, obras)}</span>
              {detalle && <span className="silice-obra__detalle cds--type-helper-text-01">{detalle}</span>}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
