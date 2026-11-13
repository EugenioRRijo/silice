import { Button, Select, SelectItem } from "@carbon/react";
import { InlineLoading, InlineNotification } from "../../comun/carbonEs";
import { useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useCarga } from "../../comun/useCarga";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { unidadEscrita } from "../../comun/unidades";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

// F5 vial, tarea 6 (diseño 2026-11-03 §7): auditar un libro con un APU por hoja y, si viene, su libro de presupuesto
// (`POST /v1/libros/apu-por-hoja`). El servidor recalcula cada hoja, la compara con lo impreso y dice cada hallazgo con
// su celda; aquí no se calcula nada: los precios llegan ya presentados a dos decimales y solo se escriben en es-VE.
// Nada se guarda: ni los libros ni el informe.
//
// E2E-2 (prueba de punta a punta del 2026-11-13): el perfil se elige de la lista del servidor
// (`GET /v1/libros/perfiles-apu-por-hoja`: los del paquete y los de esta instalación, con la hoja del presupuesto
// que lee cada uno; uno mal escrito sale sin poder elegirse y con su motivo). Si la lista no se lee, se audita con el
// de siempre (`apu_por_hoja`, sin mandar el campo) y se dice. El aviso AH11 (la hoja del presupuesto parece de otra
// obra) sale arriba del informe, además de en la tabla.

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
  hoja_presupuesto: string | null;
  cumple: boolean;
  por_severidad: Record<string, number>;
  apus: ApuPorHoja[];
  hallazgos: HallazgoDelLibro[];
  desperdicios: DesperdicioLeido[];
}

export interface PerfilDisponible {
  nombre: string;
  origen: "paquete" | "local";
  hoja_presupuesto: string | null;
  motivo: string | null;
}

export function auditarApuPorHoja(libro: File, presupuesto: File | null, perfil: string | null = null): Promise<InformeApuPorHoja> {
  const cuerpo = new FormData();
  cuerpo.append("libro", libro);
  if (presupuesto) cuerpo.append("presupuesto", presupuesto);
  if (perfil) cuerpo.append("perfil", perfil);
  return pedir<InformeApuPorHoja>("/v1/libros/apu-por-hoja", { metodo: "POST", cuerpo });
}

const POR_OMISION = "apu_por_hoja";
const RUTA_PERFILES = "/v1/libros/perfiles-apu-por-hoja";
const AVISO_OTRA_OBRA = "AH11";
const ID_TITULO_OTRA_OBRA = "auditoria-apu-por-hoja-otra-obra";
const TITULO_OTRA_OBRA = "La hoja del presupuesto parece de otra obra";
const origenDe = (origen: "paquete" | "local") => (origen === "local" ? "de esta instalación" : "del paquete");

function textoDelPerfil(p: PerfilDisponible): string {
  return p.motivo !== null || p.hoja_presupuesto === null
    ? `${p.nombre} · no se puede usar: ${p.motivo ?? "sin hoja de presupuesto"}`
    : `${p.nombre} · lee la hoja ${p.hoja_presupuesto} (${origenDe(p.origen)})`;
}

// El perfil que se propone: el de siempre si se puede usar; si no, el primero que se pueda.
function perfilInicial(perfiles: PerfilDisponible[]): string | null {
  const usables = perfiles.filter((p) => p.motivo === null && p.hoja_presupuesto !== null);
  return (usables.find((p) => p.nombre === POR_OMISION) ?? usables[0])?.nombre ?? null;
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
  const lista = useCarga<PerfilDisponible[]>(RUTA_PERFILES, alExpirar);
  const perfiles = lista.estado === "listo" ? lista.datos : null;
  const sinLista = lista.estado !== "listo" && lista.estado !== "cargando";
  const [elegido, setElegido] = useState<string | null>(null);
  const perfil = elegido ?? (perfiles ? perfilInicial(perfiles) : null);

  async function auditar() {
    if (libro === null) return;
    setError(null);
    setInforme(null);
    setAuditando(true);
    try {
      setInforme(await auditarApuPorHoja(libro, presupuesto, perfil));
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
      {perfiles !== null && perfiles.length > 0 && (
        <Select
          id="auditoria-apu-perfil"
          labelText="Perfil del libro"
          helperText="Dice cómo leer las hojas de APU y qué hoja del presupuesto comparar. Con un presupuesto de varios frentes, elija el del frente de este libro."
          value={perfil ?? ""}
          onChange={(e) => setElegido(e.target.value)}
          disabled={auditando}
        >
          {perfiles.map((p) => (
            <SelectItem
              key={p.nombre}
              value={p.nombre}
              text={textoDelPerfil(p)}
              disabled={p.motivo !== null || p.hoja_presupuesto === null}
            />
          ))}
        </Select>
      )}
      {sinLista && (
        <p className="silice-inicio__nota cds--type-body-compact-01">
          {`No se pudo leer la lista de perfiles: se audita con ${POR_OMISION}.`}
        </p>
      )}
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
  const origen = origenDe(informe.origen_perfil);
  const otraObra = informe.hallazgos.find((h) => h.codigo === AVISO_OTRA_OBRA);
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
        {informe.presupuesto
          ? ` · con ${informe.presupuesto}${informe.hoja_presupuesto ? ` (hoja ${informe.hoja_presupuesto})` : ""}`
          : " · sin libro de presupuesto"}
      </p>
      {otraObra && (
        <>
          {/* Nombre accesible del aviso: su título (ola 2, 2026-11-13). Todo el texto se leería dos veces y sin nombre no se
              distingue de los otros avisos. Carbon no da id al título (`title` es texto), así que el nombre va en un texto
              oculto que `aria-labelledby` sí lee. */}
          <span id={ID_TITULO_OTRA_OBRA} hidden>
            {TITULO_OTRA_OBRA}
          </span>
          <InlineNotification
            kind="warning"
            role="status"
            aria-labelledby={ID_TITULO_OTRA_OBRA}
            title={TITULO_OTRA_OBRA}
            subtitle={otraObra.descripcion}
            lowContrast
            hideCloseButton
          />
        </>
      )}
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
