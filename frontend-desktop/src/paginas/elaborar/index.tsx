import { Button, Checkbox, RadioButton, RadioButtonGroup, Select, SelectItem, TextInput } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { InformeAuditoria } from "../../comun/InformeAuditoria";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { PlanDeTrabajo } from "./PlanDeTrabajo";
import {
  AVISO_SIN_PARTIDAS_CIVILES,
  AYUDA,
  CODIGO_POR_DEFECTO,
  DOMINIOS,
  ERROR_COMPUTO_CAMBIO,
  ERROR_SIN_ITEMS_PLAN,
  ERROR_SIN_ITEMS_RENDIMIENTO,
  MONEDA_POR_DEFECTO,
  SIN_HALLAZGOS,
  TEXTO_PENDIENTES,
  TEXTO_RENDIMIENTOS,
  aceptarPropuesta,
  calcular,
  errorSinPropuestaDeRendimiento,
  errorSinTipo,
  filasDeItems,
  filasDePartidas,
  filasIguales,
  hoy,
  lineaPendiente,
  lineaPropuesta,
  mapeoCodigos,
  textoDispersion,
  textoPropuestaRendimiento,
} from "./logica";
import type {
  CalculoRespuesta,
  CuerpoCalculo,
  Dominio,
  FilaPlan,
  ItemComputo,
  PartidaCatalogo,
  PendienteConPropuestas,
  RendimientoPorDeclarar,
  TipoRendimiento,
} from "./tipos";
import "./elaborar.scss";

type ClaveCivil = "concreto" | "encofrado" | "excavacion" | "tuberia" | "relleno";
const SELECTORES_CIVIL: { clave: ClaveCivil; titulo: string }[] = [
  { clave: "concreto", titulo: "Concreto" },
  { clave: "encofrado", titulo: "Encofrado" },
  { clave: "excavacion", titulo: "Excavación" },
  { clave: "tuberia", titulo: "Tubería" },
];

interface Elaboracion {
  respuesta: CalculoRespuesta;
  // El cuerpo con que se calculo: el libro de Excel se pide con el mismo (RA-6).
  cuerpo: CuerpoCalculo;
}

function Metrica({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="silice-elaborar__metrica">
      <span className="silice-elaborar__metrica-titulo cds--type-label-01">{titulo}</span>
      <span className="silice-elaborar__metrica-valor cds--type-heading-03">{valor}</span>
    </div>
  );
}

