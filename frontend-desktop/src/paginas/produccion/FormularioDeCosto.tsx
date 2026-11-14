import { Button, Select, SelectItem } from "@carbon/react";
import { useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { registrarCosto } from "../../api/costos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import { hoyISO } from "../existencias/formato";
import { CENTROS, CONCEPTOS, OPCIONES_DE_MONEDA, fechaInicial, leerMonto, mensajeDeCostos, nombreDelMes } from "./logica";

interface Props {
  // El mes que se está viendo: el costo se registra en él, y su fecha debe caer dentro.
  periodo: string;
  alCerrar: () => void;
  // Ya se registró: la pantalla vuelve a leer la lista.
  alRegistrar: () => void;
  alExpirar: () => void;
}

interface Errores {
  centro?: string;
  monto?: string;
  moneda?: string;
  fecha?: string;
  fuente?: string;
}

const ID_FORMULARIO = "silice-costo-nuevo";

// «Registrar un costo»: un costo de la cantera o de la planta en el mes abierto. Todo se valida aquí antes de
// enviar; lo que la API rechaza se dice en español. El centro y la moneda no tienen valor por defecto: de ellos
// depende a qué producto se reparte el costo y un monto sin moneda no es un dato.
export function FormularioDeCosto({ periodo, alCerrar, alRegistrar, alExpirar }: Props): JSX.Element {
  const base = useId();
  const [centro, setCentro] = useState("");
  const [concepto, setConcepto] = useState(CONCEPTOS[0]!.valor);
  const [monto, setMonto] = useState("");
  const [moneda, setMoneda] = useState("");
  const [fecha, setFecha] = useState(() => fechaInicial(periodo, hoyISO()));
  const [fuente, setFuente] = useState("");
  const [nota, setNota] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    const lectura = leerMonto(monto);
    const nuevos: Errores = {};
    if (centro === "") nuevos.centro = "Elija el centro del costo.";
    if ("error" in lectura) nuevos.monto = lectura.error;
    if (moneda === "") nuevos.moneda = "Elija la moneda del monto.";
    if (!fecha.startsWith(`${periodo}-`)) nuevos.fecha = `La fecha debe caer en ${nombreDelMes(periodo)}.`;
    if (fuente.trim() === "") nuevos.fuente = "Escriba la fuente: la factura, el recibo o la nómina de donde sale el monto.";
    setErrores(nuevos);
    if ("error" in lectura || Object.keys(nuevos).length > 0) return;

    setEnviando(true);
    try {
      await registrarCosto({ periodo, centro, concepto, monto: lectura.valor, moneda, fecha, fuente: fuente.trim(), nota: nota.trim() });
      alRegistrar();
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(mensajeDeCostos(razon));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <MarcoDeDialogo
      titulo="Registrar un costo"
      alCerrar={alCerrar}
      inicial={() => document.getElementById(`${base}-monto`)}
      pie={
        <>
          <Button kind="secondary" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button kind="primary" type="submit" form={ID_FORMULARIO} disabled={enviando}>
            Registrar costo
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} className="costos-formulario" onSubmit={(e) => void enviar(e)} noValidate>
        <p className="costos-nota cds--type-body-compact-01">Se registra en {nombreDelMes(periodo)}.</p>
        <Select
          id={`${base}-centro`}
          labelText="Centro"
          value={centro}
          onChange={(e) => setCentro(e.target.value)}
          invalid={errores.centro !== undefined}
          invalidText={errores.centro ?? ""}
        >
          <SelectItem value="" text="Elija el centro" />
          {CENTROS.map((c) => (
            <SelectItem key={c.valor} value={c.valor} text={c.texto} />
          ))}
        </Select>
        <Select id={`${base}-concepto`} labelText="Concepto" value={concepto} onChange={(e) => setConcepto(e.target.value)}>
          {CONCEPTOS.map((c) => (
            <SelectItem key={c.valor} value={c.valor} text={c.texto} />
          ))}
        </Select>
        <CampoTexto
          id={`${base}-monto`}
          labelText="Monto"
          inputMode="decimal"
          autoComplete="off"
          helperText={AYUDA_CIFRAS}
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          invalid={errores.monto !== undefined}
          invalidText={errores.monto ?? ""}
        />
        <Select
          id={`${base}-moneda`}
          labelText="Moneda"
          value={moneda}
          onChange={(e) => setMoneda(e.target.value)}
          invalid={errores.moneda !== undefined}
          invalidText={errores.moneda ?? ""}
        >
          <SelectItem value="" text="Elija la moneda" />
          {OPCIONES_DE_MONEDA.map((m) => (
            <SelectItem key={m.valor} value={m.valor} text={m.texto} />
          ))}
        </Select>
        <CampoTexto
          id={`${base}-fecha`}
          type="date"
          labelText="Fecha"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          invalid={errores.fecha !== undefined}
          invalidText={errores.fecha ?? ""}
        />
        <CampoTexto
          id={`${base}-fuente`}
          labelText="Fuente (factura o recibo)"
          autoComplete="off"
          value={fuente}
          onChange={(e) => setFuente(e.target.value)}
          invalid={errores.fuente !== undefined}
          invalidText={errores.fuente ?? ""}
        />
        <CampoTexto id={`${base}-nota`} labelText="Nota (opcional)" autoComplete="off" value={nota} onChange={(e) => setNota(e.target.value)} />
        <AvisoError error={error} titulo="No se pudo registrar el costo" />
      </form>
    </MarcoDeDialogo>
  );
}
