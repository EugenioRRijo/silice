import { WarningAltFilled } from "@carbon/icons-react";
import { Button, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { compararDecimales } from "../../comun/TablaDensa";
import { AYUDA_CIFRAS, leerCifra, textoParaEscribir } from "../../indicadores/cifraEscrita";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { Monto } from "./Cifras";
import { describirError, rutaDeAfectados, rutaDeUsar, textoDeAfectados } from "./logica";
import type { Estudio } from "./logica";

type Paso =
  | { fase: "editando" }
  | { fase: "consultando" }
  | { fase: "confirmando"; apus: string[] }
  | { fase: "guardando" };

// La propuesta y «Usar este precio». El campo llega prellenado con la propuesta, escrita como se teclea («2.010,50»);
// lo que la persona escribe se envia tal cual y lo interpreta el servidor. Antes se revisa con la misma regla
// (`leerCifra`) para decir el error en el campo sin ir a la API; el valor leido no se usa. En compra, antes de guardar
// se dice que partidas cambiaran de precio y se pide confirmar (D-MP2); en cobro se guarda el precio objetivo citando
// las observaciones de las cifras.
export function UsarPrecio({ estudio }: { estudio: Estudio }) {
  const { alExpirar } = useAplicacion();
  const { lado, codigo, moneda, propuesta, estadisticas } = estudio;
  const propuesto = propuesta.precio === null ? "" : textoParaEscribir(propuesta.precio);
  const [base, setBase] = useState(propuesto);
  const [precio, setPrecio] = useState(propuesto);
  const [respaldo, setRespaldo] = useState("");
  const [errorDelCampo, setErrorDelCampo] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [hecho, setHecho] = useState<string | null>(null);
  const [paso, setPaso] = useState<Paso>({ fase: "editando" });
  const campo = useRef<HTMLInputElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const pregunta = useRef<HTMLDivElement>(null);
  // Al cerrar la pregunta (confirmar o cancelar), el foco vuelve a «Usar este precio», que se vuelve a montar.
  const devolverFoco = useRef(false);
  const idTitulo = `mercado-${lado}-precio-titulo`;

  // Si la propuesta cambia (otra ventana de dias, una observacion nueva) y la persona no habia escrito nada propio, el
  // campo toma la nueva; lo escrito no se pisa.
  if (propuesto !== base) {
    setBase(propuesto);
    if (precio === base) setPrecio(propuesto);
  }

  useFormularioSucio("mercado", precio !== base);

  useEffect(() => {
    if (paso.fase === "confirmando") pregunta.current?.focus();
    if (paso.fase === "editando" && devolverFoco.current) {
      devolverFoco.current = false;
      boton.current?.focus();
    }
  }, [paso.fase]);

  const debajoDelPiso =
    lado === "cobro" &&
    estudio.piso !== null &&
    estadisticas.q1 !== null &&
    compararDecimales(estadisticas.q1, estudio.piso) < 0;
  const citables = estudio.observaciones.filter((o) => o.cuenta);
  const ocupado = paso.fase === "consultando" || paso.fase === "guardando";

  function fallo(e: unknown) {
    if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
    if (e instanceof ErrorDeApi && e.estado === 422) {
      setErrorDelCampo(e.detalle);
      setPaso({ fase: "editando" });
      campo.current?.focus();
      return;
    }
    setError(e);
    setPaso({ fase: "editando" });
  }

  async function guardar() {
    setPaso({ fase: "guardando" });
    try {
      if (lado === "compra") {
        const cita = citables.find((o) => String(o.id) === respaldo);
        const r = await pedir<{ lista: string }>(rutaDeUsar("compra", codigo), {
          metodo: "POST",
          cuerpo: { precio, observacion_id: cita ? cita.id : null },
        });
        setHecho(`Precio guardado en «${r.lista}».`);
      } else {
        const r = await pedir<{ codigo: string; precio: string; moneda: string }>(rutaDeUsar("cobro", codigo), {
          metodo: "POST",
          cuerpo: { precio, observaciones: estadisticas.ids },
        });
        setHecho(
          `Precio objetivo guardado: ${formatoEsVe(r.precio)} ${r.moneda}. La Hoja lo mostrará junto al precio del APU.`,
        );
      }
      setBase(precio);
      devolverFoco.current = true;
      setPaso({ fase: "editando" });
    } catch (e) {
      fallo(e);
    }
  }

  async function usar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setHecho(null);
    const lectura = leerCifra(precio);
    if ("error" in lectura) {
      setErrorDelCampo(lectura.error);
      campo.current?.focus();
      return;
    }
    if (lado === "cobro") {
      await guardar();
      return;
    }
    setPaso({ fase: "consultando" });
    try {
      const r = await pedir<{ apus: string[] }>(rutaDeAfectados(codigo));
      setPaso({ fase: "confirmando", apus: r.apus });
    } catch (e) {
      fallo(e);
    }
  }

  function cancelar() {
    devolverFoco.current = true;
    setPaso({ fase: "editando" });
  }

  return (
    <section className="silice-mercado__bloque" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Su precio
      </h2>
      {propuesta.precio !== null ? (
        <>
          <p className="cds--type-body-compact-01">
            Propuesta de Sílice:{" "}
            <strong>
              <Monto valor={propuesta.precio} moneda={moneda} />
            </strong>
          </p>
          <p className="silice-mercado__razon cds--type-body-compact-01">
            {debajoDelPiso && (
              <WarningAltFilled aria-label="Aviso" className="silice-mercado__icono-aviso" />
            )}
            <span>{propuesta.razon}</span>
          </p>
        </>
      ) : (
        <p className="silice-mercado__nota cds--type-body-compact-01">
          Sin propuesta: no hay observaciones con qué compararla. Si ya sabe su precio, escríbalo.
        </p>
      )}

      <form className="silice-mercado__usar" onSubmit={(e) => void usar(e)} noValidate>
        <CampoTexto
          ref={campo}
          id={`mercado-${lado}-precio`}
          labelText="Su precio"
          helperText={`En ${moneda}. ${AYUDA_CIFRAS}`}
          size="md"
          inputMode="decimal"
          autoComplete="off"
          value={precio}
          invalid={errorDelCampo !== null}
          invalidText={errorDelCampo ?? ""}
          {...describirError(`mercado-${lado}-precio`, errorDelCampo !== null)}
          readOnly={paso.fase !== "editando"}
          onChange={(e) => {
            setPrecio(e.target.value);
            setErrorDelCampo(null);
            setHecho(null);
          }}
        />
        {lado === "compra" ? (
          <Select
            id={`mercado-${lado}-respaldo`}
            labelText="Observación que respalda el precio"
            helperText="Opcional: queda como fuente del precio en la lista."
            size="md"
            value={respaldo}
            disabled={paso.fase !== "editando"}
            onChange={(e) => setRespaldo(e.target.value)}
          >
            <SelectItem value="" text="Ninguna: es un precio propio" />
            {citables.map((o) => (
              <SelectItem
                key={o.id}
                value={String(o.id)}
                text={`n.º ${o.id} · ${o.fuente} · ${fechaEsVe(o.fecha)} · ${formatoEsVe(o.precio)} ${o.moneda}`}
              />
            ))}
          </Select>
        ) : null}
        <p className="silice-mercado__nota silice-mercado__ancho cds--type-helper-text-01">
          {lado === "compra"
            ? "Entra en la lista para armar de la carpeta con la fecha de hoy. Las versiones ya guardadas no cambian."
            : `Se guarda como su precio de venta objetivo de ${codigo}, citando las observaciones de las cifras.`}
        </p>
        {paso.fase !== "confirmando" && (
          <div className="silice-mercado__ancho">
            <Button ref={boton} type="submit" kind="primary" size="md" disabled={ocupado}>
              {ocupado ? "Un momento…" : "Usar este precio"}
            </Button>
          </div>
        )}
      </form>

      {paso.fase === "confirmando" && (
        <div ref={pregunta} tabIndex={-1} className="silice-mercado__pregunta" role="group" aria-label="Confirmar el precio">
          <p className="cds--type-body-compact-01">{textoDeAfectados(paso.apus)}</p>
          <p className="cds--type-body-compact-01">{`¿Usar ${precio} ${moneda} para ${codigo}?`}</p>
          <div className="silice-mercado__botones">
            <Button kind="primary" size="md" onClick={() => void guardar()}>
              Confirmar
            </Button>
            <Button kind="secondary" size="md" onClick={cancelar}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      <AvisoError error={error} titulo="No se usó el precio" />
      <p role="status" className="silice-mercado__estado cds--type-body-compact-01">
        {hecho ?? ""}
      </p>
    </section>
  );
}
