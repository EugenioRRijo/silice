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

      <Tabs>
        <TabList aria-label="Secciones de la hoja">
          {PESTANAS.map((p) => (
            <Tab key={p}>{p}</Tab>
          ))}
        </TabList>
        <TabPanels>
          {PESTANAS.map((p) => (
            <TabPanel key={p}>
              <p className="cds--type-body-compact-01">La sección «{p}» llega en la siguiente entrega.</p>
            </TabPanel>
          ))}
        </TabPanels>
      </Tabs>
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
