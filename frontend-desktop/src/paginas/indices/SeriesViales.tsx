import { Button, Select, SelectItem } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { InlineLoading, InlineNotification } from "../../comun/carbonEs";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AYUDA_SERIES_VIALES,
  COLUMNAS_HISTORIA,
  EXTENSIONES_VIALES,
  MAXIMO_FUENTE,
  RUTA_IMPORTAR_SERIE_VIAL,
  RUTA_SERIES_VIALES,
  filasDeHistoria,
  formularioDeImportacion,
  resumenDeLaSerie,
  textoDeOmitidas,
  validarImportacion,
} from "./logicaSeriesViales";
import type { ErroresDeImportacion, ImportacionVial, SeriesViales as Datos } from "./logicaSeriesViales";
import { hoyIso } from "./logica";

type Carga = { tipo: "cargando" } | { tipo: "listo"; datos: Datos } | { tipo: "error"; error: unknown };
type Resultado =
  | { tipo: "ninguno" }
  | { tipo: "enCurso" }
  | { tipo: "error"; error: unknown; serie: string }
  | { tipo: "hecho"; respuesta: ImportacionVial };
type Campo = "fuente" | "fecha" | "archivo";
const ORDEN_DE_CAMPOS: readonly Campo[] = ["fuente", "fecha", "archivo"];

