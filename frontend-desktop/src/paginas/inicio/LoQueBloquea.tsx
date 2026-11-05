import { WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import { Button, SkeletonText } from "@carbon/react";
import { Link } from "react-router";
import type { PendienteDeObra } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification } from "../../comun/carbonEs";
import { RUTA_DE_PENDIENTES } from "../../marco/secciones";
import { usePendientes } from "../../marco/usePendientes";
import { useAplicacion } from "../../shell/contexto";
import { paginaPorId, usable } from "../../shell/rutas";
import { claveDeObra, contarUrgencias, destinoDelPendiente, paginaQueAbre } from "../pendientes/logica";
import { TEXTOS as TEXTOS_PENDIENTES } from "../pendientes/textos";
import { TEXTOS } from "./textos";

// Cuántos pendientes caben en la Vista general: el resto se ve en la bandeja.
const MAXIMO = 5;

// La carpeta de una obra, solo si otra obra de otra carpeta se llama igual (la misma regla de la barra lateral y la bandeja).
type CarpetaDe = (p: PendienteDeObra) => string | undefined;

// La urgencia en palabras con su ícono (el color nunca va solo): los de error y advertencia de la severidad (DESIGN.md).
function Urgencia({ valor }: { valor: PendienteDeObra["urgencia"] }) {
  const bloquea = valor === "bloquea";
  const Icono = bloquea ? WarningFilled : WarningAltFilled;
  return (
    <span className={`silice-inicio__urgencia silice-sev silice-sev--${bloquea ? "error" : "advertencia"}`}>
      <Icono size={16} className="silice-sev__icono" aria-hidden="true" />
      {TEXTOS_PENDIENTES.urgencias[valor]}
    </span>
  );
}

// El primer bloque de la Vista general (contrato de rutas 4; diseño visual B.2): lo que bloquea, antes que cualquier cifra.
// Los datos son los del marco (`usePendientes`, ya ordenados por la API con lo que bloquea primero y vueltos a pedir cada vez
// que se entra en Inicio). Muestra los primeros cinco; la bandeja tiene el resto y el detalle de cada uno.
export function LoQueBloquea({ carpetaDe }: { carpetaDe: CarpetaDe }) {
  const carga = usePendientes();
  const { sesion, modulosApagados } = useAplicacion();
  const { bloquea, aviso } = contarUrgencias(carga.estado === "listo" ? carga.pendientes : []);
  return (
    <section className="silice-inicio__bloque" aria-labelledby="inicio-bloquea">
      <h2 id="inicio-bloquea" className="cds--type-heading-compact-02">
        {TEXTOS.bloquea.titulo}
      </h2>
      {carga.estado === "cargando" && (
        <div role="status" aria-busy="true" aria-label={TEXTOS.bloquea.cargando}>
          <SkeletonText paragraph lineCount={3} />
        </div>
      )}
      {carga.estado === "error" && (
        <div className="silice-inicio__acciones">
          <AvisoError error={carga.mensaje} titulo={TEXTOS.bloquea.error} />
          <Button kind="tertiary" size="sm" onClick={carga.recargar}>
            {TEXTOS_PENDIENTES.reintentar}
          </Button>
        </div>
      )}
      {carga.estado === "listo" && carga.carpetasOmitidas > 0 && (
        <InlineNotification kind="warning" title={TEXTOS_PENDIENTES.omitidas(carga.carpetasOmitidas)} lowContrast hideCloseButton />
      )}
      {carga.estado === "listo" &&
        (carga.pendientes.length === 0 ? (
          <p className="silice-inicio__nota cds--type-body-compact-01">{TEXTOS.bloquea.ninguno}</p>
        ) : (
          <>
            <p className="cds--type-label-01 silice-inicio__resumen">
              {TEXTOS_PENDIENTES.resumen(bloquea, aviso)}
            </p>
            <ul className="silice-inicio__urgentes" aria-label={TEXTOS.bloquea.lista}>
              {carga.pendientes.slice(0, MAXIMO).map((p, i) => {
                // El paso lleva a la pantalla de la acción; si la cuenta no puede usarla, no se ofrece (la API la rechazaría).
                const pagina = paginaPorId(paginaQueAbre(p));
                const puede = pagina !== undefined && usable(pagina, sesion.acciones, sesion.modo_entrega, modulosApagados);
                const carpeta = carpetaDe(p);
                return (
                  <li key={`${claveDeObra(p.carpeta, p.obra_id)}|${i}`} className="silice-inicio__urgente">
                    <Urgencia valor={p.urgencia} />
                    <span className="silice-inicio__obra cds--type-body-compact-01">
                      {p.obra}
                      {carpeta !== undefined && <span className="silice-inicio__carpeta"> · {carpeta}</span>}
                    </span>
                    <span className="silice-inicio__texto cds--type-body-compact-01">{p.texto}</span>
                    {puede ? (
                      <Link className="cds--link silice-inicio__paso" to={destinoDelPendiente(p)}>
                        {p.accion.texto}
                      </Link>
                    ) : (
                      <span className="silice-inicio__paso cds--type-body-compact-01">{TEXTOS_PENDIENTES.sinPermiso}</span>
                    )}
                  </li>
                );
              })}
            </ul>
            <Link className="cds--link" to={RUTA_DE_PENDIENTES}>
              {TEXTOS.bloquea.irALaBandeja(carga.pendientes.length)}
            </Link>
          </>
        ))}
    </section>
  );
}
