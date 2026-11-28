import type { JSX } from "react";
import { Link, useInRouterContext } from "react-router";
import type { EnlaceDeNotificacion } from "./modelo";

interface PropsDeEnlaceDeNotificacion {
  enlace: EnlaceDeNotificacion;
  className?: string;
  alSeguir?: () => void;
}

// Funciona tanto dentro del enrutador de la aplicación como en pruebas unitarias aisladas sin Router.
export function EnlaceDeNotificacionVista({
  enlace,
  className,
  alSeguir,
}: PropsDeEnlaceDeNotificacion): JSX.Element {
  const enRouter = useInRouterContext();
  if (enRouter) {
    return (
      <Link to={enlace.ruta} className={className} onClick={alSeguir}>
        {enlace.texto}
      </Link>
    );
  }
  const destino = enlace.ruta.startsWith("#") ? enlace.ruta : `#${enlace.ruta}`;
  return (
    <a href={destino} className={className} onClick={alSeguir}>
      {enlace.texto}
    </a>
  );
}
