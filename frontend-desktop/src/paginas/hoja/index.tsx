import { Button, InlineNotification, Select, SelectItem, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useContext, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { AprobacionDeVersion } from "./AprobacionDeVersion";
import { OfertaDeRetomar as OfertaDeRetomarVista } from "./OfertaDeRetomar";
import {
  SIN_VERSIONES,
  TITULO,
  esBorradorAusente,
  pestanasVisibles,
  rotuloDeVersion,
  textoDeCambios,
  versionesOfrecidas,
} from "./logica";
import type { BorradorAbierto, PestanaId, Resumen } from "./logica";
import { CAUSA_SOLO_LECTURA } from "./logicaGuardar";
import { BotonExcel } from "./BotonExcel";
import { ContextoAuditoria } from "./ContextoAuditoria";
import type { AlCrearVersion } from "./OperacionesDePrecios";
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
import { ContextoDeLaHoja, ProveedorDeLaHoja, useHojaDeLaObra } from "./ProveedorDeLaHoja";
import "./hoja.scss";

// La Hoja de la obra (pantalla `hoja`, la sección Presupuesto): el estado del borrador, el reparto de las pestañas y el
// cuerpo que los junta. Desde la Tarea 3 del plan F4 el borrador es de `ProveedorDeLaHoja`, y desde la 4 también la pestaña
// abierta. Pasa de 250 líneas porque junta tres piezas que solo se entienden juntas: el estado del borrador, el cuerpo con
// sus avisos y el reparto de las pestañas (`ContenidoDePestana`); la Tarea 6 (Versiones) y la 11 (Archivos y planos) le
// quitan lo que se va a sus secciones.

function EstadoDelBorrador({
  borrador,
  alDescartar,
  alGuardar,
  puedeEditar,
}: {
  borrador: BorradorAbierto;
  alDescartar: () => void;
  alGuardar: () => void;
  // F4 2b: sin permiso de edición (o con un borrador de solo lectura) no se ofrece guardar ni descartar.
  puedeEditar: boolean;
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
      {puedeEditar && (resumen.cambios > 0 || base.version === null) && !confirmando && (
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

// Solo se monta la pestaña activa y solo cuando el borrador está abierto: así solo se pide su vista. Las que se editan no se
// vuelven a montar con cada `rev` (perdería lo escrito; llevan `key` del borrador) y cada una vuelve a leer su vista; las de
// solo lectura se vuelven a montar con cada cambio (llevan `llave`).
function ContenidoDePestana({
  pestana,
  borrador,
  alAusente,
  alAceptar,
  alRecargarBorrador,
  alReabrir,
  filtro,
  alQuitarFiltro,
  alCrearVersion,
}: {
  pestana: PestanaId;
  borrador: BorradorAbierto | null;
  alAusente: () => void;
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  alReabrir: () => void;
  filtro: FiltroDeAuditoria | null;
  alQuitarFiltro: () => void;
  // Se creó una versión nueva (restaurar, cotizar, retirar, convertir): la página la abre.
  alCrearVersion: AlCrearVersion;
}) {
  if (borrador === null) return null;
  const llave = `${borrador.id}-${borrador.resumen.rev}`;
  const moneda = borrador.resumen.moneda;
  const deEdicion = {
    id: borrador.id,
    base: borrador.base,
    rev: borrador.resumen.rev,
    alAusente,
    alAceptar,
    alRecargarBorrador,
    alReabrir,
  };
  switch (pestana) {
    case "espacio":
      return <PestanaEspacio key={borrador.id} {...deEdicion} />;
    case "partidas":
      return <PestanaPresupuesto key={borrador.id} {...deEdicion} />;
    case "apu":
      return <PestanaApu key={borrador.id} {...deEdicion} moneda={moneda} />;
    case "plan":
      // «Plan y equilibrio» (baja 23): la matriz y la curva, y debajo el punto de equilibrio, que solo se lee.
      return (
        <>
          <PestanaPlan key={borrador.id} {...deEdicion} />
          <PestanaEquilibrio key={llave} id={borrador.id} alAusente={alAusente} />
        </>
      );
    case "precios":
      return (
        <PestanaPrecios
          key={llave}
          proyecto={borrador.base.proyecto}
          version={borrador.base.version}
          alAusente={alAusente}
          cambios={borrador.resumen.cambios}
          alCrearVersion={alCrearVersion}
        />
      );
    case "revision":
      return <PestanaAuditoria key={llave} id={borrador.id} alAusente={alAusente} filtro={filtro} alQuitarFiltro={alQuitarFiltro} />;
    case "ajustes":
      return (
        <PestanaParametros
          key={borrador.id}
          {...deEdicion}
          conversion={{
            proyecto: borrador.base.proyecto,
            version: borrador.base.version,
            cambios: borrador.resumen.cambios,
            alCrearVersion,
          }}
        />
      );
    case "trazabilidad":
      return (
        <PestanaTrazabilidad
          key={llave}
          proyecto={borrador.base.proyecto}
          version={borrador.base.version}
          alAusente={alAusente}
          cambios={borrador.resumen.cambios}
          alCrearVersion={alCrearVersion}
        />
      );
  }
}

const NOTA_SOLO_LECTURA = "Está viendo este presupuesto en solo lectura.";

// El cuerpo de la Hoja: lo que se ve de la obra abierta (la oferta de retomar, el selector de versión, el estado del
// borrador y las pestañas). El borrador, las versiones y los diálogos de guardar y de cambiar de versión son de
// `ProveedorDeLaHoja` (Tarea 3 del plan F4), que comparte la obra con Archivos y planos y Versiones.
function CuerpoDeLaHoja() {
  const {
    proyecto,
    nombreProyecto,
    versiones,
    codigo,
    estado,
    puedeEditar,
    ofrecidos,
    retomar,
    descartarOfrecidos,
    descartando,
    falloAlDescartar,
    existente,
    pedirVersion,
    refrescar,
    aplicar,
    reabrirNuevo,
    descartarCambios,
    abrirGuardado,
    alCrearVersion,
    exito,
    quitarExito,
    inerte,
    pestana,
    irAPestana,
    espacioPedido,
  } = useHojaDeLaObra();
  const ofrecidas = versiones.estado === "listo" ? versionesOfrecidas(versiones.datos.versiones) : [];

  // «Ver en Revisión» desde el Estado de una fila: va a esa pestaña con el filtro de la fila. La pestaña abierta es del
  // proveedor (Tarea 4): sobrevive al pasar a Archivos y planos o a Versiones.
  const [filtro, setFiltro] = useState<FiltroDeAuditoria | null>(null);
  const verEnRevision = (f: FiltroDeAuditoria) => {
    setFiltro(f);
    irAPestana("revision");
  };
  const visibles = estado.estado === "listo" ? pestanasVisibles(estado.borrador.resumen, espacioPedido) : [];

  if (versiones.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las versiones" />;
  if (versiones.estado !== "listo") return <AvisoError error={versiones.error} />;

  return (
    <div className="silice-hoja__contenido" inert={inerte}>
      {exito !== null && exito.proyecto === proyecto && (
        <InlineNotification
          kind="success"
          role="status"
          lowContrast
          title="Versión guardada"
          subtitle={exito.texto}
          onCloseButtonClick={quitarExito}
        />
      )}
      {ofrecidos.length > 0 && (
        <OfertaDeRetomarVista
          proyecto={nombreProyecto ?? proyecto}
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
          <EstadoVacio
            titulo={SIN_VERSIONES}
            descripcion="Agregue las partidas en «Presupuesto» (o, en una obra de instalaciones, describa el espacio o importe un plano) y guarde la primera versión con «Guardar primera versión…»."
          />
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
          {/* Tarea 19: la aprobación de la versión abierta, junto a ella (una versión guardada; el borrador en blanco no). */}
          {estado.borrador.base.version !== null && (
            <AprobacionDeVersion
              key={`${proyecto}|${estado.borrador.base.version}`}
              proyecto={proyecto}
              version={estado.borrador.base.version}
              cambios={estado.borrador.resumen.cambios}
              base={estado.borrador.base}
              alHacerVersionNueva={() => {
                setFiltro(null);
                irAPestana("partidas");
              }}
            />
          )}
          <EstadoDelBorrador
            borrador={estado.borrador}
            alDescartar={() => void descartarCambios()}
            alGuardar={abrirGuardado}
            puedeEditar={puedeEditar}
          />
          <BotonExcel id={estado.borrador.id} />
        </>
      )}

      {!puedeEditar && (
        <p role="note" className="silice-hoja__solo-lectura cds--type-body-compact-01">
          {NOTA_SOLO_LECTURA}
          {estado.estado === "listo" && estado.borrador.base.solo_lectura && ` Esta versión no se puede guardar: ${CAUSA_SOLO_LECTURA}.`}
        </p>
      )}
      {estado.estado === "listo" && (
        <ContextoAuditoria.Provider value={verEnRevision}>
          <Tabs
            selectedIndex={Math.max(0, visibles.findIndex((p) => p.id === pestana))}
            onChange={({ selectedIndex }) => {
              setFiltro(null);
              irAPestana(visibles[selectedIndex]!.id);
            }}
          >
            <TabList aria-label="Secciones del presupuesto">
              {visibles.map((p) => (
                <Tab key={p.id}>{p.titulo}</Tab>
              ))}
            </TabList>
            <TabPanels>
              {visibles.map((p) => (
                <TabPanel key={p.id}>
                  {p.id === pestana && (
                    <ContenidoDePestana
                      pestana={p.id}
                      borrador={estado.borrador}
                      alAusente={refrescar}
                      alAceptar={aplicar}
                      alRecargarBorrador={refrescar}
                      alReabrir={reabrirNuevo}
                      filtro={filtro}
                      alQuitarFiltro={() => setFiltro(null)}
                      alCrearVersion={alCrearVersion}
                    />
                  )}
                </TabPanel>
              ))}
            </TabPanels>
          </Tabs>
        </ContextoAuditoria.Provider>
      )}
      {/* Punto de acoplamiento del asistente de IA (diseño §2.10): vacío y oculto hasta que exista. */}
      <aside aria-label="Asistente de IA" hidden />
    </div>
  );
}

// Dentro de una obra, EspacioDeObra ya montó `ProveedorDeLaHoja` alrededor de la sección y la Hoja usa ese: así el borrador
// sigue abierto al pasar a Archivos y planos o a Versiones. Montada sola (las pruebas de la Hoja, o una ruta vieja sin
// obra) no hay ninguno encima y monta el suyo. Nunca hay dos: si hay uno de la obra, manda.
export default function PaginaHoja() {
  const { proyecto } = useAplicacion();
  const deLaObra = useContext(ContextoDeLaHoja);
  return (
    <section className="silice-pagina silice-hoja">
      <h1 className="cds--type-heading-04">{TITULO}</h1>
      {proyecto === null ? (
        <EstadoVacio titulo="Elija una obra" />
      ) : deLaObra !== null ? (
        <CuerpoDeLaHoja />
      ) : (
        <ProveedorDeLaHoja>
          <CuerpoDeLaHoja />
        </ProveedorDeLaHoja>
      )}
    </section>
  );
}
