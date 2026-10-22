import { Button, InlineNotification, RadioButton, RadioButtonGroup } from "@carbon/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { Dato } from "./Dato";
import { reaccionar } from "./fallos";
import type { Reacciones } from "./fallos";
import { fechaIsoDe, hoyISO } from "./formato";
import type { ImportacionRespuesta } from "./tipos";
import { CampoTexto } from "../../comun/CampoTexto";

interface Props {
  // Se importo un reporte: hay que volver a leer el tablero.
  alImportar: () => void;
  alVerSospechosos: () => void;
  reacciones: Reacciones;
}

const RUTA_IMPORTAR = "/v1/produccion/bascula/importar";

type Unidad = "encabezado" | "kg" | "t";

// Como se le llama a cada campo del reporte en la pantalla (la API los nombra como el detector de columnas).
const ROTULOS_DE_CAMPO: Record<string, string> = {
  ticket: "ticket",
  fecha: "fecha",
  placa: "placa",
  cliente: "cliente",
  material: "material",
  bruto: "peso bruto",
  tara: "tara",
  neto: "peso neto",
  peso: "peso",
};

const rotuloDeCampo = (campo: string) => ROTULOS_DE_CAMPO[campo] ?? campo;

// Los campos que la API no pudo ubicar: el 422 del lector trae `faltan` ademas del `detalle`.
function camposFaltantes(error: unknown): string[] | null {
  if (!(error instanceof ErrorDeApi) || error.estado !== 422) return null;
  const cuerpo = error.cuerpo;
  if (!cuerpo || typeof cuerpo !== "object") return null;
  const { faltan } = cuerpo as { faltan?: unknown };
  if (!Array.isArray(faltan)) return null;
  const campos = faltan.filter((c): c is string => typeof c === "string" && c !== "");
  return campos.length > 0 ? campos : null;
}

