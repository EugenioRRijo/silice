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
  PESTANAS,
  SIN_VERSIONES,
  TITULO,
  esBorradorAusente,
  pestanaInicial,
  rotuloDeVersion,
  textoDeCambios,
  versionesOfrecidas,
} from "./logica";
import type { BorradorAbierto, Resumen } from "./logica";
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
// cuerpo que los junta. Desde la Tarea 3 del plan F4 el borrador es de `ProveedorDeLaHoja`. Pasa de 250 líneas por el
// reparto de las nueve pestañas (`ContenidoDePestana`), que la Tarea 4 reordena.

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
  alCrearVersion,
}: {
  indice: number;
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
  if (indice === 0) {
    return (
      <PestanaEspacio
        key={borrador.id}
        id={borrador.id}
        base={borrador.base}
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
        base={borrador.base}
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
        base={borrador.base}
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
        base={borrador.base}
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
  }
  // Las que se editan no se vuelven a montar con cada `rev` (perdería lo escrito); cada una vuelve a leer su vista.
  if (indice === 6) {
    return (
      <PestanaParametros
        key={borrador.id}
        id={borrador.id}
        base={borrador.base}
        rev={borrador.resumen.rev}
        moneda={moneda}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargarBorrador={alRecargarBorrador}
        alReabrir={alReabrir}
        conversion={{
          proyecto: borrador.base.proyecto,
          version: borrador.base.version,
          cambios: borrador.resumen.cambios,
          alCrearVersion,
        }}
      />
    );
  }
  if (indice === 7) {
    return <PestanaAuditoria key={llave} id={borrador.id} alAusente={alAusente} filtro={filtro} alQuitarFiltro={alQuitarFiltro} />;
  }
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
  } = useHojaDeLaObra();
  const ofrecidas = versiones.estado === "listo" ? versionesOfrecidas(versiones.datos.versiones) : [];

  const [pestana, setPestana] = useState(0);
  // La pestaña con que abre la obra (Tarea 11): sin espacio, «Presupuesto». Se fija una vez por obra, con su primer borrador;
  // cambiar de versión no mueve a la persona de la pestaña en que está. Ajuste durante el render (react.dev, «You might
  // not need an effect»).
  const [pestanaDe, setPestanaDe] = useState<string | null>(null);
  if (estado.estado === "listo" && pestanaDe !== proyecto) {
    setPestanaDe(proyecto);
    setPestana(pestanaInicial(estado.borrador.resumen));
  }
  // «Ver en Auditoría» desde el Estado de una fila: va a esa pestaña con el filtro de la fila.
  const [filtro, setFiltro] = useState<FiltroDeAuditoria | null>(null);
  const verEnAuditoria = (f: FiltroDeAuditoria) => {
    setFiltro(f);
    setPestana(PESTANAS.indexOf("Auditoría"));
  };

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
                setPestana(PESTANAS.indexOf("Presupuesto"));
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
                    alCrearVersion={alCrearVersion}
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
