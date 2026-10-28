import "./Pildora.scss";

// El contador pequeño de la barra lateral (maqueta aprobada: píldora, no bloque). Va oculto a los lectores de pantalla:
// el nombre accesible del enlace que la lleva ya dice «n por hacer».
export function Pildora({ valor }: { valor: number }) {
  return (
    <span className="silice-pildora" aria-hidden="true">
      {valor}
    </span>
  );
}
