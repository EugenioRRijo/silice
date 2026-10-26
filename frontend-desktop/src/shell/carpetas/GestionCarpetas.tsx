import { Button, Select, SelectItem, SkeletonText, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useCallback, useContext, useEffect, useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CasoRespuesta, CasosRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { mensajeDeError } from "../../comun/errores";
import { CampoTexto } from "../../comun/CampoTexto";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { ContextoAplicacion } from "../contexto";
import type { MonedaPendiente } from "../contexto";
import { nombreDeCarpeta } from "../Selectores";
import "./GestionCarpetas.scss";

// De donde se abrio una carpeta: el dialogo se cierra al abrir una de la lista o la demostracion, y se queda abierto
// para contar lo que paso al crear o subir.
export type OrigenDeApertura = "lista" | "creada" | "subida" | "demostracion";

interface Props {
  // Abre la carpeta por su nombre (con .db). La del armazon pregunta antes si hay trabajo sin guardar y resuelve si la
  // abrio (false: la persona se quedo); si la API la rechaza, lanza el error y aqui se muestra en linea. Con `preparar`
  // (crear la carpeta) pregunta primero, luego llama a `preparar` y abre el nombre que devuelve: «Quedarme» no crea nada.
  alAbrir: (nombre: string, preparar?: () => Promise<string>) => void | Promise<boolean>;
  // Estrenar la demostracion exige `editar_hoja` (BCP-5 §4.2); sin ella la pestana no aparece y se dice por que.
  conDemostracion: boolean;
  // Declarar la moneda de la carpeta (`PUT /v1/carpeta/moneda`) exige `editar_hoja`; sin ella, crear no la pide.
  puedeDeclararMoneda?: boolean;
  // Despues de abrir una carpeta.
  alAbierta?: (origen: OrigenDeApertura) => void;
  // Nivel de los titulos de sus dos partes: 3 dentro del dialogo (su titulo es el h2), 2 en Administracion.
  nivelDeTitulo?: 2 | 3;
}

const EXPLICACION = "Una carpeta de trabajo guarda su catálogo, sus precios y sus obras en un solo archivo.";
const MIB = 1024 * 1024;
// El tope de `POST /v1/casos/subida` y su texto (`aplicacion/casos.py`, `MENSAJE_GRANDE`): un archivo mayor no se envia.
const TOPE_SUBIDA = 20 * MIB;
const MENSAJE_GRANDE = "El archivo pasa de 20 MiB.";

// El tamano del archivo en MiB con un decimal y coma (es-VE): cuenta entera de decimas, sin redondeo de coma flotante
// a la vista ni `toFixed` (la interfaz no calcula montos; esto es solo el tamano de un archivo).
export function mibEsVe(bytes: number): string {
  const decimas = Math.round((bytes * 10) / MIB);
  if (decimas === 0 && bytes > 0) return "menos de 0,1 MiB";
  return `${formatoEsVe(`${Math.floor(decimas / 10)}.${decimas % 10}`)} MiB`;
}

// Que se puede hacer con las carpetas de trabajo (BCP-5 §4.3 a §4.7; diseno de modulos §7 y §12.2): ver la lista de la
// instalacion y abrir otra, crear una (con su moneda de trabajo), subir un .db y estrenar la demostracion. La usan el
// dialogo «Carpetas de trabajo» de la barra y Administracion › Carpetas de trabajo.
export function GestionCarpetas({
  alAbrir,
  conDemostracion,
  puedeDeclararMoneda = true,
  alAbierta,
  nivelDeTitulo = 3,
}: Props): JSX.Element {
  const base = useId();
  const aplicacion = useContext(ContextoAplicacion);
  const alExpirar = aplicacion?.alExpirar;
  const [casos, setCasos] = useState<CasosRespuesta | null>(null);
  const [errorLista, setErrorLista] = useState<unknown>(null);
  const [recarga, setRecarga] = useState(0);
  const [abriendo, setAbriendo] = useState<string | null>(null);
  const [errorAbrir, setErrorAbrir] = useState<unknown>(null);
  const Titulo = nivelDeTitulo === 2 ? "h2" : "h3";
  const claseTitulo = nivelDeTitulo === 2 ? "cds--type-heading-compact-02" : "cds--type-heading-compact-01";

  // Un 401 es la sesion vencida: la aplicacion vuelve a «Entrar». Cualquier otro error se muestra donde ocurrio.
  const vencida = useCallback(
    (e: unknown): boolean => {
      if (e instanceof ErrorDeApi && e.estado === 401) {
        alExpirar?.();
        return true;
      }
      return false;
    },
    [alExpirar],
  );

  // F9: la lista se pide al abrir y despues de crear, subir o abrir (la carpeta nueva se ve).
  useEffect(() => {
    let vigente = true;
    pedir<CasosRespuesta>("/v1/casos")
      .then((r) => {
        if (vigente && r?.actual && Array.isArray(r.casos)) {
          setCasos(r);
          setErrorLista(null);
        }
      })
      .catch((e: unknown) => {
        if (vigente && !vencida(e)) setErrorLista(e);
      });
    return () => {
      vigente = false;
    };
  }, [recarga, vencida]);
  const recargar = useCallback(() => setRecarga((n) => n + 1), []);

  // Abre y dice si lo hizo; `null` si la API la rechazo (el error queda en `errorAbrir`).
  const abrir = useCallback(
    async (nombre: string, origen: OrigenDeApertura): Promise<boolean | null> => {
      setAbriendo(nombre);
      setErrorAbrir(null);
      try {
        const abierta = (await alAbrir(nombre)) ?? true;
        if (abierta) {
          recargar();
          alAbierta?.(origen);
        }
        return abierta;
      } catch (e) {
        if (!vencida(e)) setErrorAbrir(e);
        return null;
      } finally {
        setAbriendo(null);
      }
    },
    [alAbrir, alAbierta, recargar, vencida],
  );

  // Crear y abrir, o estrenar la demostracion y abrirla (ronda 2 del arbitro de MOD-3b): la pregunta va ANTES de crear,
  // porque `preparar` (el `POST /v1/casos` o `/v1/casos/demostracion`) corre dentro de la confirmacion del armazon. Los
  // errores siguen hacia quien lo pidio, que sabe si la carpeta llego a crearse.
  const crearYAbrir = useCallback(
    async (nombre: string, preparar: () => Promise<string>, origen: OrigenDeApertura): Promise<boolean> => {
      setErrorAbrir(null);
      const abierta = (await alAbrir(nombre, preparar)) ?? true;
      if (abierta) {
        recargar();
        alAbierta?.(origen);
      }
      return abierta;
    },
    [alAbrir, alAbierta, recargar],
  );

  // La carpeta abierta siempre esta en la lista, aunque la API no la traiga (D1 del recorrido funcional).
  const lista = casos
    ? casos.casos.some((c) => c.nombre === casos.actual.nombre)
      ? casos.casos
      : [casos.actual, ...casos.casos]
    : null;

  return (
    <div className="silice-carpetas">
      <section className="silice-carpetas__parte" aria-labelledby={`${base}-lista`}>
        <Titulo id={`${base}-lista`} className={`silice-carpetas__titulo ${claseTitulo}`}>
          Carpetas de la instalación
        </Titulo>
        <p className="silice-carpetas__ayuda cds--type-helper-text-01">{EXPLICACION}</p>
        {lista === null && errorLista === null && <SkeletonText paragraph lineCount={3} />}
        <AvisoError error={errorLista} titulo="No se pudo leer la lista de carpetas de trabajo" />
        {lista && casos && (
          <ul className="silice-carpetas__lista" aria-label="Carpetas de trabajo de la instalación">
            {lista.map((c) => (
              <FilaDeCarpeta
                key={c.ruta_relativa}
                carpeta={c}
                abierta={c.nombre === casos.actual.nombre}
                deLaEmpresa={casos.empresa?.nombre === c.nombre}
                ocupada={abriendo !== null || aplicacion?.declarandoMoneda === true}
                alAbrir={() => void abrir(c.nombre, "lista")}
              />
            ))}
          </ul>
        )}
        <AvisoError error={errorAbrir} titulo="No se pudo abrir la carpeta de trabajo" />
      </section>

      <section className="silice-carpetas__parte" aria-labelledby={`${base}-agregar`}>
        <Titulo id={`${base}-agregar`} className={`silice-carpetas__titulo ${claseTitulo}`}>
          Agregar una carpeta
        </Titulo>
        <Tabs>
          <TabList aria-label="Formas de agregar una carpeta de trabajo" contained>
            <Tab>Crear</Tab>
            <Tab>Subir un archivo</Tab>
            {conDemostracion ? <Tab>Demostración</Tab> : null}
          </TabList>
          <TabPanels>
            <TabPanel>
              <Crear
                puedeDeclararMoneda={puedeDeclararMoneda}
                crearYAbrir={crearYAbrir}
                recargar={recargar}
                vencida={vencida}
              />
            </TabPanel>
            <TabPanel>
              <Subir abrir={abrir} recargar={recargar} vencida={vencida} />
            </TabPanel>
            {conDemostracion ? (
              <TabPanel>
                <Demostracion crearYAbrir={crearYAbrir} vencida={vencida} />
              </TabPanel>
            ) : null}
          </TabPanels>
        </Tabs>
        {!conDemostracion && (
          <p className="silice-carpetas__ayuda cds--type-helper-text-01">
            La carpeta de demostración la abre una cuenta que arma presupuestos.
          </p>
        )}
      </section>
    </div>
  );
}

function FilaDeCarpeta({
  carpeta,
  abierta,
  deLaEmpresa,
  ocupada,
  alAbrir,
}: {
  carpeta: CasoRespuesta;
  abierta: boolean;
  deLaEmpresa: boolean;
  ocupada: boolean;
  alAbrir: () => void;
}) {
  const nombre = nombreDeCarpeta(carpeta.nombre);
  const marcas = [
    abierta ? "Abierta" : null,
    deLaEmpresa ? "Carpeta de la empresa" : null,
    carpeta.nombre === "demostracion.db" ? "Datos inventados" : null,
  ].filter((m): m is string => m !== null);
  return (
    <li className="silice-carpetas__fila" aria-current={abierta ? "true" : undefined}>
      <span className="silice-carpetas__datos">
        <span className="silice-carpetas__nombre cds--type-body-compact-01">{nombre}</span>
        {marcas.length > 0 && (
          <span className="silice-carpetas__marcas cds--type-helper-text-01">{marcas.join(" · ")}</span>
        )}
      </span>
      {!abierta && (
        <Button kind="ghost" size="sm" disabled={ocupada} aria-label={`Abrir ${nombre}`} onClick={alAbrir}>
          Abrir
        </Button>
      )}
    </li>
  );
}

type Abrir = (nombre: string, origen: OrigenDeApertura) => Promise<boolean | null>;

type CrearYAbrir = (nombre: string, preparar: () => Promise<string>, origen: OrigenDeApertura) => Promise<boolean>;

// La moneda que quedo sin declarar tras crear y abrir la carpeta (el `PUT` fallo): la guarda el armazon, que sobrevive
// al remontaje de la pagina (Administracion); sin armazon (la pieza sola), la guarda el formulario.
function useMonedaPendiente(vencida: (e: unknown) => boolean) {
  const aplicacion = useContext(ContextoAplicacion);
  const [local, setLocal] = useState<MonedaPendiente | null>(null);
  const delArmazon = aplicacion?.declararMoneda;
  const pendiente = delArmazon ? (aplicacion?.monedaPendiente ?? null) : local;
  async function declarar(carpeta: string, moneda: string): Promise<boolean> {
    if (delArmazon) return delArmazon(carpeta, moneda);
    try {
      await pedir("/v1/carpeta/moneda", { metodo: "PUT", cuerpo: { moneda } });
      setLocal(null);
      return true;
    } catch (e) {
      if (!vencida(e)) setLocal({ carpeta, moneda, error: e });
      return false;
    }
  }
  return { pendiente, declarar };
}

function Crear({
  puedeDeclararMoneda,
  crearYAbrir,
  recargar,
  vencida,
}: {
  puedeDeclararMoneda: boolean;
  crearYAbrir: CrearYAbrir;
  recargar: () => void;
  vencida: (e: unknown) => boolean;
}) {
  const base = useId();
  const [nombre, setNombre] = useState("");
  const [moneda, setMoneda] = useState("");
  const [faltaMoneda, setFaltaMoneda] = useState(false);
  const [faltaNombre, setFaltaNombre] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);
  // La carpeta se creo pero no se pudo abrir: se dice con su nombre (no «No se pudo crear»).
  const [sinAbrir, setSinAbrir] = useState<{ carpeta: string; error: unknown } | null>(null);
  const { pendiente, declarar: declararMoneda } = useMonedaPendiente(vencida);
  const [hecho, setHecho] = useState<string | null>(null);

  // Declara la moneda de la carpeta ya abierta; si falla, queda pendiente con su error para reintentar solo esto.
  async function declarar(carpeta: string, elegida: string) {
    if (await declararMoneda(carpeta, elegida)) setHecho(`Se creó la carpeta de trabajo «${carpeta}» y ya trabaja con ella.`);
  }

  async function crear(e: FormEvent) {
    e.preventDefault();
    setHecho(null);
    setError(null);
    setSinAbrir(null);
    // Lo que falta se dice en el campo, sin llamar a la API.
    const sinNombre = nombre.trim() === "";
    const sinMoneda = puedeDeclararMoneda && moneda === "";
    setFaltaNombre(sinNombre);
    setFaltaMoneda(sinMoneda);
    if (sinNombre || sinMoneda) return;
    setOcupado(true);
    // BCP-5 §4.3 con la pregunta delante: confirmar, crear, abrir (si abrir falla, la carpeta existe y no esta abierta)
    // y, ya abierta, declarar su moneda de trabajo (D-MP1, una por carpeta).
    // Lo escribe `preparar` dentro de la confirmacion: si queda en null, nada se creo.
    const creada = { nombre: null as string | null };
    try {
      const abierta = await crearYAbrir(
        nombre,
        async () => {
          const r = await pedir<CasoRespuesta>("/v1/casos", { metodo: "POST", cuerpo: { nombre } });
          creada.nombre = r.nombre;
          recargar();
          return r.nombre;
        },
        "creada",
      );
      // «Quedarme» (nada se creo) o la sesion vencio: no hay nada que contar aqui.
      if (!abierta || creada.nombre === null) return;
      const final = nombreDeCarpeta(creada.nombre);
      setNombre("");
      if (puedeDeclararMoneda) await declarar(final, moneda);
      else setHecho(`Se creó la carpeta de trabajo «${final}» y ya trabaja con ella.`);
      setMoneda("");
    } catch (e) {
      if (vencida(e)) return;
      if (creada.nombre === null) setError(e);
      else setSinAbrir({ carpeta: nombreDeCarpeta(creada.nombre), error: e });
    } finally {
      setOcupado(false);
    }
  }

  async function reintentar() {
    if (!pendiente) return;
    setOcupado(true);
    await declarar(pendiente.carpeta, pendiente.moneda);
    setOcupado(false);
  }

  return (
    <form className="silice-carpetas__formulario" onSubmit={(e) => void crear(e)} noValidate>
      <CampoTexto
        id={`${base}-nombre`}
        labelText="Nombre de la carpeta"
        helperText="Lo que no se puede usar en el nombre de un archivo se cambia por «_»."
        value={nombre}
        maxLength={200}
        invalid={faltaNombre}
        invalidText="Escriba un nombre para la carpeta de trabajo."
        onChange={(e) => {
          setNombre(e.target.value);
          setFaltaNombre(false);
        }}
      />
      {puedeDeclararMoneda ? (
        <Select
          id={`${base}-moneda`}
          labelText="Moneda de trabajo"
          helperText="Todas las obras de la carpeta se valoran en esta moneda; después no se cambia."
          value={moneda}
          invalid={faltaMoneda}
          invalidText="Elija la moneda de trabajo de la carpeta."
          onChange={(e) => {
            setMoneda(e.target.value);
            setFaltaMoneda(false);
          }}
        >
          <SelectItem value="" text="Elija…" />
          <SelectItem value="Bs" text="Bolívares (Bs)" />
          <SelectItem value="USD" text="Dólares estadounidenses (USD)" />
        </Select>
      ) : (
        <p className="silice-carpetas__ayuda cds--type-helper-text-01">
          La moneda de trabajo la declara una cuenta que arma presupuestos.
        </p>
      )}
      <div>
        <Button type="submit" size="sm" disabled={ocupado || pendiente !== null}>
          Crear y abrir
        </Button>
      </div>
      {ocupado && (
        <p className="silice-carpetas__estado cds--type-body-compact-01" role="status">
          {pendiente ? "Declarando la moneda…" : "Creando la carpeta…"}
        </p>
      )}
      <AvisoError error={error} titulo="No se pudo crear la carpeta de trabajo" />
      {sinAbrir && (
        <AvisoError
          error={`La carpeta «${sinAbrir.carpeta}» se creó, pero no se pudo abrir: ${mensajeDeError(sinAbrir.error)} Ábrala de la lista cuando quiera.`}
          titulo="Carpeta creada sin abrir"
        />
      )}
      {pendiente && (
        <div className="silice-carpetas__hecho">
          <AvisoError
            error={`La carpeta «${pendiente.carpeta}» se creó y ya trabaja con ella, pero no se pudo declarar su moneda: ${mensajeDeError(pendiente.error)}`}
            titulo="Falta declarar la moneda"
          />
          <Button kind="tertiary" size="sm" disabled={ocupado} onClick={() => void reintentar()}>
            Declarar la moneda
          </Button>
        </div>
      )}
      {hecho && (
        <p className="silice-carpetas__hecho cds--type-body-compact-01" role="status">
          {hecho}
        </p>
      )}
    </form>
  );
}

