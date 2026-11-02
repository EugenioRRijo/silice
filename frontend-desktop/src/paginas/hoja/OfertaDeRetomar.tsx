import { Button } from "@carbon/react";
import { useId } from "react";
import { rotuloDeOferta } from "./logicaRetomar";
import type { OfertaDeRetomar } from "./logicaRetomar";

interface Props {
  proyecto: string;
  ofertas: OfertaDeRetomar[];
  alRetomar: (oferta: OfertaDeRetomar) => void;
  // Borra los borradores ofrecidos y abre la versión de nuevo.
  alDescartar: () => void;
  ocupado: boolean;
}

// Borradores con cambios sin guardar que el servidor conserva de una visita anterior (recargar la página o cambiar de menú o
// de proyecto no los pierde). Mientras la persona no decide, no se abre otro borrador encima.
export function OfertaDeRetomar({ proyecto, ofertas, alRetomar, alDescartar, ocupado }: Props) {
  const titulo = useId();
  const varias = ofertas.length > 1;
  return (
    <section className="silice-hoja__retomar" role="group" aria-labelledby={titulo}>
      <h2 id={titulo} className="cds--type-heading-compact-02">
        Retomar borrador
      </h2>
      <p className="cds--type-body-compact-01">
        {varias ? "Quedaron borradores" : "Quedó un borrador"} de este proyecto con cambios sin guardar. Puede seguir donde lo dejó o
        descartarlo y abrir la versión de nuevo.
      </p>
      <div className="silice-hoja__acciones">
        {ofertas.map((o) => (
          <Button key={o.id} kind="primary" size="sm" disabled={ocupado} onClick={() => alRetomar(o)}>
            {rotuloDeOferta(o, proyecto, varias)}
          </Button>
        ))}
        <Button kind="danger--tertiary" size="sm" disabled={ocupado} onClick={alDescartar}>
          {varias ? "Descartar todos y abrir de nuevo" : "Descartar y abrir de nuevo"}
        </Button>
      </div>
    </section>
  );
}
