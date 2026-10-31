import { Button, InlineLoading, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { comprobarObra, proyectarObra } from "../../api/riesgo";
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
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import { rutaDeVersiones, versionesOfrecidas } from "../hoja/logica";
import type { VersionesRespuesta } from "../hoja/logica";
import { useCarga } from "../inicio/useCarga";
import { CAMPOS_INICIALES, ROTULOS, leerCampos, rutaDelInformeDeRiesgo } from "./logica";
import type { Campos } from "./logica";
import { ParametrosDelRiesgo } from "./ParametrosDelRiesgo";
import { ResultadoDeLaComprobacion, ResultadoDeLaProyeccion } from "./ResultadoDelRiesgo";
import "./riesgo.scss";

const SIN_OBRA = "Abra una obra para ver el riesgo de precios de su presupuesto.";
const SIN_VERSIONES = "Esta obra aún no tiene versiones guardadas. Guarde una en la Hoja para proyectar su riesgo.";
const ESPERA = "Comprobando hacia atrás: puede tardar cerca de medio minuto en una obra mediana.";

type Pedido<T> = { estado: "nada" } | { estado: "cargando" } | { estado: "listo"; datos: T } | { estado: "error"; error: unknown };
const NADA = { estado: "nada" } as const;

function rutaDeInsumos(proyecto: string, version: string): string {
  return `/v1/riesgo/insumos?proyecto=${encodeURIComponent(proyecto)}&version=${encodeURIComponent(version)}`;
}

// «Riesgo de la obra»: la proyección del riesgo de precios de una versión (P50, P80, la reserva y los insumos que más
// empujan) y su comprobación hacia atrás (cobertura y número de cortes). Todo lo calcula el servidor con semilla fija;
// la pantalla solo lee lo tecleado (coma decimal, punto de miles) y escribe lo que llega en centésimas.
export default function RiesgoDeLaObra() {
  const { nombreProyecto, alExpirar } = useAplicacion();
  const nombre = nombreProyecto ?? null;
  const versiones = useCarga<VersionesRespuesta>(nombre === null ? null : rutaDeVersiones(nombre), alExpirar);
  const ofrecidas = versiones.estado === "listo" ? versionesOfrecidas(versiones.datos.versiones) : [];
  const [elegida, setElegida] = useState<string | null>(null);
  const porOmision = versiones.estado === "listo" ? (versiones.datos.por_omision ?? ofrecidas.at(-1)?.codigo ?? null) : null;
  const version = elegida !== null && ofrecidas.some((v) => v.codigo === elegida) ? elegida : porOmision;
  const insumos = useCarga<InsumosDeLaObra>(nombre !== null && version !== null ? rutaDeInsumos(nombre, version) : null, alExpirar);

  const [campos, setCampos] = useState<Campos>(CAMPOS_INICIALES);
  const [errores, setErrores] = useState<Partial<Record<keyof Campos, string>>>({});
  // El mapa es de la versión que se ve: al cambiar de versión empieza vacío.
  const [mapaDe, setMapaDe] = useState<{ version: string | null; mapa: MapaDeSeries }>({ version: null, mapa: {} });
  const mapa = mapaDe.version === version ? mapaDe.mapa : {};
  const [proyeccion, setProyeccion] = useState<Pedido<ProyeccionDeLaObra>>(NADA);
  // Lo que se pidió en la última proyección: el informe en Excel se baja con lo mismo.
  const [proyectado, setProyectado] = useState<PedidoDeProyeccion | null>(null);
  const [comprobacion, setComprobacion] = useState<Pedido<ComprobacionDeLaObra>>(NADA);
  const regionProyeccion = useRef<HTMLElement>(null);
  const regionComprobacion = useRef<HTMLElement>(null);
  const cajaDelError = useRef<HTMLDivElement>(null);

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

  async function pedir<T>(fijar: (p: Pedido<T>) => void, llamar: () => Promise<T>) {
    fijar({ estado: "cargando" });
    try {
      fijar({ estado: "listo", datos: await llamar() });
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      fijar({ estado: "error", error: razon });
    }
  }

  function proyectar() {
    if (nombre === null || version === null) return;
    const lectura = leerCampos(campos, ["meses", "trayectorias", "semilla", "ventana"] as const);
    if ("errores" in lectura) {
      setErrores(lectura.errores);
      return;
    }
    const { meses, trayectorias, semilla, ventana } = lectura.valores;
    setComprobacion(NADA);
    const inicio = campos.inicio === "" ? null : campos.inicio;
    const pedido = { proyecto: nombre, version, inicio, meses, trayectorias, semilla, ventana_meses: ventana, mapa };
    setProyectado(pedido);
    void pedir(setProyeccion, () => proyectarObra(pedido));
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
    void pedir(setComprobacion, () => comprobarObra(pedido));
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
      {nombre === null && <EstadoVacio titulo={SIN_OBRA} />}
      {versiones.estado === "error" && <AvisoError error={versiones.error} titulo="No se pudieron leer las versiones" />}
      {versiones.estado === "listo" && ofrecidas.length === 0 && <EstadoVacio titulo={SIN_VERSIONES} />}
      {version !== null && (
        <>
          <Select id="riesgo-version" labelText="Versión" value={version} onChange={(e) => setElegida(e.target.value)}>
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
              />
              <div className="riesgo-acciones">
                <Button kind="primary" size="md" disabled={ocupado} onClick={proyectar}>
                  Proyectar
                </Button>
                {proyeccion.estado === "cargando" && <InlineLoading description="Proyectando..." />}
              </div>
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
                  Comprobar hacia atrás
                </Button>
                {comprobacion.estado === "cargando" && <InlineLoading description={ESPERA} />}
              </div>
            </>
          )}
          {errorVisible !== null && (
            <div ref={cajaDelError} tabIndex={-1}>
              <AvisoError error={errorVisible} titulo="No se pudo calcular el riesgo" />
            </div>
          )}
          {proyeccion.estado === "listo" && (
            <ResultadoDeLaProyeccion datos={proyeccion.datos} region={regionProyeccion}>
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
        </>
      )}
    </div>
  );
}
