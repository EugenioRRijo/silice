import { Logout } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderMenuButton, HeaderName } from "@carbon/react";
import type { ReactNode } from "react";

interface Props {
  nombre?: string;
  alSalir?: () => void;
  // Selectores de caso y de proyecto (solo dentro del shell).
  selectores?: ReactNode;
  // Boton que abre el menu lateral en pantallas angostas; sin el, la cabecera no lo muestra.
  menu?: { abierto: boolean; alternar: () => void };
  // Punto de montaje para los controles que una pagina pinta en la cabecera con un portal (hoy, los de «Libro de la
  // empresa»). Se llama con el elemento al montar y con null al desmontar.
  ranura?: (elemento: HTMLElement | null) => void;
}

export function Cabecera({ nombre, alSalir, selectores, menu, ranura }: Props) {
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
      {ranura && <div className="silice-cabecera__libro" ref={ranura} />}
      {nombre && (
        <HeaderGlobalBar>
          {selectores}
          <span className="silice-usuario cds--type-body-compact-01">{nombre}</span>
          <button type="button" className="silice-salir cds--type-body-compact-01" onClick={alSalir}>
            <Logout size={16} aria-hidden="true" />
            Salir
          </button>
        </HeaderGlobalBar>
      )}
    </Header>
  );
}
