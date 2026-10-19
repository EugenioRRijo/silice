import { Button, SkeletonText } from "@carbon/react";
import { useEffect, useRef } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useCarga } from "../inicio/useCarga";
import { fechaEsVe } from "./logica";

// Una auditoria guardada completa (GET /v1/auditorias-libro/{id}). Los montos llegan como texto decimal exacto y
// se muestran sin pasar por Number; el libro y el PDF no estan: solo su nombre y su huella (RNF-28).
export interface HallazgoGuardado {
  regla: string;
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

// El monto en es-VE a la vista y el exacto en el tooltip y para el lector de pantalla.
function Monto({ exacto }: { exacto: string }) {
  return (
    <span title={`Valor exacto: ${exacto}`} className="silice-cifra">
      {formatoEsVe(exacto)}
      <span className="cds--visually-hidden">{`. Valor exacto: ${exacto}`}</span>
    </span>
  );
}

function Resumen({ a }: { a: AuditoriaDetalleRespuesta }) {
  return (
    <dl className="silice-historial__datos">
      <Dato rotulo="Archivo">{a.archivo}</Dato>
      <Dato rotulo="Tipo">{a.tipo === "pdf" ? "PDF" : "Libro"}</Dato>
      <Dato rotulo="Fecha y hora">{fechaEsVe(a.fecha)}</Dato>
      <Dato rotulo="Realizada por">{a.usuario}</Dato>
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
      <Dato rotulo="Errores">{a.errores}</Dato>
      <Dato rotulo="Advertencias">{a.advertencias}</Dato>
      <Dato rotulo="Informativos">{a.informativos}</Dato>
      <Dato rotulo="Precios atípicos">{a.atipicos}</Dato>
      <Dato rotulo="Huella SHA-256 del archivo">
        <span className="silice-historial__huella">{a.sha256}</span>
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
              { clave: "regla", titulo: "Regla" },
              { clave: "hoja", titulo: "Hoja" },
              { clave: "celda", titulo: "Celda" },
              { clave: "mensaje", titulo: "Qué se encontró" },
            ]}
            filas={carga.datos.hallazgos.map((h, i) => ({ id: String(i), ...h }))}
            vacio={{ titulo: "Esta auditoría no dejó hallazgos guardados" }}
          />
        </>
      )}
    </section>
  );
}
