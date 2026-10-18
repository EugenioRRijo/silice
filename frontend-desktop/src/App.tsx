import { Logout } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderName, Theme } from "@carbon/react";
import { Entrar } from "./sesion/Entrar";
import { useSesion } from "./sesion/useSesion";
import { Visor } from "./visor/Visor";

export function App() {
  const { estado, entrar, salir, expirar } = useSesion();

  return (
    <Theme theme="g10">
      <Header aria-label="Sílice">
        <HeaderName href="#" prefix="">
          Sílice
        </HeaderName>
        {estado.tipo === "activa" && (
          <HeaderGlobalBar>
            <span className="silice-usuario cds--type-body-compact-01">{estado.sesion.nombre}</span>
            <button type="button" className="silice-salir cds--type-body-compact-01" onClick={() => void salir().catch(() => undefined)}>
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
      {estado.tipo === "activa" && <Visor alExpirar={expirar} />}
    </Theme>
  );
}
