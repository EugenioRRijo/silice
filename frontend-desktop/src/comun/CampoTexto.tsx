import { TextInput } from "@carbon/react";
import type { ComponentProps } from "react";
import { useEffect, useRef } from "react";

// El TextInput de Carbon monta siempre un <span role="alert" aria-live> vacío (el anuncio del contador de caracteres),
// aunque no haya contador: con 4 a 8 campos por página el lector de pantalla encuentra otras tantas regiones vivas sin
// contenido (VB-18). Este campo las deja solo si el contador está activo; el resto del comportamiento es el de Carbon.
// `display: contents` mantiene al campo como hijo directo de la rejilla de su formulario.
export function CampoTexto(props: ComponentProps<typeof TextInput>) {
  const raiz = useRef<HTMLDivElement>(null);
  const conContador = props.enableCounter === true;
  useEffect(() => {
    if (conContador) return;
    raiz.current?.querySelectorAll(".cds--text-input__counter-alert").forEach((region) => {
      region.removeAttribute("role");
      region.removeAttribute("aria-live");
      region.removeAttribute("aria-atomic");
    });
  });
  return (
    <div ref={raiz} style={{ display: "contents" }}>
      <TextInput {...props} />
    </div>
  );
}
