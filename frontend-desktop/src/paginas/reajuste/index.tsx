import { Button, Checkbox, InlineNotification, Select, SelectItem, TextInput } from "@carbon/react";
import { useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import type { Carga } from "../inicio/useCarga";
import { FilasEditables } from "./FilasEditables";
import type { ColumnaEditable } from "./FilasEditables";
import { armarCuerpo, columnasDeResultado, filasDeResultado, formularioInicial } from "./logica";
import type { ClausulaTextos, Fila, Formulario } from "./logica";
import "./reajuste.scss";

interface ProyectoDelCaso {
  codigo: string;
  nombre: string;
}

interface VersionDelContrato {
  codigo: string;
  motivo: string;
  revalorada: boolean;
}

interface Contexto {
  versiones: VersionDelContrato[];
  periodicidades: string[];
  mecanismos: string[];
  estructuras: string[];
  componentes: string[];
}

interface Parcial {
  id: number;
  fecha_calculo: string;
}

interface Calculo {
  estado: string;
  moneda: string;
  columnas: string[];
  filas: Fila[];
  avisos: string[];
  mensaje_parcial: string;
  parciales: Parcial[];
}

const COLUMNAS_COMPONENTE: ColumnaEditable[] = [
  { clave: "componente", titulo: "Componente", fija: true },
  { clave: "serie", titulo: "Serie" },
  { clave: "peso", titulo: "Peso" },
];
const COLUMNAS_PERIODO: ColumnaEditable[] = [
  { clave: "desde", titulo: "Desde", ayuda: "AAAA-MM-DD" },
  { clave: "hasta", titulo: "Hasta", ayuda: "AAAA-MM-DD" },
  { clave: "version_comprobacion", titulo: "Versión de comprobación" },
  { clave: "excepcion", titulo: "Excepción" },
];
const COLUMNAS_EJECUTADO: ColumnaEditable[] = [
  { clave: "periodo", titulo: "Periodo" },
  { clave: "partida", titulo: "Partida" },
  { clave: "cantidad", titulo: "Cantidad" },
  { clave: "fuente", titulo: "Fuente" },
];
const ETIQUETA_RESULTADO = "Escalatoria y comprobación, lado a lado";

// 2027-02-10 -> 10/02/2027, como se ve en la pantalla de Streamlit.
function fechaCorta(iso: string): string {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

// UC-18 (spec S1 §8): la cláusula de reajuste, los periodos con lo ejecutado y su fuente, la escalatoria y la
// comprobación directa lado a lado, el guardado del estudio y su Excel. Toda cifra la calcula el servidor (RB-2);
// aquí solo se escribe y se muestra. Lo guardado es siempre lo que está en el formulario: si se cambia un dato
// después de calcular, la tabla se retira y hay que calcular de nuevo.
export default function PaginaReajuste() {
  const { alExpirar, proyecto: codigo } = useAplicacion();
  const proyectos = useCarga<ProyectoDelCaso[]>("/v1/proyectos", alExpirar);
  const nombre = proyectos.estado === "listo" ? proyectos.datos.find((p) => p.codigo === codigo)?.nombre : undefined;

  return (
    <div className="silice-reajuste">
      <h1 className="cds--type-heading-04">Reajuste de precios</h1>
      {codigo === null && (
        <EstadoVacio
          titulo="Abra un proyecto en la barra superior (Proyecto) para reajustar sus precios."
          descripcion="El estudio de reajuste se hace sobre una versión guardada del contrato."
        />
      )}
      {codigo !== null && proyectos.estado === "cargando" && <EsqueletoPagina etiqueta="Cargando el proyecto" />}
      {codigo !== null && nombre !== undefined && <Estudio key={nombre} proyecto={nombre} alExpirar={alExpirar} />}
      <MensajeDeCarga carga={proyectos} />
    </div>
  );
}

function MensajeDeCarga({ carga }: { carga: Carga<unknown> }) {
  if (carga.estado === "error") return <AvisoError error={carga.error} titulo="No se pudo cargar" />;
  if (carga.estado === "sin_permiso") {
    return <AvisoError error="Su cuenta no tiene permiso para esta acción." titulo="Sin permiso" />;
  }
  if (carga.estado === "no_disponible") return <AvisoError error="No se encontró lo pedido." titulo="No disponible" />;
  return null;
}

function Estudio({ proyecto, alExpirar }: { proyecto: string; alExpirar: () => void }) {
  const contexto = useCarga<Contexto>(`/v1/reajuste/contexto?proyecto=${encodeURIComponent(proyecto)}`, alExpirar);
  if (contexto.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las versiones" />;
  if (contexto.estado !== "listo") return <MensajeDeCarga carga={contexto} />;
  if (contexto.datos.versiones.length === 0) {
    return (
      <EstadoVacio titulo="El proyecto no tiene versiones guardadas: guarde la del contrato primero." />
    );
  }
  return <Formulario proyecto={proyecto} contexto={contexto.datos} alExpirar={alExpirar} />;
}

function Formulario({
  proyecto,
  contexto,
  alExpirar,
}: {
  proyecto: string;
  contexto: Contexto;
  alExpirar: () => void;
}) {
  const [form, setForm] = useState<Formulario>(() => ({
    ...formularioInicial(),
    version: contexto.versiones[0].codigo,
  }));
  const [calculo, setCalculo] = useState<Calculo | null>(null);
  const [guardado, setGuardado] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ocupado, setOcupado] = useState(false);
  const [fuente, setFuente] = useState("");
  const [responsable, setResponsable] = useState("");
  const [reemplaza, setReemplaza] = useState("");

  // Todo cambio del formulario retira el resultado y el aviso de guardado: ya no corresponden a lo escrito.
  const editar = (cambio: (f: Formulario) => Formulario) => {
    setForm(cambio);
    setCalculo(null);
    setGuardado(null);
    setError(null);
  };
  const campo = (clave: keyof ClausulaTextos, valor: string) =>
    editar((f) => ({ ...f, clausula: { ...f.clausula, [clave]: valor } }));

  const revaloradas = contexto.versiones.filter((v) => v.revalorada).map((v) => v.codigo);

  async function enviar<T>(ruta: string, cuerpo: object): Promise<T | undefined> {
    setOcupado(true);
    setError(null);
    try {
      return await pedir<T>(ruta, { metodo: "POST", cuerpo });
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
      return undefined;
    } finally {
      setOcupado(false);
    }
  }

  async function calcular() {
    setGuardado(null);
    setReemplaza("");
    setCalculo((await enviar<Calculo>("/v1/reajuste/calcular", armarCuerpo(proyecto, form))) ?? null);
  }

  async function guardar() {
    const respuesta = await enviar<{ estudio: number; estado: string }>("/v1/reajuste/guardar", {
      ...armarCuerpo(proyecto, form),
      fuente,
      responsable,
      reemplaza_a: reemplaza === "" ? null : Number(reemplaza),
    });
    if (respuesta) setGuardado(`Estudio ${respuesta.estudio} guardado (${respuesta.estado}).`);
  }

  return (
    <>
      <Select
        id="reajuste-version"
        labelText="Versión del contrato"
        value={form.version}
        onChange={(e) => editar((f) => ({ ...f, version: e.target.value }))}
      >
        {contexto.versiones.map((v) => (
          <SelectItem key={v.codigo} value={v.codigo} text={v.codigo} />
        ))}
      </Select>

      <section className="silice-reajuste__bloque" aria-labelledby="reajuste-clausula">
        <h2 id="reajuste-clausula" className="cds--type-heading-03">
          1. La cláusula de reajuste (S1 §8.1, a cotejar con la Gaceta)
        </h2>
        <div className="silice-reajuste__rejilla">
          <TextInput id="rj-inicio" labelText="Inicio del contrato" placeholder="AAAA-MM-DD" value={form.clausula.fecha_inicio} onChange={(e) => campo("fecha_inicio", e.target.value)} />
          <TextInput id="rj-duracion" labelText="Duración (meses)" value={form.clausula.duracion_meses} onChange={(e) => campo("duracion_meses", e.target.value)} />
          <TextInput id="rj-primer" labelText="El primer año corre desde" helperText="Por defecto, el inicio del contrato (a cotejar)." placeholder="AAAA-MM-DD" value={form.clausula.fecha_referencia_primer_anio} onChange={(e) => campo("fecha_referencia_primer_anio", e.target.value)} />
          <Select id="rj-periodicidad" labelText="Periodicidad" value={form.clausula.periodicidad} onChange={(e) => campo("periodicidad", e.target.value)}>
            {contexto.periodicidades.map((p) => (
              <SelectItem key={p} value={p} text={p} />
            ))}
          </Select>
          <Select id="rj-mecanismo" labelText="Mecanismo" value={form.clausula.mecanismo} onChange={(e) => campo("mecanismo", e.target.value)}>
            {contexto.mecanismos.map((m) => (
              <SelectItem key={m} value={m} text={m} />
            ))}
          </Select>
          <Select id="rj-pagadero" labelText="Mecanismo pagadero (solo con «ambos»)" value={form.clausula.mecanismo_pagadero} onChange={(e) => campo("mecanismo_pagadero", e.target.value)}>
            <SelectItem value="" text="" />
            {contexto.mecanismos
              .filter((m) => m !== "ambos")
              .map((m) => (
                <SelectItem key={m} value={m} text={m} />
              ))}
          </Select>
          <TextInput id="rj-fuente-pagadero" labelText="Fuente del mecanismo pagadero" value={form.clausula.fuente_pagadero} onChange={(e) => campo("fuente_pagadero", e.target.value)} />
          <Select id="rj-estructura" labelText="Estructura" value={form.clausula.estructura} onChange={(e) => campo("estructura", e.target.value)}>
            {contexto.estructuras.map((x) => (
              <SelectItem key={x} value={x} text={x} />
            ))}
          </Select>
          <TextInput id="rj-base" labelText="Mes base de los índices (I0)" placeholder="AAAA-MM-DD" value={form.clausula.fecha_base_indices} onChange={(e) => campo("fecha_base_indices", e.target.value)} />
          <TextInput id="rj-r" labelText="R (fracción no reajustable)" value={form.clausula.r} onChange={(e) => campo("r", e.target.value)} />
          <TextInput id="rj-fuente-r" labelText="Fuente de R" helperText="Si el contrato no la trae, escriba 0 y declárelo." value={form.clausula.fuente_r} onChange={(e) => campo("fuente_r", e.target.value)} />
          <TextInput id="rj-fuente" labelText="Fuente de la cláusula" helperText="Contrato, número, fecha." value={form.clausula.fuente} onChange={(e) => campo("fuente", e.target.value)} />
          <TextInput id="rj-responsable" labelText="Responsable" helperText="En blanco, su nombre de usuario." value={form.clausula.responsable} onChange={(e) => campo("responsable", e.target.value)} />
        </div>
        <Checkbox
          id="rj-r-comprobacion"
          labelText="La cláusula aplica R también a la comprobación (S1-R14)"
          checked={form.clausula.r_en_comprobacion === "si"}
          onChange={(_, { checked }) => campo("r_en_comprobacion", checked ? "si" : "no")}
        />
        <p className="silice-reajuste__nota cds--type-body-compact-01">
          Componentes: la serie de cada uno y, si la estructura es declarada, su peso.
        </p>
        <FilasEditables
          etiqueta="Componentes"
          columnas={COLUMNAS_COMPONENTE}
          filas={form.componentes}
          fijas
          alCambiar={(filas) => editar((f) => ({ ...f, componentes: filas }))}
        />
      </section>

      <section className="silice-reajuste__bloque" aria-labelledby="reajuste-periodos">
        <h2 id="reajuste-periodos" className="cds--type-heading-03">
          2. Periodos y lo ejecutado (con su fuente)
        </h2>
        <p className="silice-reajuste__nota cds--type-body-compact-01">
          {`Versiones revaloradas para la comprobación directa: ${
            revaloradas.length > 0 ? revaloradas.join(", ") : "ninguna (la comprobación quedará «no disponible»)"
          }`}
        </p>
        <FilasEditables
          etiqueta="Periodos"
          columnas={COLUMNAS_PERIODO}
          filas={form.periodos}
          alCambiar={(filas) => editar((f) => ({ ...f, periodos: filas }))}
        />
        <Checkbox
          id="rj-valuaciones"
          labelText="Tomar lo ejecutado de las valuaciones registradas (cada una al periodo de su fecha hasta)"
          checked={form.con_valuaciones}
          onChange={(_, { checked }) => editar((f) => ({ ...f, con_valuaciones: checked }))}
        />
        {form.con_valuaciones ? (
          <p className="silice-reajuste__nota cds--type-body-compact-01">
            Lo ejecutado sale de las valuaciones no anuladas y el estudio las cita.
          </p>
        ) : (
          <>
            <FilasEditables
              etiqueta="Ejecutado"
              columnas={COLUMNAS_EJECUTADO}
              filas={form.ejecutado}
              alCambiar={(filas) => editar((f) => ({ ...f, ejecutado: filas }))}
            />
            <p className="silice-reajuste__nota cds--type-body-compact-01">
              Fechas en AAAA-MM-DD. «Periodo» es el número de la fila de periodos (1, 2, ...).
            </p>
          </>
        )}
        <div>
          <Button kind="primary" size="md" disabled={ocupado} onClick={() => void calcular()}>
            Calcular
          </Button>
        </div>
      </section>

      <AvisoError error={error} titulo="No se pudo completar" alCerrar={() => setError(null)} />

      {calculo && (
        <section className="silice-reajuste__bloque" aria-labelledby="reajuste-resultado">
          <h2 id="reajuste-resultado" className="cds--type-heading-03">
            3. Escalatoria y comprobación, lado a lado
          </h2>
          <TablaDensa
            etiqueta={ETIQUETA_RESULTADO}
            columnas={columnasDeResultado(calculo.columnas)}
            filas={filasDeResultado(calculo.filas)}
          />
          {calculo.avisos.map((aviso) => (
            <InlineNotification key={aviso} kind="warning" title="Aviso" subtitle={aviso} lowContrast hideCloseButton />
          ))}
          {calculo.mensaje_parcial && (
            <InlineNotification kind="info" title="Estudio parcial" subtitle={calculo.mensaje_parcial} lowContrast hideCloseButton />
          )}

          <h2 className="cds--type-heading-03">4. Guardar el estudio</h2>
          <div className="silice-reajuste__rejilla">
            <TextInput id="rj-estudio-fuente" labelText="Fuente del estudio" value={fuente} onChange={(e) => setFuente(e.target.value)} />
            <TextInput id="rj-estudio-responsable" labelText="Responsable del estudio" helperText="En blanco, su nombre de usuario." value={responsable} onChange={(e) => setResponsable(e.target.value)} />
            {calculo.estado === "cerrado" && calculo.parciales.length > 0 && (
              <Select id="rj-reemplaza" labelText="Reemplaza al estudio parcial" value={reemplaza} onChange={(e) => setReemplaza(e.target.value)}>
                <SelectItem value="" text="ninguno" />
                {calculo.parciales.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)} text={`${p.id} (calculado el ${fechaCorta(p.fecha_calculo)})`} />
                ))}
              </Select>
            )}
          </div>
          <div className="silice-reajuste__acciones">
            <Button kind="primary" size="md" disabled={ocupado} onClick={() => void guardar()}>
              Guardar estudio
            </Button>
            <DescargaArchivo
              ruta="/v1/reajuste/excel"
              metodo="POST"
              cuerpo={armarCuerpo(proyecto, form)}
              etiqueta="Descargar Excel"
              nombrePorOmision={`reajuste_${form.version}.xlsx`}
              alExpirar={alExpirar}
            />
          </div>
          {guardado && (
            <p role="status" className="cds--type-body-compact-01">
              {guardado}
            </p>
          )}
        </section>
      )}
    </>
  );
}
