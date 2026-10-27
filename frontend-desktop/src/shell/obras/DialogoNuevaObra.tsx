import { Button, Select, SelectItem } from "@carbon/react";
import { useContext, useEffect, useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { abrirCarpeta, volverALaCarpetaDeLaEmpresa } from "../../api/carpetaYObra";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CarpetaRespuesta, ProyectoRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { mensajeDeError } from "../../comun/errores";
import { TIPO_DE_OBRA } from "../../comun/logicaBusqueda";
import { hojasConCambios } from "../carpetas/hojasConCambios";
import { MarcoDeDialogo } from "../carpetas/MarcoDeDialogo";
import { ContextoAplicacion } from "../contexto";
import { confirmarSalida } from "../salida";
import "./DialogoNuevaObra.scss";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  // La obra creada (201 de `POST /v1/proyectos`): el armazon recarga la lista y la elige.
  // La carpeta donde quedo es el segundo argumento (null = la de la empresa); sin `carpetas`, la que ya estaba abierta.
  alCrear: (obra: ProyectoRespuesta, carpeta?: string | null) => void;
  // Las carpetas donde se puede crear la obra (las que tienen obras para esta cuenta). Con mas de una, el dialogo pide
  // la carpeta; con una o ninguna, no (rediseno del marco, Tarea 6).
  carpetas?: CarpetaDeObra[];
  // La carpeta abierta ahora (null = la de la empresa): la que se propone y la unica cuya moneda se conoce.
  carpetaAbierta?: string | null;
  // Las obras de la carpeta abierta, para nombrar los borradores que se perderian («Hoja de Casa Demo»).
  obrasDeLaCarpeta?: readonly Pick<ProyectoRespuesta, "codigo" | "nombre">[];
}

export interface CarpetaDeObra {
  carpeta: string | null;
  titulo: string;
}

const MONEDAS = [
  { valor: "Bs", texto: "Bolívares (Bs)" },
  { valor: "USD", texto: "Dólares estadounidenses (USD)" },
];
const CONVERSION = "Esta obra se valorará convirtiendo los precios de la carpeta con la tasa del BCV del día.";
const ID_FORMULARIO = "silice-nueva-obra";
// Ningun nombre de carpeta puede ser este (todos terminan en .db): es la de la empresa en el selector.
const VALOR_EMPRESA = "empresa";

const conMayuscula = (texto: string) => texto.charAt(0).toLocaleUpperCase("es") + texto.slice(1);

// «Nueva obra» (diseno de modulos §7 y §12.7; BCP-6 §5.2, el dialogo «Nuevo proyecto» renombrado): nombre (obligatorio;
// lo valida la API), cliente y ubicacion (la ficha de la obra), tipo de obra y moneda. La moneda propuesta es la de la
// carpeta (`GET /v1/carpeta`, D-MP1); elegir la otra se puede y se dice que se convertira con la tasa del BCV. Sin moneda
// de la carpeta no hay propuesta y es obligatoria (UC-01: sin valor por defecto).
export function DialogoNuevaObra({ abierto, ...resto }: Props): JSX.Element | null {
  if (!abierto) return null;
  return <Formulario {...resto} />;
}

function Formulario({ alCerrar, alCrear, carpetas = [], carpetaAbierta = null, obrasDeLaCarpeta }: Omit<Props, "abierto">) {
  const base = useId();
  const alExpirar = useContext(ContextoAplicacion)?.alExpirar;
  const [nombre, setNombre] = useState("");
  const [cliente, setCliente] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [dominio, setDominio] = useState("");
  const [moneda, setMoneda] = useState("");
  // La moneda de la carpeta: undefined mientras llega, null si no tiene.
  const [deLaCarpeta, setDeLaCarpeta] = useState<string | null | undefined>(undefined);
  const pideCarpeta = carpetas.length > 1;
  const [carpetaElegida, setCarpetaElegida] = useState<string | null>(carpetaAbierta);
  const [faltaMoneda, setFaltaMoneda] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let vigente = true;
    pedir<CarpetaRespuesta>("/v1/carpeta")
      .then((r) => {
        if (!vigente) return;
        const propia = typeof r?.moneda === "string" && MONEDAS.some((m) => m.valor === r.moneda) ? r.moneda : null;
        setDeLaCarpeta(propia);
        // Se propone solo si la persona aun no eligio otra.
        if (propia) setMoneda((elegida) => elegida || propia);
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
  }, [alExpirar]);

  const puedeEditar = useContext(ContextoAplicacion)?.sesion.acciones.includes("editar_hoja") ?? true;
  const irA = (carpeta: string | null) => (carpeta === null ? volverALaCarpetaDeLaEmpresa() : abrirCarpeta(carpeta));

  // Todo o nada: si crear falla despues de cambiar de carpeta, la sesion vuelve a la que estaba (los numeros de obra se
  // repiten entre carpetas). Si la vuelta tambien falla, se dice: la persona sigue en otra carpeta.
  async function volverALaAbierta(fallo: unknown): Promise<unknown> {
    try {
      await irA(carpetaAbierta);
      return fallo;
    } catch (e) {
      return `${mensajeDeError(fallo)} Además, no se pudo volver a la carpeta anterior: ${mensajeDeError(e)}`;
    }
  }

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (moneda === "") {
      setFaltaMoneda(true);
      return;
    }
    setOcupado(true);
    let cambio = false;
    try {
      // Crear en otra carpeta es abrirla primero (la API crea la obra en la carpeta de la sesion), y cambiar de carpeta
      // descarta los borradores de la Hoja: se pregunta antes y, con «Quedarme», no se cambia ni se crea nada.
      cambio = pideCarpeta && carpetaElegida !== carpetaAbierta;
      if (cambio) {
        const hojas = puedeEditar ? await hojasConCambios(obrasDeLaCarpeta) : [];
        if (!(await confirmarSalida("carpeta", hojas))) return;
        await irA(carpetaElegida);
      }
      const obra = await pedir<ProyectoRespuesta>("/v1/proyectos", {
        metodo: "POST",
        cuerpo: { nombre, moneda, dominio, descripcion: "", cliente, ubicacion },
      });
      alCrear(obra, pideCarpeta ? carpetaElegida : carpetaAbierta);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
      else setError(cambio ? await volverALaAbierta(e) : e);
    } finally {
      setOcupado(false);
    }
  }

  // La moneda que se conoce es la de la carpeta abierta: en otra no hay propuesta.
  const monedaDeCarpeta = carpetaElegida === carpetaAbierta ? deLaCarpeta : null;
  let ayudaMoneda: string;
  if (monedaDeCarpeta && moneda && moneda !== monedaDeCarpeta) ayudaMoneda = CONVERSION;
  else if (monedaDeCarpeta) ayudaMoneda = `Es la moneda de la carpeta de trabajo (${monedaDeCarpeta}).`;
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
        {pideCarpeta && (
          <Select
            id={`${base}-carpeta`}
            labelText="Carpeta"
            value={carpetaElegida ?? VALOR_EMPRESA}
            onChange={(e) => {
              const nueva = e.target.value === VALOR_EMPRESA ? null : e.target.value;
              setCarpetaElegida(nueva);
              setMoneda(nueva === carpetaAbierta ? (deLaCarpeta ?? "") : "");
              setFaltaMoneda(false);
            }}
          >
            {carpetas.map((c) => (
              <SelectItem key={c.carpeta ?? VALOR_EMPRESA} value={c.carpeta ?? VALOR_EMPRESA} text={c.titulo} />
            ))}
          </Select>
        )}
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
          {MONEDAS.map((m) => (
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
