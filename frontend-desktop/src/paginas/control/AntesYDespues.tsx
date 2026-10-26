import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";

// Un monto como lo manda la API: `texto` a dos decimales y `exacto` sin redondear, los dos con punto decimal.
interface Monto {
  texto: string;
  exacto: string;
}

export interface FilaAntesYDespues {
  partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  costo_antes: Monto;
  costo_despues: Monto;
  duracion_antes: string;
  duracion_despues: string;
  termino_antes: number | null;
  termino_despues: number | null;
  equilibrio_antes: Monto | null;
  equilibrio_despues: Monto | null;
}

export interface AntesYDespuesRespuesta {
  linea_base: string | null;
  version: string | null;
  moneda: string;
  filas: FilaAntesYDespues[];
  aviso: string | null;
}

const TITULO = "Antes y después de las partidas cambiadas";
const SIN_CALCULAR = "Sin calcular";

type Estado = { tipo: "cargando" } | { tipo: "listo"; datos: AntesYDespuesRespuesta } | { tipo: "error"; error: unknown };

// Días hábiles: «1 día», «2 días», «23,5 días» (el texto llega con punto decimal y se formatea una sola vez).
function dias(texto: string): string {
  return `${formatoEsVe(texto)} ${texto === "1" ? "día" : "días"}`;
}

function CifraMonto({ monto, moneda }: { monto: Monto | null; moneda: string }) {
  if (monto === null) return <span>{SIN_CALCULAR}</span>;
  return (
    <span title={monto.exacto}>
      {formatoEsVe(monto.texto)} {moneda}
    </span>
  );
}

function AntesDespues({ antes, despues }: { antes: ReactNode; despues: ReactNode }) {
  return (
    <span>
      {antes} pasa a {despues}
    </span>
  );
}

// «Antes y después» de Control de obra (Tarea 26, diseño de montar un presupuesto §11 meta 5): cuando una versión nueva
// cambia el APU de una partida para solventar una crisis (una línea agregada o quitada, otro rendimiento), por cada partida
// cambiada su costo directo unitario, su duración por rendimientos y su efecto en el término de la obra y en el punto de
// equilibrio, contra la línea base (`GET /v1/hoja/antes-y-despues?proyecto=`). Solo lee; no calcula ni redondea nada.
export function AntesYDespues({ proyecto }: { proyecto: string }) {
  const { alExpirar } = useAplicacion();
  const [estado, setEstado] = useState<{ proyecto: string; valor: Estado } | null>(null);

  useEffect(() => {
    let vigente = true;
    pedir<AntesYDespuesRespuesta>(`/v1/hoja/antes-y-despues?${new URLSearchParams({ proyecto }).toString()}`).then(
      (datos) => {
        if (vigente) setEstado({ proyecto, valor: { tipo: "listo", datos } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setEstado({ proyecto, valor: { tipo: "error", error } });
      },
    );
    return () => {
      vigente = false;
    };
  }, [proyecto, alExpirar]);

  const actual: Estado = estado !== null && estado.proyecto === proyecto ? estado.valor : { tipo: "cargando" };

  return (
    <section className="silice-control__bloque" aria-labelledby="control-antes-y-despues" aria-busy={actual.tipo === "cargando"}>
      <h2 id="control-antes-y-despues" className="cds--type-heading-compact-02">
        {TITULO}
      </h2>
      {actual.tipo === "error" && <AvisoError error={actual.error} titulo="No se pudo comparar con la línea base" />}
      {actual.tipo === "listo" && <Contenido datos={actual.datos} />}
    </section>
  );
}

function Contenido({ datos }: { datos: AntesYDespuesRespuesta }) {
  if (datos.aviso !== null || datos.filas.length === 0) {
    return <p className="cds--type-body-compact-01">{datos.aviso ?? ""}</p>;
  }
  const { moneda } = datos;
  const porPartida = new Map(datos.filas.map((f) => [f.partida, f]));
  const de = (fila: FilaDensa) => porPartida.get(fila.partida!)!;
  const columnas: ColumnaDensa[] = [
    { clave: "nombre", titulo: "Partida", ordenable: false },
    {
      clave: "costo",
      titulo: "Costo directo por unidad",
      ordenable: false,
      celda: (f) => (
        <AntesDespues
          antes={<CifraMonto monto={de(f).costo_antes} moneda={moneda} />}
          despues={<CifraMonto monto={de(f).costo_despues} moneda={moneda} />}
        />
      ),
    },
    {
      clave: "duracion",
      titulo: "Duración de la partida",
      ordenable: false,
      celda: (f) => <AntesDespues antes={dias(de(f).duracion_antes)} despues={dias(de(f).duracion_despues)} />,
    },
    {
      clave: "termino",
      titulo: "Término de la obra",
      ordenable: false,
      celda: (f) => {
        const { termino_antes: antes, termino_despues: despues } = de(f);
        if (antes === null || despues === null) return SIN_CALCULAR;
        return <AntesDespues antes={dias(String(antes))} despues={dias(String(despues))} />;
      },
    },
    {
      clave: "equilibrio",
      titulo: "Punto de equilibrio",
      ordenable: false,
      celda: (f) => {
        const { equilibrio_antes: antes, equilibrio_despues: despues } = de(f);
        if (antes === null || despues === null) return SIN_CALCULAR;
        return <AntesDespues antes={<CifraMonto monto={antes} moneda={moneda} />} despues={<CifraMonto monto={despues} moneda={moneda} />} />;
      },
    },
  ];
  return (
    <>
      <p className="cds--type-body-compact-01">
        Compara la versión {datos.version} con la línea base {datos.linea_base}: el costo directo por unidad de cada partida
        cambiada, su duración según el rendimiento y el efecto de ese cambio, solo, en el término y en el punto de equilibrio de
        la obra.
      </p>
      <TablaDensa
        etiqueta={TITULO}
        columnas={columnas}
        filas={datos.filas.map((f) => ({ id: f.partida, partida: f.partida, nombre: `${f.partida} · ${f.descripcion}` }))}
      />
    </>
  );
}
