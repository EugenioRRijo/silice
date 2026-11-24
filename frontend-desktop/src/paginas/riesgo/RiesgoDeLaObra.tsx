import { Button, Select, SelectItem } from "@carbon/react";
import { InlineLoading } from "../../comun/carbonEs";
import { useContext, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { ErrorDeApi } from "../../api/cliente";
import { comprobarObra, guardarMapa, proyectarObra } from "../../api/riesgo";
import type {
  ComprobacionDeLaObra,
  InsumosDeLaObra,
  MapaDeSeries,
  PedidoDeProyeccion,
  ProyeccionDeLaObra,
} from "../../api/riesgo";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EnlaceComoBoton } from "../../comun/EnlaceComoBoton";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { useAplicacion } from "../../shell/contexto";
import { rutaDeVersiones, versionesOfrecidas } from "../hoja/logica";
import type { VersionesRespuesta } from "../hoja/logica";
import { useCarga } from "../../comun/useCarga";
import {
  CAMPOS_INICIALES,
  ROTULOS,
  SIN_INICIO,
  SIN_RECORDAR,
  avisoDeDescartados,
  faltaCargarSeries,
  leerCampos,
  notaDeLaPrecarga,
  pideLaFechaDeInicio,
  rutaDelInformeDeRiesgo,
} from "./logica";
import { rutaOPendientes } from "../../marco/espacios";
import type { Campos } from "./logica";
import { MejoraDeLaEstimacion } from "./MejoraDeLaEstimacion";
import { CamposDeProyectar, ParametrosDelRiesgo } from "./ParametrosDelRiesgo";
import { ResultadoDeLaComprobacion, ResultadoDeLaProyeccion } from "./ResultadoDelRiesgo";
import "./riesgo.scss";

const SIN_OBRA = "Abra una obra para ver el riesgo de precios de su presupuesto.";
const SIN_OBRA_DONDE = "Las obras están en «Obras» de la barra lateral; también puede buscarla con Ctrl+K.";
const SIN_VERSIONES = "Esta obra aún no tiene versiones";
const SIN_VERSIONES_DESCRIPCION =
  "Esta obra aún no tiene versiones guardadas. Guarde una en el presupuesto para proyectar su riesgo.";
const ESPERA = "Probando con meses pasados: puede tardar cerca de medio minuto en una obra mediana.";

type Pedido<T> = { estado: "nada" } | { estado: "cargando" } | { estado: "listo"; datos: T } | { estado: "error"; error: unknown };
const NADA = { estado: "nada" } as const;

function rutaDeInsumos(proyecto: string, version: string): string {
  return `/v1/riesgo/insumos?proyecto=${encodeURIComponent(proyecto)}&version=${encodeURIComponent(version)}`;
}

