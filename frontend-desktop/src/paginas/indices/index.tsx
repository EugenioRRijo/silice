import { Button, InlineLoading, InlineNotification, Select, SelectItem, TextInput } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AVISO_SIN_XLRD,
  AYUDA,
  COLUMNAS_RECHAZOS,
  COLUMNAS_SERIES,
  SIN_ARCHIVO,
  cambiarDefinicion,
  definicionesIniciales,
  faltaXlrd,
  filasRechazos,
  filasSeries,
  formularioConfirmacion,
  formularioLectura,
  hoyIso,
  textoOmitidos,
} from "./logica";
import type { Confirmacion, Contexto, Definicion, Informe, Lectura } from "./logica";
import "./indices.scss";

type CargaContexto =
  | { tipo: "cargando" }
  | { tipo: "listo"; contexto: Contexto }
  | { tipo: "error"; error: unknown };

type EstadoLectura =
  | { tipo: "ninguna" }
  | { tipo: "leyendo" }
  | { tipo: "sinArchivo" }
  | { tipo: "error"; error: unknown }
  | { tipo: "lista"; lectura: Lectura };

type EstadoConfirmacion =
  | { tipo: "ninguna" }
  | { tipo: "enCurso" }
  | { tipo: "error"; error: unknown }
  | { tipo: "hecha"; mensajes: string[] };

