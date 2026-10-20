import { Select, SelectItem } from "@carbon/react";
import type { CasosRespuesta, ProyectoRespuesta } from "../api/tipos";

interface PropsCaso {
  casos: CasosRespuesta;
  // Sin la accion `cambiar_caso` el selector se ve pero no se puede mover.
  puedeCambiar: boolean;
  ocupado: boolean;
  alElegir: (nombre: string) => void;
}

// El caso es la base de datos en uso (RM-2): la API lo guarda por sesion.
export function SelectorCaso({ casos, puedeCambiar, ocupado, alElegir }: PropsCaso) {
  return (
    <div className="silice-selector">
      <Select
        id="selector-caso"
        labelText="Caso"
        inline
        size="sm"
        value={casos.actual.nombre}
        disabled={!puedeCambiar || ocupado}
        onChange={(e) => alElegir(e.target.value)}
      >
        {casos.casos.map((c) => (
          <SelectItem key={c.ruta_relativa} value={c.nombre} text={c.nombre} />
        ))}
      </Select>
    </div>
  );
}

interface PropsProyecto {
  proyectos: ProyectoRespuesta[];
  // Codigo del elegido, o null.
  elegido: string | null;
  alElegir: (codigo: string | null) => void;
}

// El proyecto elegido vive en el estado de la aplicacion, no en el navegador (RT-9).
// El codigo es un numero interno: se elige por el nombre. Solo si dos se llaman igual, el codigo los distingue.
export function rotuloDeProyecto(p: ProyectoRespuesta, todos: ProyectoRespuesta[]): string {
  return todos.filter((q) => q.nombre === p.nombre).length > 1 ? `${p.nombre} (${p.codigo})` : p.nombre;
}

export function SelectorProyecto({ proyectos, elegido, alElegir }: PropsProyecto) {
  return (
    <div className="silice-selector">
      <Select
        id="selector-proyecto"
        labelText="Proyecto"
        inline
        size="sm"
        value={elegido ?? ""}
        onChange={(e) => alElegir(e.target.value || null)}
      >
        <SelectItem value="" text="Sin proyecto" />
        {proyectos.map((p) => (
          <SelectItem key={p.codigo} value={p.codigo} text={rotuloDeProyecto(p, proyectos)} />
        ))}
      </Select>
    </div>
  );
}
