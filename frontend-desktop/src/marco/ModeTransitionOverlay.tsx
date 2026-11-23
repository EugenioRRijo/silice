import { Catalog, DocumentView, Industry, Workspace } from "@carbon/icons-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ESPACIOS } from "./espacios";
import "./ModeTransitionOverlay.scss";

export type EstacionMayor = "obras" | "auditoria" | "precios" | "produccion";

interface Metadatos {
  titulo: string;
  subtitulo: string;
}

// Un solo nombre por espacio: el de `ESPACIOS`, el mismo de la barra lateral y del selector de la barra superior. Lo de
// debajo son sus herramientas, tal como se llaman en su barra; nada de rótulos propios de la cortina.
function metadatosDe(destino: EstacionMayor): Metadatos {
  if (destino === "obras") {
    return { titulo: "Obras", subtitulo: "Vista general, pendientes y las obras de la carpeta" };
  }
  const espacio = ESPACIOS[destino];
  return {
    titulo: espacio.titulo,
    subtitulo: espacio.herramientas.map((h) => h.titulo).join(", "),
  };
}

function prefiereMenosMovimiento(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// La barra avanza sola mientras dura la cortina (340 ms): es una animación, no la medida de una carga, así que no se
// escribe ningún porcentaje. Los temporizadores se programan una vez por destino (el `key` de abajo): la función de
// cierre se lee de una referencia, porque Marco pasa una nueva en cada dibujo y reprogramarlos alargaba la cortina.
function ContenidoTransicion({ destino, alTerminar }: { destino: EstacionMayor; alTerminar: () => void }) {
  const reducido = prefiereMenosMovimiento();
  const [progreso, setProgreso] = useState(14);
  const terminar = useRef(alTerminar);
  useLayoutEffect(() => {
    terminar.current = alTerminar;
  }, [alTerminar]);

  useEffect(() => {
    if (reducido) {
      const t = window.setTimeout(() => terminar.current(), 0);
      return () => window.clearTimeout(t);
    }
    const t1 = window.setTimeout(() => setProgreso(66), 80);
    const t2 = window.setTimeout(() => setProgreso(100), 210);
    const t3 = window.setTimeout(() => terminar.current(), 340);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [reducido]);

  if (reducido) return null;

  const meta = metadatosDe(destino);
  const Icono =
    destino === "auditoria"
      ? DocumentView
      : destino === "precios"
        ? Catalog
        : destino === "produccion"
          ? Industry
          : Workspace;

  return (
    <div className="silice-transicion" role="status" aria-live="polite" aria-label={`Cargando ${meta.titulo}`}>
      <div className="silice-transicion__tarjeta">
        <div className="silice-transicion__acento" aria-hidden="true" />
        <div className="silice-transicion__cuerpo">
          <div className="silice-transicion__icono" aria-hidden="true">
            <Icono size={24} />
          </div>
          <div>
            <p className="silice-transicion__titulo">{meta.titulo}</p>
            <p className="silice-transicion__sub">{meta.subtitulo}</p>
          </div>
        </div>
        <div className="silice-transicion__barra-bloque">
          <div className="silice-transicion__pista" aria-hidden="true">
            <div className="silice-transicion__progreso" style={{ inlineSize: `${progreso}%` }} />
          </div>
          <p className="silice-transicion__detalle">{`Abriendo ${meta.titulo}…`}</p>
        </div>
      </div>
    </div>
  );
}

export function ModeTransitionOverlay({
  destino,
  alTerminar,
}: {
  destino: EstacionMayor | null;
  alTerminar: () => void;
}) {
  if (!destino) return null;
  return <ContenidoTransicion key={destino} destino={destino} alTerminar={alTerminar} />;
}
