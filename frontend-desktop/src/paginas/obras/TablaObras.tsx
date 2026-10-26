import { WarningFilled } from "@carbon/icons-react";
import { Button, DataTableSkeleton, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@carbon/react";
import { useId } from "react";
import type { JSX, ReactNode } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import type { Carga } from "../inicio/useCarga";
import { etiquetaAvance, textoTotal } from "./logica";
import type { ObraFilaRespuesta, ResumenObrasRespuesta } from "./logica";

const COLUMNAS = ["Obra", "Etapa", "Avance", "Total", "Qué pasa"];
const SIN_OBRAS = "Todavía no hay obras en esta carpeta de trabajo.";

interface Props {
  carga: Carga<ResumenObrasRespuesta>;
  // Si la cuenta puede abrir la pantalla de un siguiente paso (la columna solo existe si alguna fila trae uno que si).
  puedeIr: (pagina: string) => boolean;
  // Elige la obra y abre la pantalla (con la confirmacion si hay trabajo sin guardar).
  alIr: (codigo: string, pagina: string) => void;
  // Lo que se le ofrece a la cuenta cuando no hay obras (texto y botones que dependen de sus acciones).
  vacio: { descripcion: string; acciones: ReactNode };
}

// «Obras»: cada obra de la carpeta con su etapa, su avance (real de plan), su total, que le pasa y el siguiente paso.
// Tabla Carbon `sm`; los montos y porcentajes, en es-VE sobre el texto de la API.
export function TablaObras({ carga, puedeIr, alIr, vacio }: Props): JSX.Element | null {
  const idTitulo = useId();
  if (carga.estado === "sin_permiso") return null;

  let cuerpo: ReactNode;
  if (carga.estado === "cargando") {
    cuerpo = (
      <div role="status" aria-busy="true" aria-label="Cargando las obras">
        <DataTableSkeleton
          size="sm"
          columnCount={COLUMNAS.length}
          rowCount={3}
          headers={COLUMNAS.map((header) => ({ header }))}
          showHeader={false}
          showToolbar={false}
        />
      </div>
    );
  } else if (carga.estado !== "listo") {
    cuerpo = <AvisoError error={carga.error} titulo="No se pudieron leer las obras ni sus cifras" />;
  } else if (carga.datos.obras.length === 0) {
    cuerpo = (
      <EstadoVacio titulo={SIN_OBRAS} descripcion={vacio.descripcion}>
        {vacio.acciones}
      </EstadoVacio>
    );
  } else {
    cuerpo = <Tabla obras={carga.datos.obras} puedeIr={puedeIr} alIr={alIr} />;
  }

  return (
    <section className="silice-mesa__bloque" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Obras
      </h2>
      {cuerpo}
    </section>
  );
}

function Etapa({ obra }: { obra: ObraFilaRespuesta }) {
  if (obra.etapa !== "atrasada") return <span className="silice-mesa__etapa">{obra.etapa_texto}</span>;
  // El color no va solo: el icono de advertencia acompana a la palabra.
  return (
    <span className="silice-mesa__etapa silice-mesa__etapa--atrasada">
      <WarningFilled size={16} aria-hidden="true" />
      {obra.etapa_texto}
    </span>
  );
}

function Tabla({ obras, puedeIr, alIr }: { obras: ObraFilaRespuesta[]; puedeIr: Props["puedeIr"]; alIr: Props["alIr"] }) {
  const base = useId();
  const paso = (obra: ObraFilaRespuesta) => (obra.siguiente !== null && puedeIr(obra.siguiente.pagina) ? obra.siguiente : null);
  const conPaso = obras.some((o) => paso(o) !== null);

  return (
    <div className="silice-tabla silice-mesa__tabla">
      <Table size="sm" aria-label="Obras de la carpeta de trabajo">
        <TableHead>
          <TableRow>
            <TableHeader>Obra</TableHeader>
            <TableHeader>Etapa</TableHeader>
            <TableHeader className="silice-cifra">Avance</TableHeader>
            <TableHeader className="silice-cifra">Total</TableHeader>
            <TableHeader>Qué pasa</TableHeader>
            {conPaso && <TableHeader>Siguiente paso</TableHeader>}
          </TableRow>
        </TableHead>
        <TableBody>
          {obras.map((obra) => {
            const idNombre = `${base}-${obra.codigo}`;
            const siguiente = paso(obra);
            const total = textoTotal(obra.total, obra.moneda);
            return (
              <TableRow key={obra.codigo}>
                <TableCell>
                  <span id={idNombre} className="silice-mesa__obra-nombre">
                    {obra.nombre}
                  </span>
                  {obra.cliente && <span className="silice-mesa__obra-cliente cds--type-helper-text-01">{obra.cliente}</span>}
                </TableCell>
                <TableCell>
                  <Etapa obra={obra} />
                </TableCell>
                <TableCell className="silice-cifra">{etiquetaAvance(obra.avance_real, obra.avance_plan)}</TableCell>
                <TableCell className="silice-cifra">
                  {total ?? <span className="silice-mesa__sin-dato">Sin presupuesto</span>}
                </TableCell>
                <TableCell>{obra.que_pasa}</TableCell>
                {conPaso && (
                  <TableCell className="silice-mesa__paso">
                    {siguiente && (
                      <Button
                        kind="ghost"
                        size="sm"
                        aria-describedby={idNombre}
                        onClick={() => alIr(obra.codigo, siguiente.pagina)}
                      >
                        {siguiente.texto}
                      </Button>
                    )}
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