// «Riesgo de la obra»: la proyección del riesgo de precios de una versión (P50, P80, la reserva y los insumos que más
// empujan) y su prueba con meses pasados (cobertura y número de cortes). Todo lo calcula el servidor con semilla fija;
// la pantalla solo lee lo tecleado (coma decimal, punto de miles) y escribe lo que llega en centésimas. Al pie, la
// mejora de la estimación (Tarea 15), que no lee la obra: se ofrece aunque no haya una abierta. La serie que mueve cada
// insumo se recuerda en el caso (mejora de la DS-81): al volver, el selector viene precargado con lo último que se usó.
export default function RiesgoDeLaObra() {
  const { nombreProyecto, alExpirar, sesion } = useAplicacion();
  const obra = useContext(ContextoDeLaObra);
  const obraAbierta = obra ? { carpeta: obra.carpeta, obraId: obra.obraId } : undefined;
  const nombre = nombreProyecto ?? null;
  const versiones = useCarga<VersionesRespuesta>(nombre === null ? null : rutaDeVersiones(nombre), alExpirar);
  const ofrecidas = versiones.estado === "listo" ? versionesOfrecidas(versiones.datos.versiones) : [];
  const [elegida, setElegida] = useState<string | null>(null);
  const porOmision = versiones.estado === "listo" ? (versiones.datos.por_omision ?? ofrecidas.at(-1)?.codigo ?? null) : null;
  const version = elegida !== null && ofrecidas.some((v) => v.codigo === elegida) ? elegida : porOmision;
  const insumos = useCarga<InsumosDeLaObra>(nombre !== null && version !== null ? rutaDeInsumos(nombre, version) : null, alExpirar);

  const [campos, setCampos] = useState<Campos>(CAMPOS_INICIALES);
  const [errores, setErrores] = useState<Partial<Record<keyof Campos, string>>>({});
  // El mapa es de la versión que se ve: al cambiar de versión empieza con lo que Sílice recordó de ella (DS-90) o vacío;
  // lo que se elige a mano manda sobre lo recordado.
  const [mapaDe, setMapaDe] = useState<{ version: string | null; mapa: MapaDeSeries }>({ version: null, mapa: {} });
  const recordado = insumos.estado === "listo" && insumos.datos.version === version ? (insumos.datos.mapa_guardado ?? null) : null;
  const editado = mapaDe.version === version;
  const mapa = editado ? mapaDe.mapa : (recordado?.mapa ?? {});
  // El mapa no se pudo recordar en el caso: se dice sin estorbar, el resultado ya está.
  const [sinRecordar, setSinRecordar] = useState(false);
  // La versión cuyo mapa propio ya se guardó desde que se eligió: la nota de la precarga y el aviso de lo descartado se
  // retiran, porque lo que se ve ya es lo recordado de esa versión (DS-94).
  const [guardadoEn, setGuardadoEn] = useState<string | null>(null);
  const precargaVigente = !editado && guardadoEn !== version ? recordado : null;
  // Los guardados del mapa van uno detrás de otro: uno viejo nunca confirma después de uno nuevo (DS-94).
  const colaDeGuardado = useRef<Promise<void>>(Promise.resolve());
  const [proyeccion, setProyeccion] = useState<Pedido<ProyeccionDeLaObra>>(NADA);
  // Lo que se pidió en la última proyección: el informe en Excel se baja con lo mismo.
  const [proyectado, setProyectado] = useState<PedidoDeProyeccion | null>(null);
  const [comprobacion, setComprobacion] = useState<Pedido<ComprobacionDeLaObra>>(NADA);
  // Turno del último pedido: sube con cada pedido y al cambiar de versión, y la respuesta que llegue con un turno viejo
  // se descarta (sería de otra versión o de un pedido ya reemplazado).
  const turno = useRef(0);
  const regionProyeccion = useRef<HTMLElement>(null);
  const regionComprobacion = useRef<HTMLElement>(null);
  const cajaDelError = useRef<HTMLDivElement>(null);
  // Sube cuando falta la fecha de inicio (hallazgo 9 del recorrido): el error va al campo y el foco también.
  const [enfocarInicio, setEnfocarInicio] = useState(0);
  useEffect(() => {
    if (enfocarInicio > 0) document.getElementById("riesgo-inicio")?.focus();
  }, [enfocarInicio]);

  // Lo que llega (el resultado o el error) recibe el foco: el botón queda desactivado mientras se espera.
  useEffect(() => {
    if (proyeccion.estado === "listo") regionProyeccion.current?.focus();
  }, [proyeccion]);
  useEffect(() => {
    if (comprobacion.estado === "listo") regionComprobacion.current?.focus();
  }, [comprobacion]);
  const hayError = proyeccion.estado === "error" || comprobacion.estado === "error";
  useEffect(() => {
    if (hayError) cajaDelError.current?.focus();
  }, [hayError]);

  function cambiar(clave: keyof Campos, valor: string) {
    setCampos((c) => ({ ...c, [clave]: valor }));
    setErrores((e) => ({ ...e, [clave]: undefined }));
  }

  function elegirSerie(insumo: string, serie: string) {
    const nuevo = { ...mapa };
    if (serie === "") delete nuevo[insumo];
    else nuevo[insumo] = serie;
    setMapaDe({ version, mapa: nuevo });
  }

  // Lo que se ve es de la versión elegida: la proyección, la comprobación y lo proyectado de la anterior se retiran.
  function elegirVersion(codigo: string) {
    turno.current += 1;
    setElegida(codigo);
    setProyeccion(NADA);
    setComprobacion(NADA);
    setProyectado(null);
    setSinRecordar(false);
    // Lo que se tocó sin proyectar en la versión anterior no se guarda: al volver, vuelve lo recordado.
    setMapaDe({ version: null, mapa: {} });
    setGuardadoEn(null);
  }

  function marcarInicio(texto: string) {
    setErrores((e) => ({ ...e, inicio: texto }));
    setEnfocarInicio((n) => n + 1);
  }

  // Recuerda el mapa que se acaba de usar con éxito, en una petición aparte del cálculo (DS-91), en la cola de guardados.
  function recordar(mio: number, pedido: { proyecto: string; version: string; mapa: MapaDeSeries }) {
    const enviar = async () => {
      try {
        await guardarMapa(pedido);
        if (mio === turno.current) setGuardadoEn(pedido.version);
      } catch (razon) {
        if (mio !== turno.current) return;
        if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
        setSinRecordar(true);
      }
    };
    colaDeGuardado.current = colaDeGuardado.current.then(enviar);
  }

  async function pedir<T>(fijar: (p: Pedido<T>) => void, llamar: () => Promise<T>, recordarMapa: { proyecto: string; version: string; mapa: MapaDeSeries }) {
    const mio = ++turno.current;
    fijar({ estado: "cargando" });
    setSinRecordar(false);
    try {
      const datos = await llamar();
      if (mio !== turno.current) return;
      fijar({ estado: "listo", datos });
      recordar(mio, recordarMapa);
    } catch (razon) {
      if (mio !== turno.current) return;
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      // El 422 de la fecha de inicio es de un campo: se dice en él, no en un aviso bajo los botones.
      if (razon instanceof ErrorDeApi && razon.estado === 422 && pideLaFechaDeInicio(razon.detalle)) {
        fijar(NADA);
        marcarInicio(razon.detalle);
        return;
      }
      fijar({ estado: "error", error: razon });
    }
  }

  function proyectar() {
    if (nombre === null || version === null) return;
    const lectura = leerCampos(campos, ["meses", "trayectorias", "semilla", "ventana"] as const);
    const faltaInicio = campos.inicio === "" && insumos.estado === "listo" && insumos.datos.inicio_linea_base === null;
    if ("errores" in lectura || faltaInicio) {
      setErrores("errores" in lectura ? lectura.errores : {});
      if (faltaInicio) marcarInicio(SIN_INICIO);
      return;
    }
    const { meses, trayectorias, semilla, ventana } = lectura.valores;
    setComprobacion(NADA);
    const inicio = campos.inicio === "" ? null : campos.inicio;
    const pedido = { proyecto: nombre, version, inicio, meses, trayectorias, semilla, ventana_meses: ventana, mapa };
    setProyectado(pedido);
    void pedir(setProyeccion, () => proyectarObra(pedido), { proyecto: nombre, version, mapa });
  }

  function comprobar() {
    if (nombre === null || version === null) return;
    const lectura = leerCampos(campos, ["meses", "porCorte", "semilla", "ventana"] as const);
    if ("errores" in lectura) {
      setErrores(lectura.errores);
      return;
    }
    const { meses, porCorte, semilla, ventana } = lectura.valores;
    setProyeccion((p) => (p.estado === "error" ? NADA : p));
    const pedido = { proyecto: nombre, version, meses, trayectorias_por_corte: porCorte, semilla, ventana_meses: ventana, mapa };
    void pedir(setComprobacion, () => comprobarObra(pedido), { proyecto: nombre, version, mapa });
  }

  const ocupado = proyeccion.estado === "cargando" || comprobacion.estado === "cargando";
  const errorVisible = proyeccion.estado === "error" ? proyeccion.error : comprobacion.estado === "error" ? comprobacion.error : null;
  return (
    <div className="riesgo silice-pagina">
      <h1 className="cds--type-heading-04">Riesgo de la obra</h1>
      <p className="riesgo-nota cds--type-body-compact-01">
        Cuánto puede subir el presupuesto si los precios se mueven como en los meses pasados, y qué tanto acertó esa cuenta
        con lo que de verdad pasó. El sistema hace todas las cuentas; aquí se leen.
      </p>
      {nombre === null && <EstadoVacio titulo={SIN_OBRA} descripcion={SIN_OBRA_DONDE} />}
      {versiones.estado === "error" && <AvisoError error={versiones.error} titulo="No se pudieron leer las versiones" />}
      {versiones.estado === "listo" && ofrecidas.length === 0 && (
        <EstadoVacio titulo={SIN_VERSIONES} descripcion={SIN_VERSIONES_DESCRIPCION}>
          <EnlaceComoBoton to={rutaOPendientes("hoja", obraAbierta)} kind="primary">
            Ir al presupuesto
          </EnlaceComoBoton>
        </EstadoVacio>
      )}
      {version !== null && (
        <>
          <Select
            id="riesgo-version"
            labelText="Versión"
            value={version}
            disabled={ocupado}
            onChange={(e) => elegirVersion(e.target.value)}
          >
            {ofrecidas.map((v) => (
              <SelectItem key={v.codigo} value={v.codigo} text={v.codigo} />
            ))}
          </Select>
          {insumos.estado === "cargando" && <InlineLoading description="Leyendo los insumos de la versión..." />}
          {(insumos.estado === "error" || insumos.estado === "no_disponible") && (
            <AvisoError error={insumos.error} titulo="No se pudieron leer los insumos de la versión" />
          )}
          {insumos.estado === "listo" && (
            <>
              <ParametrosDelRiesgo
                campos={campos}
                errores={errores}
                alCambiar={cambiar}
                insumos={insumos.datos}
                mapa={mapa}
                alElegirSerie={elegirSerie}
                nota={precargaVigente !== null && version !== null ? notaDeLaPrecarga(precargaVigente, version) : null}
                aviso={precargaVigente !== null ? avisoDeDescartados(precargaVigente.descartados) : null}
              />
              <fieldset className="riesgo-seccion">
                <legend className="cds--type-heading-compact-01">Proyectar</legend>
                <div className="riesgo-acciones">
                  <CamposDeProyectar
                    campos={campos}
                    errores={errores}
                    alCambiar={cambiar}
                    insumos={insumos.datos}
                  />
                  <Button kind="primary" size="md" disabled={ocupado} onClick={proyectar}>
                    Proyectar
                  </Button>
                  {proyeccion.estado === "cargando" && <InlineLoading description="Proyectando..." />}
                </div>
              </fieldset>
              <fieldset className="riesgo-seccion">
                <legend className="cds--type-heading-compact-01">Probar precisión con meses pasados</legend>
                <div className="riesgo-acciones">
                  <CampoTexto
                    id="riesgo-porCorte"
                    labelText={ROTULOS.porCorte}
                    inputMode="numeric"
                    value={campos.porCorte}
                    invalid={errores.porCorte !== undefined}
                    invalidText={errores.porCorte}
                    onChange={(e) => cambiar("porCorte", e.target.value)}
                  />
                  <Button kind="secondary" size="md" disabled={ocupado} onClick={comprobar}>
                    Probar precisión con meses pasados
                  </Button>
                  {comprobacion.estado === "cargando" && <InlineLoading description={ESPERA} />}
                </div>
              </fieldset>
            </>
          )}
          {errorVisible !== null && (
            <div ref={cajaDelError} tabIndex={-1}>
              <AvisoError error={errorVisible} titulo="No se pudo calcular el riesgo" />
              {/* Falta una serie: quien administra los precios la carga en «Índices del BCV» (sin permiso la API diría 403). */}
              {faltaCargarSeries(errorVisible) && sesion.acciones.includes("administrar_precios") && (
                <p className="riesgo-nota cds--type-body-compact-01">
                  <Link className="cds--link" to={rutaOPendientes("indices")}>
                    Cargar las series en Índices del BCV
                  </Link>
                </p>
              )}
            </div>
          )}
          {proyeccion.estado === "listo" && (
            <ResultadoDeLaProyeccion
              datos={proyeccion.datos}
              region={regionProyeccion}
              conSeries={proyectado !== null && Object.keys(proyectado.mapa).length > 0}
            >
              {proyectado !== null && (
                <DescargaArchivo
                  ruta={rutaDelInformeDeRiesgo(proyectado)}
                  etiqueta="Descargar el informe de riesgo"
                  nombrePorOmision="riesgo.xlsx"
                  alExpirar={alExpirar}
                  kind="tertiary"
                  size="sm"
                />
              )}
            </ResultadoDeLaProyeccion>
          )}
          {comprobacion.estado === "listo" && <ResultadoDeLaComprobacion datos={comprobacion.datos} region={regionComprobacion} />}
          {sinRecordar && (
            <p className="riesgo-nota cds--type-body-compact-01" role="status">
              {SIN_RECORDAR}
            </p>
          )}
        </>
      )}
      <MejoraDeLaEstimacion
        precarga={
          proyeccion.estado === "listo"
            ? { cifra: proyeccion.datos.p50, base: proyeccion.datos.total_base, version: proyeccion.datos.version, moneda: proyeccion.datos.moneda }
            : null
        }
        alExpirar={alExpirar}
      />
    </div>
  );
}