// «Índices del BCV» (UC-17 pasos 1-3): leer un archivo del BCV sin escribir nada, revisar el informe previo y
// confirmar. La interfaz no calcula nada ni muestra valores de índices: la API trae recuentos, rangos de fechas y
// los mensajes de cada serie, que se muestran tal cual. «Confirmar» vuelve a enviar el archivo leído (la API no
// guarda el informe entre una y otra) con su huella, y la API comprueba que sea el mismo.
export default function PaginaIndices() {
  const { alExpirar } = useAplicacion();
  const [carga, setCarga] = useState<CargaContexto>({ tipo: "cargando" });
  const [tipo, setTipo] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [fuente, setFuente] = useState("");
  const [fechaDescarga, setFechaDescarga] = useState(hoyIso());
  const [lectura, setLectura] = useState<EstadoLectura>({ tipo: "ninguna" });
  const [definiciones, setDefiniciones] = useState<Definicion[]>([]);
  const [confirmacion, setConfirmacion] = useState<EstadoConfirmacion>({ tipo: "ninguna" });
  const consultaLectura = useRef(0);
  const consultaConfirmacion = useRef(0);

  const expirada = (error: unknown) => {
    if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
  };

  useEffect(() => {
    let vigente = true;
    pedir<Contexto>("/v1/indices/contexto").then(
      (contexto) => {
        if (!vigente) return;
        setCarga({ tipo: "listo", contexto });
        setTipo((actual) => actual || (contexto.tipos[0]?.id ?? ""));
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setCarga({ tipo: "error", error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [alExpirar]);

  const contexto = carga.tipo === "listo" ? carga.contexto : null;

  const leer = (evento: FormEvent) => {
    evento.preventDefault();
    if (!contexto || lectura.tipo === "leyendo") return;
    ++consultaConfirmacion.current;
    setConfirmacion({ tipo: "ninguna" });
    if (archivo === null) {
      ++consultaLectura.current;
      setLectura({ tipo: "sinArchivo" });
      return;
    }
    const numero = ++consultaLectura.current;
    const datos = { tipo, archivo, fuente, fechaDescarga };
    setLectura({ tipo: "leyendo" });
    pedir<Informe>("/v1/indices/leer", { metodo: "POST", cuerpo: formularioLectura(datos) }).then(
      (informe) => {
        if (numero !== consultaLectura.current) return;
        setDefiniciones(definicionesIniciales(informe.series, contexto.unidad_por_defecto, contexto.periodicidades));
        setLectura({ tipo: "lista", lectura: { ...datos, informe } });
      },
      (error: unknown) => {
        if (numero !== consultaLectura.current) return;
        expirada(error);
        setLectura({ tipo: "error", error });
      },
    );
  };

  const confirmar = (leida: Lectura) => {
    if (confirmacion.tipo === "enCurso") return;
    const numero = ++consultaConfirmacion.current;
    setConfirmacion({ tipo: "enCurso" });
    pedir<Confirmacion>("/v1/indices/confirmar", {
      metodo: "POST",
      cuerpo: formularioConfirmacion(leida, definiciones),
    }).then(
      (respuesta) => {
        if (numero !== consultaConfirmacion.current) return;
        // Ya se guardó: el informe previo se retira, como en la pantalla clásica.
        setLectura({ tipo: "ninguna" });
        setConfirmacion({ tipo: "hecha", mensajes: respuesta.mensajes });
      },
      (error: unknown) => {
        if (numero !== consultaConfirmacion.current) return;
        expirada(error);
        setConfirmacion({ tipo: "error", error });
      },
    );
  };

  return (
    <div className="silice-indices">
      <h1 className="cds--type-heading-04">Índices del BCV</h1>
      <p className="cds--type-body-compact-01">{AYUDA}</p>

      {carga.tipo === "cargando" && <EsqueletoPagina etiqueta="Cargando las opciones" />}
      {carga.tipo === "error" && <AvisoError error={carga.error} titulo="No se pudo abrir la página" />}

      {contexto && (
        <form className="silice-indices__formulario" onSubmit={leer}>
          <div className="silice-indices__campos">
            <Select
              id="indices-tipo"
              labelText="Qué archivo es"
              size="sm"
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
            >
              {contexto.tipos.map((t) => (
                <SelectItem key={t.id} value={t.id} text={t.rotulo} />
              ))}
            </Select>
            <TextInput
              id="indices-fuente"
              labelText="Dirección de la página del BCV de donde lo bajó"
              size="sm"
              value={fuente}
              onChange={(e) => setFuente(e.target.value)}
            />
            <TextInput
              id="indices-fecha"
              type="date"
              labelText="Fecha de descarga"
              size="sm"
              value={fechaDescarga}
              onChange={(e) => setFechaDescarga(e.target.value)}
            />
          </div>
          <SubidaArchivo
            id="indices-archivo"
            etiqueta="Suelte aquí el archivo (.xls, .xlsx o .csv), o haga clic para elegirlo"
            extensiones={contexto.extensiones}
            alElegir={setArchivo}
          />
          {archivo && <p className="silice-indices__nota cds--type-label-01">Archivo elegido: {archivo.name}</p>}
          {faltaXlrd(tipo, archivo, contexto.lee_xls) && (
            <InlineNotification
              kind="warning"
              role="status"
              title="Falta un componente"
              subtitle={AVISO_SIN_XLRD}
              lowContrast
              hideCloseButton
            />
          )}
          <div className="silice-indices__acciones">
            <Button type="submit" kind="primary" size="md" disabled={lectura.tipo === "leyendo"}>
              Leer
            </Button>
            {lectura.tipo === "leyendo" && <InlineLoading description="Leyendo..." status="active" />}
          </div>
        </form>
      )}

      <div aria-live="polite" aria-atomic="true" className="silice-indices__avisos">
        {lectura.tipo === "sinArchivo" && (
          <InlineNotification
            kind="error"
            role="alert"
            title="Falta el archivo"
            subtitle={SIN_ARCHIVO}
            lowContrast
            hideCloseButton
          />
        )}
        {lectura.tipo === "error" && <AvisoError error={lectura.error} titulo="No se pudo leer el archivo" />}
        {confirmacion.tipo === "hecha" &&
          confirmacion.mensajes.map((mensaje, i) => (
            <InlineNotification
              key={i}
              kind="success"
              role="status"
              title="Importación"
              subtitle={mensaje}
              lowContrast
              hideCloseButton
            />
          ))}
      </div>

      {contexto && lectura.tipo === "lista" && (
        <InformePrevio
          lectura={lectura.lectura}
          contexto={contexto}
          definiciones={definiciones}
          alCambiar={(posicion, campo, valor) =>
            setDefiniciones((previas) => cambiarDefinicion(previas, posicion, campo, valor))
          }
          confirmacion={confirmacion}
          alConfirmar={() => confirmar(lectura.lectura)}
        />
      )}
    </div>
  );
}

interface PropsInforme {
  lectura: Lectura;
  contexto: Contexto;
  definiciones: Definicion[];
  alCambiar: (posicion: number, campo: keyof Omit<Definicion, "serie">, valor: string) => void;
  confirmacion: EstadoConfirmacion;
  alConfirmar: () => void;
}

function InformePrevio({ lectura, contexto, definiciones, alCambiar, confirmacion, alConfirmar }: PropsInforme) {
  const { informe } = lectura;
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titulo.current?.focus();
  }, [informe]);
  const enCurso = confirmacion.tipo === "enCurso";
  return (
    <section className="silice-indices__informe" aria-labelledby="indices-informe">
      <h2 id="indices-informe" ref={titulo} tabIndex={-1} className="cds--type-heading-compact-02">
        Informe previo (todavía no se guardó nada)
      </h2>
      <section aria-label="Resumen de la lectura">
        <dl className="silice-indices__datos">
          <div>
            <dt className="cds--type-label-01">Filas leídas</dt>
            <dd className="cds--type-heading-04">{informe.filas_leidas}</dd>
          </div>
          <div>
            <dt className="cds--type-label-01">Rechazadas</dt>
            <dd className="cds--type-heading-04">{informe.filas_rechazadas}</dd>
          </div>
          <div>
            <dt className="cds--type-label-01">Provisionales</dt>
            <dd className="cds--type-heading-04">{informe.provisionales}</dd>
          </div>
        </dl>
      </section>
      <TablaDensa
        etiqueta="Series leídas"
        columnas={COLUMNAS_SERIES}
        filas={filasSeries(informe.series)}
        vacio={{ titulo: "El archivo no trae ninguna serie" }}
      />
      {informe.rechazos.length > 0 && (
        <TablaDensa etiqueta="Filas rechazadas" columnas={COLUMNAS_RECHAZOS} filas={filasRechazos(informe.rechazos)} />
      )}
      {informe.rechazos_omitidos > 0 && (
        <p className="silice-indices__nota cds--type-label-01">{textoOmitidos(informe.rechazos_omitidos)}</p>
      )}
      {informe.advertencias.length > 0 && (
        <ul className="silice-indices__advertencias cds--type-body-compact-01" aria-label="Advertencias del lector">
          {informe.advertencias.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      )}

      {lectura.tipo === "csv" &&
        definiciones.map((d, i) => (
          <fieldset key={d.serie} className="silice-indices__serie">
            <legend className="cds--type-heading-compact-01">Serie {d.serie}</legend>
            <div className="silice-indices__campos">
              <TextInput
                id={`indices-nombre-${i}`}
                labelText={`Nombre de ${d.serie}`}
                size="sm"
                value={d.nombre}
                onChange={(e) => alCambiar(i, "nombre", e.target.value)}
              />
              <TextInput
                id={`indices-organismo-${i}`}
                labelText={`Organismo de ${d.serie}`}
                size="sm"
                value={d.organismo}
                onChange={(e) => alCambiar(i, "organismo", e.target.value)}
              />
              <TextInput
                id={`indices-unidad-${i}`}
                labelText={`Unidad de ${d.serie}`}
                size="sm"
                value={d.unidad}
                onChange={(e) => alCambiar(i, "unidad", e.target.value)}
              />
              <Select
                id={`indices-periodicidad-${i}`}
                labelText={`Periodicidad de ${d.serie}`}
                size="sm"
                value={d.periodicidad}
                onChange={(e) => alCambiar(i, "periodicidad", e.target.value)}
              >
                {contexto.periodicidades.map((p) => (
                  <SelectItem key={p} value={p} text={p} />
                ))}
              </Select>
            </div>
          </fieldset>
        ))}

      <p className="cds--type-body-compact-01">Responsable de la importación: {contexto.responsable}</p>
      <div className="silice-indices__acciones">
        <Button kind="primary" size="md" disabled={enCurso} onClick={alConfirmar}>
          Confirmar la importación
        </Button>
        {enCurso && <InlineLoading description="Guardando..." status="active" />}
      </div>
      {confirmacion.tipo === "error" && <AvisoError error={confirmacion.error} titulo="No se pudo confirmar" />}
    </section>
  );
}
