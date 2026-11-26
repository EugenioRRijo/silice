import { NOMBRE_DEL_PRODUCTO } from "../comun/tituloDelDocumento";

interface Opciones {
  // Navegación del marco: el foco va al h1 aunque otro control lo tenga (el lector de pantalla anuncia la pantalla
  // nueva) y la ventana pasa a llamarse «<pantalla> · Sílice». Sin esto solo se recupera un foco perdido.
  forzar?: boolean;
}

// Pasa el foco al h1 de la pantalla (el real, no el de un esqueleto). Por omisión solo si se perdió: si lo tiene otro
// control, no se toca. La pantalla se carga a demanda: se espera su h1 unos cuadros (240, unos 4 s). Devuelve cómo dejar
// de esperar. Lo usan el marco al cambiar de pantalla (con `forzar`) y la obra al reintentar, que quita el botón que
// tenía el foco (sin `forzar`).
export function enfocarElTitulo({ forzar = false }: Opciones = {}): () => void {
  let cuadro = 0;
  let intento = 0;
  const buscar = () => {
    if (!forzar) {
      const activo = document.activeElement;
      if (activo && activo !== document.body) return;
    }
    const h1 = document.querySelector<HTMLElement>("#contenido h1:not([data-esqueleto])");
    if (h1) {
      h1.tabIndex = -1;
      h1.focus({ preventScroll: true });
      if (forzar) nombrarLaVentana(h1.textContent?.trim() ?? "");
      return;
    }
    if (++intento < 240) cuadro = requestAnimationFrame(buscar);
  };
  cuadro = requestAnimationFrame(buscar);
  return () => cancelAnimationFrame(cuadro);
}

// El título de la ventana empieza por la pantalla. Si ya lo hace (el del marco suma la obra o el espacio), se deja; sin h1
// con texto queda como estaba.
function nombrarLaVentana(pantalla: string) {
  if (pantalla === "" || document.title.startsWith(pantalla)) return;
  document.title = `${pantalla} · ${NOMBRE_DEL_PRODUCTO}`;
}
