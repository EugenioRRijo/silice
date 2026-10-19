import type { InformeAuditoriaRespuesta } from "../api/tipos";
import { TablaDensa } from "./TablaDensa";

interface Props {
  informe: InformeAuditoriaRespuesta;
}

// El informe de auditoria (UC-05) a partir del JSON de la API. Todo va como texto plano en celdas de tabla: la
// descripcion de un hallazgo puede traer el nombre de un insumo importado, que en Markdown seria un enlace o una
// imagen (SEG-3, RV-14). Se muestra tenga hallazgos o no: el informe se genera siempre (NORMAS.md §2, principio 7).
export function InformeAuditoria({ informe }: Props) {
  return (
    <section className="silice-informe" aria-label="Informe de auditoría">
      <p className="cds--type-body-compact-01">
        <strong>Presupuesto {informe.codigo_presupuesto}</strong> · Hallazgos: {informe.total_hallazgos} · Resultado:{" "}
        {informe.veredicto}
      </p>
      {informe.reglas_evaluadas.length > 0 && (
        <>
          <p className="cds--type-label-01">Reglas evaluadas</p>
          <TablaDensa
            etiqueta="Reglas evaluadas"
            columnas={[
              { clave: "regla", titulo: "Regla" },
              { clave: "nombre", titulo: "Nombre" },
              { clave: "hallazgos", titulo: "Hallazgos", numerica: true },
            ]}
            filas={informe.reglas_evaluadas.map((r) => ({
              id: r.regla,
              regla: r.regla,
              nombre: r.nombre,
              hallazgos: String(r.hallazgos),
            }))}
          />
        </>
      )}
      {informe.hallazgos.length === 0 ? (
        informe.sin_hallazgos && <p className="cds--type-label-01">{informe.sin_hallazgos}</p>
      ) : (
        <TablaDensa
          etiqueta="Hallazgos"
          columnas={[
            { clave: "numero", titulo: "#", numerica: true },
            { clave: "regla", titulo: "Regla" },
            { clave: "severidad", titulo: "Severidad" },
            { clave: "partida", titulo: "Partida" },
            { clave: "descripcion", titulo: "Descripción" },
            { clave: "impacto", titulo: "Impacto", numerica: true },
            { clave: "observado", titulo: "Observado", numerica: true },
            { clave: "esperado", titulo: "Esperado", numerica: true },
            { clave: "origen", titulo: "Origen" },
          ]}
          filas={informe.hallazgos.map((h) => ({
            id: String(h.numero),
            numero: String(h.numero),
            regla: h.regla,
            severidad: h.severidad,
            partida: h.partida ?? "-",
            descripcion: h.descripcion,
            impacto: h.impacto ?? "",
            observado: h.observado ?? "",
            esperado: h.esperado ?? "",
            origen: h.origen.join("; "),
          }))}
        />
      )}
    </section>
  );
}
