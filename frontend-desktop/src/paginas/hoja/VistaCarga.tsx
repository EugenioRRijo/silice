import { useEffect } from "react";
import type { ReactNode } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { useAplicacion } from "../../shell/contexto";
import { esBorradorAusente } from "./logica";
import { useVista } from "./useVista";

interface Props<T> {
  ruta: string;
  // Nombre de la pestaña, para el marcador de carga y el aviso de error.
  etiqueta: string;
  // El servidor ya no tiene el borrador: la página lo dice una sola vez y ofrece abrirlo de nuevo.
  alAusente: () => void;
  // Sube cada vez que hay que volver a leer la vista (por ejemplo tras una edición); la anterior sigue a la vista.
  recarga?: number;
  children: (datos: T, actualizando: boolean) => ReactNode;
}

// Estados de carga, error y listo de una vista de la hoja.
export function VistaCarga<T>({ ruta, etiqueta, alAusente, recarga = 0, children }: Props<T>) {
  const { alExpirar } = useAplicacion();
  const vista = useVista<T>(ruta, alExpirar, recarga);
  const ausente = vista.estado === "error" && esBorradorAusente(vista.error);

  useEffect(() => {
    if (ausente) alAusente();
  }, [ausente, alAusente]);

  if (vista.estado === "cargando") return <EsqueletoPagina etiqueta={`Cargando ${etiqueta}`} />;
  if (vista.estado === "error") {
    return ausente ? null : <AvisoError error={vista.error} titulo={`No se pudo cargar ${etiqueta}`} />;
  }
  return <>{children(vista.datos, vista.actualizando)}</>;
}
