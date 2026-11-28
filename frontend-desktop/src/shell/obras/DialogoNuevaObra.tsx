import { Button, Select, SelectItem } from "@carbon/react";
import { useContext, useEffect, useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { useInRouterContext, useNavigate } from "react-router";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CarpetaRespuesta, ProyectoRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { anteriorA, hoyIso, leerFechaEscrita } from "../../comun/fechaEscrita";
import { TIPO_DE_OBRA } from "../../comun/logicaBusqueda";
import { MONEDAS, rotuloDeMoneda } from "../../comun/monedas";
import { rutaDeObra } from "../../marco/secciones";
import { MarcoDeDialogo } from "../carpetas/MarcoDeDialogo";
import { ContextoAplicacion } from "../contexto";
import { formulariosSucios } from "../sucio";
import "./DialogoNuevaObra.scss";

export type ModoDeInicioObra = "en_blanco" | "computo";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  // La obra creada (201 de `POST /v1/proyectos`): el armazon recarga la lista y la elige.
  alCrear: (obra: ProyectoRespuesta, inicio: ModoDeInicioObra) => void;
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
const NOTA_TASA_BCV = "La tasa usada queda anotada en cada versión.";
const ID_FORMULARIO = "silice-nueva-obra";
// Como llama `POST /v1/proyectos` a la carpeta de la empresa (ningun nombre de carpeta real lo es: todos terminan en .db).
const CARPETA_DE_LA_EMPRESA = "empresa";

const conMayuscula = (texto: string) => texto.charAt(0).toLocaleUpperCase("es") + texto.slice(1);

// El mismo texto que el 422 de `PUT /v1/obras/{codigo}/entrega` (`aplicacion/entrega_de_obra.py`): aquí se mira
// antes de crear, para que una fecha pasada no deje la obra creada sin su fecha (y un segundo intento, una obra doble).
const MENSAJE_FECHA_PASADA = "La fecha de entrega al cliente no puede estar en el pasado.";

function ConRouter({ children }: { children: (navegar: (ruta: string) => void) => JSX.Element }): JSX.Element {
  const navegar = useNavigate();
  return children((ruta: string) => {
    void navegar(ruta);
  });
}

function ConNavegacionOpcional({
  children,
}: {
  children: (navegar: ((ruta: string) => void) | null) => JSX.Element;
}): JSX.Element {
  const enRouter = useInRouterContext();
  return enRouter ? <ConRouter>{children}</ConRouter> : children(null);
}

// «Nueva obra › Componer la obra» (especificación 01b-nueva-obra.html): secciones «Datos de la obra» (nombre, cliente y
// ubicación opcionales, tipo de obra, moneda con su ayuda y nota de conversión con la tasa del BCV), «Cómo empezar» como
// grupo de radios con dos opciones («En blanco» y «Desde un cómputo en Excel») y «Dónde se guarda» (la carpeta, la primera
// versión y quién la crea). Mismos datos y mismo endpoint (`POST /v1/proyectos`).
export function DialogoNuevaObra({ abierto, ...resto }: Props): JSX.Element | null {
  if (!abierto) return null;
  return (
    <ConNavegacionOpcional>
      {(navegar) => <Formulario {...resto} navegar={navegar} />}
    </ConNavegacionOpcional>
  );
}

function Formulario({
  alCerrar,
  alCrear,
  destino,
  navegar,
}: Omit<Props, "abierto"> & { navegar: ((ruta: string) => void) | null }) {
  const base = useId();
  const contexto = useContext(ContextoAplicacion);
  const alExpirar = contexto?.alExpirar;
  const nombrePersona = contexto?.sesion.nombre ?? null;
  const [nombre, setNombre] = useState("");
  const [cliente, setCliente] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [dominio, setDominio] = useState("");
  const [moneda, setMoneda] = useState("");
  const [fechaEntrega, setFechaEntrega] = useState("");
  const [errorFechaEntrega, setErrorFechaEntrega] = useState<string | null>(null);
  const [inicio, setInicio] = useState<ModoDeInicioObra>("en_blanco");
  // La moneda de la carpeta: undefined mientras llega, null si no tiene.
  const [deLaCarpeta, setDeLaCarpeta] = useState<string | null | undefined>(undefined);
  const enOtraCarpeta = destino.enOtraCarpeta ?? false;
  const [faltaNombre, setFaltaNombre] = useState(false);
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
    if (nombre.trim() === "") {
      setFaltaNombre(true);
      document.getElementById(`${base}-nombre`)?.focus();
      return;
    }
    if (moneda === "") {
      setFaltaMoneda(true);
      return;
    }
    // En otra carpeta el campo no se ofrece: `PUT /v1/obras/{codigo}/entrega` va a la carpeta de la sesión.
    const lecturaFecha = enOtraCarpeta ? { ok: true as const, iso: null } : leerFechaEscrita(fechaEntrega);
    const errorDeFecha = !lecturaFecha.ok
      ? lecturaFecha.error
      : lecturaFecha.iso !== null && anteriorA(lecturaFecha.iso, hoyIso())
        ? MENSAJE_FECHA_PASADA
        : null;
    if (errorDeFecha !== null) {
      setErrorFechaEntrega(errorDeFecha);
      document.getElementById(`${base}-fecha-entrega`)?.focus();
      return;
    }
    setOcupado(true);
    try {
      const cuerpo = { nombre, moneda, dominio, descripcion: "", cliente, ubicacion };
      const obra = await pedir<ProyectoRespuesta>("/v1/proyectos", {
        metodo: "POST",
        cuerpo: { ...cuerpo, carpeta: destino.carpeta ?? CARPETA_DE_LA_EMPRESA },
      });
      if (lecturaFecha.ok && lecturaFecha.iso !== null) {
        await pedir(`/v1/obras/${encodeURIComponent(obra.codigo)}/entrega`, {
          metodo: "PUT",
          cuerpo: { fecha_entrega: lecturaFecha.iso },
        });
      }
      alCrear(obra, inicio);
      if (inicio === "computo" && /^\d+$/.test(obra.codigo) && navegar !== null) {
        const rutaComputo = rutaDeObra(destino.carpeta, Number(obra.codigo), "archivos");
        if (formulariosSucios(rutaComputo).length === 0) navegar(rutaComputo);
      }
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
      else setError(e);
    } finally {
      setOcupado(false);
    }
  }

  // La moneda que se conoce es la de la carpeta abierta: en otra no hay propuesta.
  const monedaDeCarpeta = enOtraCarpeta ? null : deLaCarpeta;
  const convierteConBcv = Boolean(monedaDeCarpeta && moneda && moneda !== monedaDeCarpeta);
  let ayudaMoneda: string;
  if (convierteConBcv) ayudaMoneda = CONVERSION;
  else if (monedaDeCarpeta) ayudaMoneda = `Es la moneda de esta carpeta (${monedaDeCarpeta}).`;
  else ayudaMoneda = "En esta moneda se calcularán los precios de la obra.";

  const resumenTipo = dominio && TIPO_DE_OBRA[dominio] ? conMayuscula(TIPO_DE_OBRA[dominio]) : "Sin tipo especificado";
  const resumenInicio = inicio === "computo" ? "Empieza desde un cómputo en Excel" : "Empieza en blanco";

  return (
    <MarcoDeDialogo
      titulo="Nueva obra"
      ancho="ancho"
      alCerrar={alCerrar}
      inicial={() => document.getElementById(`${base}-nombre`)}
      pie={
        <>
          <Button kind="secondary" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button kind="primary" type="submit" form={ID_FORMULARIO} disabled={ocupado}>
            {ocupado ? "Creando la obra…" : "Crear la obra"}
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} className="silice-nueva-obra" onSubmit={(e) => void crear(e)} noValidate>
        <div className="silice-nueva-obra__cabecera">
          <span className="silice-nueva-obra__sobre">Componer la obra · Los datos se pueden cambiar después</span>
          <div className="silice-nueva-obra__datos">
            <span>{resumenTipo}</span>
            {moneda && <span>{`Moneda ${moneda}`}</span>}
            <span>{resumenInicio}</span>
          </div>
        </div>

        <section className="silice-nueva-obra__seccion" aria-labelledby={`${base}-sec-datos`}>
          <h3 id={`${base}-sec-datos`} className="silice-nueva-obra__subtitulo">
            Datos de la obra
          </h3>
          <CampoTexto
            id={`${base}-nombre`}
            labelText="Nombre de la obra"
            helperText="Así se verá en la lista de obras y en el presupuesto que se entrega"
            value={nombre}
            maxLength={120}
            invalid={faltaNombre}
            invalidText="Escriba el nombre de la obra"
            onChange={(e) => {
              setNombre(e.target.value);
              setFaltaNombre(false);
            }}
          />
          <div className="silice-nueva-obra__par">
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
          </div>
          <div className="silice-nueva-obra__par">
            <Select
              id={`${base}-tipo`}
              labelText="Tipo de obra"
              helperText="Decide qué catálogo y qué reglas de auditoría se usan"
              value={dominio}
              onChange={(e) => setDominio(e.target.value)}
            >
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
          </div>
          {convierteConBcv && (
            <p className="silice-nueva-obra__nota-bcv" role="note">
              <strong>Si elige otra moneda:</strong> {NOTA_TASA_BCV}
            </p>
          )}
          {!enOtraCarpeta && (
            <div className="silice-nueva-obra__par">
              <CampoTexto
                id={`${base}-fecha-entrega`}
                labelText="Fecha de entrega al cliente"
                placeholder="dd/mm/aaaa"
                helperText="Opcional · dd/mm/aaaa"
                value={fechaEntrega}
                maxLength={10}
                invalid={errorFechaEntrega !== null}
                invalidText={errorFechaEntrega ?? ""}
                onChange={(e) => {
                  setFechaEntrega(e.target.value);
                  setErrorFechaEntrega(null);
                }}
              />
            </div>
          )}
        </section>

        <section className="silice-nueva-obra__seccion" aria-labelledby={`${base}-sec-inicio`}>
          <h3 id={`${base}-sec-inicio`} className="silice-nueva-obra__subtitulo">
            Cómo empezar
          </h3>
          <div role="radiogroup" aria-labelledby={`${base}-sec-inicio`} className="silice-nueva-obra__opciones">
            <label
              className={`silice-nueva-obra__opcion${inicio === "en_blanco" ? " silice-nueva-obra__opcion--activa" : ""}`}
            >
              <span className="silice-nueva-obra__opcion-cab">
                <input
                  type="radio"
                  name={`${base}-inicio`}
                  value="en_blanco"
                  checked={inicio === "en_blanco"}
                  onChange={() => setInicio("en_blanco")}
                  aria-labelledby={`${base}-op-blanco`}
                  aria-describedby={`${base}-op-blanco-desc`}
                />
                <span id={`${base}-op-blanco`} className="silice-nueva-obra__opcion-titulo">
                  En blanco
                </span>
              </span>
              <span id={`${base}-op-blanco-desc`} className="silice-nueva-obra__opcion-desc">
                Agregue las partidas una a una desde el catálogo
              </span>
            </label>

            <label
              className={`silice-nueva-obra__opcion${inicio === "computo" ? " silice-nueva-obra__opcion--activa" : ""}`}
            >
              <span className="silice-nueva-obra__opcion-cab">
                <input
                  type="radio"
                  name={`${base}-inicio`}
                  value="computo"
                  checked={inicio === "computo"}
                  onChange={() => setInicio("computo")}
                  aria-labelledby={`${base}-op-computo`}
                  aria-describedby={`${base}-op-computo-desc`}
                />
                <span id={`${base}-op-computo`} className="silice-nueva-obra__opcion-titulo">
                  Desde un cómputo en Excel
                </span>
              </span>
              <span id={`${base}-op-computo-desc`} className="silice-nueva-obra__opcion-desc">
                Traiga las partidas y cantidades de un cómputo métrico
              </span>
            </label>
          </div>
          <p className="silice-nueva-obra__ayuda">
            Empezar en blanco no cierra nada: desde Presupuestar › Plano o cómputo puede traer partidas cuando quiera.
          </p>
        </section>

        <section className="silice-nueva-obra__seccion" aria-labelledby={`${base}-sec-guarda`}>
          <h3 id={`${base}-sec-guarda`} className="silice-nueva-obra__subtitulo">
            Dónde se guarda
          </h3>
          <dl className="silice-nueva-obra__pares">
            <dt>Carpeta</dt>
            <dd className="silice-nueva-obra__destino">Se creará en {destino.titulo}</dd>
            <dt>Primera versión</dt>
            <dd>V1 · en elaboración</dd>
            {nombrePersona && (
              <>
                <dt>Quién la crea</dt>
                <dd>{nombrePersona}</dd>
              </>
            )}
          </dl>
          <p className="silice-nueva-obra__ayuda">
            {inicio === "computo"
              ? "Después de crearla se abre Presupuestar › Plano o cómputo"
              : "Después de crearla se abre la portada de la obra"}
          </p>
        </section>

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
