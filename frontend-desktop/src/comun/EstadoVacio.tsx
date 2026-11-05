import type { ReactNode } from "react";

interface Props {
  titulo: string;
  // Si el título es el encabezado de la pantalla (un aviso que sustituye a la pantalla entera), su nivel; por omisión es un párrafo.
  nivel?: 1 | 2 | 3;
  // Que hacer para que haya algo que ver (DESIGN.md: los estados vacios ensenan).
  descripcion?: string;
  // La accion que lleva a llenarlo (un boton o un enlace).
  children?: ReactNode;
}

export function EstadoVacio({ titulo, nivel, descripcion, children }: Props) {
  const Titulo = nivel === undefined ? "p" : (`h${nivel}` as const);
  return (
    <div className="silice-vacio">
      <Titulo className="silice-vacio__titulo cds--type-heading-compact-01">{titulo}</Titulo>
      {descripcion && <p className="silice-vacio__texto cds--type-body-compact-01">{descripcion}</p>}
      {children}
    </div>
  );
}
