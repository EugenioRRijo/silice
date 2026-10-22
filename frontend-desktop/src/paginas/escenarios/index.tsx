import { Accordion, AccordionItem, Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { Add, TrashCan } from "@carbon/icons-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AVISO_PENDIENTES,
  AYUDA,
  CAMPOS_PARAMETROS,
  EJEMPLO_PRECIOS,
  COLUMNAS_COMPARACION,
  COLUMNAS_PARTIDAS,
  NOTA_PARAMETROS,
  NOTA_PENDIENTES,
  NOTA_PRECIOS,
  ROTULOS_PARAMETROS,
  SIN_ESCENARIOS,
  SIN_PRESUPUESTOS,
  TITULO_COMPARACION,
  armarEscenario,
  campoNombrado,
  etiquetaDePresupuesto,
  filasComparacion,
  filasPartidas,
  lineaPendiente,
  nombrePorOmision,
  notaHallazgos,
  rutaEscenarios,
} from "./logica";
import type { FilaPrecio } from "./logica";
import type {
  CampoParametro,
  EscenarioPeticion,
  EscenariosBaseRespuesta,
  EscenariosRespuesta,
  PresupuestoResumen,
} from "./tipos";
import "./escenarios.scss";
import { CampoTexto } from "../../comun/CampoTexto";

type Parametros = Record<CampoParametro, string>;

const PARAMETROS_VACIOS: Parametros = { fcas: "", bono_alimentacion: "", administracion: "", utilidad: "" };

// Dos presupuestos de proyectos distintos pueden compartir codigo: entonces la clave es la etiqueta completa.
function claveDe(p: PresupuestoResumen, todos: PresupuestoResumen[]): string {
  return todos.filter((o) => o.codigo === p.codigo).length > 1 ? etiquetaDePresupuesto(p) : p.codigo;
}

function parametrosDe(base: EscenariosBaseRespuesta): Parametros {
  return {
    fcas: base.parametros.fcas ?? "",
    bono_alimentacion: base.parametros.bono_alimentacion ?? "",
    administracion: base.parametros.administracion ?? "",
    utilidad: base.parametros.utilidad ?? "",
  };
}

