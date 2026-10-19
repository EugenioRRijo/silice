import { Button, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TextInput } from "@carbon/react";
import { Add, TrashCan } from "@carbon/icons-react";
import { AVISO_PLAN_REINICIADO, TEXTO_PLAN } from "./logica";
import type { FilaPlan } from "./tipos";

interface Props {
  filas: FilaPlan[];
  alCambiar: (filas: FilaPlan[]) => void;
  // La ultima elaboracion sin plan descarto uno editado.
  reiniciado: boolean;
  ocupado: boolean;
  alAplicar: () => void;
}

const CAMPOS: { clave: keyof FilaPlan; titulo: string; etiqueta: string }[] = [
  { clave: "periodo", titulo: "periodo", etiqueta: "Periodo" },
  { clave: "codigo_partida", titulo: "codigo_partida", etiqueta: "Codigo de partida" },
  { clave: "fraccion", titulo: "fraccion", etiqueta: "Fraccion" },
];

// «Plan de trabajo» (UC-01 6): tabla editable con filas anadibles y quitables. Las fracciones son texto: la API las
// valida (un plan invalido es 422 con su detalle) y las filas en blanco las ignora el servidor.
export function PlanDeTrabajo({ filas, alCambiar, reiniciado, ocupado, alAplicar }: Props) {
  const cambiar = (n: number, clave: keyof FilaPlan, valor: string) =>
    alCambiar(filas.map((f, i) => (i === n ? { ...f, [clave]: valor } : f)));

  return (
    <section className="silice-elaborar__bloque" aria-label="Plan de trabajo">
      <h2 className="cds--type-heading-03">Plan de trabajo</h2>
      <p className="cds--type-body-compact-01">{TEXTO_PLAN}</p>
      {reiniciado && (
        <p className="silice-elaborar__nota cds--type-label-01" role="status">
          {AVISO_PLAN_REINICIADO}
        </p>
      )}
      <div className="silice-elaborar__plan">
        <Table size="sm" aria-label="Plan de trabajo">
          <TableHead>
            <TableRow>
              {CAMPOS.map((c) => (
                <TableHeader key={c.clave}>{c.titulo}</TableHeader>
              ))}
              <TableHeader>
                <span className="cds--visually-hidden">Quitar</span>
              </TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {filas.map((fila, n) => (
              <TableRow key={n}>
                {CAMPOS.map((c) => (
                  <TableCell key={c.clave}>
                    <TextInput
                      id={`elaborar-plan-${c.clave}-${n}`}
                      labelText={`${c.etiqueta}, fila ${n + 1}`}
                      hideLabel
                      size="sm"
                      value={fila[c.clave]}
                      onChange={(e) => cambiar(n, c.clave, e.target.value)}
                    />
                  </TableCell>
                ))}
                <TableCell>
                  <Button
                    kind="ghost"
                    size="sm"
                    hasIconOnly
                    renderIcon={TrashCan}
                    iconDescription={`Quitar fila ${n + 1}`}
                    tooltipPosition="left"
                    onClick={() => alCambiar(filas.filter((_, i) => i !== n))}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="silice-elaborar__acciones">
        <Button
          kind="ghost"
          size="sm"
          renderIcon={Add}
          onClick={() => alCambiar([...filas, { periodo: "", codigo_partida: "", fraccion: "" }])}
        >
          Añadir fila
        </Button>
        <Button kind="tertiary" size="md" disabled={ocupado} onClick={alAplicar}>
          Aplicar plan y volver a elaborar
        </Button>
      </div>
    </section>
  );
}
