import { SkeletonText, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@carbon/react";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import type { Carga } from "./useCarga";

// Una auditoria guardada (GET /v1/auditorias-libro). Solo resumen: el libro y el PDF nunca se guardan.
export interface AuditoriaGuardadaRespuesta {
  id: number;
  archivo: string;
  // ISO con hora, sin zona.
  fecha: string;
  tipo: "libro" | "pdf";
  errores: number;
  advertencias: number;
}

function plural(n: number, uno: string, varios: string): string {
  return `${n} ${n === 1 ? uno : varios}`;
}

export function resultadoEnUnaLinea(errores: number, advertencias: number): string {
  if (errores === 0 && advertencias === 0) return "Sin errores ni advertencias";
  return `${plural(errores, "error", "errores")}, ${plural(advertencias, "advertencia", "advertencias")}`;
}

export function UltimasAuditorias({ carga }: { carga: Carga<AuditoriaGuardadaRespuesta[]> }) {
  if (carga.estado === "cargando") {
    return (
      <div role="status" aria-busy="true" aria-label="Cargando las auditorías">
        <SkeletonText paragraph lineCount={3} />
      </div>
    );
  }
  if (carga.estado === "no_disponible") {
    return (
      <EstadoVacio
        titulo="El historial de auditorías aún no está disponible"
        descripcion="Puede auditar un presupuesto igual; el resultado no quedará guardado hasta que el historial esté activo."
      />
    );
  }
  if (carga.estado === "sin_permiso") return <EstadoVacio titulo="Sin historial de auditorías para su cuenta" />;
  if (carga.estado === "error") return <AvisoError error={carga.error} titulo="No se pudo leer el historial" />;
  if (carga.datos.length === 0) {
    return (
      <EstadoVacio
        titulo="Todavía no hay auditorías guardadas"
        descripcion="Suelte arriba el Excel de un presupuesto: el resumen y los hallazgos quedarán aquí."
      />
    );
  }
  return (
    <div className="silice-tabla">
      <Table size="sm" aria-label="Últimas auditorías guardadas">
        <TableHead>
          <TableRow>
            <TableHeader>Archivo</TableHeader>
            <TableHeader>Tipo</TableHeader>
            <TableHeader>Fecha</TableHeader>
            <TableHeader>Resultado</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {carga.datos.map((a) => (
            <TableRow key={a.id}>
              <TableCell>{a.archivo}</TableCell>
              <TableCell>{a.tipo === "pdf" ? "PDF" : "Libro"}</TableCell>
              <TableCell className="silice-inicio__sinquiebre">{fechaEsVe(a.fecha)}</TableCell>
              <TableCell className="silice-inicio__sinquiebre">
                {resultadoEnUnaLinea(a.errores, a.advertencias)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