// «Escenarios de sensibilidad» (UC-08): recalcula un presupuesto guardado con otros parametros o precios y lo
// compara contra el base. Nada se guarda; la API recalcula sin estado, asi que cada envio lleva todos los
// escenarios acumulados. La interfaz no calcula ningun monto.
export default function PaginaEscenarios() {
  const { alExpirar } = useAplicacion();
  const [lista, setLista] = useState<PresupuestoResumen[] | null>(null);
  const [errorLista, setErrorLista] = useState<unknown>(null);
  const [seleccion, setSeleccion] = useState<PresupuestoResumen | null>(null);
  const [base, setBase] = useState<EscenariosBaseRespuesta | null>(null);
  const [errorBase, setErrorBase] = useState<unknown>(null);
  const [peticiones, setPeticiones] = useState<EscenarioPeticion[]>([]);
  const [resultado, setResultado] = useState<EscenariosRespuesta | null>(null);
  const [nombre, setNombre] = useState<string | null>(null);
  const [parametros, setParametros] = useState<Parametros>(PARAMETROS_VACIOS);
  const [filas, setFilas] = useState<FilaPrecio[]>([]);
  const [errorGenerar, setErrorGenerar] = useState<unknown>(null);
  const [generando, setGenerando] = useState(false);
  const cargaBase = useRef(0);
  const siguienteFila = useRef(1);
  const focoPendiente = useRef<string | null>(null);

  // Foco tras anadir o quitar una fila de precios: se aplica cuando React ya la pinto.
  useLayoutEffect(() => {
    const id = focoPendiente.current;
    if (id === null) return;
    focoPendiente.current = null;
    document.getElementById(id)?.focus();
  }, [filas]);

  const campoInvalido = errorGenerar === null ? null : campoNombrado(mensajeDeError(errorGenerar));

  const falla = (error: unknown) => {
    if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
  };

  function elegir(presupuesto: PresupuestoResumen) {
    const numero = ++cargaBase.current;
    // Los escenarios pertenecen a un base: comparar contra otro no significa nada.
    setSeleccion(presupuesto);
    setBase(null);
    setErrorBase(null);
    setPeticiones([]);
    setResultado(null);
    setNombre(null);
    setFilas([]);
    setErrorGenerar(null);
    setGenerando(false);
    pedir<EscenariosBaseRespuesta>(rutaEscenarios(presupuesto.codigo, presupuesto.proyecto, "/base")).then(
      (respuesta) => {
        if (numero !== cargaBase.current) return;
        setBase(respuesta);
        setParametros(parametrosDe(respuesta));
      },
      (error: unknown) => {
        if (numero !== cargaBase.current) return;
        falla(error);
        setErrorBase(error);
      },
    );
  }

  useEffect(() => {
    let vigente = true;
    pedir<PresupuestoResumen[]>("/presupuestos").then(
      (respuesta) => {
        if (!vigente) return;
        setLista(respuesta);
        if (respuesta.length > 0) elegir(respuesta[0]);
      },
      (error: unknown) => {
        if (!vigente) return;
        falla(error);
        setErrorLista(error);
      },
    );
    return () => {
      vigente = false;
    };
    // Carga unica al montar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function generar(evento: FormEvent) {
    evento.preventDefault();
    if (!seleccion || !base || generando) return;
    const nueva = armarEscenario(nombre ?? "", parametros, filas, peticiones.length);
    const todas = [...peticiones, nueva];
    const numero = cargaBase.current;
    setGenerando(true);
    setErrorGenerar(null);
    pedir<EscenariosRespuesta>(rutaEscenarios(seleccion.codigo, seleccion.proyecto), {
      metodo: "POST",
      cuerpo: { escenarios: todas },
    }).then(
      (respuesta) => {
        if (numero !== cargaBase.current) return;
        setPeticiones(todas);
        setResultado(respuesta);
        setNombre(null);
        setGenerando(false);
      },
      (error: unknown) => {
        if (numero !== cargaBase.current) return;
        falla(error);
        setErrorGenerar(error); // el escenario nuevo no entra en la lista
        setGenerando(false);
      },
    );
  }

  function cambiarFila(id: number, cambio: Partial<FilaPrecio>) {
    setFilas((actuales) => actuales.map((f) => (f.id === id ? { ...f, ...cambio } : f)));
  }

  const encabezado = (
    <>
      <h1 className="cds--type-heading-04">Escenarios de sensibilidad</h1>
      <p className="cds--type-body-compact-01">{AYUDA}</p>
    </>
  );

  if (errorLista !== null) {
    return (
      <div className="silice-escenarios silice-pagina">
        {encabezado}
        <AvisoError error={errorLista} titulo="No se pudo leer la lista de presupuestos" />
      </div>
    );
  }
  if (lista === null) {
    return (
      <div className="silice-escenarios silice-pagina">
        {encabezado}
        <EsqueletoPagina etiqueta="Cargando los presupuestos" />
      </div>
    );
  }
  if (lista.length === 0) {
    return (
      <div className="silice-escenarios silice-pagina">
        {encabezado}
        <EstadoVacio titulo={SIN_PRESUPUESTOS} />
      </div>
    );
  }

  return (
    <div className="silice-escenarios silice-pagina">
      {encabezado}
      <div className="silice-escenarios__selector">
        <Select
          id="escenarios-base"
          labelText="Presupuesto base"
          size="sm"
          value={seleccion ? claveDe(seleccion, lista) : ""}
          onChange={(e) => {
            const elegido = lista.find((p) => claveDe(p, lista) === e.target.value);
            if (elegido) elegir(elegido);
          }}
        >
          {lista.map((p) => (
            <SelectItem key={claveDe(p, lista)} value={claveDe(p, lista)} text={etiquetaDePresupuesto(p)} />
          ))}
        </Select>
      </div>

      {errorBase !== null && <AvisoError error={errorBase} titulo="No se pudo leer el presupuesto base" />}
      {errorBase === null && base === null && <EsqueletoPagina etiqueta="Cargando el presupuesto base" />}

      {base !== null && (
        <>
          {base.pendientes_base.length > 0 && (
            <InlineNotification kind="warning" role="status" title="Pendientes" lowContrast hideCloseButton
              subtitle={undefined}>
              <div className="silice-escenarios__pendientes">
                <p>{AVISO_PENDIENTES}</p>
                <ul>
                  {base.pendientes_base.map((p) => (
                    <li key={p.origen_id}>{lineaPendiente(p)}</li>
                  ))}
                </ul>
                <p>{NOTA_PENDIENTES}</p>
              </div>
            </InlineNotification>
          )}

          <form className="silice-escenarios__formulario" onSubmit={generar}>
            <div className="silice-escenarios__nombre">
              <CampoTexto
                id="escenarios-nombre"
                size="sm"
                labelText="Nombre del escenario"
                value={nombre ?? nombrePorOmision(peticiones.length)}
                onChange={(e) => setNombre(e.target.value)}
              />
            </div>
            <p className="silice-escenarios__nota cds--type-label-01">{NOTA_PARAMETROS}</p>
            <div className="silice-escenarios__parametros">
              {CAMPOS_PARAMETROS.map((campo) => (
                <CampoTexto
                  key={campo}
                  id={`escenarios-${campo}`}
                  size="sm"
                  labelText={ROTULOS_PARAMETROS[campo]}
                  invalid={campoInvalido === campo}
                  invalidText={campoInvalido === campo ? mensajeDeError(errorGenerar) : undefined}
                  value={parametros[campo]}
                  onChange={(e) => setParametros((p) => ({ ...p, [campo]: e.target.value }))}
                />
              ))}
            </div>
            <p className="silice-escenarios__nota cds--type-label-01">{NOTA_PRECIOS}</p>
            <div className="silice-escenarios__precios" role="group" aria-label="Precios de ensayo">
              {filas.length === 0 ? (
                <p className="silice-escenarios__nota cds--type-label-01">{EJEMPLO_PRECIOS}</p>
              ) : (
                <div className="silice-escenarios__fila-precio silice-escenarios__cabecera" aria-hidden="true">
                  <span className="cds--type-label-01">Insumo (descripción exacta)</span>
                  <span className="cds--type-label-01">Precio nuevo</span>
                  <span />
                </div>
              )}
              {filas.map((fila, i) => (
                <div key={fila.id} className="silice-escenarios__fila-precio">
                  <CampoTexto
                    id={`escenarios-insumo-${fila.id}`}
                    size="sm"
                    labelText={`Insumo ${i + 1}`}
                    hideLabel
                    value={fila.insumo}
                    onChange={(e) => cambiarFila(fila.id, { insumo: e.target.value })}
                  />
                  <CampoTexto
                    id={`escenarios-precio-${fila.id}`}
                    size="sm"
                    labelText={`Precio nuevo ${i + 1}`}
                    hideLabel
                    value={fila.precio}
                    onChange={(e) => cambiarFila(fila.id, { precio: e.target.value })}
                  />
                  <Button
                    kind="ghost"
                    size="sm"
                    hasIconOnly
                    renderIcon={TrashCan}
                    iconDescription={`Quitar precio ${i + 1}`}
                    tooltipPosition="left"
                    onClick={() => {
                      const siguiente = filas[i + 1];
                      focoPendiente.current = siguiente ? `escenarios-insumo-${siguiente.id}` : "escenarios-agregar-precio";
                      setFilas((actuales) => actuales.filter((f) => f.id !== fila.id));
                    }}
                  />
                </div>
              ))}
              <div>
                <Button
                  id="escenarios-agregar-precio"
                  kind="tertiary"
                  size="sm"
                  renderIcon={Add}
                  onClick={() => {
                    const id = siguienteFila.current++;
                    focoPendiente.current = `escenarios-insumo-${id}`;
                    setFilas((actuales) => [...actuales, { id, insumo: "", precio: "" }]);
                  }}
                >
                  Agregar precio
                </Button>
              </div>
            </div>
            <div>
              <Button type="submit" kind="primary" size="sm" disabled={generando}>
                Generar escenario
              </Button>
            </div>
          </form>

          <AvisoError error={errorGenerar} titulo="No se pudo generar el escenario" alCerrar={() => setErrorGenerar(null)} />

          <div aria-live="polite" aria-atomic="false">
            {resultado === null || peticiones.length === 0 ? (
              <InlineNotification kind="info" role="status" title="Sin escenarios" subtitle={SIN_ESCENARIOS} lowContrast hideCloseButton />
            ) : (
              <section className="silice-escenarios__resultados" aria-labelledby="escenarios-comparacion">
                <h2 id="escenarios-comparacion" className="cds--type-heading-compact-02">
                  {TITULO_COMPARACION}
                </h2>
                <TablaDensa etiqueta={TITULO_COMPARACION} columnas={COLUMNAS_COMPARACION} filas={filasComparacion(resultado)} />
                <div className="silice-escenarios__acciones">
                  <DescargaArchivo
                    ruta={rutaEscenarios(base.codigo, base.proyecto, "/csv")}
                    metodo="POST"
                    cuerpo={{ escenarios: peticiones }}
                    etiqueta="Descargar tabla (CSV, valores exactos)"
                    nombrePorOmision={`escenarios_${base.codigo}.csv`}
                    alExpirar={alExpirar}
                    size="sm"
                  />
                  <Button
                    kind="ghost"
                    size="sm"
                    onClick={() => {
                      setPeticiones([]);
                      setResultado(null);
                      setNombre(null);
                    }}
                  >
                    Descartar escenarios
                  </Button>
                </div>
                <Accordion size="sm">
                  {resultado.escenarios.map((e, i) => (
                    <AccordionItem key={`${e.nombre}-${i}`} title={`Detalle por partida: ${e.nombre}`}>
                      <div className="silice-escenarios__detalle">
                        <TablaDensa
                          etiqueta={`Detalle por partida: ${e.nombre}`}
                          columnas={COLUMNAS_PARTIDAS}
                          filas={filasPartidas(e.partidas)}
                        />
                        <p className="silice-escenarios__nota cds--type-label-01">{notaHallazgos(e)}</p>
                      </div>
                    </AccordionItem>
                  ))}
                </Accordion>
              </section>
            )}
          </div>
        </>
      )}
    </div>
  );
}
