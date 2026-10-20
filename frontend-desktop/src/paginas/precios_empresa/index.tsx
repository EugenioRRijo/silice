import { Button, InlineLoading, InlineNotification, Select, SelectItem, TextInput } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AYUDA,
  COLUMNAS_DESCONOCIDOS,
  ETIQUETA_ATIPICOS,
  EXTENSIONES,
  MENSAJE_FALTA,
  MONEDAS,
  NOTA_ATIPICOS,
  ROTULO_ATIPICOS,
  ROTULO_REFERENCIA,
  SIN_BASES,
  SIN_LISTAS,
  TITULO,
  TITULO_HALLAZGOS,
  TITULO_LISTA,
  TITULO_REFERENCIA,
  columnasAtipicos,
  columnasHallazgos,
  etiquetaBase,
  faltaAlgo,
  filasAtipicos,
  filasDesconocidos,
  filasHallazgos,
  formularioLista,
  hoyIso,
  rutaAtipicos,
  rutaHallazgos,
} from "./logica";
import type { Atipicos, Base, Estado, Hallazgos, ListaCreada, ListaEmpresa } from "./logica";
import "./precios_empresa.scss";

type Lectura =
  | { tipo: "cargando" }
  | { tipo: "listo"; estado: Estado }
  | { tipo: "error"; error: unknown };

type Referencia =
  | { tipo: "ninguna" }
  | { tipo: "cargando" }
  | { tipo: "listo"; mensaje: string }
  | { tipo: "error"; error: unknown };

type Creacion =
  | { tipo: "ninguna" }
  | { tipo: "enviando" }
  | { tipo: "falta" }
  | { tipo: "listo"; creada: ListaCreada }
  | { tipo: "error"; error: unknown };

// DESIGN.md: el atipico (RF-100) va en morado. La severidad sigue diciendo «Advertencia» con su icono; solo su color
// toma el token de los atipicos (como los halos del visor), nunca el color solo.
const MORADO_ATIPICO = { "--silice-sev-advertencia": "var(--silice-atipico)" } as CSSProperties;

type Busqueda =
  | { tipo: "ninguna" }
  | { tipo: "buscando" }
  | { tipo: "listo"; atipicos: Atipicos }
  | { tipo: "error"; error: unknown };

// La respuesta lleva la clave (lista y fecha) que la pidio: si ya no es la vigente, se esta cargando otra.
type Lectura3 =
  | { tipo: "listo"; clave: string; hallazgos: Hallazgos }
  | { tipo: "error"; clave: string; error: unknown };

// «Precios de la empresa» (UC-17 4-5): la referencia MaPreX en Bs, la lista de una empresa y sus hallazgos de R11 y
// R12. La interfaz no calcula nada: el impacto llega como texto y se muestra tal cual. El archivo lo valida la API.
export default function PaginaPreciosEmpresa() {
  const { alExpirar } = useAplicacion();
  const [lectura, setLectura] = useState<Lectura>({ tipo: "cargando" });
  const consulta = useRef(0);

  const expirada = useCallback(
    (error: unknown) => {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
    },
    [alExpirar],
  );

  const leer = useCallback(() => {
    const numero = ++consulta.current;
    pedir<Estado>("/v1/precios-empresa").then(
      (estado) => {
        if (numero === consulta.current) setLectura({ tipo: "listo", estado });
      },
      (error: unknown) => {
        if (numero !== consulta.current) return;
        expirada(error);
        setLectura({ tipo: "error", error });
      },
    );
  }, [expirada]);

  useEffect(() => {
    leer();
    return () => {
      consulta.current += 1;
    };
  }, [leer]);

  return (
    <div className="silice-precios-empresa silice-pagina">
      <h1 className="cds--type-heading-04">{TITULO}</h1>
      <p className="cds--type-body-compact-01">{AYUDA}</p>

      {lectura.tipo === "cargando" && <EsqueletoPagina etiqueta="Cargando las listas de precios" />}
      {lectura.tipo === "error" && <AvisoError error={lectura.error} titulo="No se pudo leer el caso" />}
      {lectura.tipo === "listo" && (
        <>
          <SeccionReferencia alCargada={leer} alExpirar={expirada} />
          <SeccionLista bases={lectura.estado.bases} alCreada={leer} alExpirar={expirada} />
          <SeccionHallazgos listas={lectura.estado.listas} alExpirar={expirada} />
        </>
      )}
    </div>
  );
}

