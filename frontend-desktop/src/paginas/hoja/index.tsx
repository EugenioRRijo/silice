import { Button, InlineNotification, Select, SelectItem, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import { DialogoDeGuardar } from "./DialogoDeGuardar";
import { DialogoDeVersion } from "./DialogoDeVersion";
import { OfertaDeRetomar as OfertaDeRetomarVista } from "./OfertaDeRetomar";
import {
  PESTANAS,
  SIN_VERSIONES,
  TITULO,
  esBorradorAusente,
  rotuloDeVersion,
  rutaDeVersiones,
  textoDeCambios,
  versionesOfrecidas,
} from "./logica";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "./logica";
import { RUTA_DE_BORRADORES, borradorExistente, ofertasDeRetomar } from "./logicaRetomar";
import type { OfertaDeRetomar } from "./logicaRetomar";
import { conVersionGuardada, textoDeExito, usuarioDeSesion } from "./logicaGuardar";
import type { GuardadoRespuesta } from "./logicaGuardar";
import { useGuardado } from "./useGuardado";
import { ContextoAuditoria } from "./ContextoAuditoria";
import type { FiltroDeAuditoria } from "./ContextoAuditoria";
import { PestanaApu } from "./PestanaApu";
import { PestanaAuditoria } from "./PestanaAuditoria";
import { PestanaEquilibrio } from "./PestanaEquilibrio";
import { PestanaEspacio } from "./PestanaEspacio";
import { PestanaPrecios } from "./PestanaPrecios";
import { PestanaTrazabilidad } from "./PestanaTrazabilidad";
import { PestanaParametros } from "./PestanaParametros";
import { PestanaPlan } from "./PestanaPlan";
import { PestanaPresupuesto } from "./PestanaPresupuesto";
import { useBorrador } from "./useBorrador";
import "./hoja.scss";

function EstadoDelBorrador({
  borrador,
  alDescartar,
  alGuardar,
}: {
  borrador: BorradorAbierto;
  alDescartar: () => void;
  alGuardar: () => void;
}) {
  const { base, resumen } = borrador;
  const [confirmando, setConfirmando] = useState(false);
  return (
    <section className="silice-hoja__estado" role="region" aria-label="Estado del borrador">
      <h2 className="cds--type-heading-compact-02">Estado del borrador</h2>
      <p className="cds--type-body-compact-01">
        {base.version === null ? "Borrador en blanco" : `Versión ${base.version}`} · {textoDeCambios(resumen.cambios)}
      </p>
      <p className="silice-hoja__total cds--type-heading-03" aria-live="polite" title={resumen.total.exacto}>
        Total {formatoEsVe(resumen.total.texto)} {resumen.moneda}
        <span className="cds--visually-hidden"> Valor exacto {resumen.total.exacto}</span>
      </p>
      {resumen.version_mas_nueva !== null && (
        <p className="cds--type-helper-text-01">La versión vigente ahora es la {resumen.version_mas_nueva}.</p>
      )}
      {(resumen.cambios > 0 || base.version === null) && !confirmando && (
        <div className="silice-hoja__acciones">
          <Button id="hoja-guardar-version" kind="primary" size="sm" onClick={alGuardar}>
            {base.version === null ? "Guardar primera versión…" : "Guardar versión…"}
          </Button>
          {resumen.cambios > 0 && (
            <Button kind="ghost" size="sm" onClick={() => setConfirmando(true)}>
              Descartar cambios
            </Button>
          )}
        </div>
      )}
      {resumen.cambios > 0 && confirmando && (
        <div className="silice-hoja__confirmar" role="group" aria-label="Descartar cambios">
          <p className="cds--type-body-compact-01">
            {resumen.cambios === 1
              ? "¿Descartar el cambio sin guardar? No se puede recuperar."
              : `¿Descartar los ${resumen.cambios} cambios sin guardar? No se pueden recuperar.`}
          </p>
          <Button kind="danger--tertiary" size="sm" onClick={alDescartar}>
            Descartar y abrir de nuevo
          </Button>
          <Button kind="secondary" size="sm" onClick={() => setConfirmando(false)}>
            Seguir editando
          </Button>
        </div>
      )}
    </section>
  );
}

// Solo se monta la pestaña activa y solo cuando el borrador está abierto: así solo se pide su vista.
function ContenidoDePestana({
  indice,
  borrador,
  alAusente,
  alAceptar,
  alRecargarBorrador,
  alReabrir,
  filtro,
  alQuitarFiltro,
}: {
  indice: number;
  borrador: BorradorAbierto | null;
  alAusente: () => void;
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  alReabrir: () => void;
  filtro: FiltroDeAuditoria | null;
  alQuitarFiltro: () => void;
}) {
  if (borrador === null) return null;
  const llave = `${borrador.id}-${borrador.resumen.rev}`;
  const moneda = borrador.resumen.moneda;
  if (indice === 0) {
    return (
      <PestanaEspacio
        key={borrador.id}
        id={borrador.id}
        rev={borrador.resumen.rev}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargarBorrador={alRecargarBorrador}
        alReabrir={alReabrir}
      />
    );
  }
  if (indice === 1) {
    return (
      <PestanaApu
        key={borrador.id}
        id={borrador.id}
        rev={borrador.resumen.rev}
        moneda={moneda}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargarBorrador={alRecargarBorrador}
        alReabrir={alReabrir}
      />
    );
  }
  if (indice === 2) {
    return (
      <PestanaPresupuesto
        key={borrador.id}
        id={borrador.id}
        rev={borrador.resumen.rev}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargarBorrador={alRecargarBorrador}
        alReabrir={alReabrir}
      />
    );
  }
  if (indice === 3) {
    return (
      <PestanaPlan
        key={borrador.id}
        id={borrador.id}
        rev={borrador.resumen.rev}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargarBorrador={alRecargarBorrador}
        alReabrir={alReabrir}
      />
    );
  }
  if (indice === 4) return <PestanaEquilibrio key={llave} id={borrador.id} alAusente={alAusente} />;
  if (indice === 5) {
    return <PestanaPrecios key={llave} proyecto={borrador.base.proyecto} version={borrador.base.version} alAusente={alAusente} />;
  }
  // Las que se editan no se vuelven a montar con cada `rev` (perdería lo escrito); cada una vuelve a leer su vista.
  if (indice === 6) {
    return (
      <PestanaParametros
        key={borrador.id}
        id={borrador.id}
        rev={borrador.resumen.rev}
        moneda={moneda}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargarBorrador={alRecargarBorrador}
        alReabrir={alReabrir}
      />
    );
  }
  if (indice === 7) {
    return <PestanaAuditoria key={llave} id={borrador.id} alAusente={alAusente} filtro={filtro} alQuitarFiltro={alQuitarFiltro} />;
  }
  return <PestanaTrazabilidad key={llave} proyecto={borrador.base.proyecto} version={borrador.base.version} alAusente={alAusente} />;
}

type Ofertas = { estado: "buscando" } | { estado: "listo"; lista: OfertaDeRetomar[] };

// Los borradores con cambios que el servidor conserva de este proyecto (E10): se piden al abrir la hoja, antes de abrir uno
// nuevo. Si la lectura falla no se ofrece nada: abrir la hoja no depende de ella.
function useOfertas(proyecto: string, alExpirar: () => void) {
  const [intento, setIntento] = useState(0);
  const [res, setRes] = useState<{ clave: string; lista: OfertaDeRetomar[] } | null>(null);
  const clave = JSON.stringify([proyecto, intento]);
  useEffect(() => {
    let vigente = true;
    pedir<unknown>(RUTA_DE_BORRADORES).then(
      (r) => {
        if (vigente) setRes({ clave, lista: ofertasDeRetomar(r, proyecto) });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setRes({ clave, lista: [] });
      },
    );
    return () => {
      vigente = false;
    };
  }, [clave, proyecto, alExpirar]);
  const recargar = useCallback(() => setIntento((n) => n + 1), []);
  const ofertas: Ofertas = res?.clave === clave ? { estado: "listo", lista: res.lista } : { estado: "buscando" };
  return { ofertas, recargar };
}

function textoDeCambiarVersion(cambios: number): string {
  return `Tiene ${textoDeCambios(cambios)}. Si abre otra versión se pierden: guarde primero o descarte.`;
}

function HojaDeProyecto({ proyecto }: { proyecto: string }) {
  const { alExpirar, sesion } = useAplicacion();
  const versiones = useCarga<VersionesRespuesta>(rutaDeVersiones(proyecto), alExpirar);
  const { ofertas, recargar: recargarOfertas } = useOfertas(proyecto, alExpirar);
  const [elegida, setElegida] = useState<{ proyecto: string; codigo: string } | null>(null);
  // El borrador que la persona decidió retomar (en vez de abrir uno nuevo) y el proyecto cuyas ofertas ya no valen.
  const [retomando, setRetomando] = useState<{ proyecto: string; id: string; version: string | null } | null>(null);
  const [sinOfertas, setSinOfertas] = useState<string | null>(null);
  const [descartando, setDescartando] = useState(false);
  const [falloAlDescartar, setFalloAlDescartar] = useState<unknown>(null);
  // La versión que la persona pidió con cambios sin guardar: espera su confirmación.
  const [versionPendiente, setVersionPendiente] = useState<string | null>(null);

  const retomado = retomando?.proyecto === proyecto ? retomando : null;
  const ofrecidos = ofertas.estado === "listo" && retomado === null && sinOfertas !== proyecto ? ofertas.lista : [];

  // Tras guardar se vuelve a leer la lista de versiones sin desmontar la página (valen mientras la carga inicial sea la misma).
  const [frescas, setFrescas] = useState<{ proyecto: string; sobre: VersionesRespuesta; datos: VersionesRespuesta } | null>(null);
  const cargadas = versiones.estado === "listo" ? versiones.datos : null;
  const datos = frescas !== null && frescas.proyecto === proyecto && frescas.sobre === cargadas ? frescas.datos : cargadas;
  const datosActuales = useRef(datos);
  useEffect(() => {
    datosActuales.current = datos;
  });
  const [exito, setExito] = useState<{ proyecto: string; texto: string } | null>(null);
  const ofrecidas = datos ? versionesOfrecidas(datos.versiones) : [];
  const delProyecto = elegida?.proyecto === proyecto ? elegida.codigo : null;
  const codigo =
    datos === null || ofertas.estado !== "listo" || ofrecidos.length > 0
      ? undefined
      : retomado !== null
        ? retomado.version
        : ofrecidas.some((v) => v.codigo === delProyecto)
          ? delProyecto
          : (datos.por_omision ?? null);

  const { estado, refrescar, reabrir, aplicar, descartarCambios, descartarActual, cerrarGuardado } = useBorrador(
    proyecto,
    codigo,
    alExpirar,
    retomado?.id ?? null,
  );
  const hayCambios = estado.estado === "listo" && estado.borrador.resumen.cambios > 0;

  // E11: si al abrir el servidor dice que ya hay un borrador con cambios de esa versión, se ofrece retomarlo.
  const existente = estado.estado === "error" ? borradorExistente(estado.error) : null;
  const [existenteVisto, setExistenteVisto] = useState<string | null>(null);
  if (existente !== null && existente !== existenteVisto) {
    // Ajuste durante el render (react.dev, «You might not need an effect»): se vuelve a leer la lista, que ya lo incluye.
    setExistenteVisto(existente);
    setSinOfertas(null);
    recargarOfertas();
  }

  const abrirVersion = (nueva: string) => {
    setRetomando(null);
    setElegida({ proyecto, codigo: nueva });
  };
  const pedirVersion = (nueva: string) => {
    if (nueva === codigo) return;
    if (hayCambios && estado.estado === "listo") setVersionPendiente(nueva);
    else abrirVersion(nueva);
  };
  // El foco vuelve a su sitio cuando el diálogo ya se cerró y el `inert` se quitó (en un navegador real no se puede enfocar
  // dentro de un subárbol inert): quien cierra el diálogo anota adónde, y este efecto (tras cada commit) lo cumple.
  const devolverFoco = useRef<"version" | "guardar" | null>(null);
  // Vuelve a leer la lista de versiones sin desmontar nada. Con `nueva`, si no se pudo leer, se agrega esa versión a mano para
  // que el selector la tenga (la persona no pierde su sitio por un fallo de lectura).
  const recargarVersiones = useCallback(
    async (nueva?: string) => {
      const sobre = cargadas;
      if (sobre === null) return;
      try {
        const frescos = await pedir<VersionesRespuesta>(rutaDeVersiones(proyecto));
        setFrescas({ proyecto, sobre, datos: frescos });
      } catch (error) {
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        if (nueva !== undefined) setFrescas({ proyecto, sobre, datos: conVersionGuardada(datosActuales.current ?? sobre, nueva) });
      }
    },
    [cargadas, proyecto, alExpirar],
  );
  // El servidor guardó la versión `nueva` (o ya estaba guardada): el borrador viejo ya no sirve y se abre la nueva, en la misma
  // pestaña. No vuelve a ofrecer retomar nada: lo que había se resolvió al guardar.
  const abrirGuardada = useCallback(
    async (nueva: string) => {
      cerrarGuardado();
      setSinOfertas(proyecto);
      await recargarVersiones(nueva);
      setRetomando(null);
      setElegida({ proyecto, codigo: nueva });
      devolverFoco.current = "version";
    },
    [cerrarGuardado, proyecto, recargarVersiones],
  );
  const alGuardada = useCallback(
    async (r: GuardadoRespuesta) => {
      setExito({ proyecto, texto: textoDeExito(r, r.proyecto) });
      await abrirGuardada(r.codigo);
    },
    [proyecto, abrirGuardada],
  );
  const guardado = useGuardado({
    id: estado.estado === "listo" ? estado.borrador.id : null,
    rev: estado.estado === "listo" ? estado.borrador.resumen.rev : 0,
    proyecto,
    alExpirar,
    alGuardada,
  });
  const cancelarGuardado = guardado.cerrar;
  const cancelarYDevolverFoco = useCallback(() => {
    devolverFoco.current = "guardar";
    cancelarGuardado();
  }, [cancelarGuardado]);
  useEffect(() => {
    if (versionPendiente !== null || guardado.abierto || devolverFoco.current === null) return;
    const destino = devolverFoco.current;
    devolverFoco.current = null;
    const boton = destino === "guardar" ? document.getElementById("hoja-guardar-version") : null;
    (boton ?? document.getElementById("hoja-version"))?.focus();
  });
  const seguirEditando = useCallback(() => {
    setVersionPendiente(null);
    devolverFoco.current = "version";
  }, []);
  const descartarYAbrir = async () => {
    const nueva = versionPendiente;
    setVersionPendiente(null);
    devolverFoco.current = "version";
    if (nueva === null) return;
    if (await descartarActual()) abrirVersion(nueva);
  };
  // Un fallo del guardado que pide ir a otra versión. Con «versión más nueva» la persona aún tiene cambios: pasa por la misma
  // confirmación de descartar que el selector. Con «ya se guardó» no hay nada que perder.
  const abrirDesdeElGuardado = async (nueva: string) => {
    const yaGuardado = guardado.error?.clase === "ya-guardado";
    cancelarYDevolverFoco();
    if (yaGuardado) {
      await abrirGuardada(nueva);
      return;
    }
    await recargarVersiones();
    pedirVersion(nueva);
  };
  const retomar = (oferta: OfertaDeRetomar) => {
    setFalloAlDescartar(null);
    setRetomando({ proyecto, id: oferta.id, version: oferta.version });
  };
  const descartarOfrecidos = async () => {
    setDescartando(true);
    setFalloAlDescartar(null);
    try {
      await Promise.all(ofrecidos.map((o) => pedir(`${RUTA_DE_BORRADORES}/${o.id}`, { metodo: "DELETE" })));
      setSinOfertas(proyecto);
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setFalloAlDescartar(error);
    } finally {
      setDescartando(false);
    }
  };
  // «Abrir de nuevo» (el borrador ya no está o ya no sirve): se abre uno nuevo de la versión, sin volver a ofrecer los viejos.
  const reabrirNuevo = () => {
    setRetomando(null);
    setSinOfertas(proyecto);
    reabrir();
  };

  const [pestana, setPestana] = useState(0);
  // «Ver en Auditoría» desde el Estado de una fila: va a esa pestaña con el filtro de la fila.
  const [filtro, setFiltro] = useState<FiltroDeAuditoria | null>(null);
  const verEnAuditoria = (f: FiltroDeAuditoria) => {
    setFiltro(f);
    setPestana(PESTANAS.indexOf("Auditoría"));
  };

  useEffect(() => {
    const alVolver = () => {
      if (document.visibilityState === "visible") refrescar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => document.removeEventListener("visibilitychange", alVolver);
  }, [refrescar]);

  // Con cambios sin guardar, el navegador avisa antes de cerrar o recargar la ventana (la clásica no podía).
  useEffect(() => {
    if (!hayCambios) return;
    const avisar = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [hayCambios]);

  if (versiones.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las versiones" />;
  if (versiones.estado !== "listo") return <AvisoError error={versiones.error} />;

  return (
    <>
    <div className="silice-hoja__contenido" inert={versionPendiente !== null || guardado.abierto}>
      {exito !== null && exito.proyecto === proyecto && (
        <InlineNotification
          kind="success"
          role="status"
          lowContrast
          title="Versión guardada"
          subtitle={exito.texto}
          onCloseButtonClick={() => setExito(null)}
        />
      )}
      {ofrecidos.length > 0 && (
        <OfertaDeRetomarVista
          proyecto={proyecto}
          ofertas={ofrecidos}
          alRetomar={retomar}
          alDescartar={() => void descartarOfrecidos()}
          ocupado={descartando}
        />
      )}
      {falloAlDescartar !== null && <AvisoError error={falloAlDescartar} titulo="No se pudo descartar el borrador" />}
      {ofrecidos.length === 0 &&
        (ofrecidas.length > 0 ? (
          <Select id="hoja-version" labelText="Versión" value={codigo ?? ""} onChange={(e) => pedirVersion(e.target.value)}>
            {ofrecidas.map((v) => (
              <SelectItem key={v.codigo} value={v.codigo} text={rotuloDeVersion(v)} />
            ))}
          </Select>
        ) : (
          <EstadoVacio titulo={SIN_VERSIONES} descripcion="Se abre un borrador en blanco para describir el espacio." />
        ))}

      {estado.estado === "abriendo" && <EsqueletoPagina etiqueta="Abriendo el borrador" />}
      {estado.estado === "error" &&
        (esBorradorAusente(estado.error) ? (
          <div className="silice-hoja__ausente">
            <AvisoError error={estado.error} titulo="El borrador ya no está" />
            <Button kind="tertiary" size="sm" onClick={reabrirNuevo}>
              Abrir de nuevo
            </Button>
          </div>
        ) : existente !== null && ofrecidos.length > 0 ? null : (
          <AvisoError error={estado.error} titulo="No se pudo abrir la hoja" />
        ))}
      {estado.estado === "listo" && (
        <>
          {estado.borrador.instantanea.mensaje && (
            <InlineNotification
              kind="info"
              lowContrast
              hideCloseButton
              title="Instantánea de la versión"
              subtitle={estado.borrador.instantanea.mensaje}
            />
          )}
          <EstadoDelBorrador borrador={estado.borrador} alDescartar={() => void descartarCambios()} alGuardar={guardado.abrir} />
        </>
      )}

      <ContextoAuditoria.Provider value={verEnAuditoria}>
        <Tabs
          selectedIndex={pestana}
          onChange={({ selectedIndex }) => {
            setFiltro(null);
            setPestana(selectedIndex);
          }}
        >
          <TabList aria-label="Secciones de la hoja">
            {PESTANAS.map((p) => (
              <Tab key={p}>{p}</Tab>
            ))}
          </TabList>
          <TabPanels>
            {PESTANAS.map((p, i) => (
              <TabPanel key={p}>
                {i === pestana && (
                  <ContenidoDePestana
                    indice={i}
                    borrador={estado.estado === "listo" ? estado.borrador : null}
                    alAusente={refrescar}
                    alAceptar={aplicar}
                    alRecargarBorrador={refrescar}
                    alReabrir={reabrirNuevo}
                    filtro={filtro}
                    alQuitarFiltro={() => setFiltro(null)}
                  />
                )}
              </TabPanel>
            ))}
          </TabPanels>
        </Tabs>
      </ContextoAuditoria.Provider>
      {/* Punto de acoplamiento del asistente de IA (diseño §2.10): vacío y oculto hasta que exista. */}
      <aside aria-label="Asistente de IA" hidden />
    </div>
    {guardado.abierto && estado.estado === "listo" && (
      <DialogoDeGuardar
        proyecto={estado.borrador.base.proyecto}
        version={estado.borrador.base.version}
        soloLectura={estado.borrador.base.solo_lectura}
        cambiosSinGuardar={estado.borrador.resumen.cambios}
        total={estado.borrador.resumen.total}
        moneda={estado.borrador.resumen.moneda}
        usuario={usuarioDeSesion(sesion)}
        fuente={guardado.fuente}
        alCambiarFuente={guardado.escribir}
        cambios={guardado.cambios}
        enviando={guardado.enviando}
        error={guardado.error}
        alGuardar={(confirmar) => void guardado.guardar(confirmar)}
        alCancelar={cancelarYDevolverFoco}
        alRecargar={() => void refrescar().then(guardado.limpiarError)}
        alAbrirVersion={(v) => void abrirDesdeElGuardado(v)}
        alAbrirDeNuevo={() => {
          cancelarYDevolverFoco();
          reabrirNuevo();
        }}
      />
    )}
    {versionPendiente !== null && estado.estado === "listo" && (
      <DialogoDeVersion
        titulo="Descartar los cambios"
        texto={textoDeCambiarVersion(estado.borrador.resumen.cambios)}
        textoConfirmar="Descartar y abrir"
        textoCancelar="Seguir editando"
        alConfirmar={() => void descartarYAbrir()}
        alCancelar={seguirEditando}
      />
    )}
    </>
  );
}

export default function PaginaHoja() {
  const { proyecto } = useAplicacion();
  return (
    <section className="silice-pagina silice-hoja">
      <h1 className="cds--type-heading-04">{TITULO}</h1>
      {proyecto === null ? (
        <EstadoVacio titulo="Elija un proyecto" descripcion="Use el selector de la cabecera para abrir su hoja." />
      ) : (
        <HojaDeProyecto proyecto={proyecto} />
      )}
    </section>
  );
}
