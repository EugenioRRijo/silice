import { Button, InlineNotification, Select, SelectItem, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useEffect, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
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

function EstadoDelBorrador({ borrador, alDescartar }: { borrador: BorradorAbierto; alDescartar: () => void }) {
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
      {resumen.cambios > 0 && !confirmando && (
        <div>
          <Button kind="ghost" size="sm" onClick={() => setConfirmando(true)}>
            Descartar cambios
          </Button>
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
  if (indice === 1) return <PestanaApu key={llave} id={borrador.id} moneda={moneda} alAusente={alAusente} />;
  if (indice === 2) return <PestanaPresupuesto key={llave} id={borrador.id} alAusente={alAusente} />;
  if (indice === 3) return <PestanaPlan key={llave} id={borrador.id} alAusente={alAusente} />;
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

function HojaDeProyecto({ proyecto }: { proyecto: string }) {
  const { alExpirar } = useAplicacion();
  const versiones = useCarga<VersionesRespuesta>(rutaDeVersiones(proyecto), alExpirar);
  const [elegida, setElegida] = useState<{ proyecto: string; codigo: string } | null>(null);

  const datos = versiones.estado === "listo" ? versiones.datos : null;
  const ofrecidas = datos ? versionesOfrecidas(datos.versiones) : [];
  const delProyecto = elegida?.proyecto === proyecto ? elegida.codigo : null;
  const codigo =
    datos === null ? undefined : ofrecidas.some((v) => v.codigo === delProyecto) ? delProyecto : (datos.por_omision ?? null);

  const { estado, refrescar, reabrir, aplicar, descartarCambios } = useBorrador(proyecto, codigo, alExpirar);
  const hayCambios = estado.estado === "listo" && estado.borrador.resumen.cambios > 0;
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
      {ofrecidas.length > 0 ? (
        <Select
          id="hoja-version"
          labelText="Versión"
          value={codigo ?? ""}
          onChange={(e) => setElegida({ proyecto, codigo: e.target.value })}
        >
          {ofrecidas.map((v) => (
            <SelectItem key={v.codigo} value={v.codigo} text={rotuloDeVersion(v)} />
          ))}
        </Select>
      ) : (
        <EstadoVacio titulo={SIN_VERSIONES} descripcion="Se abre un borrador en blanco para describir el espacio." />
      )}

      {estado.estado === "abriendo" && <EsqueletoPagina etiqueta="Abriendo el borrador" />}
      {estado.estado === "error" &&
        (esBorradorAusente(estado.error) ? (
          <div className="silice-hoja__ausente">
            <AvisoError error={estado.error} titulo="El borrador ya no está" />
            <Button kind="tertiary" size="sm" onClick={reabrir}>
              Abrir de nuevo
            </Button>
          </div>
        ) : (
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
          <EstadoDelBorrador borrador={estado.borrador} alDescartar={() => void descartarCambios()} />
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
                    alReabrir={reabrir}
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
