import { Button, Checkbox, Select, SelectItem } from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
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
import { MONEDAS, rotuloDeMoneda } from "../../comun/monedas";
import { enumeradas } from "../../comun/perfilesDeLibros";
import type { PerfilDisponible } from "../../comun/perfilesDeLibros";
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
//
// Libro por frentes (ola 2, línea 3, 2026-11-13): un perfil puede leer varias hojas del presupuesto (una por frente) y las
// hojas se eligen aparte del perfil. Al elegir el libro del presupuesto se piden sus hojas (`POST /v1/libros/hojas`, solo
// los nombres) y se marcan las del perfil que el libro tiene; lo marcado viaja como `hoja_presupuesto`, una vez por hoja.
// Si las hojas no se pueden leer, decide el perfil (no se manda nada).
//
// Después del informe, quien arma lleva el libro auditado a la Hoja de la obra elegida (`POST /v1/hoja/libro`): se
// mandan otra vez los mismos libros, el perfil y las hojas con que se auditó, la obra y la moneda de los precios (la
// declara la persona: Sílice no la adivina). El servidor dice cada partida con el P.U. del libro y el de la Hoja, ya
// presentados, y si casan; aquí no se compara ni se calcula nada.

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
  hojas_presupuesto?: string[];
  cumple: boolean;
  por_severidad: Record<string, number>;
  apus: ApuPorHoja[];
  hallazgos: HallazgoDelLibro[];
  desperdicios: DesperdicioLeido[];
}

export function auditarApuPorHoja(
  libro: File,
  presupuesto: File | null,
  perfil: string | null = null,
  hojas: string[] = [],
): Promise<InformeApuPorHoja> {
  const cuerpo = new FormData();
  cuerpo.append("libro", libro);
  if (presupuesto) cuerpo.append("presupuesto", presupuesto);
  if (perfil) cuerpo.append("perfil", perfil);
  for (const hoja of hojas) cuerpo.append("hoja_presupuesto", hoja);
  return pedir<InformeApuPorHoja>("/v1/libros/apu-por-hoja", { metodo: "POST", cuerpo });
}

export async function hojasDelLibro(libro: File): Promise<string[] | null> {
  const cuerpo = new FormData();
  cuerpo.append("libro", libro);
  const respuesta = await pedir<{ hojas?: unknown }>("/v1/libros/hojas", { metodo: "POST", cuerpo });
  const hojas = respuesta.hojas;
  return Array.isArray(hojas) && hojas.every((h) => typeof h === "string") ? hojas : null;
}

const hojasDe = (p: { hoja_presupuesto: string | null; hojas_presupuesto?: string[] }): string[] =>
  p.hojas_presupuesto && p.hojas_presupuesto.length > 0 ? p.hojas_presupuesto : p.hoja_presupuesto ? [p.hoja_presupuesto] : [];

const lasHojas = (hojas: string[]) => (hojas.length === 1 ? `la hoja ${hojas[0]}` : `las hojas ${enumeradas(hojas)}`);

// Las hojas se comparan como en el servidor: sin mayúsculas ni espacios de más.
const igualada = (hoja: string) => hoja.replace(/\s+/g, " ").trim().toLocaleLowerCase("es");

const POR_OMISION = "apu_por_hoja";
// La hoja que lee el perfil de siempre cuando no se pudo leer la lista de perfiles.
const POR_OMISION_HOJA = "PRESUPUESTO";
const RUTA_PERFILES = "/v1/libros/perfiles-apu-por-hoja";
const AVISO_OTRA_OBRA = "AH11";
const ID_TITULO_OTRA_OBRA = "auditoria-apu-por-hoja-otra-obra";
const TITULO_OTRA_OBRA = "La hoja del presupuesto parece de otra obra";
const origenDe = (origen: "paquete" | "local") => (origen === "local" ? "de esta instalación" : "del paquete");

function textoDelPerfil(p: PerfilDisponible): string {
  return p.motivo !== null || p.hoja_presupuesto === null
    ? `${p.nombre} · no se puede usar: ${p.motivo ?? "sin hoja de presupuesto"}`
    : `${p.nombre} · lee ${lasHojas(hojasDe(p))} (${origenDe(p.origen)})`;
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
  // La obra elegida en la barra (su nombre) y si la cuenta puede editar su Hoja (`editar_hoja`).
  obra?: string | null;
  puedeLlevar?: boolean;
}

// Lo que se auditó, tal cual, para llevarlo después a la Hoja con los mismos archivos y las mismas hojas.
interface Auditado {
  libro: File;
  presupuesto: File | null;
  perfil: string | null;
  hojas: string[];
}

