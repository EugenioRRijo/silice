import { Button, Select, SelectItem } from "@carbon/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { AYUDA_CIFRAS, leerCifra } from "../../indicadores/cifraEscrita";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { FUENTES, describirError, fuenteInicial, hoyIso } from "./logica";
import type { Lado } from "./logica";

interface Props {
  lado: Lado;
  codigo: string;
  moneda: string;
  // Tras anotar, el estudio se vuelve a leer (las cifras cambian).
  alCambiar: () => void;
}

// «Anotar una observación»: un precio visto en el mercado, en la moneda de la carpeta. El precio se envia tal como se
// escribio (lo interpreta el servidor); antes se revisa con la misma regla para decir el error en el campo. Los demas
// errores de la API (fuente vacia, fecha futura, precio no positivo) se dicen con su mensaje tal cual.
export function AnotarObservacion({ lado, codigo, moneda, alCambiar }: Props) {
  const { alExpirar } = useAplicacion();
  const [tipo, setTipo] = useState(fuenteInicial(lado));
  const [fuente, setFuente] = useState("");
  const [fecha, setFecha] = useState(hoyIso);
  const [precio, setPrecio] = useState("");
  const [nota, setNota] = useState("");
  const [errorDelPrecio, setErrorDelPrecio] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [hecho, setHecho] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const id = `mercado-${lado}-anotar`;

  useFormularioSucio("mercado", fuente.trim() !== "" || precio.trim() !== "" || nota.trim() !== "");

  async function anotar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setHecho(null);
    const lectura = leerCifra(precio);
    if ("error" in lectura) {
      setErrorDelPrecio(lectura.error);
      document.getElementById(`${id}-precio`)?.focus();
      return;
    }
    setEnviando(true);
    try {
      const r = await pedir<{ id: number }>("/v1/mercado/observaciones", {
        metodo: "POST",
        cuerpo: { lado, codigo, fuente_tipo: tipo, fuente, fecha, precio, nota },
      });
      setFuente("");
      setPrecio("");
      setNota("");
      setHecho(`Observación n.º ${r.id} anotada.`);
      alCambiar();
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="silice-mercado__bloque" aria-labelledby={`${id}-titulo`}>
      <h2 id={`${id}-titulo`} className="cds--type-heading-compact-02">
        Anotar una observación
      </h2>
      <form className="silice-mercado__anotar" aria-labelledby={`${id}-titulo`} onSubmit={(e) => void anotar(e)} noValidate>
        <Select id={`${id}-tipo`} labelText="De dónde sale" size="md" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          {FUENTES.map(([valor, nombre]) => (
            <SelectItem key={valor} value={valor} text={nombre} />
          ))}
        </Select>
        <CampoTexto
          id={`${id}-fuente`}
          labelText="Fuente"
          helperText="Quién o dónde: el proveedor, el competidor o la cotización."
          size="md"
          maxLength={200}
          value={fuente}
          onChange={(e) => setFuente(e.target.value)}
        />
        <CampoTexto
          id={`${id}-fecha`}
          labelText="Fecha"
          helperText="El día en que vio el precio; no puede ser posterior a hoy."
          size="md"
          type="date"
          max={hoyIso()}
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
        />
        <CampoTexto
          id={`${id}-precio`}
          labelText={`Precio (${moneda})`}
          helperText={AYUDA_CIFRAS}
          size="md"
          inputMode="decimal"
          autoComplete="off"
          value={precio}
          invalid={errorDelPrecio !== null}
          invalidText={errorDelPrecio ?? ""}
          {...describirError(`${id}-precio`, errorDelPrecio !== null)}
          onChange={(e) => {
            setPrecio(e.target.value);
            setErrorDelPrecio(null);
          }}
        />
        <CampoTexto
          id={`${id}-nota`}
          labelText="Nota (opcional)"
          helperText="Condiciones del precio: contado, a crédito, flete incluido…"
          size="md"
          maxLength={500}
          value={nota}
          onChange={(e) => setNota(e.target.value)}
        />
        <div className="silice-mercado__ancho">
          <Button type="submit" kind="secondary" size="md" disabled={enviando}>
            {enviando ? "Anotando…" : "Anotar observación"}
          </Button>
        </div>
      </form>
      <AvisoError error={error} titulo="No se anotó la observación" />
      <p role="status" className="silice-mercado__estado cds--type-body-compact-01">
        {hecho ?? ""}
      </p>
    </section>
  );
}
