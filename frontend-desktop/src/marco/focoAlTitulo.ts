// Pasa el foco al h1 de la pantalla (el real, no el de un esqueleto) si se perdió: si lo tiene otro control, no se
// toca. La pantalla se carga a demanda: se espera su h1 unos cuadros (240, unos 4 s). Devuelve cómo dejar de esperar.
// Lo usan el marco al cambiar de pantalla y la obra al reintentar, que quita el botón que tenía el foco.
export function enfocarElTitulo(): () => void {
  let cuadro = 0;
  let intento = 0;
  const buscar = () => {
    const activo = document.activeElement;
    if (activo && activo !== document.body) return;
    const h1 = document.querySelector<HTMLElement>("#contenido h1:not([data-esqueleto])");
    if (h1) {
      h1.tabIndex = -1;
      h1.focus({ preventScroll: true });
      return;
    }
    if (++intento < 240) cuadro = requestAnimationFrame(buscar);
  };
  cuadro = requestAnimationFrame(buscar);
  return () => cancelAnimationFrame(cuadro);
}
