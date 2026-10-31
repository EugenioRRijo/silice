import { useContext } from "react";
import { ContextoDeLaHoja } from "../paginas/hoja/ProveedorDeLaHoja";
import type { HojaDeLaObra } from "../paginas/hoja/ProveedorDeLaHoja";
import { ContextoAplicacion } from "../shell/contexto";
import { ListaDeLaCarpeta } from "../shell/ListaDeLaCarpeta";
import { EtapaDeObra } from "./EtapaDeObra";
import type { FichaDeLaObra } from "./useFichaDeLaObra";

interface Props {
  carpeta: string | null;
  obraId: number;
  // El nombre y la versión vigente, de la lista de obras (`useObras`); undefined mientras no está en la lista.
  nombre: string | undefined;
  version: string | null | undefined;
  ficha: FichaDeLaObra;
}

// La línea de la versión. Dentro de las secciones con Hoja (Tarea 3 del plan F4), si el borrador abierto sale de otra
// versión que la vigente, se dice cuál está abierta y cuál es la vigente (foco 5): las dos las da el borrador
// (`base.version` y `base.vigente`), que es lo que la persona edita. Si no, la vigente de la lista de obras, como antes.
function lineaDeVersion(version: string | null | undefined, hoja: HojaDeLaObra | null): string {
  const base = hoja?.estado.estado === "listo" ? hoja.estado.borrador.base : null;
  if (base !== null && base.version !== null && base.vigente !== null && base.version !== base.vigente) {
    return `Versión abierta: ${base.version} (la vigente es ${base.vigente})`;
  }
  return `Versión: ${version ?? "sin versión guardada"}`;
}

// La cabecera de la obra abierta (Tarea 1 del plan F4; antes `ObraAbierta` dentro de EspacioDeObra): su nombre, el estado
// en palabras con su ícono (solo con la ficha lista; sin permiso o sin fila no se dice nada) y la versión, y debajo la
// moneda y la lista de su carpeta. No es un encabezado: el h1 es el de la sección, que es lo que la persona vino a hacer.
export function CabeceraDeObra({ carpeta, obraId, nombre, version, ficha }: Props) {
  const base = useContext(ContextoAplicacion);
  const hoja = useContext(ContextoDeLaHoja);
  return (
    <section aria-label="Obra abierta" className="silice-obra-abierta">
      <p className="silice-obra-abierta__nombre">{nombre ?? `Obra ${obraId}`}</p>
      <ul className="silice-obra-abierta__datos">
        {ficha.estado === "lista" && (
          <li>
            Estado: <EtapaDeObra etapa={ficha.obra.etapa} texto={ficha.obra.etapa_texto} />
          </li>
        )}
        <li>{lineaDeVersion(version, hoja)}</li>
      </ul>
      {base && <ListaDeLaCarpeta key={carpeta ?? ""} alExpirar={base.alExpirar} />}
    </section>
  );
}
