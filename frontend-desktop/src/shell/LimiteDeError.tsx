import { Component } from "react";
import type { ReactNode } from "react";
import { AvisoError } from "../comun/AvisoError";

interface Props {
  children: ReactNode;
}

interface Estado {
  error: unknown;
}

// Si una pagina no se puede cargar (el archivo perezoso no llega) o falla al dibujarse, se dice en pantalla en vez
// de dejarla en blanco. El Shell le cambia la `key` al navegar, asi que ir a otra pagina lo reinicia.
export class LimiteDeError extends Component<Props, Estado> {
  state: Estado = { error: null };

  static getDerivedStateFromError(error: unknown): Estado {
    return { error: error ?? new Error("error") };
  }

  render() {
    if (this.state.error !== null) {
      return (
        <div className="silice-pagina-aviso">
          <AvisoError
            titulo="No se pudo abrir la pantalla"
            error="La pantalla no cargó. Recargue la página; si sigue igual, avise a quien administra Sílice."
          />
        </div>
      );
    }
    return this.props.children;
  }
}