export function AuditarApuPorHoja({ alExpirar, obra = null, puedeLlevar = false }: Props): JSX.Element {
  const [libro, setLibro] = useState<File | null>(null);
  const [presupuesto, setPresupuesto] = useState<File | null>(null);
  const [informe, setInforme] = useState<InformeApuPorHoja | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [auditando, setAuditando] = useState(false);
  const [auditado, setAuditado] = useState<Auditado | null>(null);
  const lista = useCarga<PerfilDisponible[]>(RUTA_PERFILES, alExpirar);
  const perfiles = lista.estado === "listo" ? lista.datos : null;
  const sinLista = lista.estado !== "listo" && lista.estado !== "cargando";
  const [elegido, setElegido] = useState<string | null>(null);
  const perfil = elegido ?? (perfiles ? perfilInicial(perfiles) : null);
  // Las hojas del libro del presupuesto (null: sin libro o no se pudieron leer) y las que la persona marcó (null: las del
  // perfil que el libro tiene).
  const [hojasDelPresupuesto, setHojasDelPresupuesto] = useState<string[] | null>(null);
  const [marcadas, setMarcadas] = useState<string[] | null>(null);
  const delPerfil = hojasDe(perfiles?.find((p) => p.nombre === perfil) ?? { hoja_presupuesto: POR_OMISION_HOJA });
  const porOmision = (hojasDelPresupuesto ?? []).filter((h) => delPerfil.some((d) => igualada(d) === igualada(h)));
  const hojas = hojasDelPresupuesto === null ? [] : (marcadas ?? porOmision);

  async function elegirPresupuesto(archivo: File) {
    setPresupuesto(archivo);
    setHojasDelPresupuesto(null);
    setMarcadas(null);
    try {
      setHojasDelPresupuesto(await hojasDelLibro(archivo));
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      // sin la lista de hojas decide el perfil: el error del libro lo dirá la auditoría
    }
  }

  function marcar(hoja: string, marcada: boolean) {
    const actuales = marcadas ?? porOmision;
    setMarcadas(marcada ? (hojasDelPresupuesto ?? []).filter((h) => h === hoja || actuales.includes(h)) : actuales.filter((h) => h !== hoja));
  }

  async function auditar() {
    if (libro === null) return;
    setError(null);
    setInforme(null);
    setAuditado(null);
    setAuditando(true);
    const enviadas = presupuesto ? hojas : [];
    try {
      setInforme(await auditarApuPorHoja(libro, presupuesto, perfil, enviadas));
      setAuditado({ libro, presupuesto, perfil, hojas: enviadas });
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
          helperText="Dice cómo leer las hojas de APU y qué hojas del presupuesto se marcan al elegirlo."
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
        alElegir={(archivo) => void elegirPresupuesto(archivo)}
        deshabilitada={auditando}
      />
      {hojasDelPresupuesto !== null && hojasDelPresupuesto.length > 0 && (
        <fieldset className="cds--fieldset">
          <legend className="cds--label">Hojas del presupuesto que se comparan</legend>
          {porOmision.length === 0 && delPerfil.length > 0 && (
            <p className="silice-inicio__nota cds--type-body-compact-01">
              {`El perfil lee ${lasHojas(delPerfil)}, que este libro no tiene: marque las hojas que quiere comparar.`}
            </p>
          )}
          {hojasDelPresupuesto.map((h, i) => (
            <Checkbox
              key={h}
              id={`auditoria-apu-hoja-${i}`}
              labelText={h}
              checked={hojas.includes(h)}
              disabled={auditando}
              onChange={(_e, { checked }) => marcar(h, checked)}
            />
          ))}
        </fieldset>
      )}
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
      {informe && auditado && puedeLlevar && <LlevarALaHoja auditado={auditado} obra={obra} alExpirar={alExpirar} />}
    </section>
  );
}

function Informe({ informe }: { informe: InformeApuPorHoja }): JSX.Element {
  const origen = origenDe(informe.origen_perfil);
  const leidas = hojasDe({ hoja_presupuesto: informe.hoja_presupuesto, hojas_presupuesto: informe.hojas_presupuesto });
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
          ? ` · con ${informe.presupuesto}${leidas.length > 0 ? ` (${leidas.length === 1 ? "hoja" : "hojas"} ${enumeradas(leidas)})` : ""}`
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

interface PartidaLlevada {
  codigo: string;
  codigo_libro: string;
  hoja: string;
  nueva: boolean;
  precio_impreso: string;
  precio_hoja: string | null;
  casa: boolean;
}

interface LibroLlevado {
  borrador_id: string;
  renglones: number;
  partidas: PartidaLlevada[];
  sin_apu: string[];
  sin_cantidad: string[];
  lista: string;
  moneda: string;
}

const COLUMNAS_LLEVADAS: ColumnaDensa[] = [
  { clave: "codigo", titulo: "Código en Sílice", ordenable: false },
  { clave: "hoja", titulo: "Hoja del libro", ordenable: false },
  { clave: "impreso", titulo: "P.U. del libro", numerica: true, ordenable: false, presentar: formatoEsVe },
  { clave: "hoja_pu", titulo: "P.U. en la Hoja", numerica: true, ordenable: false, presentar: formatoEsVe },
  { clave: "casa", titulo: "¿Casa?", ordenable: false },
];

function LlevarALaHoja({ auditado, obra, alExpirar }: { auditado: Auditado; obra: string | null; alExpirar: () => void }): JSX.Element {
  const [moneda, setMoneda] = useState("");
  const [frente, setFrente] = useState("");
  const [llevando, setLlevando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [llevado, setLlevado] = useState<LibroLlevado | null>(null);

  if (obra === null) {
    return <p className="silice-inicio__nota cds--type-body-compact-01">Elija una obra en la barra de arriba para llevar el libro a su Hoja.</p>;
  }

  async function llevar() {
    if (obra === null || !moneda) return;
    setError(null);
    setLlevado(null);
    setLlevando(true);
    const cuerpo = new FormData();
    cuerpo.append("libro", auditado.libro);
    if (auditado.presupuesto) cuerpo.append("presupuesto", auditado.presupuesto);
    if (auditado.perfil) cuerpo.append("perfil", auditado.perfil);
    for (const hoja of auditado.hojas) cuerpo.append("hoja_presupuesto", hoja);
    cuerpo.append("proyecto", obra);
    cuerpo.append("moneda", moneda);
    if (!auditado.presupuesto && frente.trim()) cuerpo.append("frente", frente.trim());
    try {
      setLlevado(await pedir<LibroLlevado>("/v1/hoja/libro", { metodo: "POST", cuerpo }));
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    } finally {
      setLlevando(false);
    }
  }

  const filas = (llevado?.partidas ?? []).map((p) => ({
    id: p.codigo,
    codigo: p.codigo === p.codigo_libro ? p.codigo : `${p.codigo} (del libro: ${p.codigo_libro})`,
    hoja: p.hoja,
    impreso: p.precio_impreso,
    hoja_pu: p.precio_hoja ?? "Pendiente",
    casa: p.casa ? "Casa" : "No casa",
  }));
  return (
    <section aria-labelledby="auditoria-apu-llevar" className="silice-inicio__bloque">
      <h3 id="auditoria-apu-llevar" className="cds--type-heading-compact-01">
        Llevar el libro a la Hoja
      </h3>
      <p className="silice-inicio__nota cds--type-body-compact-01">
        Cada APU entra al catálogo con sus materiales, equipos y mano de obra, y cada renglón del presupuesto a la Hoja de la
        obra con su cantidad y su frente (la hoja del presupuesto). Los precios quedan con su fuente: el libro y la celda.
        Nada se guarda como versión hasta que lo guarde en la Hoja.
      </p>
      <Select
        id="auditoria-apu-moneda"
        labelText="Moneda de los precios del libro"
        value={moneda}
        onChange={(e) => setMoneda(e.target.value)}
        disabled={llevando}
      >
        <SelectItem value="" text="Elija la moneda" />
        {MONEDAS.map((m) => (
          <SelectItem key={m} value={m} text={rotuloDeMoneda(m)} />
        ))}
      </Select>
      {!auditado.presupuesto && (
        <CampoTexto
          id="auditoria-apu-frente"
          labelText="Frente de los renglones (opcional)"
          value={frente}
          onChange={(e) => setFrente(e.target.value)}
          disabled={llevando}
        />
      )}
      <div className="silice-inicio__acciones">
        <Button kind="primary" size="md" disabled={!moneda || llevando} onClick={() => void llevar()}>
          {`Llevar el libro a la Hoja de «${obra}»`}
        </Button>
        {llevando && <InlineLoading description="Llevando el libro a la Hoja..." />}
      </div>
      <AvisoError error={error} titulo="No se llevó el libro" />
      {llevado && (
        <>
          <InlineNotification
            kind="success"
            role="status"
            title={`Se llevaron ${llevado.renglones} renglones a la Hoja de «${obra}», sin guardar: ábrala para revisarlos y guardar la versión.`}
            lowContrast
            hideCloseButton
          />
          <TablaDensa etiqueta="Partidas llevadas a la Hoja" columnas={COLUMNAS_LLEVADAS} filas={filas} />
          {llevado.sin_apu.length > 0 && (
            <p className="silice-inicio__nota cds--type-body-compact-01">{`No se llevaron, sin hoja de APU: ${enumeradas(llevado.sin_apu)}.`}</p>
          )}
          {llevado.sin_cantidad.length > 0 && (
            <p className="silice-inicio__nota cds--type-body-compact-01">{`No se llevaron, sin cantidad: ${enumeradas(llevado.sin_cantidad)}.`}</p>
          )}
        </>
      )}
    </section>
  );
}
