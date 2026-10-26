import { Button, Select, SelectItem, SkeletonText, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useCallback, useContext, useEffect, useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CasoRespuesta, CasosRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { ContextoAplicacion } from "../contexto";
import { nombreDeCarpeta } from "../Selectores";
import "./GestionCarpetas.scss";

// De donde se abrio una carpeta: el dialogo se cierra al abrir una de la lista o la demostracion, y se queda abierto
// para contar lo que paso al crear o subir.
export type OrigenDeApertura = "lista" | "creada" | "subida" | "demostracion";

interface Props {
  // Abre la carpeta por su nombre (con .db). La del armazon pregunta antes si hay trabajo sin guardar y resuelve si la
  // abrio (false: la persona se quedo); si la API la rechaza, lanza el error y aqui se muestra en linea.
  alAbrir: (nombre: string) => void | Promise<boolean>;
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
                ocupada={abriendo !== null}
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
              <Crear puedeDeclararMoneda={puedeDeclararMoneda} abrir={abrir} recargar={recargar} vencida={vencida} />
            </TabPanel>
            <TabPanel>
              <Subir abrir={abrir} recargar={recargar} vencida={vencida} />
            </TabPanel>
            {conDemostracion ? (
              <TabPanel>
                <Demostracion abrir={abrir} vencida={vencida} />
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

function Crear({
  puedeDeclararMoneda,
  abrir,
  recargar,
  vencida,
}: {
  puedeDeclararMoneda: boolean;
  abrir: Abrir;
  recargar: () => void;
  vencida: (e: unknown) => boolean;
}) {
  const base = useId();
  const [nombre, setNombre] = useState("");
  const [moneda, setMoneda] = useState("");
  const [faltaMoneda, setFaltaMoneda] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [hecho, setHecho] = useState<string | null>(null);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setHecho(null);
    setError(null);
    if (puedeDeclararMoneda && moneda === "") {
      setFaltaMoneda(true);
      return;
    }
    setOcupado(true);
    try {
      // BCP-5 §4.3: crear, luego abrir (dos llamadas: si la segunda falla, la carpeta existe y no esta abierta) y, ya
      // abierta, declarar su moneda de trabajo (D-MP1, una por carpeta).
      const creada = await pedir<CasoRespuesta>("/v1/casos", { metodo: "POST", cuerpo: { nombre } });
      recargar();
      const final = nombreDeCarpeta(creada.nombre);
      const abierta = await abrir(creada.nombre, "creada");
      if (abierta === null) return;
      if (!abierta) {
        setHecho(`Se creó la carpeta de trabajo «${final}»; ábrala de la lista cuando quiera.`);
        return;
      }
      if (puedeDeclararMoneda) await pedir("/v1/carpeta/moneda", { metodo: "PUT", cuerpo: { moneda } });
      setHecho(`Se creó la carpeta de trabajo «${final}» y ya trabaja con ella.`);
      setNombre("");
      setMoneda("");
    } catch (e) {
      if (!vencida(e)) setError(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <form className="silice-carpetas__formulario" onSubmit={(e) => void crear(e)} noValidate>
      <CampoTexto
        id={`${base}-nombre`}
        labelText="Nombre de la carpeta"
        helperText="Lo que no se puede usar en el nombre de un archivo se cambia por «_»."
        value={nombre}
        maxLength={200}
        onChange={(e) => setNombre(e.target.value)}
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
        <Button type="submit" size="sm" disabled={ocupado}>
          Crear y abrir
        </Button>
      </div>
      {ocupado && (
        <p className="silice-carpetas__estado cds--type-body-compact-01" role="status">
          Creando la carpeta…
        </p>
      )}
      <AvisoError error={error} titulo="No se pudo crear la carpeta de trabajo" />
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
      <SubidaArchivo
        id={`${base}-archivo`}
        etiqueta="Suelte aquí el archivo .db, o haga clic para elegirlo"
        extensiones={[".db"]}
        deshabilitada={ocupado}
        alElegir={(a) => {
          setArchivo(a);
          setError(null);
          setSubida(null);
        }}
      />
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

function Demostracion({ abrir, vencida }: { abrir: Abrir; vencida: (e: unknown) => boolean }) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function estrenar() {
    setOcupado(true);
    setError(null);
    try {
      // 201 si la creo, 200 si ya estaba: las dos la abren (F7).
      const demo = await pedir<CasoRespuesta>("/v1/casos/demostracion", { metodo: "POST" });
      await abrir(demo.nombre, "demostracion");
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
