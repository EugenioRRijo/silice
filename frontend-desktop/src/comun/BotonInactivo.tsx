import { Button, Popover, PopoverContent } from "@carbon/react";
import { useEffect, useId, useRef, useState } from "react";
import type { ComponentProps, FocusEvent, JSX, KeyboardEvent, MouseEvent as EventoRaton, ReactNode } from "react";

type PropiedadesBoton = ComponentProps<typeof Button>;

export interface PropsBotonInactivo {
  motivo: string;
  children: ReactNode;
  kind?: PropiedadesBoton["kind"];
  size?: PropiedadesBoton["size"];
  className?: string;
  renderIcon?: PropiedadesBoton["renderIcon"];
  iconDescription?: string;
}

// Acción que no se puede ejecutar todavía (especificación «Papel y resaltador», sección Botones): no usa el atributo
// HTML `disabled` para no expulsar el control del orden de tabulación ni dejar a la persona sin saber qué falta.
// Al pulsarlo o activarlo con Intro o Espacio muestra y anuncia el motivo en un globo anclado.
export function BotonInactivo({
  motivo,
  children,
  kind = "primary",
  size,
  className,
  renderIcon,
  iconDescription,
}: PropsBotonInactivo): JSX.Element {
  const [abierto, setAbierto] = useState(false);
  const idGlobo = useId();
  const envoltorio = useRef<HTMLSpanElement>(null);
  const boton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!abierto) return;
    function alPulsarFuera(evento: MouseEvent) {
      if (envoltorio.current && evento.target instanceof Node && !envoltorio.current.contains(evento.target)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", alPulsarFuera);
    return () => document.removeEventListener("mousedown", alPulsarFuera);
  }, [abierto]);

  function alternar() {
    setAbierto((previo) => !previo);
  }

  function alHacerClic(evento: EventoRaton<HTMLButtonElement>) {
    evento.preventDefault();
    alternar();
  }

  function alTeclearEnvoltorio(evento: KeyboardEvent<HTMLSpanElement>) {
    if (evento.key === "Escape" && abierto) {
      evento.stopPropagation();
      setAbierto(false);
      boton.current?.focus();
    }
  }

  function alTeclearBoton(evento: KeyboardEvent<HTMLButtonElement>) {
    if (evento.key === "Enter" || evento.key === " ") {
      evento.preventDefault();
      alternar();
    }
  }

  function alPerderFoco(evento: FocusEvent<HTMLSpanElement>) {
    if (abierto && evento.relatedTarget instanceof Node && !evento.currentTarget.contains(evento.relatedTarget)) {
      setAbierto(false);
    }
  }

  return (
    <Popover
      open={abierto}
      align="bottom-start"
      ref={envoltorio}
      onKeyDown={alTeclearEnvoltorio}
      onBlur={alPerderFoco}
      className="silice-boton-inactivo"
    >
      <Button
        ref={boton}
        type="button"
        kind={kind}
        size={size}
        className={className}
        renderIcon={renderIcon}
        iconDescription={iconDescription}
        aria-disabled="true"
        aria-expanded={abierto}
        aria-controls={abierto ? idGlobo : undefined}
        aria-describedby={abierto ? idGlobo : undefined}
        onClick={alHacerClic}
        onKeyDown={alTeclearBoton}
      >
        {children}
      </Button>
      <PopoverContent id={idGlobo} className="silice-boton-inactivo__globo">
        <span role="status" aria-live="polite">
          {abierto ? motivo : null}
        </span>
      </PopoverContent>
    </Popover>
  );
}
