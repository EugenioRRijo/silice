import type { MouseEvent, ReactNode } from "react";
import { Link } from "react-router";
import { esClicSimple, useNavegarSeguro } from "../../shell/navegarSeguro";
import { formulariosSucios } from "../../shell/sucio";

// Un enlace de la ayuda (a una guía, a un término o a una sección de la Cuenta). Vive dentro del lienzo, que el marco no
// intercepta (Marco.alClicAntes): con cambios sin guardar pregunta él mismo antes de irse, como los de `BarraDeEspacio`.
// Sin nada que perder navega solo, así que abrir en otra pestaña y el foco quedan como en cualquier enlace.
export function EnlaceDeAyuda({ a, children }: { a: string; children: ReactNode }) {
  const navegarSeguro = useNavegarSeguro();
  function alPulsar(e: MouseEvent<HTMLAnchorElement>) {
    if (!esClicSimple(e)) return;
    if (formulariosSucios(a).length === 0) return;
    e.preventDefault();
    void navegarSeguro(a);
  }
  return (
    <Link className="cds--link" to={a} onClick={alPulsar}>
      {children}
    </Link>
  );
}
