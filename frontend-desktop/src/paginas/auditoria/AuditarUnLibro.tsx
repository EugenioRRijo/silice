import { Button, SkeletonText } from "@carbon/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import { useNavigate } from "react-router";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { LibroVisualRespuesta } from "../../api/tipos";
import { useAnunciar } from "../../comun/Anunciador";
import { AvisoError } from "../../comun/AvisoError";
import { BotonInactivo } from "../../comun/BotonInactivo";
import { CampoTexto } from "../../comun/CampoTexto";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { rutaOPendientes } from "../../marco/espacios";
import { useAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido } from "../../shell/recorrido";
import { fijarArchivoPendiente } from "../inicio/archivoPendiente";
import { AlertasDePrecio } from "./AlertasDePrecio";
import { useCatalogoQueHacer } from "../../comun/catalogoQueHacer";
import { ConclusionDelLibro } from "./ConclusionDelLibro";
import {
  anuncioDeResultado,
  avisosDePrecio,
  cuentaDeHallazgos,
  cuerpoDeLibro,
  desgloseDeSeveridad,
  fechaDeHoy,
  fraseDeRespuesta,
  pasoSiguiente,
} from "./logicaDelLibro";
import { ProblemasDelLibro } from "./ProblemasDelLibro";
import { useAuditoriaDelLibro } from "./useAuditoriaDelLibro";
import "./auditoria.scss";

const ISO = /^\d{4}-\d{2}-\d{2}$/;

function Numero({ n }: { n: number }): JSX.Element {
  return (
    <span aria-hidden="true" className="silice-libro__numero">
      {n}
    </span>
  );
}

function Esqueleto(): JSX.Element {
  // Sin región viva ni cifras: un estado de espera no se anuncia (guía `accessibility`); el botón dice «Auditando…».
  return (
    <div className="silice-libro__esqueleto" aria-busy="true">
      <p className="cds--type-body-compact-01">Auditando el libro…</p>
      <SkeletonText heading width="40%" />
      <SkeletonText paragraph lineCount={4} />
    </div>
  );
}

interface Props {
  alAuditar?: () => void;
}

