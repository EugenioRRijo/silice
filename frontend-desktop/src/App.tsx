import { Theme } from "@carbon/react";
import { useState } from "react";
import { HashRouter } from "react-router";
import { CambiarContrasena } from "./sesion/CambiarContrasena";
import { Entrar } from "./sesion/Entrar";
import { useSesion } from "./sesion/useSesion";
import { Cabecera } from "./shell/Cabecera";
import { Shell } from "./shell/Shell";
import { crearAlmacen } from "./visor/almacen";
import type { AlmacenDelVisor } from "./visor/almacen";
import type { CrearHojaVisor } from "./visor/hojaVisor";

// Direccion de la interfaz Streamlit para el enlace de las pantallas aun no migradas. Se fija al compilar
// (VITE_URL_CLASICA); si no se conoce, el menu solo dice «En la interfaz clásica».
const URL_CLASICA_DE_COMPILACION: string | undefined = import.meta.env.VITE_URL_CLASICA;

// El enrutador es de hash (`/app/#/libros`): el servidor de /app es estatico y no devuelve index.html para
// /app/libros al recargar, y asi tampoco hace falta tocarlo cuando la interfaz vaya dentro de Tauri.
interface Props {
  // Solo en pruebas: el visor de hojas (por omision, Univer).
  crearHoja?: CrearHojaVisor;
}

export function App({ crearHoja }: Props = {}) {
  const { estado, entrar, cambiarContrasena, salir, expirar } = useSesion();
  // El libro abierto vive aqui, por encima de la puerta de sesion, solo en memoria: si la sesion vence y entra la
  // MISMA cuenta, reaparece; si entra otra, se descarta (UC-26).
  const [almacenes] = useState(() => new Map<string, AlmacenDelVisor>());
  let almacen: AlmacenDelVisor | undefined;
  if (estado.tipo === "activa") {
    const login = estado.sesion.login;
    almacen = almacenes.get(login);
    if (!almacen) {
      almacenes.clear();
      almacen = crearAlmacen();
      almacenes.set(login, almacen);
    }
  }
  const alSalir = () => {
    almacenes.clear();
    void salir().catch(() => undefined);
  };

  return (
    <Theme theme="g10">
      {estado.tipo === "activa" && !estado.sesion.debe_cambiar_clave ? (
        <HashRouter>
          <Shell
            sesion={estado.sesion}
            alSalir={alSalir}
            alExpirar={expirar}
            urlClasica={estado.sesion.url_clasica ?? URL_CLASICA_DE_COMPILACION}
            almacen={almacen}
            crearHoja={crearHoja}
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
