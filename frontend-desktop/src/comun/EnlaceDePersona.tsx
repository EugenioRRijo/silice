import { Link, useInRouterContext } from "react-router";
import { rutaDeActividad } from "../marco/espacios";
import { extraerPersona } from "./responsable";

interface Props {
  dato: string | null | undefined;
  usuarioExplicito?: string | null;
}

// Muestra el nombre de la persona como enlace a su actividad si trae usuario; sin usuario queda como texto.
export function EnlaceDePersona({ dato, usuarioExplicito }: Props) {
  const enRuta = useInRouterContext();
  const persona = extraerPersona(dato, usuarioExplicito);
  if (persona === null) return null;
  if (persona.usuario === null || !enRuta) return <>{persona.nombre}</>;
  return (
    <Link
      to={rutaDeActividad(persona.usuario)}
      className="cds--link"
      aria-label={`Ver la actividad de ${persona.nombre}`}
    >
      {persona.nombre}
    </Link>
  );
}
