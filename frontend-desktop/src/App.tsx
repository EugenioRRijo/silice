import { Theme } from "@carbon/react";
import { HashRouter } from "react-router";
import { CambiarContrasena } from "./sesion/CambiarContrasena";
import { Entrar } from "./sesion/Entrar";
import { useSesion } from "./sesion/useSesion";
import { Cabecera } from "./shell/Cabecera";
import { Shell } from "./shell/Shell";

// Direccion de la interfaz Streamlit para el enlace de las pantallas aun no migradas. Se fija al compilar
// (VITE_URL_CLASICA); si no se conoce, el menu solo dice «En la interfaz clásica».
const URL_CLASICA_DE_COMPILACION: string | undefined = import.meta.env.VITE_URL_CLASICA;

// El enrutador es de hash (`/app/#/libros`): el servidor de /app es estatico y no devuelve index.html para
// /app/libros al recargar, y asi tampoco hace falta tocarlo cuando la interfaz vaya dentro de Tauri.
export function App() {
  const { estado, entrar, cambiarContrasena, salir, expirar } = useSesion();
  const alSalir = () => void salir().catch(() => undefined);

  return (
    <Theme theme="g10">
      {estado.tipo === "activa" && !estado.sesion.debe_cambiar_clave ? (
        <HashRouter>
          <Shell
            sesion={estado.sesion}
            alSalir={alSalir}
            alExpirar={expirar}
            urlClasica={estado.sesion.url_clasica ?? URL_CLASICA_DE_COMPILACION}
          />
        </HashRouter>
      ) : (
        <>
          <Cabecera nombre={estado.tipo === "activa" ? estado.sesion.nombre : undefined} alSalir={alSalir} />
          {estado.tipo === "cargando" && (
            <main className="silice-entrada">
              <p className="silice-entrada__texto cds--type-body-compact-01" role="status">
                Comprobando su sesión…
              </p>
            </main>
          )}
          {estado.tipo === "sin_sesion" && (
            <Entrar
              onEntrar={entrar}
              aviso={estado.expirada ? "Su sesión venció. Entre de nuevo para seguir." : undefined}
            />
          )}
          {estado.tipo === "activa" && <CambiarContrasena alCambiar={cambiarContrasena} />}
        </>
      )}
    </Theme>
  );
}
