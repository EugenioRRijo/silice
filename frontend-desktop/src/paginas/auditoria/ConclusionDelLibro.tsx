import { CheckmarkFilled, WarningFilled } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import type { JSX } from "react";
import { Link } from "react-router";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification } from "../../comun/carbonEs";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { FranjaIndicadores } from "../../indicadores/FranjaIndicadores";
import { rutaOPendientes } from "../../marco/espacios";
import { EXPLICACION_DEL_PDF } from "../../visor/Visor";
import { cuerpoDeLibro, pasoSiguiente, veredictoDelLibro } from "./logicaDelLibro";
import type { AuditoriaDelLibro, CuentaDeHallazgos } from "./logicaDelLibro";

interface Props {
  auditoria: AuditoriaDelLibro;
  cuenta: CuentaDeHallazgos;
  archivo: File;
  // La fecha con que se pidió la auditoría (la del servidor manda si la devolvió).
  fecha: string;
  alOtro: () => void;
  alVerLaHoja: () => void;
  preparandoLaHoja: boolean;
  errorDeLaHoja: unknown;
  alExpirar: () => void;
}

// «Conclusión y entrega» (B2, ficha-b2 §1.8 y D2): el veredicto del servidor dicho con palabra e ícono, los totales del libro
// frente a los de Sílice y el paso que sigue, con un solo principal: con algo que entregar, el informe en PDF; sin nada,
// auditar otro libro. No es el «Dictamen» firmado de Aprobar y Revisar: una auditoría de libro no es de una obra ni se firma.
export function ConclusionDelLibro({
  auditoria,
  cuenta,
  archivo,
  fecha,
  alOtro,
  alVerLaHoja,
  preparandoLaHoja,
  errorDeLaHoja,
  alExpirar,
}: Props): JSX.Element {
  const veredicto = veredictoDelLibro(auditoria.cumple, cuenta);
  const paso = pasoSiguiente(cuenta);
  const fechaDelInforme = auditoria.fecha_devolucion ?? fecha;
  const Icono = veredicto.cumple ? CheckmarkFilled : WarningFilled;
  return (
    <section aria-labelledby="libro-conclusion" className="silice-libro__seccion">
      <h2 id="libro-conclusion" className="cds--type-heading-compact-02">
        <span aria-hidden="true" className="silice-libro__numero">
          3
        </span>
        Conclusión y entrega
      </h2>

      <p className={`silice-libro__veredicto silice-libro__veredicto--${veredicto.cumple ? "cumple" : "no-cumple"}`}>
        <Icono size={20} aria-hidden="true" className="silice-libro__icono-veredicto" />
        <strong>{veredicto.titulo}</strong> <span>{veredicto.detalle}</span>
      </p>

      {(auditoria.indicadores?.length ?? 0) > 0 && (
        <FranjaIndicadores
          indicadores={auditoria.indicadores ?? []}
          totalesLibro={auditoria.totales_libro}
          totalesSilice={auditoria.totales_silice}
          partidasConOmision={auditoria.partidas_con_omision ?? []}
          rotuloMeta="Según Sílice"
        />
      )}

      {auditoria.aviso_historial && (
        <InlineNotification
          kind="warning"
          role="status"
          title="Historial"
          subtitle={auditoria.aviso_historial}
          lowContrast
          hideCloseButton
        />
      )}

      <div className="silice-libro__acciones">
        {paso === "informe" ? (
          <div className="silice-libro__informe">
            <DescargaArchivo
              key={`${auditoria.libro.sha256}-${fechaDelInforme}`}
              ruta="/v1/libros/auditoria/pdf"
              metodo="POST"
              cuerpo={cuerpoDeLibro(archivo, fechaDelInforme)}
              etiqueta="Descargar el informe en PDF"
              nombrePorOmision="hallazgos.pdf"
              alExpirar={alExpirar}
              kind="primary"
              descripcionId="libro-informe-nota"
            />
            <p id="libro-informe-nota" className="cds--type-helper-text-01">
              {EXPLICACION_DEL_PDF}
            </p>
          </div>
        ) : (
          <Button kind="primary" size="md" onClick={alOtro}>
            Auditar otro libro
          </Button>
        )}
        <Button kind="secondary" size="md" disabled={preparandoLaHoja} onClick={alVerLaHoja}>
          {preparandoLaHoja ? "Preparando la hoja…" : "Ver la hoja marcada"}
        </Button>
        <Link className="cds--link" to={rutaOPendientes("historial")}>
          Ver el historial
        </Link>
      </div>
      <AvisoError error={errorDeLaHoja} titulo="No se pudo preparar la hoja" />
    </section>
  );
}