// «Series del riesgo vial» (índice del asfalto y gasoil): las dos series que usa «Riesgo de la obra». Se leen al abrir la
// página (definición e historia ya cargada) y se importan de a una desde su CSV canónico: la API guarda solo esa serie,
// todo o nada, y dice cuánto entró o que ya estaba. Al importar se vuelve a leer lo guardado. La interfaz no calcula nada.
export function SeriesViales() {
  const { alExpirar } = useAplicacion();
  const [carga, setCarga] = useState<Carga>({ tipo: "cargando" });
  const [relectura, setRelectura] = useState<unknown>(null);
  const [serie, setSerie] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [fuente, setFuente] = useState("");
  const [fuenteEscrita, setFuenteEscrita] = useState(false);
  const [fechaDescarga, setFechaDescarga] = useState(hoyIso());
  const [errores, setErrores] = useState<ErroresDeImportacion>({});
  const [foco, setFoco] = useState<{ campo: Campo; intento: number } | null>(null);
  const [resultado, setResultado] = useState<Resultado>({ tipo: "ninguno" });
  const consulta = useRef(0);
  const lecturas = useRef(0);
  const montado = useRef(true);
  const campoFuente = useRef<HTMLInputElement>(null);
  const campoFecha = useRef<HTMLInputElement>(null);
  const avisoDelArchivo = useRef<HTMLDivElement>(null);

  const expirada = useCallback(
    (error: unknown) => {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
    },
    [alExpirar],
  );

  // Lee lo cargado. La primera vez deja elegida la primera serie y su organismo como fuente; las siguientes (tras
  // importar) solo refrescan la historia y, si falla, lo dicen sin esconder el formulario. Una respuesta que llega
  // después de otra lectura más nueva (o de desmontar) se descarta.
  const leer = useCallback(
    (primera: boolean) => {
      const numero = ++lecturas.current;
      pedir<Datos>(RUTA_SERIES_VIALES).then(
        (datos) => {
          if (!montado.current || numero !== lecturas.current) return;
          setRelectura(null);
          setCarga({ tipo: "listo", datos });
          if (primera) {
            setSerie(datos.series[0]?.codigo ?? "");
            setFuente(datos.series[0]?.organismo ?? "");
          }
        },
        (error: unknown) => {
          if (!montado.current || numero !== lecturas.current) return;
          expirada(error);
          if (primera) setCarga({ tipo: "error", error });
          else setRelectura(error);
        },
      );
    },
    [expirada],
  );

  useEffect(() => {
    montado.current = true;
    leer(true);
    return () => {
      montado.current = false;
    };
  }, [leer]);

  // El foco va al primer campo inválido, ya pintado su error.
  useEffect(() => {
    if (foco === null) return;
    if (foco.campo === "fuente") campoFuente.current?.focus();
    else if (foco.campo === "fecha") campoFecha.current?.focus();
    else avisoDelArchivo.current?.focus();
  }, [foco]);

  const datos = carga.tipo === "listo" ? carga.datos : null;

  // Lo que ya se dijo de una importación se refiere a la serie, el archivo, la fuente y la fecha de entonces: si la persona
  // cambia cualquiera, ese aviso deja de aplicarse y se quita (y una respuesta que llegue tarde se descarta).
  const soltarResultado = () => {
    ++consulta.current;
    setResultado({ tipo: "ninguno" });
  };

  const elegirSerie = (codigo: string) => {
    soltarResultado();
    setSerie(codigo);
    // Mientras la persona no haya escrito la fuente, sigue a la serie elegida (FRED/BLS o Gaceta Oficial).
    if (!fuenteEscrita) setFuente(datos?.series.find((s) => s.codigo === codigo)?.organismo ?? "");
  };

  const importar = (evento: FormEvent) => {
    evento.preventDefault();
    if (resultado.tipo === "enCurso") return;
    const falta = validarImportacion({ archivo, fuente, fechaDescarga, hoy: hoyIso() });
    setErrores(falta);
    const primero = ORDEN_DE_CAMPOS.find((c) => falta[c] !== undefined);
    if (primero !== undefined || archivo === null) {
      ++consulta.current;
      setResultado({ tipo: "ninguno" });
      if (primero !== undefined) setFoco((antes) => ({ campo: primero, intento: (antes?.intento ?? 0) + 1 }));
      return;
    }
    const numero = ++consulta.current;
    const serieEnviada = serie;
    setResultado({ tipo: "enCurso" });
    pedir<ImportacionVial>(RUTA_IMPORTAR_SERIE_VIAL, {
      metodo: "POST",
      cuerpo: formularioDeImportacion({ serie, archivo, fuente: fuente.trim(), fechaDescarga }),
    }).then(
      (respuesta) => {
        if (!montado.current || numero !== consulta.current) return;
        setResultado({ tipo: "hecho", respuesta });
        if (respuesta.importada) leer(false);
      },
      (error: unknown) => {
        if (!montado.current || numero !== consulta.current) return;
        expirada(error);
        setResultado({ tipo: "error", error, serie: serieEnviada });
      },
    );
  };

  // Con la importación en vuelo nada se puede cambiar: lo que se manda ya salió y su aviso es de esa serie y ese archivo.
  const enviando = resultado.tipo === "enCurso";

  return (
    <section className="silice-indices__formulario" aria-labelledby="indices-series-viales">
      <h2 id="indices-series-viales" className="cds--type-heading-compact-02">
        Series del riesgo vial
      </h2>
      <p className="cds--type-body-compact-01">{AYUDA_SERIES_VIALES}</p>

      {carga.tipo === "cargando" && <EsqueletoPagina etiqueta="Cargando las series viales" />}
      {carga.tipo === "error" && <AvisoError error={carga.error} titulo="No se pudieron leer las series viales" />}

      {datos !== null && (
        <form className="silice-indices__formulario" onSubmit={importar} noValidate>
          <div className="silice-indices__campos">
            <Select
              id="series-viales-serie"
              labelText="Serie"
              size="sm"
              value={serie}
              disabled={enviando}
              onChange={(e) => elegirSerie(e.target.value)}
            >
              {datos.series.map((s) => (
                <SelectItem key={s.codigo} value={s.codigo} text={`${s.codigo} · ${s.nombre}`} />
              ))}
            </Select>
            <CampoTexto
              id="series-viales-fuente"
              ref={campoFuente}
              labelText="Fuente de la serie"
              size="sm"
              required
              maxLength={MAXIMO_FUENTE}
              disabled={enviando}
              value={fuente}
              invalid={errores.fuente !== undefined}
              invalidText={errores.fuente}
              onChange={(e) => {
                soltarResultado();
                setFuenteEscrita(true);
                setFuente(e.target.value);
                setErrores((antes) => ({ ...antes, fuente: undefined }));
              }}
            />
            <CampoTexto
              id="series-viales-fecha"
              ref={campoFecha}
              type="date"
              labelText="Fecha de descarga"
              size="sm"
              required
              max={hoyIso()}
              disabled={enviando}
              value={fechaDescarga}
              invalid={errores.fecha !== undefined}
              invalidText={errores.fecha}
              onChange={(e) => {
                soltarResultado();
                setFechaDescarga(e.target.value);
                setErrores((antes) => ({ ...antes, fecha: undefined }));
              }}
            />
          </div>
          <SubidaArchivo
            id="series-viales-archivo"
            etiqueta="Suelte aquí el archivo .csv de la serie, o haga clic para elegirlo"
            extensiones={EXTENSIONES_VIALES}
            deshabilitada={enviando}
            alElegir={(elegido) => {
              soltarResultado();
              setArchivo(elegido);
              setErrores((antes) => ({ ...antes, archivo: undefined }));
            }}
          />
          {archivo && <p className="silice-indices__nota cds--type-label-01">Archivo elegido: {archivo.name}</p>}
          {errores.archivo !== undefined && (
            <div ref={avisoDelArchivo} tabIndex={-1}>
              <InlineNotification kind="error" role="alert" title="Falta el archivo" subtitle={errores.archivo} lowContrast hideCloseButton />
            </div>
          )}
          {datos.responsable !== "" && <p className="cds--type-body-compact-01">Responsable de la importación: {datos.responsable}</p>}
          <div className="silice-indices__acciones">
            <Button type="submit" kind="primary" size="md" disabled={enviando}>
              Importar
            </Button>
            {enviando && <InlineLoading description="Importando..." status="active" />}
          </div>
        </form>
      )}

      {/* Cada aviso trae su propio rol (`alert` o `status`): el contenedor no es otra región viva. */}
      <div className="silice-indices__avisos">
        {resultado.tipo === "error" && <AvisoError error={resultado.error} titulo={`No se importó ${resultado.serie}`} />}
        {resultado.tipo === "hecho" && (
          <InlineNotification
            kind={resultado.respuesta.importada ? "success" : "info"}
            role="status"
            title={
              resultado.respuesta.importada ? `Importación de ${resultado.respuesta.serie}` : `Ya estaba importado en ${resultado.respuesta.serie}`
            }
            subtitle={resultado.respuesta.mensaje}
            lowContrast
            hideCloseButton
          />
        )}
        {relectura !== null && <AvisoError error={relectura} titulo="No se pudo releer lo cargado" />}
      </div>

      {datos?.series.map((s) => (
        <section key={s.codigo} className="silice-indices__informe" aria-labelledby={`series-viales-${s.codigo}`}>
          <h3 id={`series-viales-${s.codigo}`} className="cds--type-heading-compact-01">
            {s.nombre}
          </h3>
          <p className="silice-indices__nota cds--type-label-01">
            {s.codigo} · {s.organismo}
          </p>
          <p className="cds--type-body-compact-01">{resumenDeLaSerie(s)}</p>
          {s.historia.length > 0 && (
            <TablaDensa etiqueta={`Valores cargados de ${s.codigo}`} columnas={COLUMNAS_HISTORIA} filas={filasDeHistoria(s.historia)} />
          )}
          {s.omitidas > 0 && <p className="silice-indices__nota cds--type-label-01">{textoDeOmitidas(s.omitidas)}</p>}
        </section>
      ))}
    </section>
  );
}
