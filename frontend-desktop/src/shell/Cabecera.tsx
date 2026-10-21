import { Logout } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderMenuButton, HeaderName } from "@carbon/react";
import type { ReactNode } from "react";
import { TamanoLetra } from "../comun/TamanoLetra";

interface Props {
  nombre?: string;
  alSalir?: () => void;
  // Selectores de caso y de proyecto (solo dentro del shell).
  selectores?: ReactNode;
  // Boton que abre el menu lateral en pantallas angostas; sin el, la cabecera no lo muestra.
  menu?: { abierto: boolean; alternar: () => void };
}

export function Cabecera({ nombre, alSalir, selectores, menu }: Props) {
  return (
    <Header aria-label="Sílice">
      {menu && (
        <HeaderMenuButton
          aria-label={menu.abierto ? "Cerrar el menú" : "Abrir el menú"}
          isActive={menu.abierto}
          onClick={menu.alternar}
          aria-expanded={menu.abierto}
        />
      )}
      <HeaderName href="#/" prefix="">
        Sílice
      </HeaderName>
      <HeaderGlobalBar>
        {nombre && selectores}
        <TamanoLetra />
        {nombre && (
          <>
            <span className="silice-usuario cds--type-body-compact-01">{nombre}</span>
            <button type="button" className="silice-salir cds--type-body-compact-01" onClick={alSalir}>
              <Logout size={16} aria-hidden="true" />
              Salir
            </button>
          </>
        )}
      </HeaderGlobalBar>
    </Header>
  );
}
