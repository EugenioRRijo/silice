import { Button } from "@carbon/react";
import { PanelRecorrido } from "./PanelRecorrido";
import type { PaginaDef } from "./rutas";
import { mostrarColumna, ocultarColumna, useColumnaOculta, useRecorrido } from "./recorrido";
import "./ColumnaRecorrido.scss";

interface Props {
  paginas: readonly PaginaDef[];
  acciones: readonly string[];
  modoEntrega: boolean;
}

// Columna acoplada a la derecha del contenido (spec de la barra superior, §5.5): mientras haya un recorrido en curso
// y no este plegada, el contenido cede 16 rem (la clase `silice-con-recorrido` la pone el armazon) y los pasos quedan
// junto a la pantalla. No es una capa: no se cierra con clic fuera ni al abrir un panel de area.
export function ColumnaRecorrido({ paginas, acciones, modoEntrega }: Props) {
  const recorrido = useRecorrido();
  const oculta = useColumnaOculta();
  if (!recorrido || oculta) return null;
  return (
    <aside className="silice-columna-recorrido" aria-label="Recorrido">
      <div className="silice-columna-recorrido__acciones">
        <Button kind="ghost" size="sm" onClick={ocultarColumna}>
          Ocultar
        </Button>
      </div>
      <PanelRecorrido paginas={paginas} acciones={acciones} modoEntrega={modoEntrega} enColumna />
    </aside>
  );
}

// Para la barra: visible solo con un recorrido en curso y la columna plegada; la vuelve a mostrar.
export function BotonRecorrido() {
  const recorrido = useRecorrido();
  const oculta = useColumnaOculta();
  if (!recorrido || !oculta) return null;
  return (
    <Button kind="ghost" size="sm" onClick={mostrarColumna}>
      Recorrido
    </Button>
  );
}
