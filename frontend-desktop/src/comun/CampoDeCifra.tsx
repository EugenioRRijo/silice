import { useEffect, useRef, useState } from "react";
import type { FocusEventHandler, ReactNode, Ref } from "react";
import { MENSAJE_CIFRA, MENSAJE_CIFRA_VACIA, leerCifra } from "../indicadores/cifraEscrita";
import { useAnunciar } from "./Anunciador";
import { CampoTexto } from "./CampoTexto";

export interface CampoDeCifraProps {
  id: string;
  labelText: ReactNode;
  value: string;
  onChange: (texto: string) => void;
  onValor?: (decimal: string | null) => void;
  obligatorio?: boolean;
  helperText?: ReactNode;
  validar?: (decimal: string) => string | null;
  mostrarError?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
  hideLabel?: boolean;
  size?: "xs" | "sm" | "md" | "lg";
  placeholder?: string;
  onBlur?: FocusEventHandler<HTMLInputElement>;
  ref?: Ref<HTMLInputElement>;
}

function evaluarCifra(
  texto: string,
  obligatorio: boolean,
  validar?: (decimal: string) => string | null,
): { decimal: string | null; error: string | null } {
  const lectura = leerCifra(texto);
  if ("error" in lectura) {
    if (lectura.error === MENSAJE_CIFRA_VACIA) {
      return { decimal: null, error: obligatorio ? MENSAJE_CIFRA_VACIA : null };
    }
    return { decimal: null, error: MENSAJE_CIFRA };
  }
  const errorDeRegla = validar ? validar(lectura.valor) : null;
  if (errorDeRegla !== null && errorDeRegla !== "") {
    return { decimal: null, error: errorDeRegla };
  }
  return { decimal: lectura.valor, error: null };
}

// Espera antes de anunciar el error al salir, para no pisar la lectura del campo que recibe el foco.
const ESPERA_DEL_ANUNCIO_MS = 500;

// Campo numérico en formato es-VE (coma decimal y punto de miles) que valida al salir después de haber escrito o cuando
// el formulario activa `mostrarError`, nunca mientras la persona escribe por primera vez. Mantiene `aria-invalid="false"`
// hasta que se muestre un error y se apoya en `CampoTexto` para conservar la corrección de la región viva vacía (VB-18).
export function CampoDeCifra({
  id,
  labelText,
  value,
  onChange,
  onValor,
  obligatorio = false,
  helperText,
  validar,
  mostrarError = false,
  disabled = false,
  readOnly = false,
  hideLabel,
  size,
  placeholder,
  onBlur,
  ref,
}: CampoDeCifraProps) {
  const [edicion, setEdicion] = useState<{ valor: string; salio: boolean } | null>(null);
  const anunciar = useAnunciar();
  const ultimoAnunciado = useRef<string | null>(null);
  const relojDelAnuncio = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelarAnuncio = () => {
    if (relojDelAnuncio.current !== null) {
      clearTimeout(relojDelAnuncio.current);
      relojDelAnuncio.current = null;
    }
  };
  useEffect(() => cancelarAnuncio, []);

  const { error } = evaluarCifra(value, obligatorio, validar);
  const validadoAlSalir = edicion !== null && edicion.valor === value && edicion.salio;
  const errorVisible = !disabled && !readOnly && (validadoAlSalir || mostrarError) ? error : null;
  const invalido = errorVisible !== null;
  const hayAyuda = helperText !== undefined && helperText !== null && helperText !== "";
  const ariaDescribedBy = invalido ? `${id}-error-msg` : hayAyuda ? `${id}-helper-text` : undefined;

  return (
    <CampoTexto
      id={id}
      ref={ref}
      labelText={labelText}
      helperText={helperText}
      value={value}
      inputMode="decimal"
      aria-required={obligatorio ? "true" : undefined}
      aria-invalid={invalido ? "true" : "false"}
      aria-describedby={ariaDescribedBy}
      invalid={invalido}
      invalidText={errorVisible ?? undefined}
      disabled={disabled}
      readOnly={readOnly}
      hideLabel={hideLabel}
      size={size}
      placeholder={placeholder}
      onChange={(evento) => {
        const nuevo = evento.target.value;
        cancelarAnuncio();
        setEdicion((antes) => ({
          valor: nuevo,
          salio: antes !== null && antes.valor === value && antes.salio,
        }));
        onChange(nuevo);
        const { decimal } = evaluarCifra(nuevo, obligatorio, validar);
        onValor?.(decimal);
      }}
      onBlur={(evento) => {
        setEdicion((antes) => (antes !== null ? { valor: antes.valor, salio: true } : null));
        // Un error que aparece al salir se anuncia una vez, por la región cortés de la página y un momento después.
        const editado = edicion !== null && edicion.valor === value;
        if (error === null || disabled || readOnly) {
          ultimoAnunciado.current = null;
        } else if (editado && error !== ultimoAnunciado.current) {
          ultimoAnunciado.current = error;
          cancelarAnuncio();
          const mensaje = typeof labelText === "string" ? `${labelText}: ${error}` : error;
          relojDelAnuncio.current = setTimeout(() => {
            relojDelAnuncio.current = null;
            anunciar(mensaje);
          }, ESPERA_DEL_ANUNCIO_MS);
        }
        onBlur?.(evento);
      }}
    />
  );
}