function Pendiente({
  indice,
  pendiente,
  elegido,
  alElegir,
  alAplicar,
  ocupado,
}: {
  indice: number;
  pendiente: PendienteConPropuestas;
  elegido: string;
  alElegir: (codigo: string) => void;
  alAplicar: () => void;
  ocupado: boolean;
}) {
  return (
    <div className="silice-elaborar__pendiente">
      <p className="cds--type-body-compact-01">{lineaPendiente(pendiente)}</p>
      {pendiente.falla !== null && <p className="silice-elaborar__nota cds--type-label-01">{pendiente.falla}</p>}
      {pendiente.propuestas.length > 0 && (
        <>
          <ul className="silice-elaborar__propuestas cds--type-body-compact-01">
            {pendiente.propuestas.map((s) => (
              <li key={s.codigo}>{lineaPropuesta(s)}</li>
            ))}
          </ul>
          <div className="silice-elaborar__fila-accion">
            <Select
              id={`elaborar-propuesta-${indice}`}
              labelText={`Propuesta para ${pendiente.origen_id}`}
              size="sm"
              value={elegido}
              onChange={(e) => alElegir(e.target.value)}
            >
              {pendiente.propuestas.map((s) => (
                <SelectItem key={s.codigo} value={s.codigo} text={s.codigo} />
              ))}
            </Select>
            <Button kind="tertiary" size="sm" disabled={ocupado} onClick={alAplicar}>
              Aplicar y volver a elaborar
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

// «Elaborar un presupuesto» (UC-01): extrae el computo de un CSV con el adaptador del dominio y elabora el presupuesto
// SIN guardarlo (RA-3). La auditoria se muestra siempre. La interfaz no calcula montos: los muestra como llegan.
export default function PaginaElaborar() {
  const { sesion, alExpirar } = useAplicacion();

  // Parametros
  const [dominio, setDominio] = useState<Dominio>("civil");
  const [codigo, setCodigo] = useState(CODIGO_POR_DEFECTO);
  const [fecha, setFecha] = useState(hoy);
  const [moneda, setMoneda] = useState(MONEDA_POR_DEFECTO);

  // Civil
  const [partidasCiviles, setPartidasCiviles] = useState<PartidaCatalogo[] | null>(null);
  const [errorPartidas, setErrorPartidas] = useState<unknown>(null);
  const [seleccion, setSeleccion] = useState<Partial<Record<ClaveCivil, string>>>({});
  const [conRelleno, setConRelleno] = useState(false);

  // Computo
  const [archivo, setArchivo] = useState<File | null>(null);
  const [items, setItems] = useState<ItemComputo[] | null>(null);
  const [extrayendo, setExtrayendo] = useState(false);
  const [errorExtraer, setErrorExtraer] = useState<unknown>(null);

  // Elaboracion
  const [elaboracion, setElaboracion] = useState<Elaboracion | null>(null);
  const [elaborando, setElaborando] = useState(false);
  const [errorElaborar, setErrorElaborar] = useState<unknown>(null);
  const [elegidas, setElegidas] = useState<Record<number, string>>({});

  // Plan de trabajo (UC-01 6)
  const [plan, setPlan] = useState<FilaPlan[]>([]);
  const [planReiniciado, setPlanReiniciado] = useState(false);
  // Las filas del plan por defecto de la ultima elaboracion sin plan del proyectista: el aviso compara con ellas.
  const precargado = useRef<FilaPlan[]>([]);
  const planActual = useRef<FilaPlan[]>([]);
  useEffect(() => {
    planActual.current = plan;
  }, [plan]);

  // Rendimientos por declarar (UC-01 3b)
  const [rendimientos, setRendimientos] = useState<RendimientoPorDeclarar[]>([]);
  const [tipos, setTipos] = useState<Record<string, TipoRendimiento>>({});
  const [errorRendimiento, setErrorRendimiento] = useState<unknown>(null);

  const secuencia = useRef(0);

  useEffect(() => {
    if (dominio !== "civil" || partidasCiviles !== null) return;
    let vigente = true;
    pedir<PartidaCatalogo[]>("/partidas?dominio=civil").then(
      (partidas) => {
        if (vigente) setPartidasCiviles(partidas.filter((p) => p.dominio === "civil"));
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setErrorPartidas(error);
        setPartidasCiviles([]);
      },
    );
    return () => {
      vigente = false;
    };
  }, [dominio, partidasCiviles, alExpirar]);

  const esCivil = dominio === "civil";
  const cargandoPartidas = esCivil && partidasCiviles === null;
  const sinPartidasCiviles = esCivil && partidasCiviles !== null && partidasCiviles.length === 0;
  const hayItems = items !== null && items.length > 0;

  function codigoElegido(clave: ClaveCivil): string {
    return seleccion[clave] ?? partidasCiviles?.[0]?.codigo ?? "";
  }

  const puedeExtraer = archivo !== null && !extrayendo && (!esCivil || (partidasCiviles?.length ?? 0) > 0);

  async function extraer() {
    if (!archivo) return;
    const datos = new FormData();
    datos.append("archivo", archivo);
    if (esCivil) {
      datos.append(
        "codigos",
        JSON.stringify(
          mapeoCodigos({
            concreto: codigoElegido("concreto"),
            encofrado: codigoElegido("encofrado"),
            excavacion: codigoElegido("excavacion"),
            tuberia: codigoElegido("tuberia"),
            relleno: conRelleno ? codigoElegido("relleno") : null,
          }),
        ),
      );
    }
    setExtrayendo(true);
    setErrorExtraer(null);
    setErrorElaborar(null);
    try {
      const lista = await pedir<ItemComputo[]>(`/v1/computos/${dominio}`, { metodo: "POST", cuerpo: datos });
      setItems(lista);
      setElaboracion(null);
      setRendimientos([]);
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setItems(null);
      setErrorExtraer(error);
    } finally {
      setExtrayendo(false);
    }
  }

  // Elabora `lista`; con `filasPlan`, con el plan del proyectista. Sin el, usa el plan por defecto y precarga la tabla.
  // Si falla, muestra el error: con el plan del proyectista el presupuesto anterior sigue a la vista; sin el, se borra.
  async function elaborar(lista: ItemComputo[], filasPlan?: FilaPlan[]): Promise<boolean> {
    const numero = ++secuencia.current;
    const cuerpo: CuerpoCalculo = { codigo, fecha, moneda, items: lista, ...(filasPlan ? { plan: filasPlan } : {}) };
    setElaborando(true);
    setErrorElaborar(null);
    try {
      const resultado = await calcular(cuerpo, sesion.csrf);
      if (numero !== secuencia.current) return false;
      if (resultado.tipo === "rendimientos") {
        setRendimientos(resultado.lista);
        setErrorRendimiento(null);
        setElaboracion(null);
        return false;
      }
      const respuesta = resultado.respuesta;
      setElaboracion({ respuesta, cuerpo });
      setElegidas({});
      setRendimientos([]);
      if (filasPlan) {
        setPlanReiniciado(false);
      } else {
        // Editado = distinto del plan por defecto que se precargo, no del nuevo: si el computo cambio, el nuevo
        // difiere aunque nadie haya tocado la tabla.
        const anteriores = planActual.current;
        setPlanReiniciado(anteriores.length > 0 && !filasIguales(anteriores, precargado.current));
        precargado.current = respuesta.plan_por_defecto;
        setPlan(respuesta.plan_por_defecto);
      }
      return true;
    } catch (error) {
      if (numero !== secuencia.current) return false;
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      if (!filasPlan) setElaboracion(null);
      setErrorElaborar(error);
      return false;
    } finally {
      if (numero === secuencia.current) setElaborando(false);
    }
  }

  async function aceptar(pendiente: PendienteConPropuestas, elegido: string) {
    const nuevos = items ? aceptarPropuesta(items, pendiente, elegido) : null;
    if (!nuevos) {
      // El computo cambio (o una extraccion fallo) despues de esta elaboracion (RA-5).
      setErrorElaborar(ERROR_COMPUTO_CAMBIO);
      return;
    }
    setItems(nuevos);
    await elaborar(nuevos);
  }

  async function aplicarPlan() {
    if (!hayItems || !items) {
      setErrorElaborar(ERROR_SIN_ITEMS_PLAN);
      return;
    }
    await elaborar(items, plan);
  }

  async function registrar(entrada: RendimientoPorDeclarar) {
    const tipo = tipos[entrada.codigo_partida];
    if (!tipo) {
      setErrorRendimiento(errorSinTipo(entrada.codigo_partida));
      return;
    }
    if (!hayItems || !items) {
      setErrorRendimiento(ERROR_SIN_ITEMS_RENDIMIENTO);
      return;
    }
    setErrorRendimiento(null);
    setElaborando(true);
    try {
      await pedir("/presupuestos/calcular/declarar-rendimiento", {
        metodo: "POST",
        cuerpo: { codigo_partida: entrada.codigo_partida, tipo, fecha },
      });
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setErrorRendimiento(error);
      setElaborando(false);
      return;
    }
    await elaborar(items);
  }

  const resultado = elaboracion?.respuesta ?? null;

  return (
    <div className="silice-elaborar">
      <h1 className="cds--type-heading-04">Elaborar un presupuesto</h1>
      <p className="cds--type-body-compact-01">{AYUDA}</p>

      <section className="silice-elaborar__parametros" aria-label="Parámetros">
        <Select
          id="elaborar-dominio"
          labelText="Dominio"
          size="sm"
          value={dominio}
          onChange={(e) => setDominio(e.target.value as Dominio)}
        >
          {DOMINIOS.map((d) => (
            <SelectItem key={d} value={d} text={d} />
          ))}
        </Select>
        <TextInput
          id="elaborar-codigo"
          labelText="Código del presupuesto"
          size="sm"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
        />
        <TextInput
          id="elaborar-fecha"
          labelText="Fecha"
          size="sm"
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
        />
        <TextInput
          id="elaborar-moneda"
          labelText="Moneda"
          size="sm"
          value={moneda}
          onChange={(e) => setMoneda(e.target.value)}
        />
      </section>

      {esCivil && (
        <section className="silice-elaborar__civil" aria-label="Códigos de partida (civil)">
          <h2 className="cds--type-heading-compact-02">Códigos de partida (civil)</h2>
          <AvisoError error={errorPartidas} titulo="No se pudo leer el catálogo" />
          {cargandoPartidas && <p className="cds--type-label-01">Cargando las partidas civiles del catálogo...</p>}
          {sinPartidasCiviles && (
            <p className="silice-elaborar__aviso cds--type-body-compact-01" role="status">
              {AVISO_SIN_PARTIDAS_CIVILES}
            </p>
          )}
          {partidasCiviles !== null && partidasCiviles.length > 0 && (
            <div className="silice-elaborar__selectores">
              {SELECTORES_CIVIL.map(({ clave, titulo }) => (
                <Select
                  key={clave}
                  id={`elaborar-civil-${clave}`}
                  labelText={titulo}
                  size="sm"
                  value={codigoElegido(clave)}
                  onChange={(e) => setSeleccion({ ...seleccion, [clave]: e.target.value })}
                >
                  {partidasCiviles.map((p) => (
                    <SelectItem key={p.codigo} value={p.codigo} text={`${p.codigo} · ${p.descripcion}`} />
                  ))}
                </Select>
              ))}
              <Checkbox
                id="elaborar-civil-con-relleno"
                labelText="Incluir relleno (balance R5)"
                checked={conRelleno}
                onChange={(_e, { checked }) => setConRelleno(checked)}
              />
              {conRelleno && (
                <Select
                  id="elaborar-civil-relleno"
                  labelText="Relleno"
                  size="sm"
                  value={codigoElegido("relleno")}
                  onChange={(e) => setSeleccion({ ...seleccion, relleno: e.target.value })}
                >
                  {partidasCiviles.map((p) => (
                    <SelectItem key={p.codigo} value={p.codigo} text={`${p.codigo} · ${p.descripcion}`} />
                  ))}
                </Select>
              )}
            </div>
          )}
        </section>
      )}

      <section className="silice-elaborar__archivo" aria-label="Archivo de muestra">
        <SubidaArchivo
          id="elaborar-archivo"
          etiqueta="Archivo de muestra (CSV)"
          extensiones={[".csv"]}
          alElegir={setArchivo}
        />
        {archivo && <p className="cds--type-label-01">Archivo elegido: {archivo.name}</p>}
        <Button kind="secondary" size="md" disabled={!puedeExtraer} onClick={() => void extraer()}>
          {extrayendo ? "Extrayendo..." : "Extraer cómputo"}
        </Button>
        <AvisoError error={errorExtraer} titulo="No se pudo extraer el cómputo" alCerrar={() => setErrorExtraer(null)} />
      </section>

      {hayItems && items && (
        <section aria-label="Cómputo extraído" className="silice-elaborar__bloque">
          <h2 className="cds--type-heading-03">Cómputo extraído</h2>
          <TablaDensa
            etiqueta="Cómputo extraído"
            columnas={[
              { clave: "codigo_partida", titulo: "codigo_partida" },
              { clave: "descripcion", titulo: "descripcion" },
              { clave: "unidad", titulo: "unidad" },
              { clave: "cantidad", titulo: "cantidad", numerica: true },
              { clave: "origen_id", titulo: "origen_id" },
              { clave: "origen_tipo", titulo: "origen_tipo" },
              { clave: "regla", titulo: "regla" },
            ]}
            filas={filasDeItems(items)}
          />
        </section>
      )}

      {hayItems && items && (
        <div className="silice-elaborar__acciones">
          <Button kind="primary" size="md" disabled={elaborando} onClick={() => void elaborar(items)}>
            {elaborando ? "Elaborando..." : "Elaborar presupuesto"}
          </Button>
        </div>
      )}
      <AvisoError error={errorElaborar} titulo="No se pudo elaborar el presupuesto" alCerrar={() => setErrorElaborar(null)} />

      {rendimientos.length > 0 && (
        <section aria-label="Rendimientos por declarar" className="silice-elaborar__bloque">
          <h2 className="cds--type-heading-03">Rendimientos por declarar</h2>
          <p className="cds--type-body-compact-01">{TEXTO_RENDIMIENTOS}</p>
          {rendimientos.map((entrada) => {
            const cod = entrada.codigo_partida;
            if (entrada.propuesta === null) {
              return <AvisoError key={cod} error={errorSinPropuestaDeRendimiento(cod)} titulo="Sin rendimiento que proponer" />;
            }
            return (
              <div key={cod} className="silice-elaborar__rendimiento">
                <p className="cds--type-body-compact-01">
                  <strong>{cod}</strong>
                  {` · ${textoPropuestaRendimiento(entrada)}`}
                </p>
                <p className="silice-elaborar__nota cds--type-label-01">{textoDispersion(entrada)}</p>
                <RadioButtonGroup
                  legendText={`Tipo declarado del rendimiento de ${cod}`}
                  name={`elaborar-tipo-rendimiento-${cod}`}
                  role="radiogroup"
                  valueSelected={tipos[cod]}
                  onChange={(valor) => setTipos({ ...tipos, [cod]: valor as TipoRendimiento })}
                >
                  <RadioButton id={`elaborar-tipo-${cod}-estimado`} labelText="estimado" value="estimado" />
                  <RadioButton id={`elaborar-tipo-${cod}-medido`} labelText="medido" value="medido" />
                </RadioButtonGroup>
                <Button kind="tertiary" size="sm" disabled={elaborando} onClick={() => void registrar(entrada)}>
                  Registrar y volver a elaborar
                </Button>
              </div>
            );
          })}
          <AvisoError error={errorRendimiento} titulo="No se pudo registrar el rendimiento" />
        </section>
      )}

      {resultado && elaboracion && (
        <>
          <section aria-label="Presupuesto elaborado" className="silice-elaborar__bloque">
            <h2 className="cds--type-heading-03">Presupuesto elaborado</h2>
            <div className="silice-elaborar__metricas" role="group" aria-label="Métricas del presupuesto">
              <Metrica titulo="Total del presupuesto" valor={`${resultado.total} ${resultado.moneda}`} />
              {resultado.por_severidad.map((s) => (
                <Metrica key={s.severidad} titulo={s.severidad} valor={String(s.total)} />
              ))}
            </div>
            {resultado.por_severidad.length === 0 && (
              <p className="silice-elaborar__exito cds--type-body-compact-01" role="status">
                {SIN_HALLAZGOS}
              </p>
            )}
            <TablaDensa
              etiqueta="Partidas del presupuesto"
              columnas={[
                { clave: "codigo_partida", titulo: "codigo_partida" },
                { clave: "descripcion", titulo: "descripcion" },
                { clave: "unidad", titulo: "unidad" },
                { clave: "cantidad", titulo: "cantidad", numerica: true },
                { clave: "precio_unitario", titulo: "precio_unitario", numerica: true },
                { clave: "total", titulo: "total", numerica: true },
              ]}
              filas={filasDePartidas(resultado)}
              vacio={{ titulo: "El presupuesto no tiene partidas valoradas." }}
            />
            <DescargaArchivo
              ruta="/presupuestos/calcular/excel"
              metodo="POST"
              cuerpo={elaboracion.cuerpo}
              etiqueta="Exportar a Excel"
              nombrePorOmision={`${resultado.codigo}.xlsx`}
              alExpirar={alExpirar}
            />
          </section>

          {resultado.pendientes.length > 0 && (
            <section aria-label="Pendientes" className="silice-elaborar__bloque">
              <h2 className="cds--type-heading-03">Pendientes</h2>
              <p className="cds--type-body-compact-01">{TEXTO_PENDIENTES}</p>
              {resultado.pendientes.map((p, n) => (
                <Pendiente
                  key={`${p.origen_id}-${n}`}
                  indice={n}
                  pendiente={p}
                  elegido={elegidas[n] ?? p.propuestas[0]?.codigo ?? ""}
                  alElegir={(c) => setElegidas({ ...elegidas, [n]: c })}
                  alAplicar={() => void aceptar(p, elegidas[n] ?? p.propuestas[0]?.codigo ?? "")}
                  ocupado={elaborando}
                />
              ))}
            </section>
          )}

          <section className="silice-elaborar__bloque">
            <h2 className="cds--type-heading-03">Informe de auditoria</h2>
            <InformeAuditoria informe={resultado.informe} />
          </section>

          <PlanDeTrabajo
            filas={plan}
            alCambiar={setPlan}
            reiniciado={planReiniciado}
            ocupado={elaborando}
            alAplicar={() => void aplicarPlan()}
          />
        </>
      )}
    </div>
  );
}
