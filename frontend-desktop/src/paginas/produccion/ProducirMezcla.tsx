import { Button, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { producirMezcla } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { AYUDA_CIFRAS, leerCifra } from "../../indicadores/cifraEscrita";
import { useAplicacion } from "../../shell/contexto";
import { hoyISO } from "../existencias/formato";
import { AvisoConFoco } from "./AvisoConFoco";
import { ErrorDeCalculo } from "./ErrorDeCalculo";
import { consumosDeLaReceta } from "./logicaMezcla";
import { mensajeDePlanta } from "./logicaPlanta";
import { useMezclas } from "./useMezclas";
import "./planta.scss";

const FECHA = /^\d{4}-\d{2}-\d{2}$/;

// «Producir mezcla»: registra lo que produjo la planta con la receta que rige en la fecha. Se elige entre los productos
// que tienen receta vigente ese día y se anuncia lo que saldrá del inventario (receta por toneladas, con enteros sobre
// el texto); el servidor lo vuelve a calcular al registrar y es quien decide. Las toneladas se escriben con coma decimal.
export default function ProducirMezcla() {
  const { alExpirar } = useAplicacion();
  const [fecha, setFecha] = useState(() => hoyISO());
  const [producto, setProducto] = useState("");
  const [toneladas, setToneladas] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const cajaDelError = useRef<HTMLDivElement>(null);

  const mezclas = useMezclas(FECHA.test(fecha) ? fecha : null, alExpirar);
  const disponibles = mezclas.estado === "listo" ? mezclas.datos : [];
  const elegida = disponibles.find((m) => m.codigo === producto);
  const lectura = toneladas.trim() === "" ? null : leerCifra(toneladas);
  const cantidad = lectura && "valor" in lectura && !lectura.valor.startsWith("-") && /[1-9]/.test(lectura.valor) ? lectura.valor : null;
  const errorDeToneladas = lectura && "error" in lectura ? lectura.error : lectura && cantidad === null ? "Las toneladas deben ser mayores que cero." : undefined;
  const consumos = elegida && cantidad ? consumosDeLaReceta(elegida.receta.componentes, cantidad) : [];

  useEffect(() => {
    if (error !== null) cajaDelError.current?.focus();
  }, [error]);

  async function registrar() {
    if (!elegida || cantidad === null) return;
    setError(null);
    setAviso(null);
    setEnviando(true);
    try {
      await producirMezcla({ producto: elegida.codigo, toneladas: cantidad, fecha });
      setAviso(`Producción registrada: ${formatoEsVe(cantidad)} t de ${elegida.codigo}.`);
      setToneladas("");
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="planta silice-pagina">
      <h1 className="cds--type-heading-04">Producir mezcla</h1>
      <p className="planta-nota cds--type-body-compact-01">
        Registra lo que produjo la planta. La receta que rige en la fecha dice cuánto de cada agregado propio sale del inventario.
      </p>
      <div className="planta-barra">
        <CampoTexto id="producir-fecha" type="date" labelText="Fecha de la producción" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        <Select id="producir-mezcla" labelText="Mezcla a producir" value={elegida ? producto : ""} onChange={(e) => setProducto(e.target.value)}>
          <SelectItem value="" text="Elija la mezcla" />
          {disponibles.map((m) => (
            <SelectItem key={m.codigo} value={m.codigo} text={`${m.codigo} · ${m.nombre}`} />
          ))}
        </Select>
        <CampoTexto
          id="producir-toneladas"
          labelText="Toneladas producidas"
          helperText={AYUDA_CIFRAS}
          autoComplete="off"
          inputMode="decimal"
          value={toneladas}
          invalid={errorDeToneladas !== undefined}
          invalidText={errorDeToneladas}
          onChange={(e) => setToneladas(e.target.value)}
        />
        <Button kind="primary" size="md" disabled={!elegida || cantidad === null || enviando} onClick={() => void registrar()}>
          Registrar producción
        </Button>
      </div>
      {mezclas.estado === "error" && <AvisoError error={mensajeDePlanta(mezclas.error)} titulo="No se pudieron leer las recetas" />}
      {mezclas.estado === "listo" && disponibles.length === 0 && (
        <p className="planta-nota cds--type-body-compact-01">Ningún producto tiene receta vigente en esa fecha. Registre una en «Receta de la planta».</p>
      )}
      {consumos.length > 0 && (
        <>
          <h2 className="cds--type-heading-compact-02">Consumirá del inventario</h2>
          <ul className="planta-lista cds--type-body-compact-01" aria-label="Lo que consumirá del inventario">
            {consumos.map((c) => (
              <li key={c.codigo}>
                {formatoEsVe(c.toneladas)} t de {c.codigo}
              </li>
            ))}
          </ul>
        </>
      )}
      <AvisoConFoco aviso={aviso} alCerrar={() => setAviso(null)} />
      <ErrorDeCalculo error={error} titulo="No se pudo registrar la producción" caja={cajaDelError} />
    </div>
  );
}
