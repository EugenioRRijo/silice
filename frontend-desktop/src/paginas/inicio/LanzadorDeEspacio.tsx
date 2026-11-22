import { ArrowRight, Catalog, DocumentView, Industry } from "@carbon/icons-react";
import { Link } from "react-router";
import type { EspacioId } from "../../marco/espacios";

function IconoLanzador({ id }: { id: EspacioId }) {
  if (id === "auditoria") return <DocumentView size={16} aria-hidden="true" />;
  if (id === "precios") return <Catalog size={16} aria-hidden="true" />;
  return <Industry size={16} aria-hidden="true" />;
}

// Un lanzador de la Vista general: se llama como su espacio y lo describe con las herramientas que la cuenta puede usar
// allí (`herramientas`, ya unidas con « · »). El código de orden es adorno: va oculto a la lectora y fuera del nombre.
// Sin herramientas que decir no hay descripción: el enlace no apunta a un texto vacío.
export function LanzadorDeEspacio({
  id,
  codigo,
  titulo,
  ruta,
  herramientas,
}: {
  id: EspacioId;
  codigo: string;
  titulo: string;
  ruta: string;
  herramientas: string;
}) {
  const conDescripcion = herramientas.trim() !== "";
  return (
    <Link
      to={ruta}
      className="silice-lanzador__tarjeta"
      aria-labelledby={`lanzador-${id}`}
      aria-describedby={conDescripcion ? `lanzador-${id}-desc` : undefined}
    >
      <span className="silice-lanzador__arriba" aria-hidden="true">
        <span className="silice-lanzador__codigo">{`${codigo} · Ventana dedicada`}</span>
        <IconoLanzador id={id} />
      </span>
      <span id={`lanzador-${id}`} className="silice-lanzador__titulo">
        {titulo}
      </span>
      {conDescripcion && (
        <span id={`lanzador-${id}-desc`} className="silice-lanzador__desc">
          {herramientas}
        </span>
      )}
      <span className="silice-lanzador__accion" aria-hidden="true">
        Abrir herramienta <ArrowRight size={14} aria-hidden="true" />
      </span>
    </Link>
  );
}
