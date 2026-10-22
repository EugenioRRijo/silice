import { CheckmarkFilled, ErrorFilled } from "@carbon/icons-react";
import { Accordion, AccordionItem } from "@carbon/react";
import type { InformeAuditoriaRespuesta } from "../api/tipos";
import type { ColumnaDensa } from "./TablaDensa";
import { TablaDensa } from "./TablaDensa";

interface Props {
  informe: InformeAuditoriaRespuesta;
}

// El informe de auditoria (UC-05) a partir del JSON de la API. Todo va como texto plano en celdas de tabla: la
// descripcion de un hallazgo puede traer el nombre de un insumo importado, que en Markdown seria un enlace o una
// imagen (SEG-3, RV-14). Se muestra tenga hallazgos o no: el informe se genera siempre (NORMAS.md §2, principio 7).
// Jerarquia: veredicto primero (icono y texto), luego los hallazgos y, plegadas, las reglas evaluadas.
export function InformeAuditoria({ informe }: Props) {
  const conHallazgos = informe.reglas_evaluadas.filter((r) => r.hallazgos > 0).length;
  const hay = (campo: "impacto" | "observado" | "esperado") => informe.hallazgos.some((h) => (h[campo] ?? "") !== "");
  const columnas: ColumnaDensa[] = [
    { clave: "numero", titulo: "#", numerica: true },
    { clave: "regla", titulo: "Regla" },
    { clave: "severidad", titulo: "Severidad", celda: "severidad" },
    { clave: "partida", titulo: "Partida" },
    { clave: "descripcion", titulo: "Descripción" },
    ...(hay("impacto") ? [{ clave: "impacto", titulo: "Impacto", numerica: true }] : []),
    ...(hay("observado") ? [{ clave: "observado", titulo: "Observado", numerica: true }] : []),
    ...(hay("esperado") ? [{ clave: "esperado", titulo: "Esperado", numerica: true }] : []),
    { clave: "origen", titulo: "Origen" },
  ];
  const Icono = informe.cumple ? CheckmarkFilled : ErrorFilled;

  return (
    <section className="silice-informe" aria-label="Informe de auditoría">
      <p className="silice-informe__veredicto cds--type-body-compact-01">
        <Icono size={16} className={informe.cumple ? "silice-informe__ok" : "silice-sev__icono silice-sev--error"} />
        <strong>Presupuesto {informe.codigo_presupuesto}</strong> · Hallazgos: {informe.total_hallazgos} · Resultado:{" "}
        {informe.veredicto}
      </p>
      {informe.hallazgos.length === 0 ? (
        informe.sin_hallazgos && <p className="cds--type-label-01">{informe.sin_hallazgos}</p>
      ) : (
        <>
          <h3 className="cds--type-heading-compact-01 silice-informe__titulo">Hallazgos</h3>
          <TablaDensa
            etiqueta="Hallazgos"
            columnas={columnas}
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
        </>
      )}
      {informe.reglas_evaluadas.length > 0 && (
        <Accordion size="sm">
          <AccordionItem title={`Reglas evaluadas: ${informe.reglas_evaluadas.length}, con hallazgos: ${conHallazgos}`}>
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
          </AccordionItem>
        </Accordion>
      )}
    </section>
  );
}
