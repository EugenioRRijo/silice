import { Button, TextInput } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AVISO_HERRAMIENTA,
  MENSAJE_SIN_FILAS,
  SEMILLA_INICIAL,
  VARIACION_INICIAL,
  cuerpoDe,
  errorDeSemilla,
  errorDeVariacion,
  filasDeTabla,
  resumenDeEnvio,
} from "./logica";
import type { CuerpoSimulacion, FilaSimulada } from "./logica";
import "./simulador.scss";

const COLUMNAS: ColumnaDensa[] = [
  { clave: "tipo", titulo: "Tipo" },
  { clave: "insumo", titulo: "Insumo" },
  { clave: "unidad", titulo: "Unidad" },
  { clave: "precio", titulo: "Precio", numerica: true },
];

type Estado =
  | { fase: "inicial" }
  | { fase: "cargando" }
  | { fase: "error"; error: unknown }
  | { fase: "listo"; filas: FilaSimulada[]; cuerpo: CuerpoSimulacion };

// «Simulador de listas» (UC-07, herramienta de prueba): aplica variaciones deterministas a la lista vigente del caso
// y ofrece el CSV. Paridad con ui/paginas/simulador.py; la simulacion la hace la API, aqui no se calcula nada.
export default function PaginaSimulador() {
  const { alExpirar } = useAplicacion();
  const [semilla, setSemilla] = useState(SEMILLA_INICIAL);
  const [variacion, setVariacion] = useState(VARIACION_INICIAL);
  const [insumos, setInsumos] = useState("");
  const [estado, setEstado] = useState<Estado>({ fase: "inicial" });
  const peticion = useRef(0);
  const tituloRef = useRef<HTMLHeadingElement>(null);
  const avisoRef = useRef<HTMLDivElement>(null);
  const errorSemilla = errorDeSemilla(semilla);
  const errorVariacion = errorDeVariacion(variacion);
  const hayError = errorSemilla !== null || errorVariacion !== null;
  const cargando = estado.fase === "cargando";

  // Al terminar, el foco va al resultado (o al aviso de error) para que quien usa teclado o lector lo encuentre.
  useEffect(() => {
    if (estado.fase === "listo") tituloRef.current?.focus();
    if (estado.fase === "error") avisoRef.current?.focus();
  }, [estado]);

  async function generar(evento: FormEvent) {
    evento.preventDefault();
    if (hayError) return;
    const cuerpo = cuerpoDe({ semilla, variacion, insumos });
    const numero = ++peticion.current;
    setEstado({ fase: "cargando" });
    try {
      const respuesta = await pedir<{ filas: FilaSimulada[] }>("/v1/simulador", { metodo: "POST", cuerpo });
      if (numero === peticion.current) setEstado({ fase: "listo", filas: respuesta.filas, cuerpo });
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      if (numero === peticion.current) setEstado({ fase: "error", error });
    }
  }

  // El resultado en pantalla es el del ultimo envio: si el formulario cambio despues, se avisa.
  const cambiado =
    estado.fase === "listo" &&
    (errorSemilla !== null || JSON.stringify(cuerpoDe({ semilla, variacion, insumos })) !== JSON.stringify(estado.cuerpo));

  let resumen = "";
  if (cargando) resumen = "Simulando…";
  if (estado.fase === "listo") {
    resumen = `Lista simulada: ${estado.filas.length} ${estado.filas.length === 1 ? "fila" : "filas"}`;
  }

  return (
    <div className="silice-simulador">
      <h1 className="cds--type-heading-04">Simulador de listas</h1>
      <p className="silice-simulador__nota cds--type-body-compact-01">{AVISO_HERRAMIENTA}</p>

      <form className="silice-simulador__formulario" onSubmit={(e) => void generar(e)} noValidate>
        <TextInput
          id="simulador-semilla"
          labelText="Semilla"
          helperText="Mismo número, misma lista: sirve para repetir un resultado."
          size="md"
          inputMode="numeric"
          value={semilla}
          invalid={errorSemilla !== null}
          invalidText={errorSemilla ?? ""}
          onChange={(e) => setSemilla(e.target.value)}
        />
        <TextInput
          id="simulador-variacion"
          labelText="Variación máxima (%)"
          helperText="Cada precio sube o baja, como máximo, este porcentaje."
          size="md"
          inputMode="decimal"
          value={variacion}
          invalid={errorVariacion !== null}
          invalidText={errorVariacion ?? ""}
          onChange={(e) => setVariacion(e.target.value)}
        />
        <TextInput
          id="simulador-insumos"
          labelText="Insumos"
          helperText="Separados por coma; vacío = todos."
          size="md"
          value={insumos}
          onChange={(e) => setInsumos(e.target.value)}
        />
        <div className="silice-simulador__accion">
          <Button type="submit" kind="primary" size="md" disabled={hayError || cargando}>
            {cargando ? "Simulando…" : "Generar lista simulada"}
          </Button>
        </div>
      </form>

      <section className="silice-simulador__resultado" aria-label="Resultado de la simulación">
        <p role="status" className="silice-simulador__resumen cds--type-label-02">
          {resumen}
        </p>
        {estado.fase === "inicial" && (
          <EstadoVacio
            titulo="Aún no hay lista simulada"
            descripcion="Ajuste los parámetros y pulse Generar lista simulada."
          />
        )}
        {cargando && <TablaDensa etiqueta="lista simulada" columnas={COLUMNAS} filas={[]} cargando />}
        {estado.fase === "error" && (
          <div ref={avisoRef} tabIndex={-1} className="silice-simulador__aviso">
            <AvisoError error={estado.error} titulo="No se pudo simular la lista" />
          </div>
        )}
        {estado.fase === "listo" && (
          <>
            <div className="silice-simulador__encabezado">
              <h2 ref={tituloRef} tabIndex={-1} className="cds--type-heading-compact-02">
                Lista simulada
              </h2>
              {estado.filas.length > 0 && (
                <DescargaArchivo
                  ruta="/v1/simulador/csv"
                  metodo="POST"
                  cuerpo={estado.cuerpo}
                  etiqueta="Descargar CSV"
                  nombrePorOmision="lista_simulada.csv"
                  alExpirar={alExpirar}
                />
              )}
            </div>
            <p className="silice-simulador__nota cds--type-body-compact-01">
              {`Resultado con los valores enviados: ${resumenDeEnvio(estado.cuerpo)}.`}
              {cambiado ? " Cambió el formulario: pulse Generar lista simulada para actualizar." : ""}
            </p>
            {estado.filas.length === 0 ? (
              <EstadoVacio titulo={MENSAJE_SIN_FILAS} />
            ) : (
              <TablaDensa etiqueta="Lista simulada" columnas={COLUMNAS} filas={filasDeTabla(estado.filas)} />
            )}
          </>
        )}
      </section>
    </div>
  );
}
