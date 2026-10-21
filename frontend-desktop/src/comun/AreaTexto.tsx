import { TextArea } from "@carbon/react";
import type { ComponentProps } from "react";
import { useSinRegionVacia } from "./useSinRegionVacia";

// Igual que CampoTexto (comun/) pero para el TextArea de Carbon, que tambien monta un <span role="alert"> vacio
// (`cds--text-area__counter-alert`) aunque no haya contador (VD-6). Se conserva solo si el contador esta activo.
export function AreaTexto(props: ComponentProps<typeof TextArea>) {
  const conContador = props.enableCounter === true || props.maxCount !== undefined;
  const raiz = useSinRegionVacia<HTMLDivElement>(".cds--text-area__counter-alert", conContador);
  return (
    <div ref={raiz} style={{ display: "contents" }}>
      <TextArea {...props} />
    </div>
  );
}
