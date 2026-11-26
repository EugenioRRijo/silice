import { useContext } from "react";
import { matchPath, useLocation } from "react-router";
import { ContextoDeLaHoja } from "../paginas/hoja/ProveedorDeLaHoja";
import type { HojaDeLaObra } from "../paginas/hoja/ProveedorDeLaHoja";
import { ContextoAplicacion } from "../shell/contexto";
import { ListaDeLaCarpeta } from "../shell/ListaDeLaCarpeta";
import { BarraDeObra } from "./BarraDeObra";
import { EtapaDeObra } from "./EtapaDeObra";
import { useOferta } from "./oferta";
import { PATRON_DE_OBRA, seccionPorId } from "./secciones";
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
  const { pathname } = useLocation();
  const { oferta } = useOferta();
  // Dónde está la persona (sección y subvista), de la propia ruta: la cabecera no cambia sus props. Sin sesión (una
  // cabecera suelta) se ofrecen todas las secciones; con ella, solo las que la cuenta puede usar.
  const enLaRuta = matchPath(PATRON_DE_OBRA, pathname)?.params;
  const seccion = seccionPorId(enLaRuta?.seccion ?? "")?.id ?? "resumen";
  const usables = base?.sesion ? oferta.secciones.map((s) => s.id) : undefined;
  // La moneda de la obra la da el servidor en su ficha: undefined mientras carga, null si no hay dato.
  const monedaDeLaObra = ficha.estado === "lista" ? ficha.obra.moneda : ficha.estado === "sin_dato" ? null : undefined;
  return (
    <section aria-label="Obra abierta" className="silice-obra-abierta">
      <BarraDeObra
        carpeta={carpeta}
        obraId={obraId}
        nombre={nombre ?? `Obra ${obraId}`}
        seccion={seccion}
        subvista={enLaRuta?.subvista}
        usables={usables}
      />
      <ul className="silice-obra-abierta__datos">
        {ficha.estado === "lista" && (
          <li>
            Estado: <EtapaDeObra etapa={ficha.obra.etapa} texto={ficha.obra.etapa_texto} />
          </li>
        )}
        <li>{lineaDeVersion(version, hoja)}</li>
      </ul>
      {base && <ListaDeLaCarpeta key={carpeta ?? ""} alExpirar={base.alExpirar} monedaDeLaObra={monedaDeLaObra} />}
    </section>
  );
}
