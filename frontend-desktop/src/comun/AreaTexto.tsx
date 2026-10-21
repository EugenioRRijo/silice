import { TextArea } from "@carbon/react";
import type { ComponentProps } from "react";
import { useEffect, useRef } from "react";

// Igual que CampoTexto (comun/) pero para el TextArea de Carbon, que tambien monta un <span role="alert"> vacio
// (`cds--text-area__counter-alert`) aunque no haya contador (VD-6). Se conserva solo si el contador esta activo.
export function AreaTexto(props: ComponentProps<typeof TextArea>) {
  const raiz = useRef<HTMLDivElement>(null);
  const conContador = props.enableCounter === true || props.maxCount !== undefined;
  useEffect(() => {
    if (conContador) return;
    raiz.current?.querySelectorAll(".cds--text-area__counter-alert").forEach((region) => {
      region.removeAttribute("role");
      region.removeAttribute("aria-live");
      region.removeAttribute("aria-atomic");
    });
  });
  return (
    <div ref={raiz} style={{ display: "contents" }}>
      <TextArea {...props} />
    </div>
  );
}
