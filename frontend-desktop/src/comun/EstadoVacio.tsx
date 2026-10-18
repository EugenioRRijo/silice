import type { ReactNode } from "react";

interface Props {
  titulo: string;
  // Que hacer para que haya algo que ver (DESIGN.md: los estados vacios ensenan).
  descripcion?: string;
  // La accion que lleva a llenarlo (un boton o un enlace).
  children?: ReactNode;
}

export function EstadoVacio({ titulo, descripcion, children }: Props) {
  return (
    <div className="silice-vacio">
      <p className="silice-vacio__titulo cds--type-heading-compact-01">{titulo}</p>
      {descripcion && <p className="silice-vacio__texto cds--type-body-compact-01">{descripcion}</p>}
      {children}
    </div>
  );
}
