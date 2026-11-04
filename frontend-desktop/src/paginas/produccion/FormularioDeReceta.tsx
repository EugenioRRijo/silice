import { Button } from "@carbon/react";
import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { registrarReceta } from "../../api/produccionPlanta";
import { AvisoError } from "../../comun/AvisoError";
import { CampoDeConsulta } from "../../comun/CampoDeConsulta";
import { CampoTexto } from "../../comun/CampoTexto";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import { FilaDeComponente } from "./FilaDeComponente";
import { armarComponentes, mensajeDePlanta, rangoDeMasa, sumaDeMasa } from "./logicaPlanta";
import type { FilaDeComponente as Fila } from "./logicaPlanta";

interface Props {
  alCerrar: () => void;
  // Ya se registró: la pantalla avisa y vuelve a leer la receta vigente.
  alRegistrar: () => void;
  alExpirar: () => void;
}

interface Errores {
  producto?: string;
  vigente?: string;
  fuente?: string;
}

interface FilaConId extends Fila {
  id: number;
}

const ID_FORMULARIO = "silice-receta-nueva";
const VACIA = { codigo: "", cantidad: "", unidad: "", tipo: "" };

// «Registrar una receta nueva»: lo que lleva una tonelada de mezcla. Una receta nueva no cambia las anteriores. La suma
// de masa se muestra mientras se escribe y Guardar se bloquea fuera de la tolerancia; es un aviso previo: el servidor
// vuelve a comprobarla y es quien decide. Ni la fecha desde la que rige ni la unidad ni el tipo traen valor por defecto.
export function FormularioDeReceta({ alCerrar, alRegistrar, alExpirar }: Props): JSX.Element {
  const base = useId();
  const siguiente = useRef(2);
  const botonAgregar = useRef<HTMLButtonElement>(null);
  const [producto, setProducto] = useState("");
  const [vigente, setVigente] = useState("");
  const [fuente, setFuente] = useState("");
  const [filas, setFilas] = useState<FilaConId[]>([{ id: 1, ...VACIA }]);
  const [nueva, setNueva] = useState<number | null>(null);
  const [errores, setErrores] = useState<Errores>({});
  const [error, setError] = useState<unknown>(null);
  const [errorDeFila, setErrorDeFila] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const suma = sumaDeMasa(filas);
  const [desde, hasta] = rangoDeMasa();

  // Una fila agregada recibe el foco en su código; al quitar una, el foco va a «Agregar un componente».
  useEffect(() => {
    if (nueva !== null) document.getElementById(`${base}-${nueva}-codigo`)?.focus();
  }, [nueva, base]);

  function cambiar(id: number, cambio: Partial<Fila>) {
    setFilas((actuales) => actuales.map((f) => (f.id === id ? { ...f, ...cambio } : f)));
  }

  function agregar() {
    const id = siguiente.current++;
    setFilas((actuales) => [...actuales, { id, ...VACIA }]);
    setNueva(id);
  }

  function quitar(id: number) {
    setFilas((actuales) => actuales.filter((f) => f.id !== id));
    setNueva(null);
    botonAgregar.current?.focus();
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    const nuevos: Errores = {};
    if (producto.trim() === "") nuevos.producto = "Indique el código del producto.";
    if (vigente === "") nuevos.vigente = "Indique desde qué fecha rige la receta.";
    if (fuente.trim() === "") nuevos.fuente = "Indique la fuente de la receta (la dosificación de donde sale).";
    const lectura = armarComponentes(filas);
    setErrores(nuevos);
    setErrorDeFila("error" in lectura ? lectura.error : null);
    if ("error" in lectura || Object.keys(nuevos).length > 0 || !suma.dentro) return;

    setEnviando(true);
    try {
      await registrarReceta({ producto: producto.trim(), componentes: lectura.componentes, fuente: fuente.trim(), vigente_desde: vigente });
      alRegistrar();
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    } finally {
      setEnviando(false);
    }
  }

  const estadoDeMasa = suma.dentro
    ? "dentro del rango"
    : suma.completa
      ? "fuera del rango, el servidor no la aceptará"
      : "complete las cantidades para comprobarla";

  return (
    <MarcoDeDialogo
      titulo="Registrar una receta nueva"
      ancho="ancho"
      alCerrar={alCerrar}
      inicial={() => document.getElementById(`${base}-producto`)}
      pie={
        <>
          <Button kind="secondary" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button kind="primary" type="submit" form={ID_FORMULARIO} disabled={enviando || !suma.dentro}>
            Registrar receta
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} className="receta-formulario" onSubmit={(e) => void enviar(e)} noValidate>
        <p className="planta-nota cds--type-body-compact-01">
          Una receta nueva no cambia las anteriores: rige desde la fecha que indique.
        </p>
        <CampoDeConsulta
          id={`${base}-producto`}
          etiqueta="Producto (código)"
          tabla="materiales_produccion"
          texto={producto}
          alCambiarTexto={setProducto}
          alExpirar={alExpirar}
          invalido={errores.producto !== undefined}
          textoInvalido={errores.producto ?? ""}
        />
        <CampoTexto
          id={`${base}-vigente`}
          type="date"
          labelText="Vigente desde"
          value={vigente}
          onChange={(e) => setVigente(e.target.value)}
          invalid={errores.vigente !== undefined}
          invalidText={errores.vigente ?? ""}
        />
        <CampoTexto
          id={`${base}-fuente`}
          labelText="Fuente (dosificación)"
          autoComplete="off"
          value={fuente}
          onChange={(e) => setFuente(e.target.value)}
          invalid={errores.fuente !== undefined}
          invalidText={errores.fuente ?? ""}
        />
        {filas.map((f, i) => (
          <FilaDeComponente
            key={f.id}
            numero={i + 1}
            base={`${base}-${f.id}`}
            fila={f}
            sePuedeQuitar={filas.length > 1}
            alCambiar={(cambio) => cambiar(f.id, cambio)}
            alQuitar={() => quitar(f.id)}
            alExpirar={alExpirar}
          />
        ))}
        <div>
          <Button ref={botonAgregar} kind="tertiary" size="sm" onClick={agregar}>
            Agregar un componente
          </Button>
        </div>
        <p
          role="status"
          aria-label="Suma de masa"
          className={`receta-masa cds--type-body-compact-01${suma.completa && !suma.dentro ? " receta-masa--fuera" : ""}`}
        >
          Suma de masa: {suma.texto} t por t de mezcla, {estadoDeMasa} (debe estar entre {desde} y {hasta}). Los litros no cuentan.
        </p>
        <AvisoError error={errorDeFila} titulo="Revise los componentes" />
        <AvisoError error={error === null ? null : mensajeDePlanta(error)} titulo="No se pudo registrar la receta" />
      </form>
    </MarcoDeDialogo>
  );
}
