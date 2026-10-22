import { Theme } from "@carbon/react";
import { useState } from "react";
import { HashRouter } from "react-router";
import { Bienvenida } from "./bienvenida/Bienvenida";
import type { CuerpoDeReclamo } from "./bienvenida/FormularioDeReclamo";
import { RecuperarAcceso } from "./bienvenida/RecuperarAcceso";
import { usePrimerArranque } from "./bienvenida/usePrimerArranque";
import type { ConsultaPrimerArranque } from "./bienvenida/usePrimerArranque";
import { CambiarContrasena } from "./sesion/CambiarContrasena";
import { Entrar } from "./sesion/Entrar";
import { useSesion } from "./sesion/useSesion";
import { Cabecera } from "./shell/Cabecera";
import { Shell } from "./shell/Shell";
import { crearAlmacen } from "./visor/almacen";
import type { AlmacenDelVisor } from "./visor/almacen";
import type { CrearHojaVisor } from "./visor/hojaVisor";

// El enrutador es de hash (`/app/#/libros`): el servidor de /app es estatico y no devuelve index.html para
// /app/libros al recargar, y asi tampoco hace falta tocarlo cuando la interfaz vaya dentro de Tauri.
interface Props {
  // Solo en pruebas: el visor de hojas (por omision, Univer).
  crearHoja?: CrearHojaVisor;
}

export function App({ crearHoja }: Props = {}) {
  const { estado, entrar, reclamar, cambiarContrasena, salir, expirar } = useSesion();
  // Sin sesion se pregunta si la instalacion aun no tiene cuentas; si no tiene, la entrada es la bienvenida (BCP-4). Cualquier
  // fallo de la consulta es «Entrar». Una sesion vencida supone que ya hay cuentas: ahi no se pregunta.
  const [recuperando, setRecuperando] = useState(false);
  const sinSesion = estado.tipo === "sin_sesion";
  const vencida = estado.tipo === "sin_sesion" && estado.expirada;
  const consultada = usePrimerArranque(sinSesion && !vencida);
  const entrada: ConsultaPrimerArranque | null = !sinSesion ? null : vencida ? { tipo: "con_cuentas", info: null } : consultada;
  const reclamarYEntrar = async (cuerpo: CuerpoDeReclamo) => {
    await reclamar(cuerpo);
    setRecuperando(false);
  };
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
            almacen={almacen}
            crearHoja={crearHoja}
          />
        </HashRouter>
      ) : (
        <>
          <Cabecera nombre={estado.tipo === "activa" ? estado.sesion.nombre : undefined} alSalir={alSalir} />
          {(estado.tipo === "cargando" || entrada?.tipo === "cargando") && (
            <main className="silice-entrada">
              <p className="silice-entrada__texto cds--type-body-compact-01" role="status">
                {estado.tipo === "cargando" ? "Comprobando su sesión…" : "Comprobando su instalación…"}
              </p>
            </main>
          )}
          {entrada?.tipo === "sin_cuentas" && <Bienvenida info={entrada.info} onReclamar={reclamarYEntrar} />}
          {entrada?.tipo === "con_cuentas" && !recuperando && (
            <Entrar
              onEntrar={entrar}
              aviso={vencida ? "Su sesión venció. Entre de nuevo para seguir." : undefined}
              alRecuperar={() => setRecuperando(true)}
            />
          )}
          {entrada?.tipo === "con_cuentas" && recuperando && (
            <RecuperarAcceso info={entrada.info} onReclamar={reclamarYEntrar} alVolver={() => setRecuperando(false)} />
          )}
          {estado.tipo === "activa" && <CambiarContrasena alCambiar={cambiarContrasena} />}
        </>
      )}
    </Theme>
  );
}