interface PropsSeccion {
  alExpirar: (error: unknown) => void;
}

function SeccionReferencia({ alCargada, alExpirar }: PropsSeccion & { alCargada: () => void }) {
  const [referencia, setReferencia] = useState<Referencia>({ tipo: "ninguna" });

  const cargar = () => {
    setReferencia({ tipo: "cargando" });
    pedir<{ mensaje: string }>("/v1/precios-empresa/referencia", { metodo: "POST" }).then(
      (respuesta) => {
        setReferencia({ tipo: "listo", mensaje: respuesta.mensaje });
        alCargada();
      },
      (error: unknown) => {
        alExpirar(error);
        setReferencia({ tipo: "error", error });
      },
    );
  };

  return (
    <section className="silice-precios-empresa__seccion" aria-labelledby="precios-empresa-referencia">
      <h2 id="precios-empresa-referencia" className="cds--type-heading-compact-02">
        {TITULO_REFERENCIA}
      </h2>
      <div className="silice-precios-empresa__acciones">
        <Button kind="tertiary" size="md" onClick={cargar} disabled={referencia.tipo === "cargando"}>
          {ROTULO_REFERENCIA}
        </Button>
        {referencia.tipo === "cargando" && <InlineLoading description="Cargando la referencia..." status="active" />}
      </div>
      <div aria-live="polite" aria-atomic="true">
        {referencia.tipo === "listo" && (
          <InlineNotification kind="success" role="status" title="Referencia" subtitle={referencia.mensaje} lowContrast hideCloseButton />
        )}
        {referencia.tipo === "error" && <AvisoError error={referencia.error} titulo="No se cargó la referencia" />}
      </div>
    </section>
  );
}

