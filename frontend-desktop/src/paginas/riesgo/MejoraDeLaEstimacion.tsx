import { Button } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { calcularMejora, rutaDelInformeDeMejora } from "../../api/riesgo";
import type { MejoraDeLaEstimacion as Mejora, PedidoDeMejora } from "../../api/riesgo";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { AYUDA_CIFRAS, leerCifra } from "../../indicadores/cifraEscrita";
import { centesimasEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";

// La cifra de la proyección que se ofrece como estimación de Sílice: el P50 exacto, de qué versión y en qué moneda.
export interface Precarga {
  cifra: string;
  version: string;
  moneda: string;
}

interface Props {
  precarga: Precarga | null;
  alExpirar: () => void;
}

type Clave = "real" | "original" | "silice";
const ROTULOS: Record<Clave, string> = {
  real: "Costo final real",
  original: "Presupuesto original",
  silice: "Estimación de Sílice",
};

// Lo que llegó del servidor y con qué textos se pidió: si la persona cambia una cifra, lo de antes deja de mostrarse.
type Pedido =
  | { estado: "nada" }
  | { estado: "cargando" }
  | { estado: "listo"; textos: string; consulta: PedidoDeMejora; datos: Mejora }
  | { estado: "error"; textos: string; error: unknown };

// Qué dice la mejora en palabras: el signo no se esconde; una negativa se lee como tal.
function lecturaDeLaMejora(mejoraPp: string): string {
  if (/^[-+]?0+(?:\.0+)?$/.test(mejoraPp)) return "Las dos estimaciones se alejaron lo mismo del costo real.";
  if (mejoraPp.startsWith("-")) return "La estimación de Sílice se alejó más del costo real que el presupuesto original: la mejora es negativa.";
  return "La estimación de Sílice se acercó más al costo real que el presupuesto original.";
}

// «Mejora de la estimación» (Tarea 15): cuando la obra termina, cuánto se alejó cada estimación del costo real. La
// pantalla lee las tres cifras con coma decimal y punto de miles y las manda con punto (fila 90); los errores y la
// mejora los calcula el servidor (`POST /v1/riesgo/mejora`) y aquí solo se escriben en es-VE. No necesita la obra
// abierta. La estimación de Sílice viene con el P50 de la última proyección, en centésimas, y se puede cambiar.
export function MejoraDeLaEstimacion({ precarga, alExpirar }: Props): JSX.Element {
  const llave = precarga === null ? null : `${precarga.version}|${precarga.cifra}`;
  const [real, setReal] = useState("");
  const [original, setOriginal] = useState("");
  // Lo que la persona escribió en la de Sílice y sobre qué proyección: una proyección nueva vuelve a precargar.
  const [silice, setSilice] = useState<{ de: string | null; texto: string }>({ de: null, texto: "" });
  const textoSilice = silice.de === llave || precarga === null ? silice.texto : centesimasEsVe(precarga.cifra);
  const [errores, setErrores] = useState<Partial<Record<Clave, string>>>({});
  const [pedido, setPedido] = useState<Pedido>({ estado: "nada" });
  const region = useRef<HTMLElement>(null);
  const cajaDelError = useRef<HTMLDivElement>(null);

  const textos = JSON.stringify([real, original, textoSilice]);
  const resultado = pedido.estado === "listo" && pedido.textos === textos ? pedido : null;
  const error = pedido.estado === "error" && pedido.textos === textos ? pedido.error : null;

  // El botón queda desactivado mientras se espera: el foco pasa a lo que llegó (el resultado o el error).
  useEffect(() => {
    if (pedido.estado === "listo") region.current?.focus();
    if (pedido.estado === "error") cajaDelError.current?.focus();
  }, [pedido]);

  const valores: Record<Clave, string> = { real, original, silice: textoSilice };
  function cambiar(clave: Clave, texto: string) {
    if (clave === "real") setReal(texto);
    else if (clave === "original") setOriginal(texto);
    else setSilice({ de: llave, texto });
    setErrores((e) => ({ ...e, [clave]: undefined }));
  }

  async function calcular() {
    const leidas = { real: leerCifra(real), original: leerCifra(original), silice: leerCifra(textoSilice) };
    const malas: Partial<Record<Clave, string>> = {};
    for (const clave of Object.keys(leidas) as Clave[]) {
      const lectura = leidas[clave];
      if ("error" in lectura) malas[clave] = lectura.error;
    }
    if ("error" in leidas.real || "error" in leidas.original || "error" in leidas.silice) {
      setErrores(malas);
      return;
    }
    const consulta: PedidoDeMejora = {
      costo_final_real: leidas.real.valor,
      presupuesto_original: leidas.original.valor,
      estimacion_silice: leidas.silice.valor,
    };
    setPedido({ estado: "cargando" });
    try {
      setPedido({ estado: "listo", textos, consulta, datos: await calcularMejora(consulta) });
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      setPedido({ estado: "error", textos, error: razon });
    }
  }

  const ayudaSilice =
    precarga !== null && silice.de !== llave
      ? `Viene con el P50 de la proyección de ${precarga.version} (${precarga.moneda}); puede cambiarla.`
      : undefined;
  return (
    <section aria-labelledby="mejora-titulo" className="riesgo-mejora">
      <h2 id="mejora-titulo" className="cds--type-heading-compact-02">
        Mejora de la estimación
      </h2>
      <p className="riesgo-nota cds--type-body-compact-01">
        Cuando la obra termina, compare lo que costó de verdad con lo que se estimó antes de Sílice (el presupuesto original) y
        con Sílice. Las tres cifras van en la misma moneda y a la misma fecha de precios. {AYUDA_CIFRAS}
      </p>
      <div className="riesgo-campos">
        {(Object.keys(ROTULOS) as Clave[]).map((clave) => (
          <CampoTexto
            key={clave}
            id={`mejora-${clave}`}
            labelText={ROTULOS[clave]}
            inputMode="decimal"
            value={valores[clave]}
            helperText={clave === "silice" ? ayudaSilice : undefined}
            invalid={errores[clave] !== undefined}
            invalidText={errores[clave]}
            onChange={(e) => cambiar(clave, e.target.value)}
          />
        ))}
      </div>
      <div className="riesgo-acciones">
        <Button kind="secondary" size="md" disabled={pedido.estado === "cargando"} onClick={() => void calcular()}>
          Calcular la mejora
        </Button>
      </div>
      {error !== null && (
        <div ref={cajaDelError} tabIndex={-1}>
          <AvisoError error={error} titulo="No se pudo calcular la mejora" />
        </div>
      )}
      {resultado !== null && (
        <section ref={region} tabIndex={-1} aria-label="Resultado de la mejora" className="riesgo-resultado">
          <dl className="riesgo-cifras">
            <dt>Error del presupuesto original</dt>
            <dd className="silice-cifra">{`${formatoEsVe(resultado.datos.error_original_pct)} %`}</dd>
            <dt>Error de la estimación de Sílice</dt>
            <dd className="silice-cifra">{`${formatoEsVe(resultado.datos.error_silice_pct)} %`}</dd>
            <dt>Mejora</dt>
            <dd className="silice-cifra">{`${formatoEsVe(resultado.datos.mejora_pp)} puntos`}</dd>
          </dl>
          <p className="riesgo-nota cds--type-body-compact-01">{lecturaDeLaMejora(resultado.datos.mejora_pp)}</p>
          <DescargaArchivo
            ruta={rutaDelInformeDeMejora(resultado.consulta)}
            etiqueta="Descargar el informe de mejora (Excel)"
            nombrePorOmision="mejora.xlsx"
            alExpirar={alExpirar}
            kind="tertiary"
            size="sm"
          />
        </section>
      )}
    </section>
  );
}
