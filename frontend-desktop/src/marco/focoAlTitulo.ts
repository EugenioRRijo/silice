import { NOMBRE_DEL_PRODUCTO } from "../comun/tituloDelDocumento";

interface Opciones {
  // Navegación del marco: el foco va al h1 aunque otro control lo tenga (el lector de pantalla anuncia la pantalla
  // nueva). Si la pantalla nueva ya puso el foco en algo de su propio contenido (un campo que enfoca al montarse), se
  // respeta: gana quien llegó primero. Sin esto solo se recupera un foco perdido.
  forzar?: boolean;
  // Se llama con el h1 cuando recibe el foco. El título de la ventana NO se pone aquí: lo da el marco (`ubicar`), que
  // conoce la obra; solo el caso de una ruta que el marco no nombra usa el h1 (`nombrarLaVentana`).
  alEnfocar?: (h1: HTMLElement) => void;
}

// Pasa el foco al h1 de la pantalla (el real, no el de un esqueleto). Por omisión solo si se perdió: si lo tiene otro
// control, no se toca. La pantalla se carga a demanda: se espera su h1 unos cuadros (240, unos 4 s). Devuelve cómo dejar
// de esperar. Lo usan el marco al cambiar de pantalla (con `forzar`) y la obra al reintentar, que quita el botón que
// tenía el foco (sin `forzar`).
export function enfocarElTitulo({ forzar = false, alEnfocar }: Opciones = {}): () => void {
  let cuadro = 0;
  let intento = 0;
  const buscar = () => {
    const activo = document.activeElement;
    if (forzar) {
      // Lo que ya tiene el foco dentro del contenido nuevo (no el h1 de antes: el contenido viejo ya se desmontó) se respeta.
      if (activo?.closest("#contenido")) return;
    } else if (activo && activo !== document.body) return;
    const h1 = document.querySelector<HTMLElement>("#contenido h1:not([data-esqueleto])");
    if (h1) {
      h1.tabIndex = -1;
      h1.focus({ preventScroll: true });
      alEnfocar?.(h1);
      return;
    }
    if (++intento < 240) cuadro = requestAnimationFrame(buscar);
  };
  cuadro = requestAnimationFrame(buscar);
  return () => cancelAnimationFrame(cuadro);
}

// El título de la ventana empieza por la pantalla. Si ya lo hace, se deja; sin texto queda como estaba.
export function nombrarLaVentana(pantalla: string) {
  if (pantalla === "" || document.title.startsWith(pantalla)) return;
  document.title = `${pantalla} · ${NOMBRE_DEL_PRODUCTO}`;
}
