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
import type { BorradorAbierto, VersionesRespuesta } from "./logica";
import { ContextoAuditoria } from "./ContextoAuditoria";
import type { FiltroDeAuditoria } from "./ContextoAuditoria";
import { PestanaApu } from "./PestanaApu";
import { PestanaAuditoria } from "./PestanaAuditoria";
import { PestanaEquilibrio } from "./PestanaEquilibrio";
import { PestanaEspacio } from "./PestanaEspacio";
import { PestanaParametros } from "./PestanaParametros";
import { PestanaPlan } from "./PestanaPlan";
import { PestanaPresupuesto } from "./PestanaPresupuesto";
import { useBorrador } from "./useBorrador";
import "./hoja.scss";

function EstadoDelBorrador({ borrador }: { borrador: BorradorAbierto }) {
  const { base, resumen } = borrador;
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
    </section>
  );
}

// Solo se monta la pestaña activa y solo cuando el borrador está abierto: así solo se pide su vista.
function ContenidoDePestana({
  indice,
  nombre,
  borrador,
  alAusente,
  filtro,
  alQuitarFiltro,
}: {
  indice: number;
  nombre: string;
  borrador: BorradorAbierto | null;
  alAusente: () => void;
  filtro: FiltroDeAuditoria | null;
  alQuitarFiltro: () => void;
}) {
  if (borrador === null) return null;
  const llave = `${borrador.id}-${borrador.resumen.rev}`;
  const moneda = borrador.resumen.moneda;
  if (indice === 0) return <PestanaEspacio key={llave} id={borrador.id} alAusente={alAusente} />;
  if (indice === 1) return <PestanaApu key={llave} id={borrador.id} moneda={moneda} alAusente={alAusente} />;
  if (indice === 2) return <PestanaPresupuesto key={llave} id={borrador.id} alAusente={alAusente} />;
  if (indice === 3) return <PestanaPlan key={llave} id={borrador.id} alAusente={alAusente} />;
  if (indice === 4) return <PestanaEquilibrio key={llave} id={borrador.id} moneda={moneda} alAusente={alAusente} />;
  if (indice === 6) return <PestanaParametros key={llave} id={borrador.id} moneda={moneda} alAusente={alAusente} />;
  if (indice === 7) {
    return <PestanaAuditoria key={llave} id={borrador.id} alAusente={alAusente} filtro={filtro} alQuitarFiltro={alQuitarFiltro} />;
  }
  return <p className="cds--type-body-compact-01">La sección «{nombre}» llega en la siguiente entrega.</p>;
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

  const { estado, refrescar, reabrir } = useBorrador(proyecto, codigo, alExpirar);
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
          <EstadoDelBorrador borrador={estado.borrador} />
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
                    nombre={p}
                    borrador={estado.estado === "listo" ? estado.borrador : null}
                    alAusente={refrescar}
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
