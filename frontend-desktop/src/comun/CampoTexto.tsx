import { TextInput } from "@carbon/react";
import type { ComponentProps } from "react";
import { useSinRegionVacia } from "./useSinRegionVacia";

// El TextInput de Carbon monta siempre un <span role="alert" aria-live> vacío (VB-18): este campo lo deja solo si el
// contador está activo (ver useSinRegionVacia); el resto del comportamiento es el de Carbon.
// `display: contents` mantiene al campo como hijo directo de la rejilla de su formulario.
export function CampoTexto(props: ComponentProps<typeof TextInput>) {
  // Con `maxCount` Carbon llena la region aunque no se pida el contador: se conserva.
  const conContador = props.enableCounter === true || props.maxCount !== undefined;
  const raiz = useSinRegionVacia<HTMLDivElement>(".cds--text-input__counter-alert", conContador);
  return (
    <div ref={raiz} style={{ display: "contents" }}>
      <TextInput {...props} />
    </div>
  );
}
