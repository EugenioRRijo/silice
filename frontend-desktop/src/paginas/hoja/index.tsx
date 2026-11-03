import { Button, Tab, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { InlineNotification, TabList } from "../../comun/carbonEs";
import { useContext, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { OfertaDeRetomar as OfertaDeRetomarVista } from "./OfertaDeRetomar";
import { SIN_VERSIONES, TITULO, esBorradorAusente, textoDeCambios, versionesOfrecidas } from "./logica";
import type { BorradorAbierto, PestanaId, Resumen } from "./logica";
import { CAUSA_SOLO_LECTURA } from "./logicaGuardar";
import { BotonExcel } from "./BotonExcel";
import { FranjaDelPresupuesto } from "./FranjaDelPresupuesto";
import { ContextoAuditoria } from "./ContextoAuditoria";
import type { AlCrearVersion } from "./logicaVersiones";
import type { FiltroDeAuditoria } from "./ContextoAuditoria";
import { PestanaApu } from "./PestanaApu";
import { PestanaAuditoria } from "./PestanaAuditoria";
import { PestanaEquilibrio } from "./PestanaEquilibrio";
import { PestanaEspacio } from "./PestanaEspacio";
import { PestanaPrecios } from "./PestanaPrecios";
import { PestanaParametros } from "./PestanaParametros";
import { PestanaPlan } from "./PestanaPlan";
import { PestanaPresupuesto } from "./PestanaPresupuesto";
import { ContextoDeLaHoja, ProveedorDeLaHoja, useHojaDeLaObra } from "./ProveedorDeLaHoja";
import { ID_DEL_TITULO } from "./useGuardadoDeLaPagina";
import "./hoja.scss";

// La Hoja de la obra (pantalla `hoja`, la sección Presupuesto): el estado del borrador, el reparto de las pestañas y el
// cuerpo que los junta. Desde la Tarea 3 del plan F4 el borrador es de `ProveedorDeLaHoja`, y desde la 4 también la pestaña
// abierta. Desde la 5, la franja del paso (`FranjaDelPresupuesto`) va encima de todo y su botón es el único principal.
// Pasa de 250 líneas porque junta tres piezas que solo se entienden juntas: el estado del borrador, el cuerpo con sus
// avisos y el reparto de las pestañas (`ContenidoDePestana`); la Tarea 6 (Versiones) y la 11 (Archivos y planos) le
// quitan lo que se va a sus secciones.

// El total y «Descartar cambios» (fantasma). «Guardar versión…» pasó a la franja del paso en la Tarea 5: es la acción
// principal mientras haya cambios.
function EstadoDelBorrador({
  borrador,
  alDescartar,
  puedeEditar,
}: {
  borrador: BorradorAbierto;
  alDescartar: () => void;
  // F4 2b: sin permiso de edición (o con un borrador de solo lectura) no se ofrece descartar.
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
      <p className="silice-hoja__total cds--type-heading-03" aria-live="polite" title={formatoEsVe(resumen.total.exacto)}>
        Total {formatoEsVe(resumen.total.texto)} {resumen.moneda}
        <span className="cds--visually-hidden"> Valor exacto {formatoEsVe(resumen.total.exacto)}</span>
      </p>
      {resumen.version_mas_nueva !== null && (
        <p className="cds--type-helper-text-01">La versión vigente ahora es la {resumen.version_mas_nueva}.</p>
      )}
      {puedeEditar && resumen.cambios > 0 && !confirmando && (
        <div className="silice-hoja__acciones">
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
  pedirAgregar,
  alAtenderAgregar,
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
  // La franja pidió «Agregar la primera partida» (Tarea 5): Partidas abre su diálogo y avisa que lo atendió.
  pedirAgregar: boolean;
  alAtenderAgregar: () => void;
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
      return <PestanaPresupuesto key={borrador.id} {...deEdicion} pedirAgregar={pedirAgregar} alAtenderAgregar={alAtenderAgregar} />;
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
  }
}

const NOTA_SOLO_LECTURA = "Está viendo este presupuesto en solo lectura.";

// El cuerpo de la Hoja: lo que se ve de la obra abierta (la oferta de retomar, el estado del borrador y las pestañas). La
// versión se abre desde Versiones («Abrir», baja 9 de la Tarea 6) y el estado del borrador dice cuál es. El borrador, las
// versiones y los diálogos de guardar y de cambiar de versión son de `ProveedorDeLaHoja` (Tarea 3 del plan F4), que comparte
// la obra con Archivos y planos y Versiones.
function CuerpoDeLaHoja() {
  const {
    proyecto,
    nombreProyecto,
    versiones,
    estado,
    puedeEditar,
    ofrecidos,
    retomar,
    descartarOfrecidos,
    descartando,
    falloAlDescartar,
    existente,
    nadaQueRevisar,
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
    visibles,
  } = useHojaDeLaObra();
  const ofrecidas = versiones.estado === "listo" ? versionesOfrecidas(versiones.datos.versiones) : [];

  // «Ver en Revisión» desde el Estado de una fila: va a esa pestaña con el filtro de la fila. La pestaña abierta es del
  // proveedor (Tarea 4): sobrevive al pasar a Archivos y planos o a Versiones.
  const [filtro, setFiltro] = useState<FiltroDeAuditoria | null>(null);
  const verEnRevision = (f: FiltroDeAuditoria) => {
    setFiltro(f);
    irAPestana("revision");
  };
  // La franja pidió agregar la primera partida: se va a «Partidas» y su pestaña abre el diálogo (Tarea 5).
  const [pedirAgregar, setPedirAgregar] = useState(false);
  const alAtenderAgregar = () => setPedirAgregar(false);
  const irAPartidas = () => {
    setFiltro(null);
    irAPestana("partidas");
  };

  if (versiones.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las versiones" />;
  if (versiones.estado !== "listo") return <AvisoError error={versiones.error} />;
  if (nadaQueRevisar) {
    return (
      <EstadoVacio
        titulo="Aún no hay nada que revisar"
        descripcion="Esta obra no tiene versiones guardadas. Cuando quien arma el presupuesto guarde la primera, podrá revisarla aquí."
      />
    );
  }

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
      {ofrecidos.length === 0 && ofrecidas.length === 0 && (
        <EstadoVacio
          titulo={SIN_VERSIONES}
          descripcion="Agregue las partidas en la pestaña «Partidas» (o, en una obra de instalaciones, describa el espacio o importe un plano en «Archivos y planos») y guarde la primera versión con «Guardar primera versión…»."
        />
      )}

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
          {/* Tarea 5: la franja del paso, con el único botón principal, y la aprobación de la versión abierta (Tarea 19). */}
          <FranjaDelPresupuesto
            key={`${proyecto}|${estado.borrador.base.version ?? ""}`}
            proyecto={proyecto}
            borrador={estado.borrador}
            puedeEditar={puedeEditar}
            alAgregarPartida={() => {
              irAPartidas();
              setPedirAgregar(true);
            }}
            alGuardar={abrirGuardado}
            alVerRevision={() => {
              setFiltro(null);
              irAPestana("revision");
            }}
            alHacerVersionNueva={irAPartidas}
          />
          <EstadoDelBorrador borrador={estado.borrador} alDescartar={() => void descartarCambios()} puedeEditar={puedeEditar} />
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
                      pedirAgregar={pedirAgregar}
                      alAtenderAgregar={alAtenderAgregar}
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
      <h1 id={ID_DEL_TITULO} tabIndex={-1} className="cds--type-heading-04">
        {TITULO}
      </h1>
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
