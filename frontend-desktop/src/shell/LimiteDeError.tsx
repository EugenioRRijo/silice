import { Component } from "react";
import type { ReactNode } from "react";
import { AvisoError } from "../comun/AvisoError";

interface Props {
  children: ReactNode;
  // Cuando cambia, un error se olvida y se vuelve a intentar pintar lo de dentro; sin error no se vuelve a montar nada.
  reinicio?: string;
}

interface Estado {
  error: unknown;
  // El `reinicio` con que se pinto por ultima vez.
  reinicio: string | undefined;
}

// Si una pagina no se puede cargar (el archivo perezoso no llega) o falla al dibujarse, se dice en pantalla en vez
// de dejarla en blanco. El marco le cambia la `key` al navegar, asi que ir a otra pantalla lo reinicia; dentro de una
// obra la `key` es la de la obra (la cabecera y el proveedor de la Hoja no se vuelven a montar al cambiar de seccion) y
// `reinicio` (la ruta) olvida un error al navegar (Tarea 3 del plan F4). EspacioDeObra pone ademas uno por seccion.
export class LimiteDeError extends Component<Props, Estado> {
  state: Estado = { error: null, reinicio: this.props.reinicio };

  static getDerivedStateFromError(error: unknown): Partial<Estado> {
    return { error: error ?? new Error("error") };
  }

  // Antes de pintar con otro `reinicio` se olvida el error: si lo de dentro vuelve a fallar, el error nuevo ya es de este.
  static getDerivedStateFromProps(props: Props, estado: Estado): Partial<Estado> | null {
    return props.reinicio === estado.reinicio ? null : { error: null, reinicio: props.reinicio };
  }

  render() {
    if (this.state.error !== null) {
      return (
        <div className="silice-pagina-aviso">
          <AvisoError
            titulo="No se pudo abrir la pantalla"
            error="La pantalla no cargó. Vuelva a cargar Sílice (F5); si sigue igual, avise a quien administra Sílice."
          />
        </div>
      );
    }
    return this.props.children;
  }
}
