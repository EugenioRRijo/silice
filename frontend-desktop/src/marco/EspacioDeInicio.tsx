import { Suspense } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation, useParams } from "react-router";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { AyudaDeLaPantalla } from "../paginas/ayuda/AyudaDeLaPantalla";
import { LimiteDeError } from "../shell/LimiteDeError";
import { BarraDeEspacio } from "./BarraDeEspacio";
import type { PestanaDeEspacio } from "./BarraDeEspacio";
import { VISTAS_DE_INICIO, esVistaDeInicio, rutaDeInicio } from "./espacios";
import { RUTA_DE_VISTA_GENERAL } from "./secciones";

interface Props {
  // La Vista general (la pantalla «inicio», que pinta el marco con su registro) y la bandeja de Pendientes, que el marco monta
  // aparte porque abre los pasos por la salida segura (`irSeguro`).
  general: ReactNode;
  pendientes: ReactNode;
}

// `#/inicio` y una vista que no existe (`#/inicio/xyz`) llevan a la Vista general, con replace y conservando la consulta.
export function RaizDeInicio() {
  const { search } = useLocation();
  return <Navigate to={`${RUTA_DE_VISTA_GENERAL}${search}`} replace />;
}

// Inicio como espacio (F6, T8; contrato de rutas 1 y 4; diseño visual B.1): la cabecera «Vista general», debajo la barra con
// sus dos vistas (Vista general y Pendientes) y, en el lienzo, la vista elegida. Toda cuenta ve las dos: no hay nada que
// filtrar por permiso (cada bloque pide por su cuenta lo que su rol puede leer). La cabecera y la barra no se vuelven a
// montar al cambiar de vista (el marco da la misma clave a todo el espacio); el límite de error y la espera son de cada vista.
export function EspacioDeInicio({ general, pendientes }: Props) {
  const { vista } = useParams();
  if (vista === undefined || !esVistaDeInicio(vista)) return <RaizDeInicio />;
  const pestanas: PestanaDeEspacio[] = VISTAS_DE_INICIO.map((v) => ({ id: v.id, titulo: v.titulo, ruta: rutaDeInicio(v.id) }));
  return (
    <>
      <section aria-label="Vista general" className="silice-espacio-cabecera">
        <p className="silice-espacio-cabecera__titulo">Vista general</p>
      </section>
      <BarraDeEspacio etiqueta="Inicio" pestanas={pestanas} activa={vista} nivel="espacio" />
      {/* F7, A1: la bandeja lleva su «¿Qué es esto?»; la Vista general trae el suyo en la cartera y «Empieza aquí». */}
      {vista === "pendientes" && <AyudaDeLaPantalla pagina="pendientes" />}
      <LimiteDeError key={vista}>
        <Suspense fallback={<EsqueletoPagina />}>{vista === "general" ? general : pendientes}</Suspense>
      </LimiteDeError>
    </>
  );
}
