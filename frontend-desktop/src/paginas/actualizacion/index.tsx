import { Button, Checkbox, CheckboxGroup, InlineLoading, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { InformeAuditoria } from "../../comun/InformeAuditoria";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { Variacion } from "../../comun/Variacion";
import { useAplicacion } from "../../shell/contexto";
import {
  AYUDA,
  CODIGO_NUEVO_POR_DEFECTO,
  COLUMNAS_COMPARATIVO,
  EXTENSIONES,
  INDICACION_SIN_PRESUPUESTOS,
  MONEDA_POR_DEFECTO,
  SIN_PRESUPUESTOS,
  avisoDesconocidos,
  etiquetaDeAlta,
  etiquetaPresupuesto,
  filasComparativo,
  formularioRevaloracion,
  hoyIso,
  nombreDeLista,
  preguntaDescartar,
  rutaDescartar,
  rutaExcel,
  textoDadosDeAlta,
  textoDescartada,
  textoIgnorados,
  textoRechazados,
} from "./logica";
import type { InsumoDesconocido, PresupuestoListado, Revaloracion, VistaPrevia } from "./logica";
import "./actualizacion.scss";
import { CampoTexto } from "../../comun/CampoTexto";

type Presupuestos =
  | { tipo: "cargando" }
  | { tipo: "listo"; lista: PresupuestoListado[] }
  | { tipo: "error"; error: unknown };

type Vista =
  | { tipo: "ninguna" }
  | { tipo: "cargando" }
  | { tipo: "lista"; vista: VistaPrevia }
  | { tipo: "error"; error: unknown };

type Resultado =
  | { tipo: "ninguno" }
  | { tipo: "revalorando" }
  | { tipo: "listo"; respuesta: Revaloracion; proyecto: string }
  | { tipo: "error"; error: unknown };

type Descarte = { tipo: "no" } | { tipo: "confirmar" } | { tipo: "enCurso" } | { tipo: "hecho" } | { tipo: "error"; error: unknown };

// «Actualizar precios» (UC-02): una lista de precios nueva revalora un presupuesto guardado, registra que cambio y
// audita la version nueva. La interfaz no calcula nada: los montos y el resumen llegan de la API como texto.
export default function PaginaActualizacion() {
  const { alExpirar } = useAplicacion();
  const [presupuestos, setPresupuestos] = useState<Presupuestos>({ tipo: "cargando" });
  const [elegido, setElegido] = useState("0");
  const [codigoNuevo, setCodigoNuevo] = useState(CODIGO_NUEVO_POR_DEFECTO);
  const [vigencia, setVigencia] = useState(hoyIso());
  const [moneda, setMoneda] = useState(MONEDA_POR_DEFECTO);
  const [nombreManual, setNombreManual] = useState<string | null>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [vista, setVista] = useState<Vista>({ tipo: "ninguna" });
  const [marcadas, setMarcadas] = useState<ReadonlySet<number>>(new Set());
  const [resultado, setResultado] = useState<Resultado>({ tipo: "ninguno" });
  const [descarte, setDescarte] = useState<Descarte>({ tipo: "no" });
  const consultaVista = useRef(0);
  const consultaRevalorar = useRef(0);

  const nombre = nombreManual ?? nombreDeLista(vigencia);

  const expirada = (error: unknown) => {
    if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
  };

  useEffect(() => {
    let vigente = true;
    pedir<PresupuestoListado[]>("/presupuestos").then(
      (lista) => {
        if (vigente) setPresupuestos({ tipo: "listo", lista });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setPresupuestos({ tipo: "error", error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [alExpirar]);

  const elegirArchivo = (nuevo: File) => {
    const numero = ++consultaVista.current;
    setArchivo(nuevo);
    setMarcadas(new Set());
    setVista({ tipo: "cargando" });
    const cuerpo = new FormData();
    cuerpo.append("archivo", nuevo);
    pedir<VistaPrevia>("/listas-precios/vista-previa", { metodo: "POST", cuerpo }).then(
      (respuesta) => {
        if (numero === consultaVista.current) setVista({ tipo: "lista", vista: respuesta });
      },
      (error: unknown) => {
        if (numero !== consultaVista.current) return;
        expirada(error);
        setVista({ tipo: "error", error });
      },
    );
  };

  const desconocidos: InsumoDesconocido[] = vista.tipo === "lista" ? vista.vista.desconocidos : [];

  const marcar = (posicion: number, marcada: boolean) => {
    setMarcadas((previas) => {
      const siguientes = new Set(previas);
      if (marcada) siguientes.add(posicion);
      else siguientes.delete(posicion);
      return siguientes;
    });
  };

  const lista = presupuestos.tipo === "listo" ? presupuestos.lista : [];
  const base: PresupuestoListado | undefined = lista[Number(elegido)];
  const revalorando = resultado.tipo === "revalorando";

  const revalorar = (evento: FormEvent) => {
    evento.preventDefault();
    if (!archivo || !base || revalorando) return;
    const numero = ++consultaRevalorar.current;
    const cuerpo = formularioRevaloracion({
      archivo,
      proyecto: base.proyecto,
      codigo: base.codigo,
      codigoNuevo,
      nombre,
      moneda,
      vigenciaIso: vigencia,
      marcadas,
      desconocidos,
    });
    // Una revaloracion nueva olvida el descarte de la anterior.
    setDescarte({ tipo: "no" });
    setResultado({ tipo: "revalorando" });
    pedir<Revaloracion>("/presupuestos/revalorar", { metodo: "POST", cuerpo }).then(
      (respuesta) => {
        if (numero === consultaRevalorar.current)
          setResultado({ tipo: "listo", respuesta, proyecto: base.proyecto });
      },
      (error: unknown) => {
        if (numero !== consultaRevalorar.current) return;
        expirada(error);
        setResultado({ tipo: "error", error });
      },
    );
  };

  const descartar = (codigo: string, proyecto: string) => {
    setDescarte({ tipo: "enCurso" });
    pedir(rutaDescartar(codigo, proyecto), { metodo: "POST" }).then(
      () => setDescarte({ tipo: "hecho" }),
      (error: unknown) => {
        expirada(error);
        setDescarte({ tipo: "error", error });
      },
    );
  };

  return (
    <div className="silice-actualizacion silice-pagina">
      <h1 className="cds--type-heading-04">Actualizar precios</h1>
      <p className="cds--type-body-compact-01">{AYUDA}</p>

      {presupuestos.tipo === "cargando" && <EsqueletoPagina etiqueta="Cargando presupuestos" />}
      {presupuestos.tipo === "error" && (
        <AvisoError error={presupuestos.error} titulo="No se pudieron cargar los presupuestos" />
      )}
      {presupuestos.tipo === "listo" && lista.length === 0 && (
        <EstadoVacio titulo={SIN_PRESUPUESTOS} descripcion={INDICACION_SIN_PRESUPUESTOS} />
      )}

      {presupuestos.tipo === "listo" && lista.length > 0 && (
        <form className="silice-actualizacion__formulario" onSubmit={revalorar}>
          <div className="silice-actualizacion__campos">
            <Select
              id="actualizacion-base"
              labelText="Presupuesto base"
              size="sm"
              value={elegido}
              onChange={(e) => setElegido(e.target.value)}
            >
              {lista.map((p, i) => (
                <SelectItem key={`${p.proyecto}/${p.codigo}`} value={String(i)} text={etiquetaPresupuesto(p)} />
              ))}
            </Select>
            <CampoTexto
              id="actualizacion-codigo-nuevo"
              labelText="Código de la versión nueva"
              size="sm"
              value={codigoNuevo}
              onChange={(e) => setCodigoNuevo(e.target.value)}
            />
            <CampoTexto
              id="actualizacion-vigencia"
              type="date"
              labelText="Fecha de vigencia"
              size="sm"
              value={vigencia}
              onChange={(e) => setVigencia(e.target.value)}
            />
            <CampoTexto
              id="actualizacion-moneda"
              labelText="Moneda"
              size="sm"
              value={moneda}
              onChange={(e) => setMoneda(e.target.value)}
            />
            <CampoTexto
              id="actualizacion-nombre"
              labelText="Nombre de la lista"
              size="sm"
              value={nombre}
              onChange={(e) => setNombreManual(e.target.value)}
            />
          </div>

          <SubidaArchivo
            id="actualizacion-archivo"
            etiqueta="Suelte aquí la lista de precios (.csv o .xlsx), o haga clic para elegirla"
            extensiones={EXTENSIONES}
            alElegir={elegirArchivo}
          />
          {archivo && (
            <p className="silice-actualizacion__nota cds--type-label-01">Archivo elegido: {archivo.name}</p>
          )}

          {vista.tipo === "error" && <AvisoError error={vista.error} titulo="No se pudo leer el archivo" />}
          {vista.tipo === "lista" && vista.vista.motivo !== null && (
            <InlineNotification
              kind="info"
              role="status"
              title="Archivo"
              subtitle={vista.vista.motivo}
              lowContrast
              hideCloseButton
            />
          )}
          {desconocidos.length > 0 && (
            <>
              <InlineNotification
                kind="info"
                role="status"
                title="Insumos nuevos"
                subtitle={avisoDesconocidos(desconocidos)}
                lowContrast
                hideCloseButton
              />
              <CheckboxGroup legendText="Dar de alta">
                {desconocidos.map((d, i) => (
                  <Checkbox
                    key={i}
                    id={`actualizacion-alta-${i}`}
                    labelText={etiquetaDeAlta(i + 1, d)}
                    checked={marcadas.has(i)}
                    onChange={(_evento, { checked }) => marcar(i, checked)}
                  />
                ))}
              </CheckboxGroup>
            </>
          )}

          <div className="silice-actualizacion__acciones">
            <Button type="submit" kind="primary" size="md" disabled={archivo === null || revalorando}>
              Revalorar presupuesto
            </Button>
            {revalorando && <InlineLoading description="Revalorando..." status="active" />}
          </div>
        </form>
      )}

      <div aria-live="polite" aria-atomic="true">
        {resultado.tipo === "error" && <AvisoError error={resultado.error} titulo="No se pudo revalorar" />}
        {resultado.tipo === "listo" && (
          <ResultadoRevaloracion
            respuesta={resultado.respuesta}
            proyecto={resultado.proyecto}
            descarte={descarte}
            alDescartar={descartar}
            alPedirDescarte={() => setDescarte({ tipo: "confirmar" })}
            alCancelarDescarte={() => setDescarte({ tipo: "no" })}
            alExpirar={alExpirar}
          />
        )}
      </div>
    </div>
  );
}

interface PropsResultado {
  respuesta: Revaloracion;
  proyecto: string;
  descarte: Descarte;
  alDescartar: (codigo: string, proyecto: string) => void;
  alPedirDescarte: () => void;
  alCancelarDescarte: () => void;
  alExpirar: () => void;
}

function ResultadoRevaloracion({
  respuesta,
  proyecto,
  descarte,
  alDescartar,
  alPedirDescarte,
  alCancelarDescarte,
  alExpirar,
}: PropsResultado) {
  const guardada = respuesta.version_guardada;
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titulo.current?.focus();
  }, []);
  return (
    <div className="silice-actualizacion__resultado">
      {respuesta.avisos.map((a, i) => (
        <InlineNotification
          key={i}
          kind={a.nivel === "advertencia" ? "warning" : "info"}
          role="status"
          title={a.nivel === "advertencia" ? "Advertencia" : "Información"}
          subtitle={a.texto}
          lowContrast
          hideCloseButton
        />
      ))}
      <h2 ref={titulo} tabIndex={-1} className="cds--type-heading-compact-02">
        Comparativo por partida
      </h2>
      <section className="silice-actualizacion__totales" aria-label="Total del presupuesto">
        <p className="cds--type-label-01">
          Total del presupuesto <span className="cds--visually-hidden">{respuesta.resumen}</span>
        </p>
        <dl className="silice-actualizacion__datos">
          <div>
            <dt className="cds--type-label-01">Anterior</dt>
            <dd className="cds--type-heading-04">{respuesta.total_anterior}</dd>
          </div>
          <div>
            <dt className="cds--type-label-01">Nuevo</dt>
            <dd className="cds--type-heading-04">{respuesta.total_nuevo}</dd>
          </div>
          <div>
            <dt className="cds--type-label-01">Variación</dt>
            <dd className="cds--type-heading-04">
              <Variacion valor={respuesta.variacion} />
            </dd>
          </div>
          <div>
            <dt className="cds--type-label-01">Variación %</dt>
            <dd className="cds--type-heading-04">
              <Variacion valor={respuesta.variacion_pct} />
            </dd>
          </div>
          <div>
            <dt className="cds--type-label-01">Moneda</dt>
            <dd className="cds--type-heading-04">{respuesta.moneda}</dd>
          </div>
        </dl>
      </section>
      <TablaDensa
        etiqueta="Comparativo por partida"
        columnas={COLUMNAS_COMPARATIVO}
        filas={filasComparativo(respuesta.filas)}
      />
      {respuesta.dados_de_alta.length > 0 && (
        <InlineNotification
          kind="success"
          role="status"
          title="Altas"
          subtitle={textoDadosDeAlta(respuesta.dados_de_alta)}
          lowContrast
          hideCloseButton
        />
      )}
      {respuesta.ignorados.length > 0 && (
        <InlineNotification
          kind="warning"
          role="status"
          title="Ignorados"
          subtitle={textoIgnorados(respuesta.ignorados)}
          lowContrast
          hideCloseButton
        />
      )}
      {respuesta.rechazados.length > 0 && (
        <InlineNotification
          kind="warning"
          role="status"
          title="Rechazados"
          subtitle={textoRechazados(respuesta.rechazados)}
          lowContrast
          hideCloseButton
        />
      )}
      {guardada !== null && (
        <DescargaArchivo
          ruta={rutaExcel(guardada, proyecto)}
          etiqueta="Exportar a Excel"
          nombrePorOmision={`presupuesto_${guardada}.xlsx`}
          alExpirar={alExpirar}
        />
      )}
      <h2 className="cds--type-heading-compact-02">Informe de auditoría de la versión nueva</h2>
      <InformeAuditoria informe={respuesta.informe} />
      {guardada !== null && (
        <div className="silice-actualizacion__acciones">
          {descarte.tipo === "hecho" ? (
            <InlineNotification
              kind="info"
              role="status"
              title="Descarte"
              subtitle={textoDescartada(guardada)}
              lowContrast
              hideCloseButton
            />
          ) : (
            <Button
              kind="danger--tertiary"
              size="md"
              disabled={descarte.tipo === "enCurso" || descarte.tipo === "confirmar"}
              onClick={alPedirDescarte}
            >
              Descartar versión
            </Button>
          )}
          {descarte.tipo === "confirmar" && (
            <div role="group" aria-label="Confirmar descarte" className="silice-actualizacion__confirmar">
              <p className="cds--type-body-compact-01">{preguntaDescartar(guardada)}</p>
              <Button kind="danger" size="sm" onClick={() => alDescartar(guardada, proyecto)}>
                Confirmar descarte
              </Button>
              <Button kind="ghost" size="sm" onClick={alCancelarDescarte}>
                Cancelar
              </Button>
            </div>
          )}
          {descarte.tipo === "error" && <AvisoError error={descarte.error} titulo="No se pudo descartar" />}
        </div>
      )}
    </div>
  );
}
