import { Button, SkeletonText, Tooltip } from "@carbon/react";
import { useEffect, useRef } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { guiaDeRegla, useCatalogoQueHacer } from "../../comun/catalogoQueHacer";
import { QueHacer } from "../../comun/QueHacer";
import { TablaDensa } from "../../comun/TablaDensa";
import type { FilaDensa } from "../../comun/TablaDensa";
import { centesimasEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { useCarga } from "../../comun/useCarga";
import { EnlaceDePersona } from "../../comun/EnlaceDePersona";
import { fechaEsVe } from "./logica";

// Una auditoria guardada completa (GET /v1/auditorias-libro/{id}). Los montos llegan como texto decimal exacto y
// se muestran sin pasar por Number; el libro y el PDF no estan: solo su nombre y su huella (RNF-28).
export interface HallazgoGuardado {
  regla: string;
  nombre_regla?: string;
  hoja: string;
  celda: string;
  severidad: string;
  mensaje: string;
}

export interface AuditoriaDetalleRespuesta {
  id: number;
  archivo: string;
  fecha: string;
  tipo: "libro" | "pdf";
  errores: number;
  advertencias: number;
  usuario: string;
  sha256: string;
  fecha_libro: string | null;
  total_libro: string | null;
  total_silice: string | null;
  informativos: number;
  atipicos: number;
  recortado: boolean;
  hallazgos: HallazgoGuardado[];
}

function Dato({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="cds--type-label-01">{rotulo}</dt>
      <dd className="cds--type-body-compact-01">{children}</dd>
    </div>
  );
}

// El mismo indicador que el Libro (VB-7): el monto en centesimas y es-VE a la vista, y el exacto (es-VE, sin
// redondear) en un Tooltip de Carbon que se abre con el foco del teclado y con el raton; es la descripcion
// accesible del valor.
function Monto({ exacto }: { exacto: string }) {
  return (
    <Tooltip align="bottom-start" description={`Valor exacto: ${formatoEsVe(exacto)}`} className="silice-historial__monto">
      <button type="button" className="silice-historial__monto-valor silice-cifra">
        {centesimasEsVe(exacto)}
      </button>
    </Tooltip>
  );
}

function Resumen({ a }: { a: AuditoriaDetalleRespuesta }) {
  return (
    <dl className="silice-historial__datos">
      <Dato rotulo="Archivo">{a.archivo}</Dato>
      <Dato rotulo="Tipo">{a.tipo === "pdf" ? "PDF" : "Libro"}</Dato>
      <Dato rotulo="Fecha y hora">{fechaEsVe(a.fecha)}</Dato>
      <Dato rotulo="Realizada por">
        <EnlaceDePersona dato={a.usuario} />
      </Dato>
      {a.fecha_libro !== null && <Dato rotulo="Fecha del libro">{fechaEsVe(a.fecha_libro)}</Dato>}
      {a.total_libro !== null && (
        <Dato rotulo="Total del libro">
          <Monto exacto={a.total_libro} />
        </Dato>
      )}
      {a.total_silice !== null && (
        <Dato rotulo="Total según Sílice">
          <Monto exacto={a.total_silice} />
        </Dato>
      )}
      <Dato rotulo="Errores">{formatoEsVe(String(a.errores))}</Dato>
      <Dato rotulo="Advertencias">{formatoEsVe(String(a.advertencias))}</Dato>
      <Dato rotulo="Informativos">{formatoEsVe(String(a.informativos))}</Dato>
      <Dato rotulo="Precios atípicos">{formatoEsVe(String(a.atipicos))}</Dato>
      <Dato rotulo="Código de verificación del archivo (SHA-256)">
        <span className="silice-historial__huella">{a.sha256}</span>
        <p className="cds--type-label-01">Sirve para comprobar que corresponde al mismo archivo original</p>
      </Dato>
    </dl>
  );
}

interface Props {
  id: number;
  alExpirar: () => void;
  alCerrar: () => void;
}

export function Detalle({ id, alExpirar, alCerrar }: Props) {
  const carga = useCarga<AuditoriaDetalleRespuesta>(`/v1/auditorias-libro/${id}`, alExpirar);
  // El «Qué hacer» de cada hallazgo (B2): el mismo catálogo del servidor que usa «Auditar un libro». Solo se pide si hay
  // hallazgos guardados; sin él el detalle se ve igual.
  const catalogo = useCatalogoQueHacer(alExpirar, carga.estado === "listo" && carga.datos.hallazgos.length > 0);
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titulo.current?.focus(); // el teclado y el lector de pantalla caen en el detalle recien abierto
  }, []);

  return (
    <section className="silice-historial__detalle" aria-labelledby="historial-detalle-titulo">
      <div className="silice-historial__encabezado">
        <h2 id="historial-detalle-titulo" ref={titulo} tabIndex={-1} className="cds--type-heading-compact-02">
          Detalle de la auditoría
        </h2>
        <Button kind="ghost" size="sm" onClick={alCerrar}>
          Cerrar el detalle
        </Button>
      </div>
      {carga.estado === "cargando" && (
        <div role="status" aria-busy="true" aria-label="Cargando el detalle de la auditoría">
          <SkeletonText paragraph lineCount={3} />
        </div>
      )}
      {(carga.estado === "error" || carga.estado === "sin_permiso" || carga.estado === "no_disponible") && (
        <AvisoError error={carga.error} titulo="No se pudo leer la auditoría" />
      )}
      {carga.estado === "listo" && (
        <>
          <Resumen a={carga.datos} />
          {carga.datos.recortado && (
            <p className="cds--type-body-compact-01">
              {`Solo se guardaron los primeros ${carga.datos.hallazgos.length} hallazgos de esta auditoría; los conteos de arriba incluyen todos.`}
            </p>
          )}
          <TablaDensa
            etiqueta="Hallazgos guardados"
            columnas={[
              { clave: "severidad", titulo: "Severidad", celda: "severidad" },
              { clave: "regla", titulo: "Qué revisó Sílice" },
              { clave: "hoja", titulo: "Hoja" },
              { clave: "celda", titulo: "Celda" },
              { clave: "mensaje", titulo: "Qué se encontró" },
              ...(catalogo
                ? [
                    {
                      clave: "queHacer",
                      titulo: "Qué hacer",
                      ordenable: false,
                      celda: (fila: FilaDensa) => <QueHacer guia={guiaDeRegla(catalogo, fila["codigo"] ?? "")} />,
                    },
                  ]
                : []),
            ]}
            filas={carga.datos.hallazgos.map((h, i) => ({
              id: String(i),
              codigo: h.regla,
              severidad: h.severidad,
              regla: h.nombre_regla ? `${h.nombre_regla} (${h.regla})` : h.regla,
              hoja: h.hoja,
              celda: h.celda,
              mensaje: h.mensaje,
            }))}
            vacio={{ titulo: "Esta auditoría no dejó hallazgos guardados" }}
          />
        </>
      )}
    </section>
  );
}
