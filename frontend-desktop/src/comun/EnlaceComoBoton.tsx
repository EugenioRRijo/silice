import { Button } from "@carbon/react";
import type { ButtonKind, ButtonSize } from "@carbon/react";
import type { MouseEvent, ReactNode } from "react";
import { Link } from "react-router";
import { esClicSimple, useNavegarSeguro } from "../shell/navegarSeguro";
import { formulariosSucios } from "../shell/sucio";

interface Props {
  to: string;
  kind?: ButtonKind;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
}

// Botón de Carbon que navega como un enlace (`as={Link}`): conserva el clic con Ctrl/Cmd o botón del medio del
// navegador y, si hay cambios sin guardar en la pantalla actual, pregunta antes de salir igual que `BarraDeEspacio`.
export function EnlaceComoBoton({ to, kind = "primary", size = "md", className, children }: Props) {
  const navegarSeguro = useNavegarSeguro();
  function alPulsar(e: MouseEvent<HTMLButtonElement>) {
    if (!esClicSimple(e)) return;
    if (formulariosSucios(to).length === 0) return;
    e.preventDefault();
    void navegarSeguro(to);
  }
  return (
    <Button as={Link} to={to} kind={kind} size={size} className={className} onClick={alPulsar}>
      {children}
    </Button>
  );
}
