import { Button, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TextInput } from "@carbon/react";
import { Add, TrashCan } from "@carbon/icons-react";
import { useEffect, useRef } from "react";
import { AVISO_PLAN_REINICIADO, TEXTO_PLAN, periodoAVista, periodoAlServidor } from "./logica";
import type { FilaPlan } from "./tipos";

// Una fila del plan con un id propio y estable: la clave de React y el foco no dependen de la posicion.
export type FilaEditable = FilaPlan & { id: number };

let contador = 0;
// La tabla muestra «Día N»; lo que sale de ella (sinIds) vuelve a la forma del nucleo, «Dia N» (VB-6).
export function conIds(filas: FilaPlan[]): FilaEditable[] {
  return filas.map((f) => ({ ...f, periodo: periodoAVista(f.periodo), id: ++contador }));
}
export function sinIds(filas: FilaEditable[]): FilaPlan[] {
  return filas.map(({ periodo, codigo_partida, fraccion }) => ({
    periodo: periodoAlServidor(periodo),
    codigo_partida,
    fraccion,
  }));
}

interface Props {
  filas: FilaEditable[];
  alCambiar: (filas: FilaEditable[]) => void;
  // La ultima elaboracion sin plan descarto uno editado.
  reiniciado: boolean;
  ocupado: boolean;
  alAplicar: () => void;
}

type Foco = { fila: number } | "anadir" | null;

const CAMPOS: { clave: keyof FilaPlan; titulo: string; etiqueta: string }[] = [
  { clave: "periodo", titulo: "Período", etiqueta: "Período" },
  { clave: "codigo_partida", titulo: "Partida", etiqueta: "Partida" },
  { clave: "fraccion", titulo: "Fracción", etiqueta: "Fracción" },
];

// «Plan de trabajo» (UC-01 6): tabla editable con filas anadibles y quitables. Las fracciones son texto: la API las
// valida (un plan invalido es 422 con su detalle) y las filas en blanco las ignora el servidor.
export function PlanDeTrabajo({ filas, alCambiar, reiniciado, ocupado, alAplicar }: Props) {
  const foco = useRef<Foco>(null);
  const botonAnadir = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const destino = foco.current;
    foco.current = null;
    if (destino === "anadir") botonAnadir.current?.focus();
    else if (destino) document.getElementById(`elaborar-plan-periodo-${destino.fila}`)?.focus();
  }, [filas]);

  const cambiar = (id: number, clave: keyof FilaPlan, valor: string) =>
    alCambiar(filas.map((f) => (f.id === id ? { ...f, [clave]: valor } : f)));

  const anadir = () => {
    const [nueva] = conIds([{ periodo: "", codigo_partida: "", fraccion: "" }]);
    foco.current = { fila: nueva.id };
    alCambiar([...filas, nueva]);
  };

  const quitar = (n: number) => {
    const resto = filas.filter((_, i) => i !== n);
    const vecina = resto[n] ?? resto[n - 1];
    foco.current = vecina ? { fila: vecina.id } : "anadir";
    alCambiar(resto);
  };

  return (
    <section className="silice-elaborar__bloque" aria-label="Plan de trabajo">
      <h2 className="cds--type-heading-compact-02">Plan de trabajo</h2>
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
              <TableRow key={fila.id}>
                {CAMPOS.map((c) => (
                  <TableCell key={c.clave}>
                    <TextInput
                      id={`elaborar-plan-${c.clave}-${fila.id}`}
                      labelText={`${c.etiqueta}, fila ${n + 1}`}
                      hideLabel
                      size="sm"
                      value={fila[c.clave]}
                      onChange={(e) => cambiar(fila.id, c.clave, e.target.value)}
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
                    onClick={() => quitar(n)}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="silice-elaborar__acciones">
        <Button ref={botonAnadir} kind="ghost" size="sm" renderIcon={Add} onClick={anadir}>
          Añadir fila
        </Button>
        <Button kind="tertiary" size="md" disabled={ocupado} onClick={alAplicar}>
          Aplicar plan y volver a elaborar
        </Button>
      </div>
    </section>
  );
}
