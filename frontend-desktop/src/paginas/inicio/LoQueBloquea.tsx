import { WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import { Button, SkeletonText, Table, TableBody, TableCell, TableHead, TableRow } from "@carbon/react";
import { Link } from "react-router";
import type { ObraDeLaCartera, PendienteDeObra } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification, TableHeader } from "../../comun/carbonEs";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { rutaOPendientes } from "../../marco/espacios";
import { RUTA_DE_PENDIENTES } from "../../marco/secciones";
import { usePendientes } from "../../marco/usePendientes";
import { claveDeObra, contarUrgencias } from "../pendientes/logica";
import { TEXTOS as TEXTOS_PENDIENTES } from "../pendientes/textos";
import { TEXTOS } from "./textos";

interface FilaProblema {
  clave: string;
  carpeta: string | null;
  obraId: number;
  nombre: string;
  bloquea: number;
  aviso: number;
}

export function ResumenDeGravedad({ bloquea, aviso }: { bloquea: number; aviso: number }) {
  if (bloquea === 0 && aviso === 0) {
    return <span className="silice-inicio__ninguno">{TEXTOS.avance.ningunProblema}</span>;
  }
  return (
    <span className="silice-inicio__gravedades">
      {bloquea > 0 && (
        <span className="silice-inicio__gravedad silice-inicio__gravedad--error">
          <WarningFilled size={16} aria-hidden="true" />
          {bloquea === 1 ? "1 bloquea" : `${formatoEsVe(String(bloquea))} bloquean`}
        </span>
      )}
      {bloquea > 0 && aviso > 0 && <span aria-hidden="true"> · </span>}
      {aviso > 0 && (
        <span className="silice-inicio__gravedad silice-inicio__gravedad--adv">
          <WarningAltFilled size={16} aria-hidden="true" />
          {aviso === 1 ? "1 aviso" : `${formatoEsVe(String(aviso))} avisos`}
        </span>
      )}
    </span>
  );
}

function filasPorObra(obras: readonly ObraDeLaCartera[], pendientes: readonly PendienteDeObra[]): FilaProblema[] {
  const mapa = new Map<string, FilaProblema>();
  for (const o of obras) {
    const clave = claveDeObra(o.carpeta, o.obra_id);
    mapa.set(clave, { clave, carpeta: o.carpeta, obraId: o.obra_id, nombre: o.nombre, bloquea: 0, aviso: 0 });
  }
  for (const p of pendientes) {
    const clave = claveDeObra(p.carpeta, p.obra_id);
    let fila = mapa.get(clave);
    if (!fila) {
      fila = { clave, carpeta: p.carpeta, obraId: p.obra_id, nombre: p.obra, bloquea: 0, aviso: 0 };
      mapa.set(clave, fila);
    }
    fila[p.urgencia] += 1;
  }
  return [...mapa.values()];
}

// «Problemas abiertos por obra» (especificación 00-inicio-resumen.html): agrupa los pendientes de `usePendientes`
// (`GET /v1/obras/pendientes/todas`) por obra y muestra su gravedad siempre con su palabra («bloquea» / «aviso»).
export function LoQueBloquea({
  obras,
  carpetas,
}: {
  obras: readonly ObraDeLaCartera[];
  carpetas: ReadonlyMap<string, string>;
}) {
  const carga = usePendientes();
  const totales = contarUrgencias(carga.estado === "listo" ? carga.pendientes : []);
  const filas = carga.estado === "listo" ? filasPorObra(obras, carga.pendientes) : [];

  return (
    <section className="silice-inicio__seccion silice-inicio__seccion--compacta" aria-labelledby="inicio-bloquea">
      <h2 id="inicio-bloquea" className="silice-inicio__subtitulo-seccion cds--type-heading-compact-02">
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
      {/* Sin pendientes no hay tabla de obras en cero: la frase dice que ninguna tiene problemas. */}
      {carga.estado === "listo" && totales.bloquea + totales.aviso === 0 && (
        <p className="silice-inicio__pie">{TEXTOS.bloquea.ninguno}</p>
      )}
      {carga.estado === "listo" && totales.bloquea + totales.aviso > 0 && filas.length > 0 && (
        <>
          <div className="silice-tabla silice-inicio__marco-compacto">
            <Table size="sm" aria-label={TEXTOS.bloquea.tabla}>
              <TableHead>
                <TableRow>
                  <TableHeader>{TEXTOS.avance.obra}</TableHeader>
                  <TableHeader>{TEXTOS.avance.problemas}</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {filas.map((f) => {
                  const carpeta = carpetas.get(f.clave);
                  return (
                    <TableRow key={f.clave}>
                      <TableCell>
                        <Link className="cds--link" to={rutaOPendientes("obras", { carpeta: f.carpeta, obraId: f.obraId })}>
                          {f.nombre}
                        </Link>
                        {carpeta !== undefined && <span className="silice-inicio__carpeta"> · {carpeta}</span>}
                      </TableCell>
                      <TableCell>
                        <ResumenDeGravedad bloquea={f.bloquea} aviso={f.aviso} />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          {carga.pendientes.length === 0 ? (
            <p className="silice-inicio__pie">{TEXTOS.bloquea.ninguno}</p>
          ) : (
            <p className="silice-inicio__pie">
              {TEXTOS.bloquea.suman(TEXTOS_PENDIENTES.resumen(totales.bloquea, totales.aviso))}{" "}
              <Link className="cds--link" to={RUTA_DE_PENDIENTES}>
                {TEXTOS.bloquea.irALaBandeja(carga.pendientes.length)}
              </Link>
            </p>
          )}
        </>
      )}
    </section>
  );
}