function Subir({ abrir, recargar, vencida }: { abrir: Abrir; recargar: () => void; vencida: (e: unknown) => boolean }) {
  const base = useId();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [nombre, setNombre] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [subida, setSubida] = useState<{ nombre: string; aviso: string | null } | null>(null);

  function olvidarElegido() {
    setArchivo(null);
    setError(null);
    setSubida(null);
  }

  async function subir() {
    if (!archivo) return;
    setOcupado(true);
    setError(null);
    setSubida(null);
    try {
      const datos = new FormData();
      datos.append("archivo", archivo);
      if (nombre.trim()) datos.append("nombre", nombre);
      const r = await pedir<CasoRespuesta & { aviso: string | null }>("/v1/casos/subida", { metodo: "POST", cuerpo: datos });
      setSubida({ nombre: r.nombre, aviso: r.aviso ?? null });
      setArchivo(null);
      setNombre("");
      recargar();
    } catch (e) {
      // Un rechazo no deja nada en la carpeta de datos: la lista no cambia y no se vuelve a pedir.
      if (!vencida(e)) setError(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="silice-carpetas__formulario">
      <p className="silice-carpetas__ayuda cds--type-helper-text-01">
        Suba el archivo .db de una carpeta de trabajo, por ejemplo copiado de otro equipo. Nunca reemplaza una carpeta
        que ya exista.
      </p>
      {/* Cada eleccion (clic o soltar) empieza vaciando la anterior, en la fase de captura, antes de que `SubidaArchivo`
          entregue el archivo: uno rechazado (no es .db) no deja elegido el de antes con «Subir» habilitado. */}
      <div onChangeCapture={olvidarElegido} onDropCapture={olvidarElegido}>
        <SubidaArchivo
          id={`${base}-archivo`}
          etiqueta="Suelte aquí el archivo .db, o haga clic para elegirlo"
          extensiones={[".db"]}
          deshabilitada={ocupado}
          alElegir={(a) => {
            // El tope de la API, en el navegador: un archivo mayor no se sube entero para que lo rechace.
            if (a.size > TOPE_SUBIDA) {
              setError(MENSAJE_GRANDE);
              return;
            }
            setArchivo(a);
          }}
        />
      </div>
      {archivo && <p className="cds--type-body-compact-01">{`${archivo.name} · ${mibEsVe(archivo.size)}`}</p>}
      <CampoTexto
        id={`${base}-nombre`}
        labelText="Nombre de la carpeta (opcional)"
        helperText="Si lo deja vacío, se usa el nombre del archivo."
        value={nombre}
        maxLength={200}
        onChange={(e) => setNombre(e.target.value)}
      />
      <div>
        <Button size="sm" disabled={!archivo || ocupado} onClick={() => void subir()}>
          Subir
        </Button>
      </div>
      {ocupado && (
        <p className="silice-carpetas__estado cds--type-body-compact-01" role="status">
          Subiendo el archivo…
        </p>
      )}
      <AvisoError error={error} titulo="No se pudo subir el archivo" />
      {subida && (
        <div className="silice-carpetas__hecho" role="status">
          <p className="cds--type-body-compact-01">{`Se subió la carpeta de trabajo «${nombreDeCarpeta(subida.nombre)}».`}</p>
          {subida.aviso && <p className="cds--type-body-compact-01">{subida.aviso}</p>}
          <Button kind="tertiary" size="sm" onClick={() => void abrir(subida.nombre, "subida")}>
            Abrir ahora
          </Button>
        </div>
      )}
    </div>
  );
}

function Demostracion({ crearYAbrir, vencida }: { crearYAbrir: CrearYAbrir; vencida: (e: unknown) => boolean }) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function estrenar() {
    setOcupado(true);
    setError(null);
    try {
      // Primero se pregunta (si hay trabajo sin guardar) y solo entonces se estrena: 201 si la creo, 200 si ya estaba;
      // las dos la abren (F7).
      await crearYAbrir(
        "demostracion.db",
        async () => (await pedir<CasoRespuesta>("/v1/casos/demostracion", { metodo: "POST" })).nombre,
        "demostracion",
      );
    } catch (e) {
      if (!vencida(e)) setError(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="silice-carpetas__formulario">
      <p className="cds--type-body-compact-01">Datos de ejemplo inventados para aprender; no son una obra real.</p>
      <p className="silice-carpetas__ayuda cds--type-helper-text-01">
        Abre la carpeta «demostracion», con un catálogo y un presupuesto de ejemplo. La primera vez tarda hasta dos
        minutos en prepararse; la carpeta que tiene abierta no se toca.
      </p>
      <div>
        <Button size="sm" disabled={ocupado} onClick={() => void estrenar()}>
          Abrir la demostración
        </Button>
      </div>
      {ocupado && (
        <p className="silice-carpetas__estado cds--type-body-compact-01" role="status">
          Preparando la demostración…
        </p>
      )}
      <AvisoError error={error} titulo="No se pudo abrir la demostración" />
    </div>
  );
}
