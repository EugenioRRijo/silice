import { Button } from "@carbon/react";
import { InlineLoading } from "../../comun/carbonEs";
import { useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { unidadEscrita } from "../../comun/unidades";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

// F5 vial, tarea 6 (diseño 2026-11-03 §7): auditar un libro con un APU por hoja y, si viene, su libro de presupuesto
// (`POST /v1/libros/apu-por-hoja`). El servidor recalcula cada hoja, la compara con lo impreso y dice cada hallazgo con
// su celda; aquí no se calcula nada: los precios llegan ya presentados a dos decimales y solo se escriben en es-VE.
// Nada se guarda: ni los libros ni el informe.

interface ApuPorHoja {
  hoja: string;
  numero: number | null;
  codigo: string;
  descripcion: string;
  unidad: string;
  precio_impreso: string;
  precio_silice: string | null;
  precio_silice_exacto: string | null;
  celda_precio: string;
}

interface HallazgoDelLibro {
  codigo: string;
  severidad: string;
  descripcion: string;
  celda: string;
  impacto: string | null;
  accion: string;
}

interface DesperdicioLeido {
  descripcion: string;
  unidad: string;
  cantidad_neta: string;
  desperdicio_pct: string;
  cantidad: string;
}

export interface InformeApuPorHoja {
  libro: { nombre: string; sha256: string };
  perfil: string;
  origen_perfil: "paquete" | "local";
  presupuesto: string | null;
  cumple: boolean;
  por_severidad: Record<string, number>;
  apus: ApuPorHoja[];
  hallazgos: HallazgoDelLibro[];
  desperdicios: DesperdicioLeido[];
}

export function auditarApuPorHoja(libro: File, presupuesto: File | null): Promise<InformeApuPorHoja> {
  const cuerpo = new FormData();
  cuerpo.append("libro", libro);
  if (presupuesto) cuerpo.append("presupuesto", presupuesto);
  return pedir<InformeApuPorHoja>("/v1/libros/apu-por-hoja", { metodo: "POST", cuerpo });
}

const NO_EVALUABLE = "No evaluable";

const COLUMNAS_PRECIOS: ColumnaDensa[] = [
  { clave: "hoja", titulo: "Hoja", ordenable: false },
  { clave: "codigo", titulo: "Código", ordenable: false },
  { clave: "descripcion", titulo: "Partida", ordenable: false },
  { clave: "impreso", titulo: "P.U. impreso", numerica: true, ordenable: false, presentar: formatoEsVe },
  { clave: "silice", titulo: "P.U. de Sílice", numerica: true, ordenable: false, presentar: formatoEsVe },
];

const COLUMNAS_HALLAZGOS: ColumnaDensa[] = [
  { clave: "severidad", titulo: "Severidad", celda: "severidad", ordenable: false },
  { clave: "codigo", titulo: "Regla", ordenable: false },
  { clave: "celda", titulo: "Celda", ordenable: false },
  { clave: "descripcion", titulo: "Qué dice", ordenable: false },
];

interface Props {
  alExpirar: () => void;
}

export function AuditarApuPorHoja({ alExpirar }: Props): JSX.Element {
  const [libro, setLibro] = useState<File | null>(null);
  const [presupuesto, setPresupuesto] = useState<File | null>(null);
  const [informe, setInforme] = useState<InformeApuPorHoja | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [auditando, setAuditando] = useState(false);

  async function auditar() {
    if (libro === null) return;
    setError(null);
    setInforme(null);
    setAuditando(true);
    try {
      setInforme(await auditarApuPorHoja(libro, presupuesto));
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    } finally {
      setAuditando(false);
    }
  }

  return (
    <section className="silice-inicio__bloque" aria-labelledby="auditoria-apu-por-hoja">
      <h2 id="auditoria-apu-por-hoja" className="cds--type-heading-compact-02">
        Libro con un APU por hoja
      </h2>
      <p className="silice-inicio__nota cds--type-body-compact-01">
        Para los libros que exporta un programa de APU: una hoja por partida y, aparte, el libro del presupuesto. Sílice
        recalcula cada hoja, la compara con lo impreso y enlaza cada renglón del presupuesto con su hoja por el número.
        Sílice no conserva ninguno de los dos archivos.
      </p>
      <SubidaArchivo
        id="auditoria-apu-libro"
        etiqueta="Suelte aquí el .xlsx de los APU (una hoja por partida), o haga clic para elegirlo"
        extensiones={[".xlsx"]}
        alElegir={setLibro}
        deshabilitada={auditando}
      />
      <SubidaArchivo
        id="auditoria-apu-presupuesto"
        etiqueta="Opcional: suelte aquí el .xlsx del presupuesto, o haga clic para elegirlo"
        extensiones={[".xlsx"]}
        alElegir={setPresupuesto}
        deshabilitada={auditando}
      />
      {/* Región viva sin el rol «status»: el de la subida de arriba es el único estado de la página. */}
      <p aria-live="polite" className="silice-inicio__nota cds--type-body-compact-01">
        {[libro ? `Libro de APU: ${libro.name}` : "", presupuesto ? `Presupuesto: ${presupuesto.name}` : ""]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <div className="silice-inicio__acciones">
        <Button kind="primary" size="md" disabled={libro === null || auditando} onClick={() => void auditar()}>
          Auditar el libro de APU
        </Button>
        {auditando && <InlineLoading description="Recalculando cada hoja..." />}
      </div>
      <AvisoError error={error} titulo="No se auditó el libro" />
      {informe && <Informe informe={informe} />}
    </section>
  );
}

function Informe({ informe }: { informe: InformeApuPorHoja }): JSX.Element {
  const origen = informe.origen_perfil === "local" ? "de esta instalación" : "del paquete";
  const precios = informe.apus.map((a) => ({
    id: a.hoja,
    hoja: a.hoja,
    codigo: a.codigo,
    descripcion: a.descripcion,
    impreso: a.precio_impreso,
    silice: a.precio_silice ?? NO_EVALUABLE,
  }));
  const hallazgos = informe.hallazgos.map((h, i) => ({
    id: `${h.codigo}-${h.celda}-${i}`,
    severidad: h.severidad,
    codigo: h.codigo,
    celda: h.celda,
    descripcion: h.descripcion,
  }));
  return (
    <>
      <p className="silice-inicio__nota cds--type-body-compact-01">
        {`Perfil ${informe.perfil} (${origen}) · ${informe.libro.nombre}`}
        {informe.presupuesto ? ` · con ${informe.presupuesto}` : " · sin libro de presupuesto"}
      </p>
      <TablaDensa etiqueta="Precio unitario de cada hoja" columnas={COLUMNAS_PRECIOS} filas={precios} />
      <TablaDensa
        etiqueta="Hallazgos del libro"
        columnas={COLUMNAS_HALLAZGOS}
        filas={hallazgos}
        vacio={{ titulo: "Sin hallazgos: cada hoja cuadra con lo impreso." }}
      />
      {informe.desperdicios.length > 0 && (
        <ul className="silice-inicio__nota cds--type-body-compact-01" aria-label="Materiales con desperdicio">
          {informe.desperdicios.map((d, i) => (
            <li key={`${d.descripcion}-${i}`}>
              {`${d.descripcion}: ${formatoEsVe(d.cantidad)} ${unidadEscrita(d.unidad)} (${formatoEsVe(d.cantidad_neta)} + ${formatoEsVe(d.desperdicio_pct)} %)`}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
