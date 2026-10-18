import { ErrorFilled, WarningAltFilled } from "@carbon/icons-react";
import { SkeletonText, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@carbon/react";
import { Link } from "react-router";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import type { Carga } from "./useCarga";

// Una fila del tablero de la arenera (GET /v1/produccion/existencias). Las cantidades son texto decimal y se
// muestran tal cual: la interfaz no calcula (DESIGN.md).
export interface ExistenciaRespuesta {
  codigo: string;
  nombre: string;
  unidad_venta: string;
  existencia: string;
  minima: string;
  queda_poco: boolean;
  negativa: boolean;
}

const MENSAJE_NEGATIVA = "Existencia negativa: falta registrar producción o conteo";
const MENSAJE_POCO = "Queda poco";

// Lo que pide atencion, lo negativo primero (Carbon: la severidad lleva icono y texto, nunca solo color).
export function requierenAtencion(filas: ExistenciaRespuesta[]): ExistenciaRespuesta[] {
  const pide = filas.filter((f) => f.negativa || f.queda_poco);
  return [...pide.filter((f) => f.negativa), ...pide.filter((f) => !f.negativa)];
}

function Cuerpo({ carga }: { carga: Carga<ExistenciaRespuesta[]> }) {
  if (carga.estado === "cargando") {
    return (
      <div role="status" aria-busy="true" aria-label="Cargando la arenera">
        <SkeletonText paragraph lineCount={3} />
      </div>
    );
  }
  if (carga.estado === "sin_permiso") return <EstadoVacio titulo="Sin datos de la arenera para su cuenta" />;
  if (carga.estado === "no_disponible") return <EstadoVacio titulo="La arenera aún no está disponible" />;
  if (carga.estado === "error") return <AvisoError error={carga.error} titulo="No se pudo leer la arenera" />;

  const filas = carga.datos;
  if (filas.length === 0) {
    return (
      <EstadoVacio
        titulo="Aún no hay materiales"
        descripcion="Registre los materiales de la arenera para ver aquí cuánto queda de cada uno."
      >
        <Link className="cds--link" to="/existencias">
          Registrar materiales en Producción
        </Link>
      </EstadoVacio>
    );
  }
  const pide = requierenAtencion(filas);
  if (pide.length === 0) return <p className="silice-inicio__nota cds--type-body-compact-01">Todo sobre el mínimo</p>;

  return (
    <div className="silice-tabla">
      <Table size="sm" aria-label="Materiales de la arenera que requieren atención">
        <TableHead>
          <TableRow>
            <TableHeader>Material</TableHeader>
            <TableHeader className="silice-cifra">Existencia</TableHeader>
            <TableHeader className="silice-cifra">Mínima</TableHeader>
            <TableHeader>Estado</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {pide.map((f) => (
            <TableRow key={f.codigo}>
              <TableCell>{f.nombre}</TableCell>
              <TableCell className="silice-cifra">{`${f.existencia} ${f.unidad_venta}`}</TableCell>
              <TableCell className="silice-cifra">{`${f.minima} ${f.unidad_venta}`}</TableCell>
              <TableCell>
                <span className="silice-inicio__estado">
                  {f.negativa ? (
                    <ErrorFilled size={16} className="silice-inicio__icono--error" title="Error" />
                  ) : (
                    <WarningAltFilled size={16} className="silice-inicio__icono--advertencia" title="Advertencia" />
                  )}
                  {f.negativa ? MENSAJE_NEGATIVA : MENSAJE_POCO}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function PanelArenera({ carga }: { carga: Carga<ExistenciaRespuesta[]> }) {
  return (
    <section className="silice-inicio__bloque" aria-labelledby="inicio-arenera">
      <h2 id="inicio-arenera" className="cds--type-heading-03">
        Arenera: lo que requiere atención
      </h2>
      <Cuerpo carga={carga} />
    </section>
  );
}
