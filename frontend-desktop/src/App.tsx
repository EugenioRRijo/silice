import { Logout } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderName, Theme } from "@carbon/react";
import { useState } from "react";
import { Entrar } from "./sesion/Entrar";
import { useSesion } from "./sesion/useSesion";
import { crearAlmacen } from "./visor/almacen";
import type { AlmacenDelVisor } from "./visor/almacen";
import type { CrearHojaVisor } from "./visor/hojaVisor";
import { Visor } from "./visor/Visor";

interface Props {
  // Para las pruebas: el visor de hojas (por omision, Univer).
  crearHoja?: CrearHojaVisor;
}

export function App({ crearHoja }: Props = {}) {
  const { estado, entrar, salir, expirar } = useSesion();
  // El libro abierto vive aqui, por encima de la puerta de sesion, solo en memoria: si la sesion vence y entra la
  // MISMA cuenta, reaparece; si entra otra, se descarta (UC-26).
  const [almacenes] = useState(() => new Map<string, AlmacenDelVisor>());
  let almacen: AlmacenDelVisor | null = null;
  if (estado.tipo === "activa") {
    const login = estado.sesion.login;
    almacen = almacenes.get(login) ?? null;
    if (!almacen) {
      almacenes.clear();
      almacen = crearAlmacen();
      almacenes.set(login, almacen);
    }
  }

  return (
    <Theme theme="g10">
      <Header aria-label="Sílice">
        <HeaderName href="#" prefix="">
          Sílice
        </HeaderName>
        {estado.tipo === "activa" && (
          <HeaderGlobalBar>
            <span className="silice-usuario cds--type-body-compact-01">{estado.sesion.nombre}</span>
            <button type="button" className="silice-salir cds--type-body-compact-01" onClick={() => {
                almacenes.clear();
                void salir().catch(() => undefined);
              }}>
              <Logout size={16} aria-hidden="true" />
              Salir
            </button>
          </HeaderGlobalBar>
        )}
      </Header>
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
      {estado.tipo === "activa" && almacen && <Visor alExpirar={expirar} almacen={almacen} crearHoja={crearHoja} />}
    </Theme>
  );
}
