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
  RUTA_IMPORTAR_SERIE_VIAL,
  RUTA_SERIES_VIALES,
  SIN_ARCHIVO_VIAL,
  SIN_FUENTE_VIAL,
  filasDeHistoria,
  formularioDeImportacion,
  resumenDeLaSerie,
  textoDeOmitidas,
} from "./logicaSeriesViales";
import type { ImportacionVial, SeriesViales as Datos } from "./logicaSeriesViales";
import { hoyIso } from "./logica";

type Carga = { tipo: "cargando" } | { tipo: "listo"; datos: Datos } | { tipo: "error"; error: unknown };
type Resultado =
  | { tipo: "ninguno" }
  | { tipo: "enCurso" }
  | { tipo: "falta"; texto: string }
  | { tipo: "error"; error: unknown }
  | { tipo: "hecho"; respuesta: ImportacionVial };

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
  const [resultado, setResultado] = useState<Resultado>({ tipo: "ninguno" });
  const consulta = useRef(0);
  const vigente = useRef(true);

  const expirada = useCallback(
    (error: unknown) => {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
    },
    [alExpirar],
  );

  // Lee lo cargado. La primera vez deja elegida la primera serie y su organismo como fuente; las siguientes (tras
  // importar) solo refrescan la historia y, si falla, lo dicen sin esconder el formulario.
  const leer = useCallback(
    (primera: boolean) => {
      pedir<Datos>(RUTA_SERIES_VIALES).then(
        (datos) => {
          if (!vigente.current) return;
          setRelectura(null);
          setCarga({ tipo: "listo", datos });
          if (primera) {
            setSerie(datos.series[0]?.codigo ?? "");
            setFuente(datos.series[0]?.organismo ?? "");
          }
        },
        (error: unknown) => {
          if (!vigente.current) return;
          expirada(error);
          if (primera) setCarga({ tipo: "error", error });
          else setRelectura(error);
        },
      );
    },
    [expirada],
  );

  useEffect(() => {
    vigente.current = true;
    leer(true);
    return () => {
      vigente.current = false;
    };
  }, [leer]);

  const datos = carga.tipo === "listo" ? carga.datos : null;

  const elegirSerie = (codigo: string) => {
    setSerie(codigo);
    // Mientras la persona no haya escrito la fuente, sigue a la serie elegida (FRED/BLS o Gaceta Oficial).
    if (!fuenteEscrita) setFuente(datos?.series.find((s) => s.codigo === codigo)?.organismo ?? "");
  };

  const importar = (evento: FormEvent) => {
    evento.preventDefault();
    if (resultado.tipo === "enCurso") return;
    if (archivo === null) {
      ++consulta.current;
      setResultado({ tipo: "falta", texto: SIN_ARCHIVO_VIAL });
      return;
    }
    if (fuente.trim() === "") {
      ++consulta.current;
      setResultado({ tipo: "falta", texto: SIN_FUENTE_VIAL });
      return;
    }
    const numero = ++consulta.current;
    setResultado({ tipo: "enCurso" });
    pedir<ImportacionVial>(RUTA_IMPORTAR_SERIE_VIAL, {
      metodo: "POST",
      cuerpo: formularioDeImportacion({ serie, archivo, fuente, fechaDescarga }),
    }).then(
      (respuesta) => {
        if (numero !== consulta.current) return;
        setResultado({ tipo: "hecho", respuesta });
        if (respuesta.importada) leer(false);
      },
      (error: unknown) => {
        if (numero !== consulta.current) return;
        expirada(error);
        setResultado({ tipo: "error", error });
      },
    );
  };

  return (
    <section className="silice-indices__formulario" aria-labelledby="indices-series-viales">
      <h2 id="indices-series-viales" className="cds--type-heading-compact-02">
        Series del riesgo vial
      </h2>
      <p className="cds--type-body-compact-01">{AYUDA_SERIES_VIALES}</p>

      {carga.tipo === "cargando" && <EsqueletoPagina etiqueta="Cargando las series viales" />}
      {carga.tipo === "error" && <AvisoError error={carga.error} titulo="No se pudieron leer las series viales" />}

      {datos !== null && (
        <form className="silice-indices__formulario" onSubmit={importar}>
          <div className="silice-indices__campos">
            <Select
              id="series-viales-serie"
              labelText="Serie"
              size="sm"
              value={serie}
              onChange={(e) => elegirSerie(e.target.value)}
            >
              {datos.series.map((s) => (
                <SelectItem key={s.codigo} value={s.codigo} text={`${s.codigo} · ${s.nombre}`} />
              ))}
            </Select>
            <CampoTexto
              id="series-viales-fuente"
              labelText="Fuente de la serie"
              size="sm"
              value={fuente}
              onChange={(e) => {
                setFuenteEscrita(true);
                setFuente(e.target.value);
              }}
            />
            <CampoTexto
              id="series-viales-fecha"
              type="date"
              labelText="Fecha de descarga"
              size="sm"
              value={fechaDescarga}
              onChange={(e) => setFechaDescarga(e.target.value)}
            />
          </div>
          <SubidaArchivo
            id="series-viales-archivo"
            etiqueta="Suelte aquí el archivo .csv de la serie, o haga clic para elegirlo"
            extensiones={EXTENSIONES_VIALES}
            alElegir={setArchivo}
          />
          {archivo && <p className="silice-indices__nota cds--type-label-01">Archivo elegido: {archivo.name}</p>}
          <p className="cds--type-body-compact-01">Responsable de la importación: {datos.responsable}</p>
          <div className="silice-indices__acciones">
            <Button type="submit" kind="primary" size="md" disabled={resultado.tipo === "enCurso"}>
              Importar
            </Button>
            {resultado.tipo === "enCurso" && <InlineLoading description="Importando..." status="active" />}
          </div>
        </form>
      )}

      <div aria-live="polite" aria-atomic="true" className="silice-indices__avisos">
        {resultado.tipo === "falta" && (
          <InlineNotification kind="error" role="alert" title="Falta un dato" subtitle={resultado.texto} lowContrast hideCloseButton />
        )}
        {resultado.tipo === "error" && <AvisoError error={resultado.error} titulo="No se importó la serie" />}
        {resultado.tipo === "hecho" && (
          <InlineNotification
            kind={resultado.respuesta.importada ? "success" : "info"}
            role="status"
            title={resultado.respuesta.importada ? "Importación" : "Ya estaba importado"}
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