function SeccionLista({ bases, alCreada, alExpirar }: PropsSeccion & { bases: Base[]; alCreada: () => void }) {
  const [empresa, setEmpresa] = useState("");
  const [rif, setRif] = useState("");
  const [baseElegida, setBaseElegida] = useState("");
  const [moneda, setMoneda] = useState("");
  const [fecha, setFecha] = useState(hoyIso());
  const [fuente, setFuente] = useState("");
  const [nombre, setNombre] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [creacion, setCreacion] = useState<Creacion>({ tipo: "ninguna" });

  const baseId = bases.some((b) => String(b.id) === baseElegida) ? baseElegida : String(bases[0]?.id ?? "");

  const crear = (evento: FormEvent) => {
    evento.preventDefault();
    const datos = { empresa, rif, baseId, moneda, fecha, fuente, nombre, archivo };
    if (faltaAlgo(datos)) {
      setCreacion({ tipo: "falta" });
      return;
    }
    setCreacion({ tipo: "enviando" });
    pedir<ListaCreada>("/v1/precios-empresa/listas", { metodo: "POST", cuerpo: formularioLista(datos) }).then(
      (creada) => {
        setCreacion({ tipo: "listo", creada });
        alCreada();
      },
      (error: unknown) => {
        alExpirar(error);
        setCreacion({ tipo: "error", error });
      },
    );
  };

  return (
    <section className="silice-precios-empresa__seccion" aria-labelledby="precios-empresa-lista">
      <h2 id="precios-empresa-lista" className="cds--type-heading-compact-02">
        {TITULO_LISTA}
      </h2>
      {bases.length === 0 ? (
        <EstadoVacio titulo={SIN_BASES} />
      ) : (
        <form className="silice-precios-empresa__formulario" onSubmit={crear}>
          <div className="silice-precios-empresa__campos">
            <TextInput id="precios-empresa-empresa" labelText="Empresa (nombre)" size="sm" value={empresa} onChange={(e) => setEmpresa(e.target.value)} />
            <TextInput id="precios-empresa-rif" labelText="RIF" size="sm" value={rif} onChange={(e) => setRif(e.target.value)} />
            <Select id="precios-empresa-base" labelText="Lista base" size="sm" value={baseId} onChange={(e) => setBaseElegida(e.target.value)}>
              {bases.map((b) => (
                <SelectItem key={b.id} value={String(b.id)} text={etiquetaBase(b)} />
              ))}
            </Select>
            <Select id="precios-empresa-moneda" labelText="Moneda de la lista" size="sm" value={moneda} onChange={(e) => setMoneda(e.target.value)}>
              <SelectItem value="" text="Elija Bs o USD" />
              {MONEDAS.map((m) => (
                <SelectItem key={m} value={m} text={m} />
              ))}
            </Select>
            <TextInput id="precios-empresa-fecha" type="date" labelText="Fecha de la lista" size="sm" value={fecha} onChange={(e) => setFecha(e.target.value)} />
            <TextInput
              id="precios-empresa-fuente"
              labelText="Fuente de la lista (de donde salen estos precios)"
              size="sm"
              value={fuente}
              onChange={(e) => setFuente(e.target.value)}
            />
            <TextInput id="precios-empresa-nombre" labelText="Nombre de la lista (opcional)" size="sm" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </div>

          <SubidaArchivo
            id="precios-empresa-archivo"
            etiqueta="Archivo de precios (CSV o XLSX): suéltelo aquí, o haga clic para elegirlo"
            extensiones={EXTENSIONES}
            alElegir={setArchivo}
          />
          {archivo && <p className="silice-precios-empresa__nota cds--type-label-01">Archivo elegido: {archivo.name}</p>}

          <div className="silice-precios-empresa__acciones">
            <Button type="submit" kind="primary" size="md" disabled={creacion.tipo === "enviando"}>
              Crear la lista de la empresa
            </Button>
            {creacion.tipo === "enviando" && <InlineLoading description="Creando la lista..." status="active" />}
          </div>
        </form>
      )}

      <div aria-live="polite" aria-atomic="true">
        {creacion.tipo === "falta" && (
          <InlineNotification kind="error" role="alert" title="Faltan datos" subtitle={MENSAJE_FALTA} lowContrast hideCloseButton />
        )}
        {creacion.tipo === "error" && <AvisoError error={creacion.error} titulo="No se creó la lista" />}
        {creacion.tipo === "listo" && (
          <>
            <InlineNotification kind="success" role="status" title="Lista creada" subtitle={creacion.creada.mensaje} lowContrast hideCloseButton />
            {creacion.creada.desconocidos.length > 0 && (
              <>
                {creacion.creada.aviso && (
                  <InlineNotification kind="warning" role="status" title="Insumos desconocidos" subtitle={creacion.creada.aviso} lowContrast hideCloseButton />
                )}
                <TablaDensa
                  etiqueta="Insumos que no entraron a la lista"
                  columnas={COLUMNAS_DESCONOCIDOS}
                  filas={filasDesconocidos(creacion.creada.desconocidos)}
                />
              </>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function SeccionHallazgos({ listas, alExpirar }: PropsSeccion & { listas: ListaEmpresa[] }) {
  const [elegida, setElegida] = useState("");
  const [evaluacion, setEvaluacion] = useState(hoyIso());
  const [respuesta, setRespuesta] = useState<Lectura3 | null>(null);

  const listaId = listas.some((l) => String(l.id) === elegida) ? elegida : String(listas[0]?.id ?? "");
  const clave = `${listaId}|${evaluacion}`;
  const lectura = respuesta !== null && respuesta.clave === clave ? respuesta : null;

  useEffect(() => {
    if (listaId === "" || evaluacion === "") return;
    let vigente = true;
    pedir<Hallazgos>(rutaHallazgos(Number(listaId), evaluacion)).then(
      (hallazgos) => {
        if (vigente) setRespuesta({ tipo: "listo", clave: `${listaId}|${evaluacion}`, hallazgos });
      },
      (error: unknown) => {
        if (!vigente) return;
        alExpirar(error);
        setRespuesta({ tipo: "error", clave: `${listaId}|${evaluacion}`, error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [listaId, evaluacion, alExpirar]);

  return (
    <section className="silice-precios-empresa__seccion" aria-labelledby="precios-empresa-hallazgos">
      <h2 id="precios-empresa-hallazgos" className="cds--type-heading-compact-02">
        {TITULO_HALLAZGOS}
      </h2>
      {listas.length === 0 ? (
        <EstadoVacio titulo={SIN_LISTAS} />
      ) : (
        <>
          <div className="silice-precios-empresa__campos">
            <Select id="precios-empresa-lista-elegida" labelText="Lista" size="sm" value={listaId} onChange={(e) => setElegida(e.target.value)}>
              {listas.map((l) => (
                <SelectItem key={l.id} value={String(l.id)} text={l.nombre} />
              ))}
            </Select>
            <TextInput id="precios-empresa-evaluacion" type="date" labelText="Fecha de evaluación" size="sm" value={evaluacion} onChange={(e) => setEvaluacion(e.target.value)} />
          </div>
          {lectura?.tipo === "error" && <AvisoError error={lectura.error} titulo="No se pudieron leer los hallazgos" />}
          {lectura === null && evaluacion !== "" && <TablaDensa etiqueta="Hallazgos de la lista" columnas={columnasHallazgos(["Regla", "Severidad", "Descripción", "Impacto"])} filas={[]} cargando />}
          {lectura?.tipo === "listo" && (
            <>
              <p className="silice-precios-empresa__nota cds--type-label-01">{lectura.hallazgos.nota}</p>
              <TablaDensa
                etiqueta="Hallazgos de la lista"
                columnas={columnasHallazgos(lectura.hallazgos.columnas)}
                filas={filasHallazgos(lectura.hallazgos)}
                vacio={{ titulo: "La lista no tiene hallazgos a esa fecha" }}
              />
            </>
          )}
          {listaId !== "" && <BuscarAtipicos key={listaId} listaId={Number(listaId)} alExpirar={alExpirar} />}
        </>
      )}
    </section>
  );
}

// RF-100: el boton «Buscar variaciones atipicas de precio» de la pagina clasica, sobre los insumos de la lista
// elegida. Solo lee y solo cuando se pulsa; cada variacion es una advertencia que no impide nada. Al cambiar de lista
// el resultado se retira (el componente se monta de nuevo con su `key`).
function BuscarAtipicos({ listaId, alExpirar }: PropsSeccion & { listaId: number }) {
  const [busqueda, setBusqueda] = useState<Busqueda>({ tipo: "ninguna" });
  const vigente = useRef(true);

  useEffect(() => {
    vigente.current = true;
    return () => {
      vigente.current = false;
    };
  }, []);

  const buscar = () => {
    setBusqueda({ tipo: "buscando" });
    pedir<Atipicos>(rutaAtipicos(listaId)).then(
      (atipicos) => {
        if (vigente.current) setBusqueda({ tipo: "listo", atipicos });
      },
      (error: unknown) => {
        if (!vigente.current) return;
        alExpirar(error);
        setBusqueda({ tipo: "error", error });
      },
    );
  };

  return (
    <div className="silice-precios-empresa__atipicos">
      <div className="silice-precios-empresa__acciones">
        <Button kind="tertiary" size="md" onClick={buscar} disabled={busqueda.tipo === "buscando"}>
          {ROTULO_ATIPICOS}
        </Button>
        {busqueda.tipo === "buscando" && <InlineLoading description="Buscando variaciones atípicas..." status="active" />}
      </div>
      <div aria-live="polite" aria-atomic="true">
        {busqueda.tipo === "error" && <AvisoError error={busqueda.error} titulo="No se buscaron las variaciones atípicas" />}
        {busqueda.tipo === "listo" && (
          <>
            {busqueda.atipicos.avisos.map((aviso, i) => (
              <InlineNotification
                key={i}
                kind={aviso.nivel}
                role="status"
                title={aviso.nivel === "success" ? "Sin variaciones atípicas" : "Aviso"}
                subtitle={aviso.texto}
                lowContrast
                hideCloseButton
              />
            ))}
            {busqueda.atipicos.variaciones.length > 0 && (
              <>
                <p className="silice-precios-empresa__nota cds--type-label-01">{NOTA_ATIPICOS}</p>
                <div className="silice-precios-empresa__tabla-atipicos" style={MORADO_ATIPICO}>
                  <TablaDensa
                    etiqueta={ETIQUETA_ATIPICOS}
                    columnas={columnasAtipicos(busqueda.atipicos)}
                    filas={filasAtipicos(busqueda.atipicos)}
                  />
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
