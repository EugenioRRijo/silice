import { Button, Select, SelectItem } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { calcularCosto, calculoGuardado } from "../../api/produccionPlanta";
import type { CalculoDeCosto } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { AvisoConFoco } from "./AvisoConFoco";
import { CalculosAnteriores } from "./CalculosAnteriores";
import { ErrorDeCalculo } from "./ErrorDeCalculo";
import { MONEDAS, mesAnterior, nombreDelMes, periodoValido } from "./logica";
import { mensajeDePlanta } from "./logicaPlanta";
import { PublicarCosto } from "./PublicarCosto";
import { RepartoPorPesos, SIN_REPARTO } from "./RepartoPorPesos";
import type { Reparto } from "./RepartoPorPesos";
import { ResultadoDelCalculo } from "./ResultadoDelCalculo";
import { useProducido } from "./useProducido";
import "./planta.scss";

const ACCION = "registrar_costos_produccion";
const ACCION_PUBLICAR = "publicar_costo_propio";

// «Costo por tonelada»: el costo propio de cada agregado y de cada mezcla en un mes, calculado por el servidor con los
// costos del período, lo producido y las recetas. Cada cálculo se guarda con sus entradas (recalcular crea otro) y la
// publicación al catálogo es otra acción, solo de quien administra. La pantalla no calcula ningún monto: los escribe
// con coma decimal. La moneda no tiene valor por defecto: el costo de cada día se convierte con la tasa BCV de ese día.
export default function CostoPorTonelada() {
  const { alExpirar, sesion } = useAplicacion();
  const puede = sesion.acciones.includes(ACCION);
  const puedePublicar = sesion.acciones.includes(ACCION_PUBLICAR);
  const [periodo, setPeriodo] = useState(() => mesAnterior());
  const [moneda, setMoneda] = useState("");
  const [calculo, setCalculo] = useState<CalculoDeCosto | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [calculando, setCalculando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [reparto, setReparto] = useState<Reparto>(SIN_REPARTO);
  // Sube cuando algo pudo cambiar la lista de cálculos del mes; y «enfocar», cuando hay un resultado nuevo que mostrar.
  const [version, setVersion] = useState(0);
  const [enfocar, setEnfocar] = useState(0);
  const region = useRef<HTMLElement>(null);
  const cajaDelError = useRef<HTMLDivElement>(null);

  const valido = periodoValido(periodo);
  const producido = useProducido(puede && valido ? periodo : null, alExpirar);

  // El botón se desactiva mientras se calcula: el foco pasa a lo que llegó (el resultado o el error), no a BODY.
  useEffect(() => {
    if (enfocar > 0) region.current?.focus();
  }, [enfocar]);
  useEffect(() => {
    if (error !== null) cajaDelError.current?.focus();
  }, [error]);

  // Un resultado de otro mes o de otra moneda no puede quedar a la vista como si fuera el de ahora.
  function cambiarDatos(accion: () => void) {
    accion();
    setCalculo(null);
    setError(null);
    setAviso(null);
  }

  async function calcular() {
    setError(null);
    setAviso(null);
    setCalculando(true);
    try {
      setCalculo(await calcularCosto(periodo, moneda, reparto.activo ? (reparto.pesos ?? undefined) : undefined));
      setEnfocar((n) => n + 1);
      setVersion((n) => n + 1);
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else {
        setCalculo(null);
        setError(razon);
      }
    } finally {
      setCalculando(false);
    }
  }

  // Tras publicar (o tras un 409) se vuelve a leer el cálculo abierto para que muestre dónde quedó, sin mover el foco.
  async function releer(id: number) {
    setVersion((n) => n + 1);
    try {
      setCalculo(await calculoGuardado(id));
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
    }
  }

  if (!puede) {
    return (
      <div className="planta silice-pagina">
        <h1 className="cds--type-heading-04">Costo por tonelada</h1>
        <p className="planta-nota cds--type-body-compact-01">
          Su cuenta no registra costos de producción. Pídale a quien administra Sílice que revise su rol.
        </p>
      </div>
    );
  }

  return (
    <div className="planta silice-pagina">
      <h1 className="cds--type-heading-04">Costo por tonelada</h1>
      <p className="planta-nota cds--type-body-compact-01">
        Se calcula con los costos del mes, lo que se produjo y la receta de cada mezcla. Cada cálculo se guarda con sus datos; si
        vuelve a calcular se crea otro y el anterior queda como estaba.
      </p>
      <div className="planta-barra">
        <CampoTexto id="costo-mes" type="month" labelText="Mes" value={periodo} onChange={(e) => cambiarDatos(() => setPeriodo(e.target.value))} />
        <Select
          id="costo-moneda"
          labelText="Moneda del cálculo"
          value={moneda}
          onChange={(e) => cambiarDatos(() => setMoneda(e.target.value))}
        >
          <SelectItem value="" text="Elija la moneda" />
          {MONEDAS.map((m) => (
            <SelectItem key={m.valor} value={m.valor} text={m.texto} />
          ))}
        </Select>
        <Button kind="primary" size="md" disabled={!valido || moneda === "" || calculando || (reparto.activo && !reparto.valido)} onClick={() => void calcular()}>
          Calcular costo por tonelada
        </Button>
      </div>
      {!valido && <p className="planta-nota cds--type-body-compact-01">Elija el mes que quiere calcular.</p>}
      {valido && producido.estado === "error" && <AvisoError error={mensajeDePlanta(producido.error)} titulo="No se pudo leer lo producido" />}
      {valido && producido.estado === "listo" && (
        <>
          <h2 className="cds--type-heading-compact-02">Producido en {nombreDelMes(periodo)}</h2>
          {producido.datos.length === 0 ? (
            <p className="planta-nota cds--type-body-compact-01">Todavía no hay producción registrada en este mes.</p>
          ) : (
            <ul className="planta-lista cds--type-body-compact-01" aria-label="Toneladas producidas">
              {producido.datos.map((p) => (
                <li key={p.codigo}>
                  {p.codigo}: {formatoEsVe(p.toneladas)} t
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {valido && producido.estado === "listo" && producido.datos.length > 0 && (
        <RepartoPorPesos key={periodo} periodo={periodo} producido={producido.datos} alCambiar={setReparto} alExpirar={alExpirar} />
      )}
      <AvisoConFoco aviso={aviso} alCerrar={() => setAviso(null)} />
      <ErrorDeCalculo error={error} titulo={error instanceof ErrorDeApi && error.estado === 409 ? "No se pudo publicar el costo" : "No se pudo calcular el costo"} caja={cajaDelError} />
      {calculo && (
        <ResultadoDelCalculo calculo={calculo} region={region}>
          {puedePublicar && !calculo.publicado && calculo.productos.length > 0 && (
            <PublicarCosto
              calculo={calculo}
              alExpirar={alExpirar}
              alPublicar={(nombre) => {
                setAviso(`Publicado: lista "${nombre}".`);
                void releer(calculo.id);
              }}
              alConflicto={(razon) => {
                setError(razon);
                void releer(calculo.id);
              }}
            />
          )}
        </ResultadoDelCalculo>
      )}
      {valido && (
        <CalculosAnteriores
          periodo={periodo}
          version={version}
          alExpirar={alExpirar}
          alAbrir={(abierto) => {
            setError(null);
            setAviso(null);
            setCalculo(abierto);
            setEnfocar((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}
