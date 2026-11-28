import { Header, HeaderGlobalBar, HeaderName } from "@carbon/react";
import { MenuCuenta } from "../shell/MenuCuenta";

// Cabecera de las pantallas sin el marco (entrar, bienvenida, recuperar, cambio de contrasena obligatorio): «Sílice» y, con
// una sesión provisional, su cuenta para poder salir. El tamaño de letra vive solo en Cuenta › Configuración
// (Eugenio, 2026-11-22). Sin navegacion: todavia no hay pantallas a las que ir.
//
// El sello y la palabra van dentro de `.silice-sin-marco__marca`, que lleva el gap: HeaderName de Carbon envuelve su
// contenido en un único `<span>`, así que un `gap` en `.cds--header__name` separaba ese span de nada y el sello quedaba
// a 2 px de «Sílice» (T3, 2026-11-28).
export function CabeceraSinMarco({ nombre, alSalir }: { nombre?: string; alSalir: () => void }) {
  return (
    <Header aria-label="Sílice" className="silice-marco-barra silice-sin-marco">
      <HeaderName href="#/" prefix="">
        <span className="silice-sin-marco__marca">
          <span className="silice-sin-marco__sello" aria-hidden="true">
            S
          </span>
          <span>Sílice</span>
        </span>
      </HeaderName>
      <HeaderGlobalBar>{nombre && <MenuCuenta nombre={nombre} alSalir={alSalir} />}</HeaderGlobalBar>
    </Header>
  );
}
