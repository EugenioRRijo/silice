import { useState } from "react";
import { TAMANOS_DE_LETRA, aplicarTamanoLetra, guardarTamanoLetra, leerTamanoLetra } from "./preferenciaDeLetra";
import type { TamanoDeLetra } from "./preferenciaDeLetra";

// «Tamaño de letra» en la cabecera: tres botones con una A cada vez más grande. Es un grupo de botones de dos estados
// (aria-pressed), así que Tab los recorre y Enter o Espacio eligen. El elegido se distingue por una raya inferior y el
// fondo, no solo por el color. Elegir aplica la variable de la raíz y lo recuerda; mostrar el control no escribe nada.
export function TamanoLetra() {
  const [tamano, setTamano] = useState<TamanoDeLetra>(leerTamanoLetra);

  function elegir(nuevo: TamanoDeLetra) {
    setTamano(nuevo);
    aplicarTamanoLetra(nuevo);
    guardarTamanoLetra(nuevo);
  }

  return (
    <div role="group" aria-label="Tamaño de letra" className="silice-letra">
      {TAMANOS_DE_LETRA.map((t) => (
        <button
          key={t.valor}
          type="button"
          className={`silice-letra__opcion silice-letra__opcion--${t.valor}`}
          aria-pressed={tamano === t.valor}
          aria-label={t.rotulo}
          title={t.rotulo}
          onClick={() => elegir(t.valor)}
        >
          <span aria-hidden="true">A</span>
        </button>
      ))}
    </div>
  );
}
