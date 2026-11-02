import { useState } from "react";

// Nombre de una obra en el árbol de la barra lateral. La hoja de estilos lo limita a 2 líneas con puntos suspensivos; el
// `title` con el nombre completo solo se pone si de verdad está recortado (`scrollHeight > clientHeight`), medido al pasar
// el ratón (que es cuando el navegador muestra el `title`). Si cabe entero, un `title` repetiría lo que ya se lee.
export function NombreDeObra({ nombre }: { nombre: string }) {
  const [recortado, setRecortado] = useState(false);
  return (
    <span
      className="silice-marco-lateral__obra-nombre"
      title={recortado ? nombre : undefined}
      onMouseEnter={(e) => setRecortado(e.currentTarget.scrollHeight > e.currentTarget.clientHeight)}
    >
      {nombre}
    </span>
  );
}
