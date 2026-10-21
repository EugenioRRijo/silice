import { FileUploaderButton, FileUploaderDropContainer, InlineNotification, SkeletonPlaceholder, SkeletonText, Tab, TabList, Tabs } from "@carbon/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ErrorDeApi, pedir } from "../api/cliente";
import { tomarArchivoPendiente } from "../paginas/inicio/archivoPendiente";
import type { LibroAuditadoRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { FranjaIndicadores } from "../indicadores/FranjaIndicadores";
import type { Severidad } from "../indicadores/tipos";
import { IconoDeSeveridad } from "../severidad/IconoDeSeveridad";
import { estiloDeSeveridad } from "../severidad/severidad";
import { crearAlmacen } from "./almacen";
import type { AlmacenDelVisor } from "./almacen";
import { CapaHalos } from "./CapaHalos";
import { contextoDeFila } from "./celdas";
import { construirHalos, resumenPorHoja } from "./halos";
import type { CeldaRef, CrearHojaVisor, HojaVisor } from "./hojaVisor";
import { ListaHallazgos } from "./ListaHallazgos";
import { UniverGrid } from "./UniverGrid";
import { CampoTexto } from "../comun/CampoTexto";

// Univer es pesado: se baja en un archivo aparte y solo cuando hay un libro que dibujar.
const crearHojaUniver: CrearHojaVisor = (contenedor, libro) =>
  import("./adaptadorUniver").then((m) => m.crearHojaUniver(contenedor, libro));

interface Props {
  crearHoja?: CrearHojaVisor;
  // La API contesto 401: la sesion vencio.
  alExpirar?: () => void;
  // Donde se guarda, en memoria, lo que esta abierto: si el Visor se desmonta (sesion vencida) y vuelve a montarse
  // con el mismo almacen, reaparece tal cual.
  almacen?: AlmacenDelVisor;
  // Donde van la fecha de devolucion, el nombre del libro y Cambiar libro: la cabecera de 48 px de la pantalla.
  // undefined: en una barra propia dentro del visor; null: la ranura aun no existe (no se pinta nada); un
  // elemento: se pintan alli (portal), sin tocar la cabecera.
  ranuraCabecera?: HTMLElement | null;
}

type Fase = "vacio" | "cargando" | "listo";

const ISO = /^\d{4}-\d{2}-\d{2}$/;

// Fecha de hoy en la zona del usuario (no en UTC: a las 8 p. m. en Caracas ya seria mañana).
function hoyISO(): string {
  const d = new Date();
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
}

function esXlsx(archivo: File & { invalidFileType?: boolean }): boolean {
  return !archivo.invalidFileType && archivo.name.toLowerCase().endsWith(".xlsx");
}

function cuerpoDeLibro(archivo: File, fecha?: string): FormData {
  const cuerpo = new FormData();
  cuerpo.append("libro", archivo, archivo.name);
  if (fecha) cuerpo.append("fecha_devolucion", fecha);
  return cuerpo;
}

function mensajeDe(razon: unknown): string {
  return razon instanceof ErrorDeApi ? razon.detalle : "Ocurrió un error inesperado. Inténtelo de nuevo.";
}

function Esqueleto() {
  return (
    <div className="visor__esqueleto" role="status" aria-busy="true" aria-label="Cargando el libro">
      <div className="visor__esqueleto-hoja">
        <p className="visor__cargando cds--type-body-compact-01">Leyendo el libro y auditándolo…</p>
        <SkeletonPlaceholder className="visor__esqueleto-lienzo" />
      </div>
      <div className="visor__esqueleto-lista">
        <SkeletonText heading width="40%" />
        <SkeletonText paragraph lineCount={6} />
      </div>
    </div>
  );
}

export function Visor({ crearHoja = crearHojaUniver, alExpirar, almacen, ranuraCabecera }: Props) {
  const [propio] = useState(crearAlmacen);
  const alm = almacen ?? propio;
  const [guardado] = useState(() => alm.leer());
  const [fase, setFase] = useState<Fase>(guardado ? "listo" : "vacio");
  const [archivo, setArchivo] = useState<File | null>(guardado?.archivo ?? null);
  const [fecha, setFecha] = useState(guardado?.fecha ?? hoyISO());
  const [replica, setReplica] = useState<LibroVisualRespuesta | null>(guardado?.replica ?? null);
  const [auditoria, setAuditoria] = useState<LibroAuditadoRespuesta | null>(guardado?.auditoria ?? null);
  const [filtro, setFiltro] = useState<Severidad[]>(guardado?.filtro ?? []);
  const [error, setError] = useState<string | null>(null);
  const [visor, setVisor] = useState<HojaVisor | null>(null);
  const [hojaActiva, setHojaActiva] = useState(guardado?.hojaActiva ?? "");
  const [seleccionado, setSeleccionado] = useState<number | null>(guardado?.seleccionado ?? null);
  // La hoja que se veia antes de que venciera la sesion: se restaura cuando el visor nuevo este listo.
  const hojaPorRestaurar = useRef(guardado?.hojaActiva ?? "");
  // La hoja en que abre el libro: la primera con hallazgos a la vista.
  const hojaInicial = useRef("");
  const [enfocar, setEnfocar] = useState<{ indice: number; n: number } | null>(null);

  // Para ignorar respuestas de una carga o auditoria que ya quedo atras.
  const turno = useRef(0);
  const seleccionRef = useRef<number | null>(null);
  useEffect(() => {
    seleccionRef.current = seleccionado;
  }, [seleccionado]);

  const fallo = useCallback(
    (razon: unknown) => {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar?.();
      setError(mensajeDe(razon));
    },
    [alExpirar],
  );

  const cargar = useCallback(
    async (nuevo: File, fechaDevolucion: string) => {
      if (!esXlsx(nuevo)) {
        setError("Solo se aceptan libros de Excel con extensión .xlsx.");
        return;
      }
      const mio = ++turno.current;
      setError(null);
      setArchivo(nuevo);
      setFase("cargando");
      setSeleccionado(null);
      setEnfocar(null);
      setFiltro([]);
      hojaPorRestaurar.current = "";
      // Las dos llamadas salen a la vez: la hoja y la auditoria no dependen una de la otra.
      const [r, a] = await Promise.allSettled([
        pedir<LibroVisualRespuesta>("/v1/libros/replica", { metodo: "POST", cuerpo: cuerpoDeLibro(nuevo) }),
        pedir<LibroAuditadoRespuesta>("/v1/libros/auditoria", {
          metodo: "POST",
          cuerpo: cuerpoDeLibro(nuevo, fechaDevolucion),
        }),
      ]);
      if (mio !== turno.current) return;
      if (r.status === "rejected" || a.status === "rejected") {
        fallo(r.status === "rejected" ? r.reason : (a as PromiseRejectedResult).reason);
        setArchivo(null);
        setFase("vacio");
        return;
      }
      setReplica(r.value);
      setAuditoria(a.value);
      setFase("listo");
    },
    [fallo],
  );

  // El archivo que se solto en Inicio: al montar, quien lo toma se hace cargo y lo carga con la fecha del visor.
  const pendienteTomado = useRef(false);
  useEffect(() => {
    if (pendienteTomado.current) return;
    pendienteTomado.current = true;
    const pendiente = tomarArchivoPendiente();
    // Fuera del efecto (cargar actualiza el estado de entrada): en el turno siguiente.
    if (pendiente) void Promise.resolve().then(() => cargar(pendiente.archivo, fecha));
  }, [cargar, fecha]);

  const volverAAuditar = useCallback(
    async (actual: File, fechaDevolucion: string) => {
      const mio = ++turno.current;
      try {
        const nueva = await pedir<LibroAuditadoRespuesta>("/v1/libros/auditoria", {
          metodo: "POST",
          cuerpo: cuerpoDeLibro(actual, fechaDevolucion),
        });
        if (mio !== turno.current) return;
        setError(null);
        setAuditoria(nueva);
        setSeleccionado(null);
      } catch (razon) {
        if (mio === turno.current) fallo(razon);
      }
    },
    [fallo],
  );

  const cambiarFecha = (valor: string) => {
    setFecha(valor);
    if (fase === "listo" && archivo && ISO.test(valor)) void volverAAuditar(archivo, valor);
  };

  const alAgregar = (_evento: unknown, { addedFiles }: { addedFiles: File[] }) => {
    const elegido = addedFiles[0];
    if (!elegido) {
      setError("Solo se aceptan libros de Excel con extensión .xlsx.");
      return;
    }
    if (!ISO.test(fecha)) {
      setError("Escriba la fecha de devolución antes de cargar el libro.");
      return;
    }
    void cargar(elegido, fecha);
  };

  const hallazgos = useMemo(() => auditoria?.hallazgos ?? [], [auditoria]);
  const hojasVisibles = useMemo(() => replica?.hojas.filter((h) => h.visible) ?? [], [replica]);
  // Un hallazgo en una hoja, fila o columna oculta no se muestra sobre la hoja: la lista lo agrupa aparte.
  const { halos } = useMemo(() => construirHalos(hallazgos, replica?.hojas), [hallazgos, replica]);

  const resumenHojas = useMemo(() => resumenPorHoja(halos), [halos]);
  useEffect(() => {
    hojaInicial.current = (hojasVisibles.find((h) => resumenHojas.has(h.nombre)) ?? hojasVisibles[0])?.nombre ?? "";
  }, [hojasVisibles, resumenHojas]);

  const alCambiarVisor = useCallback((nuevo: HojaVisor | null) => {
    setVisor(nuevo);
    if (!nuevo) return;
    // Lo que se veia antes de vencer la sesion, o la primera hoja con hallazgos (no la primera del libro).
    const objetivo = hojaPorRestaurar.current || hojaInicial.current;
    hojaPorRestaurar.current = "";
    if (objetivo && objetivo !== nuevo.hojaActiva()) nuevo.irAHoja(objetivo);
    setHojaActiva(nuevo.hojaActiva());
  }, []);

  // Lo abierto se guarda en memoria (no en el navegador) para sobrevivir a una sesion vencida.
  useEffect(() => {
    alm.guardar(
      fase === "listo" && replica && auditoria
        ? { archivo, fecha, replica, auditoria, hojaActiva, filtro, seleccionado }
        : null,
    );
  }, [alm, fase, archivo, fecha, replica, auditoria, hojaActiva, filtro, seleccionado]);

  const alFallarVisor = useCallback((mensaje: string) => setError(mensaje), []);

  // La hoja a la vista cambia (desde las pestanas o desde un hallazgo): las pestanas la siguen.
  useEffect(() => {
    if (!visor) return;
    return visor.alCambiar(() => setHojaActiva(visor.hojaActiva()));
  }, [visor]);

  // Clic en una celda marcada: se elige su hallazgo y la fila recibe el foco.
  useEffect(() => {
    if (!visor) return;
    return visor.alSeleccionar((celda: CeldaRef) => {
      const halo = halos.find(
        (h) => h.hoja === celda.hoja && h.fila0 === celda.fila0 && h.columna0 === celda.columna0,
      );
      if (!halo) return;
      const actual = seleccionRef.current;
      // Si la fila elegida ya es de esta celda (vino de la lista), se respeta.
      const indice = actual !== null && halo.indices.includes(actual) ? actual : halo.indices[0];
      setSeleccionado(indice);
      setEnfocar((previo) => ({ indice, n: (previo?.n ?? 0) + 1 }));
    });
  }, [visor, halos]);

  const irACelda = (celda: CeldaRef) => visor?.irA(celda);
  const contextoDeCelda = useCallback(
    (celda: CeldaRef) => {
      const hojaDelLibro = replica?.hojas.find((h) => h.nombre === celda.hoja);
      return hojaDelLibro ? contextoDeFila(hojaDelLibro, celda.fila0, celda.columna0) : null;
    },
    [replica],
  );
  const indiceDePestana = Math.max(
    0,
    hojasVisibles.findIndex((h) => h.nombre === hojaActiva),
  );

  const cargando = fase === "cargando";

  const controles = (
    <>
      <div className="visor__fecha">
        <CampoTexto
          id="visor-fecha"
          type="date"
          size="sm"
          inline
          labelText="Fecha de devolución"
          value={fecha}
          onChange={(e) => cambiarFecha(e.target.value)}
        />
      </div>
      {archivo && (
        <>
          <span className="visor__archivo cds--type-body-compact-01">{archivo.name}</span>
          <FileUploaderButton
            labelText="Cambiar libro"
            buttonKind="ghost"
            size="sm"
            accept={[".xlsx"]}
            disableLabelChanges
            onChange={(e: { target: HTMLInputElement }) => {
              const elegido = e.target.files?.[0];
              if (elegido) alAgregar(e, { addedFiles: [elegido] });
            }}
          />
        </>
      )}
    </>
  );

  return (
    <div className="visor">
      {cargando && <div className="visor__franja-esqueleto" aria-hidden="true"><SkeletonText width="60%" /></div>}
      {fase === "listo" && auditoria && (
        <FranjaIndicadores
          indicadores={auditoria.indicadores ?? []}
          totalesLibro={auditoria.totales_libro}
          totalesSilice={auditoria.totales_silice}
          rotuloMeta="Según Sílice"
        />
      )}

      {ranuraCabecera === undefined && <div className="visor__barra">{controles}</div>}
      {ranuraCabecera && createPortal(controles, ranuraCabecera)}

      {error && (
        <InlineNotification
          kind="error"
          role="alert"
          title="No se pudo mostrar el libro"
          subtitle={error}
          lowContrast
          hideCloseButton
          className="visor__error"
        />
      )}

      {fase === "vacio" && (
        <div className="visor__soltar">
          <h2 className="cds--type-heading-04">Abra un libro para auditarlo</h2>
          <p className="visor__ayuda-fecha cds--type-body-compact-01">
            La fecha de devolución (en la barra de arriba) es la fecha con la que se audita el libro: con la misma
            fecha, el mismo libro da siempre el mismo resultado.
          </p>
          <FileUploaderDropContainer
            accept={[".xlsx"]}
            labelText="Suelte aquí el libro .xlsx de la empresa, o haga clic para elegirlo"
            name="libro"
            multiple={false}
            onAddFiles={alAgregar}
          />
          <p className="visor__ayuda cds--type-body-compact-01">
            El libro no se modifica ni se guarda: Sílice lo muestra tal como está y marca cada hallazgo sobre su celda.
          </p>
        </div>
      )}

      {cargando && <Esqueleto />}

      {fase === "listo" && replica && (
        <div className="visor__cuerpo">
          <section className="visor__hoja" aria-label="Hoja del libro">
            <Tabs
              selectedIndex={indiceDePestana}
              onChange={({ selectedIndex }: { selectedIndex: number }) => {
                const hoja = hojasVisibles[selectedIndex];
                if (hoja) visor?.irAHoja(hoja.nombre);
              }}
            >
              <TabList aria-label="Hojas del libro" contained>
                {hojasVisibles.map((h) => {
                  const resumen = resumenHojas.get(h.nombre);
                  return (
                    <Tab key={h.nombre}>
                      {h.nombre}
                      {resumen && (
                        <>
                          <span
                            className={`pestana__conteo silice-sev--${resumen.severidad.toLowerCase()}`}
                            aria-hidden="true"
                          >
                            <IconoDeSeveridad
                              nombre={estiloDeSeveridad(resumen.severidad).icono}
                              size={16}
                              className="silice-sev__icono"
                            />
                            {resumen.total}
                          </span>
                          <span className="silice-oculto">
                            {` ${resumen.total} ${resumen.total === 1 ? "hallazgo" : "hallazgos"}, el más grave: ${estiloDeSeveridad(resumen.severidad).texto}`}
                          </span>
                        </>
                      )}
                    </Tab>
                  );
                })}
              </TabList>
            </Tabs>
            <div className="visor__lienzo" role="group" aria-label="Hoja del libro, solo lectura" onContextMenuCapture={(e) => e.preventDefault()}>
              <UniverGrid libro={replica} crearHoja={crearHoja} alCambiarVisor={alCambiarVisor} alFallar={alFallarVisor} />
              {!visor && <SkeletonPlaceholder className="visor__esqueleto-lienzo visor__esqueleto-sobre" />}
              <CapaHalos
                halos={halos}
                hallazgos={hallazgos}
                visor={visor}
                seleccionado={seleccionado}
                onElegir={(indice) => {
                  setSeleccionado(indice);
                  setEnfocar((previo) => ({ indice, n: (previo?.n ?? 0) + 1 }));
                }}
              />
            </div>
          </section>
          <aside className="visor__lista">
            <ListaHallazgos
              hallazgos={hallazgos}
              hojas={replica.hojas}
              filtroInicial={filtro}
              alFiltrar={setFiltro}
              seleccionado={seleccionado}
              enfocar={enfocar}
              irACelda={irACelda}
              contextoDeCelda={contextoDeCelda}
              onElegir={setSeleccionado}
            />
          </aside>
        </div>
      )}
    </div>
  );
}