// Reporte de la bascula (.csv o .xlsx) a despachos (UC-29, RF-130 a RF-132). La interfaz solo manda el archivo, la
// fecha de referencia y, si hace falta, la unidad del peso y el numero de columna de lo que no se reconocio; leer,
// validar y no duplicar lo hace la API.
export function PestanaImportar({ alImportar, alVerSospechosos, reacciones }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [fecha, setFecha] = useState(() => hoyISO());
  const [unidad, setUnidad] = useState<Unidad>("encabezado");
  const [faltan, setFaltan] = useState<string[] | null>(null);
  const [columnas, setColumnas] = useState<Record<string, string>>({});
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorFecha, setErrorFecha] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [resultado, setResultado] = useState<ImportacionRespuesta | null>(null);
  const [importando, setImportando] = useState(false);

  const elegir = (elegido: File) => {
    setArchivo(elegido);
    setFaltan(null);
    setColumnas({});
    setErrores({});
    setError(null);
    setResultado(null);
  };

  const importar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!archivo) return;
    setError(null);

    const fechaValida = fechaIsoDe(fecha) !== "";
    setErrorFecha(fechaValida ? null : "Escriba la fecha de referencia.");

    const mapeo: Record<string, number> = {};
    const nuevosErrores: Record<string, string> = {};
    for (const campo of faltan ?? []) {
      const texto = (columnas[campo] ?? "").trim();
      if (texto === "") nuevosErrores[campo] = "Escriba el número de columna.";
      else if (!/^\d+$/.test(texto) || Number(texto) < 1) nuevosErrores[campo] = "Escriba un número entero de columna, desde 1.";
      else mapeo[campo] = Number(texto) - 1;
    }
    setErrores(nuevosErrores);
    if (!fechaValida || Object.keys(nuevosErrores).length > 0) return;

    const cuerpo = new FormData();
    cuerpo.append("archivo", archivo, archivo.name);
    cuerpo.append("fecha_referencia", fecha);
    if (unidad !== "encabezado") cuerpo.append("unidad_peso", unidad);
    if (faltan !== null) cuerpo.append("mapeo", JSON.stringify(mapeo));

    setImportando(true);
    try {
      const respuesta = await pedir<ImportacionRespuesta>(RUTA_IMPORTAR, { metodo: "POST", cuerpo });
      setResultado(respuesta);
      setFaltan(null);
      setColumnas({});
      alImportar();
    } catch (razon) {
      const campos = camposFaltantes(razon);
      if (campos) {
        setFaltan(campos);
        setColumnas({});
        setResultado(null);
      } else {
        setError(reaccionar(razon, reacciones));
      }
    } finally {
      setImportando(false);
    }
  };

  return (
    <form className="existencias-bloque" onSubmit={(e) => void importar(e)} noValidate>
      <p className="existencias-nota cds--type-body-compact-01">
        Suba el reporte de la báscula. Cada pesaje correcto entra como un despacho; los dudosos (tara mayor que el bruto,
        neto que no cuadra, fecha futura, material desconocido) van a la bandeja de pesajes sospechosos. Importar el
        mismo reporte dos veces no duplica nada.
      </p>
      {/* Carbon repite la etiqueta de la zona (una visible y otra solo para lectores de pantalla): la instruccion
          se dice una vez aqui y la zona lleva su propia etiqueta, corta. */}
      <p className="cds--type-body-compact-01">Suelte aquí el reporte de la báscula, en .csv o .xlsx.</p>
      <SubidaArchivo
        id="importar-bascula"
        etiqueta="Arrastre el archivo a este recuadro, o haga clic para elegirlo"
        extensiones={[".csv", ".xlsx"]}
        alElegir={elegir}
      />
      {archivo && (
        <p className="cds--type-body-compact-01">
          Archivo elegido: <strong>{archivo.name}</strong>
        </p>
      )}
      <div className="existencias-formulario">
        <RadioButtonGroup
          name="unidad-peso"
          legendText="Unidad del peso"
          valueSelected={unidad}
          onChange={(valor) => setUnidad(valor as Unidad)}
        >
          <RadioButton id="unidad-encabezado" labelText="Según el encabezado" value="encabezado" />
          <RadioButton id="unidad-kg" labelText="kg" value="kg" />
          <RadioButton id="unidad-t" labelText="t" value="t" />
        </RadioButtonGroup>
        <CampoTexto
          id="importar-fecha"
          type="date"
          labelText="Fecha de referencia"
          helperText="Sirve para detectar pesajes con fecha futura."
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          invalid={errorFecha !== null}
          invalidText={errorFecha ?? ""}
        />
      </div>

      {faltan !== null && (
        <section className="existencias-formulario" aria-label="Columnas por indicar">
          <p className="cds--type-body-compact-01">{`No se reconocieron las columnas de: ${faltan.map(rotuloDeCampo).join(", ")}.`}</p>
          <p className="existencias-nota cds--type-body-compact-01">
            Escriba en qué número de columna está cada una en el archivo (1 = la primera columna).
          </p>
          {faltan.map((campo) => (
            <CampoTexto
              key={campo}
              id={`columna-${campo}`}
              labelText={`Columna de ${rotuloDeCampo(campo)}`}
              inputMode="numeric"
              autoComplete="off"
              value={columnas[campo] ?? ""}
              onChange={(e) => setColumnas((previas) => ({ ...previas, [campo]: e.target.value }))}
              invalid={errores[campo] !== undefined}
              invalidText={errores[campo] ?? ""}
            />
          ))}
        </section>
      )}

      <AvisoError error={error} titulo="No se pudo importar el reporte" />

      <div>
        <Button type="submit" kind="primary" size="md" disabled={!archivo || importando}>
          Importar
        </Button>
      </div>

      {resultado && (
        <section className="existencias-bloque" aria-label="Resultado de la importación">
          <div className="existencias-resumen">
            <Dato rotulo="Despachos registrados" valor={resultado.registrados} />
            <Dato rotulo="Ya estaban registrados" valor={resultado.ya_registrados} />
            <Dato rotulo="A la bandeja de sospechosos" valor={resultado.a_la_bandeja} />
          </div>
          {resultado.a_la_bandeja > 0 && (
            <>
              <InlineNotification
                kind="warning"
                role="status"
                lowContrast
                hideCloseButton
                title={`${resultado.a_la_bandeja} ${resultado.a_la_bandeja === 1 ? "pesaje no entró" : "pesajes no entraron"} al inventario`}
                subtitle="Corríjalos o descártelos en la bandeja de pesajes sospechosos."
              />
              <div>
                <Button kind="tertiary" size="md" onClick={alVerSospechosos}>
                  Ver los pesajes sospechosos
                </Button>
              </div>
            </>
          )}
        </section>
      )}
    </form>
  );
}
