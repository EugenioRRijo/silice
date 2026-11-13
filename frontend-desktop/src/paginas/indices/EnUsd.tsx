import { Button, Select, SelectItem } from "@carbon/react";
import { InlineLoading, InlineNotification } from "../../comun/carbonEs";
import { useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AYUDA_USD,
  COLUMNAS_MUESTRA,
  COLUMNAS_OMITIDOS,
  SIN_ORIGENES,
  YA_GUARDADA,
  filasMuestra,
  filasOmitidos,
  textoDelResumen,
} from "./logicaUsd";
import type { OrigenesEnUsd, VistaEnUsd } from "./logicaUsd";

type Paso<T> = { tipo: "nada" } | { tipo: "enCurso" } | { tipo: "error"; error: unknown } | { tipo: "listo"; datos: T };
interface Revisada {
  serie: string;
  lado: string;
  vista: VistaEnUsd;
}

// «Un índice en USD» (RF-214): elegir un índice mensual en bolívares y la tasa del BCV, revisar lo que daría (la API
// trae la cuenta del primer y el último mes ya escrita en es-VE) y guardarlo con la huella revisada. Se carga al pedirlo:
// la página no hace una petición más al abrirse. La interfaz no calcula nada.
export function EnUsd() {
  const { alExpirar } = useAplicacion();
  const [origenes, setOrigenes] = useState<Paso<OrigenesEnUsd>>({ tipo: "nada" });
  const [serie, setSerie] = useState("");
  const [lado, setLado] = useState("venta");
  const [vista, setVista] = useState<Paso<Revisada>>({ tipo: "nada" });
  const [guardado, setGuardado] = useState<Paso<string[]>>({ tipo: "nada" });
  const consulta = useRef(0);

  const fallo = (error: unknown) => {
    if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
  };

  const abrir = () => {
    setOrigenes({ tipo: "enCurso" });
    pedir<OrigenesEnUsd>("/v1/indices/en-usd/origenes").then(
      (datos) => {
        setOrigenes({ tipo: "listo", datos });
        setSerie(datos.series[0]?.clave ?? "");
        setLado(datos.lado_por_omision);
      },
      (error: unknown) => {
        fallo(error);
        setOrigenes({ tipo: "error", error });
      },
    );
  };

  const revisar = () => {
    const numero = ++consulta.current;
    setGuardado({ tipo: "nada" });
    setVista({ tipo: "enCurso" });
    pedir<VistaEnUsd>("/v1/indices/en-usd/ver", { metodo: "POST", cuerpo: { serie, lado } }).then(
      (datos) => {
        if (numero === consulta.current) setVista({ tipo: "listo", datos: { serie, lado, vista: datos } });
      },
      (error: unknown) => {
        if (numero !== consulta.current) return;
        fallo(error);
        setVista({ tipo: "error", error });
      },
    );
  };

  const guardar = (revisada: Revisada) => {
    if (guardado.tipo === "enCurso") return;
    setGuardado({ tipo: "enCurso" });
    pedir<{ mensajes: string[] }>("/v1/indices/en-usd/confirmar", {
      metodo: "POST",
      cuerpo: { serie: revisada.serie, lado: revisada.lado, huella: revisada.vista.huella },
    }).then(
      (respuesta) => setGuardado({ tipo: "listo", datos: respuesta.mensajes }),
      (error: unknown) => {
        fallo(error);
        setGuardado({ tipo: "error", error });
      },
    );
  };

  const lista = origenes.tipo === "listo" ? origenes.datos : null;
  const revisada = vista.tipo === "listo" ? vista.datos : null;

  return (
    <section className="silice-indices__formulario" aria-labelledby="indices-en-usd">
      <h2 id="indices-en-usd" className="cds--type-heading-compact-02">
        Un índice en USD
      </h2>
      <p className="cds--type-body-compact-01">{AYUDA_USD}</p>

      {(origenes.tipo === "nada" || origenes.tipo === "error") && (
        <div className="silice-indices__acciones">
          <Button kind="tertiary" size="md" onClick={abrir}>
            Expresar un índice en USD
          </Button>
        </div>
      )}
      {origenes.tipo === "enCurso" && <InlineLoading description="Cargando los índices..." status="active" />}
      {origenes.tipo === "error" && <AvisoError error={origenes.error} titulo="No se pudieron leer los índices" />}

      {lista !== null && lista.series.length === 0 && (
        <InlineNotification kind="info" role="status" title="Sin índices" subtitle={SIN_ORIGENES} lowContrast hideCloseButton />
      )}
      {lista !== null && lista.series.length > 0 && (
        <>
          <div className="silice-indices__campos">
            <Select
              id="indices-usd-serie"
              labelText="Índice en bolívares"
              size="sm"
              value={serie}
              onChange={(e) => setSerie(e.target.value)}
            >
              {lista.series.map((s) => (
                <SelectItem key={s.clave} value={s.clave} text={`${s.clave} · ${s.nombre}`} />
              ))}
            </Select>
            <Select id="indices-usd-lado" labelText="Tasa del BCV" size="sm" value={lado} onChange={(e) => setLado(e.target.value)}>
              {lista.lados.map((l) => (
                <SelectItem key={l} value={l} text={l} />
              ))}
            </Select>
          </div>
          <div className="silice-indices__acciones">
            <Button kind="secondary" size="md" onClick={revisar} disabled={vista.tipo === "enCurso"}>
              Revisar
            </Button>
            {vista.tipo === "enCurso" && <InlineLoading description="Revisando..." status="active" />}
          </div>
        </>
      )}

      {vista.tipo === "error" && <AvisoError error={vista.error} titulo="No se pudo expresar en USD" />}
      {revisada !== null && (
        <section className="silice-indices__informe" aria-label="Lo que se guardaría (todavía no se guardó nada)">
          <dl className="silice-indices__datos">
            <div>
              <dt className="cds--type-label-01">Serie nueva</dt>
              <dd className="cds--type-heading-compact-02">{revisada.vista.serie_nueva}</dd>
            </div>
            <div>
              <dt className="cds--type-label-01">Nombre</dt>
              <dd className="cds--type-body-compact-01">{revisada.vista.nombre}</dd>
            </div>
          </dl>
          <p className="cds--type-body-compact-01">{textoDelResumen(revisada.vista)}</p>
          {revisada.vista.ya_guardada && <p className="silice-indices__nota cds--type-label-01">{YA_GUARDADA}</p>}
          {revisada.vista.muestra.length > 0 && (
            <TablaDensa
              etiqueta="La cuenta del primer y el último mes"
              columnas={COLUMNAS_MUESTRA}
              filas={filasMuestra(revisada.vista.muestra)}
            />
          )}
          {revisada.vista.omitidos.length > 0 && (
            <TablaDensa
              etiqueta="Meses que no se pueden expresar en USD"
              columnas={COLUMNAS_OMITIDOS}
              filas={filasOmitidos(revisada.vista.omitidos)}
            />
          )}
          {revisada.vista.meses > 0 && (
            <div className="silice-indices__acciones">
              <Button kind="primary" size="md" disabled={guardado.tipo === "enCurso"} onClick={() => guardar(revisada)}>
                Guardar la serie en USD
              </Button>
              {guardado.tipo === "enCurso" && <InlineLoading description="Guardando..." status="active" />}
            </div>
          )}
        </section>
      )}
      <div aria-live="polite" aria-atomic="true" className="silice-indices__avisos">
        {guardado.tipo === "listo" &&
          guardado.datos.map((mensaje, i) => (
            <InlineNotification
              key={i}
              kind="success"
              role="status"
              title="Índice en USD"
              subtitle={mensaje}
              lowContrast
              hideCloseButton
            />
          ))}
        {guardado.tipo === "error" && <AvisoError error={guardado.error} titulo="No se guardó la serie en USD" />}
      </div>
    </section>
  );
}
