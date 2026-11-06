import { Button, Select, SelectItem } from "@carbon/react";
import { useContext, useEffect, useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CarpetaRespuesta, ProyectoRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { TIPO_DE_OBRA } from "../../comun/logicaBusqueda";
import { MONEDAS, rotuloDeMoneda } from "../../comun/monedas";
import { MarcoDeDialogo } from "../carpetas/MarcoDeDialogo";
import { ContextoAplicacion } from "../contexto";
import "./DialogoNuevaObra.scss";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  // La obra creada (201 de `POST /v1/proyectos`): el armazon recarga la lista y la elige.
  alCrear: (obra: ProyectoRespuesta) => void;
  // Donde se crea la obra (rediseno del marco, Tarea 6b): se nombra en el dialogo y se manda al servidor, que la crea alli
  // sin mover la carpeta de la sesion. Es obligatorio: ningun camino crea una obra sin decir donde (Tarea 8).
  destino: DestinoDeNuevaObra;
}

export interface DestinoDeNuevaObra {
  // El nombre que acepta `POST /v1/casos/actual` (null = la carpeta de la empresa).
  carpeta: string | null;
  titulo: string;
  // Es otra que la abierta en la sesion: su moneda no se conoce y no se propone ninguna.
  enOtraCarpeta?: boolean;
}

const OPCIONES_DE_MONEDA = MONEDAS.map((m) => ({ valor: m, texto: rotuloDeMoneda(m, true) }));
const CONVERSION = "Esta obra se valorará convirtiendo los precios de la carpeta con la tasa del BCV del día.";
const ID_FORMULARIO = "silice-nueva-obra";
// Como llama `POST /v1/proyectos` a la carpeta de la empresa (ningun nombre de carpeta real lo es: todos terminan en .db).
const CARPETA_DE_LA_EMPRESA = "empresa";

const conMayuscula = (texto: string) => texto.charAt(0).toLocaleUpperCase("es") + texto.slice(1);

// «Nueva obra» (diseno de modulos §7 y §12.7; BCP-6 §5.2, el dialogo «Nuevo proyecto» renombrado): nombre (obligatorio;
// lo valida la API), cliente y ubicacion (la ficha de la obra), tipo de obra y moneda. La moneda propuesta es la de la
// carpeta (`GET /v1/carpeta`, D-MP1); elegir la otra se puede y se dice que se convertira con la tasa del BCV. Sin moneda
// de la carpeta (o si la obra va a otra carpeta que la abierta) no hay propuesta y es obligatoria (UC-01: sin valor por
// defecto). Dice en que carpeta se creara; no la pregunta (Tarea 6b).
export function DialogoNuevaObra({ abierto, ...resto }: Props): JSX.Element | null {
  if (!abierto) return null;
  return <Formulario {...resto} />;
}

function Formulario({ alCerrar, alCrear, destino }: Omit<Props, "abierto">) {
  const base = useId();
  const alExpirar = useContext(ContextoAplicacion)?.alExpirar;
  const [nombre, setNombre] = useState("");
  const [cliente, setCliente] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [dominio, setDominio] = useState("");
  const [moneda, setMoneda] = useState("");
  // La moneda de la carpeta: undefined mientras llega, null si no tiene.
  const [deLaCarpeta, setDeLaCarpeta] = useState<string | null | undefined>(undefined);
  const enOtraCarpeta = destino.enOtraCarpeta ?? false;
  const [faltaMoneda, setFaltaMoneda] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let vigente = true;
    pedir<CarpetaRespuesta>("/v1/carpeta")
      .then((r) => {
        if (!vigente) return;
        const propia = typeof r?.moneda === "string" && MONEDAS.some((m) => m === r.moneda) ? r.moneda : null;
        setDeLaCarpeta(propia);
        // Se propone solo si la persona aun no eligio otra.
        if (propia && !enOtraCarpeta) setMoneda((elegida) => elegida || propia);
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
        // Sin saber la moneda de la carpeta no se propone ninguna: la persona la elige.
        setDeLaCarpeta(null);
      });
    return () => {
      vigente = false;
    };
  }, [alExpirar, enOtraCarpeta]);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (moneda === "") {
      setFaltaMoneda(true);
      return;
    }
    setOcupado(true);
    try {
      const cuerpo = { nombre, moneda, dominio, descripcion: "", cliente, ubicacion };
      const obra = await pedir<ProyectoRespuesta>("/v1/proyectos", {
        metodo: "POST",
        cuerpo: { ...cuerpo, carpeta: destino.carpeta ?? CARPETA_DE_LA_EMPRESA },
      });
      alCrear(obra);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
      else setError(e);
    } finally {
      setOcupado(false);
    }
  }

  // La moneda que se conoce es la de la carpeta abierta: en otra no hay propuesta.
  const monedaDeCarpeta = enOtraCarpeta ? null : deLaCarpeta;
  let ayudaMoneda: string;
  if (monedaDeCarpeta && moneda && moneda !== monedaDeCarpeta) ayudaMoneda = CONVERSION;
  else if (monedaDeCarpeta) ayudaMoneda = `Es la moneda de esta carpeta (${monedaDeCarpeta}).`;
  else ayudaMoneda = "En esta moneda se calcularán los precios de la obra.";

  return (
    <MarcoDeDialogo
      titulo="Nueva obra"
      alCerrar={alCerrar}
      inicial={() => document.getElementById(`${base}-nombre`)}
      pie={
        <>
          <Button kind="secondary" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button kind="primary" type="submit" form={ID_FORMULARIO} disabled={ocupado}>
            Crear obra
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} className="silice-nueva-obra" onSubmit={(e) => void crear(e)} noValidate>
        <CampoTexto
          id={`${base}-nombre`}
          labelText="Nombre de la obra"
          value={nombre}
          maxLength={120}
          onChange={(e) => setNombre(e.target.value)}
        />
        <p className="silice-nueva-obra__destino cds--type-body-compact-01">Se creará en {destino.titulo}</p>
        <CampoTexto
          id={`${base}-cliente`}
          labelText="Cliente (opcional)"
          value={cliente}
          maxLength={200}
          onChange={(e) => setCliente(e.target.value)}
        />
        <CampoTexto
          id={`${base}-ubicacion`}
          labelText="Ubicación (opcional)"
          value={ubicacion}
          maxLength={200}
          onChange={(e) => setUbicacion(e.target.value)}
        />
        <Select id={`${base}-tipo`} labelText="Tipo de obra" value={dominio} onChange={(e) => setDominio(e.target.value)}>
          <SelectItem value="" text="Sin especificar" />
          {Object.entries(TIPO_DE_OBRA).map(([valor, texto]) => (
            <SelectItem key={valor} value={valor} text={conMayuscula(texto)} />
          ))}
        </Select>
        <Select
          id={`${base}-moneda`}
          labelText="Moneda"
          value={moneda}
          helperText={ayudaMoneda}
          invalid={faltaMoneda}
          invalidText="Elija la moneda de la obra."
          onChange={(e) => {
            setMoneda(e.target.value);
            setFaltaMoneda(false);
          }}
        >
          {!monedaDeCarpeta && <SelectItem value="" text="Elija…" />}
          {OPCIONES_DE_MONEDA.map((m) => (
            <SelectItem key={m.valor} value={m.valor} text={m.texto} />
          ))}
        </Select>
        {ocupado && (
          <p className="silice-nueva-obra__estado cds--type-body-compact-01" role="status">
            Creando la obra…
          </p>
        )}
        <AvisoError error={error} titulo="No se pudo crear la obra" />
      </form>
    </MarcoDeDialogo>
  );
}