// «Auditar un libro» en una sola página (B2, docs/especificaciones/2026-11-26-cara-papel-y-resaltador/b2/ficha-b2.md): 1 suba
// el libro, 2 qué se encontró y 3 conclusión y entrega. La auditoría se manda una vez; «Ver la hoja marcada» pide la réplica
// al pulsarlo y deja el resultado en el almacén del Visor, que no audita otra vez (así no se duplica el historial).
export function AuditarUnLibro({ alAuditar }: Props = {}): JSX.Element {
  const { alExpirar, almacenDelLibro } = useAplicacion();
  const navegar = useNavigate();
  const anunciar = useAnunciar();
  const { estado, elegir, auditar, reiniciar } = useAuditoriaDelLibro(alExpirar, alAuditar);
  const [fecha, setFecha] = useState(fechaDeHoy);
  const [preparando, setPreparando] = useState(false);
  const [errorDeLaHoja, setErrorDeLaHoja] = useState<unknown>(null);
  const titular = useRef<HTMLHeadingElement>(null);

  const resultado = estado.fase === "listo" ? estado : null;
  const archivo = estado.fase === "vacio" ? null : estado.archivo;
  const cargando = estado.fase === "cargando";
  const catalogo = useCatalogoQueHacer(alExpirar, resultado !== null);
  const cuenta = useMemo(() => (resultado ? cuentaDeHallazgos(resultado.auditoria) : null), [resultado]);
  const avisos = useMemo(
    () => (resultado ? avisosDePrecio(resultado.auditoria.alertas, catalogo) : []),
    [resultado, catalogo],
  );

  // Al terminar: el foco va al titular del resultado y se anuncia una sola vez (guía «update SPA titles / live regions»).
  const auditoriaLista = resultado?.auditoria ?? null;
  useEffect(() => {
    if (!auditoriaLista) return;
    titular.current?.focus();
    anunciar(anuncioDeResultado(cuentaDeHallazgos(auditoriaLista)));
  }, [auditoriaLista, anunciar]);

  const motivoInactivo = !archivo
    ? "Elija primero el libro .xlsx."
    : !ISO.test(fecha)
      ? "Escriba la fecha de la revisión en «Más opciones»."
      : null;

  const otroLibro = useCallback(() => {
    setErrorDeLaHoja(null);
    reiniciar();
  }, [reiniciar]);

  const conRecorrido = () => {
    if (!archivo) return;
    fijarArchivoPendiente(archivo, "guiado");
    iniciarRecorrido(RECORRIDO_AUDITAR);
    void navegar(rutaOPendientes("libros"));
  };

  const verLaHoja = async () => {
    if (!resultado) return;
    setPreparando(true);
    setErrorDeLaHoja(null);
    try {
      if (almacenDelLibro) {
        const replica = await pedir<LibroVisualRespuesta>("/v1/libros/replica", {
          metodo: "POST",
          cuerpo: cuerpoDeLibro(resultado.archivo),
        });
        almacenDelLibro.guardar({
          archivo: resultado.archivo,
          fecha: resultado.fecha,
          replica,
          auditoria: resultado.auditoria,
          hojaActiva: "",
          filtro: [],
          seleccionado: null,
        });
      } else {
        // Sin almacén (solo en pruebas) el Visor toma el archivo y audita por su cuenta, como siempre.
        fijarArchivoPendiente(resultado.archivo, "propio");
      }
      void navegar(rutaOPendientes("libros"));
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setErrorDeLaHoja(error);
    } finally {
      setPreparando(false);
    }
  };

  const principal = cargando ? (
    <Button kind="primary" size="md" disabled>
      Auditando…
    </Button>
  ) : motivoInactivo !== null ? (
    <BotonInactivo motivo={motivoInactivo}>Auditar el libro</BotonInactivo>
  ) : (
    <Button kind="primary" size="md" onClick={() => archivo && void auditar(archivo, fecha)}>
      {estado.fase === "error" ? "Reintentar" : "Auditar el libro"}
    </Button>
  );

  return (
    <div className="silice-libro">
      <section aria-labelledby="libro-paso-1" className="silice-libro__seccion">
        <h2 id="libro-paso-1" className="cds--type-heading-compact-02">
          <Numero n={1} />
          Suba el libro
        </h2>
        {resultado ? (
          <div className="silice-libro__paso">
            <p className="cds--type-body-compact-01">
              {"Libro auditado: "}
              <strong>{resultado.archivo.name}</strong>
              {`, revisado con la fecha ${fechaEsVe(resultado.fecha)}.`}
            </p>
            {pasoSiguiente(cuenta ?? cuentaDeHallazgos(resultado.auditoria)) === "informe" && (
              <Button kind="secondary" size="md" onClick={otroLibro}>
                Auditar otro libro
              </Button>
            )}
          </div>
        ) : (
          <>
            <p className="cds--type-body-compact-01">
              Suelte el Excel del presupuesto. Sílice recalcula cada partida y le dice lo que no cuadra. El archivo
              original no se modifica ni se guarda: solo quedan el resumen y los hallazgos.
            </p>
            <SubidaArchivo
              id="auditoria-subida"
              etiqueta="Suelte aquí el libro .xlsx del presupuesto, o haga clic para elegirlo"
              extensiones={[".xlsx"]}
              alElegir={elegir}
              deshabilitada={cargando}
            />
            <p role="status" className="cds--type-body-compact-01">
              {archivo ? `Archivo elegido: ${archivo.name}` : ""}
            </p>
            {estado.fase === "error" && <AvisoError error={estado.error} titulo="No se pudo auditar el libro" />}
            <div className="silice-libro__paso">{principal}</div>
            <details className="silice-libro__plegado">
              <summary>Más opciones</summary>
              <p className="cds--type-body-compact-01">
                {fecha === fechaDeHoy()
                  ? "Se revisa con la fecha de hoy."
                  : ISO.test(fecha)
                    ? `Se revisa con la fecha ${fechaEsVe(fecha)}.`
                    : "Falta la fecha de la revisión."}
              </p>
              <CampoTexto
                id="libro-fecha"
                type="date"
                size="sm"
                labelText="Fecha de la revisión"
                helperText="Con la misma fecha, el mismo libro da siempre el mismo resultado"
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
              />
              <div>
                <Button kind="tertiary" size="md" disabled={!archivo} onClick={conRecorrido}>
                  Auditar con recorrido guiado
                </Button>
                <p className="cds--type-helper-text-01">
                  Lleva el libro a «Libro de la empresa» con un recorrido de tres pasos.
                </p>
              </div>
            </details>
          </>
        )}
      </section>

      {cargando && <Esqueleto />}

      {resultado && cuenta && (
        <>
          <section aria-labelledby="libro-paso-2" className="silice-libro__seccion">
            <h2 id="libro-paso-2" ref={titular} tabIndex={-1} className="cds--type-heading-compact-02">
              <Numero n={2} />
              {fraseDeRespuesta(cuenta)}
            </h2>
            {cuenta.total > 0 && (
              <p className="silice-libro__datos cds--type-body-compact-01">
                {desgloseDeSeveridad(cuenta).join(" · ")}
              </p>
            )}
            <ProblemasDelLibro auditoria={resultado.auditoria} cuenta={cuenta} catalogo={catalogo} />
            <AlertasDePrecio avisos={avisos} catalogo={catalogo} />
          </section>

          <ConclusionDelLibro
            auditoria={resultado.auditoria}
            cuenta={cuenta}
            archivo={resultado.archivo}
            fecha={resultado.fecha}
            alOtro={otroLibro}
            alVerLaHoja={() => void verLaHoja()}
            preparandoLaHoja={preparando}
            errorDeLaHoja={errorDeLaHoja}
            alExpirar={alExpirar}
          />
        </>
      )}
    </div>
  );
}
