import { Button } from "@carbon/react";
import { useCallback, useContext, useState } from "react";
import { useInRouterContext } from "react-router";
import { AvisoDeGuardado } from "../../comun/AvisoDeGuardado";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification } from "../../comun/carbonEs";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import type { PartidaCompuesta } from "../componer/ComponerPartida";
import { OfertaDeRetomar as OfertaDeRetomarVista } from "./OfertaDeRetomar";
import { ContextoDeLaHoja, ProveedorDeLaHoja, useHojaDeLaObra } from "./ProveedorDeLaHoja";
import { TITULO, esBorradorAusente } from "./logica";
import { PedidoDeFocoEnLaGrilla, PedidoDesdeComponer } from "./pedidosDeLaRuta";
import { SuperficiePresupuesto } from "./superficie/SuperficiePresupuesto";
import { ID_DEL_TITULO } from "./useGuardadoDeLaPagina";
import "./hoja.scss";

// El Presupuesto de la obra (pantalla `hoja`, la sección Presupuesto): una sola superficie, sin pestañas (lote B1-10, ficha-b1
// §1 y §3.4). Aquí solo se juntan el borrador y lo que lo rodea: las versiones, la oferta de retomar un borrador con cambios,
// el aviso de «Versión guardada» y el borrador ausente. Todo lo demás (el total, las partidas, los problemas, la fila de alta)
// es de `SuperficiePresupuesto`. Las pestañas de antes (Espacio y metrajes, APU, Plan y equilibrio, Precios y Ajustes de costo)
// viven en la subvista «Espacio, plan y ajustes» (`pestanas.tsx`). El borrador, las versiones y los diálogos de guardar y de
// cambiar de versión son de `ProveedorDeLaHoja`, que comparte la obra con Archivos y planos y Versiones.

function CuerpoDeLaSuperficie() {
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
    exito,
    quitarExito,
    inerte,
  } = useHojaDeLaObra();
  // La partida con que se llega desde la subvista Componer («Agregar X al presupuesto»): la fila de alta la toma y avisa.
  const [partidaPedida, setPartidaPedida] = useState<PartidaCompuesta | null>(null);
  // «Ver en el presupuesto» de Archivos y planos: el foco va a la grilla en cuanto llega la vista.
  const [enfocarGrilla, setEnfocarGrilla] = useState(false);
  const pedirFocoEnLaGrilla = useCallback(() => setEnfocarGrilla(true), []);
  const enUnRouter = useInRouterContext();

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

  const borrador = estado.estado === "listo" ? estado.borrador : null;
  return (
    <div className="silice-hoja__contenido" inert={inerte}>
      {enUnRouter && <PedidoDesdeComponer alPedir={setPartidaPedida} />}
      {enUnRouter && <PedidoDeFocoEnLaGrilla alPedir={pedirFocoEnLaGrilla} />}
      {exito !== null && exito.proyecto === proyecto && <AvisoDeGuardado exito={exito} alCerrar={quitarExito} />}
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

      {borrador?.instantanea.mensaje && (
        <InlineNotification kind="info" lowContrast hideCloseButton title="Instantánea de la versión" subtitle={borrador.instantanea.mensaje} />
      )}
      {estado.estado !== "error" && (
        <SuperficiePresupuesto
          proyecto={proyecto}
          borrador={borrador}
          puedeEditar={puedeEditar}
          alAusente={refrescar}
          alAceptar={aplicar}
          alRecargarBorrador={refrescar}
          alGuardar={abrirGuardado}
          alDescartar={() => void descartarCambios()}
          alReabrir={reabrirNuevo}
          partidaInicial={partidaPedida}
          alConsumirPartidaInicial={() => setPartidaPedida(null)}
          enfocarGrilla={enfocarGrilla}
          alEnfocarGrilla={() => setEnfocarGrilla(false)}
        />
      )}
      {/* Punto de acoplamiento del asistente de IA (diseño §2.10): vacío y oculto hasta que exista. */}
      <aside aria-label="Asistente de IA" hidden />
    </div>
  );
}

// Dentro de una obra, EspacioDeObra ya montó `ProveedorDeLaHoja` alrededor de la sección y la superficie usa ese: así el
// borrador sigue abierto al pasar a Archivos y planos o a Versiones. Montada sola (las pruebas, o una ruta vieja sin obra) no
// hay ninguno encima y monta el suyo. Nunca hay dos: si hay uno de la obra, manda.
export default function PaginaHoja() {
  const { proyecto } = useAplicacion();
  const deLaObra = useContext(ContextoDeLaHoja);
  return (
    <section className="silice-pagina silice-hoja">
      <h1 id={ID_DEL_TITULO} tabIndex={-1} className="cds--type-heading-04">
        {TITULO}
      </h1>
      {proyecto === null ? (
        <EstadoVacio titulo="Elija una obra" descripcion="Abra una obra en «Obras» de la barra lateral, o búsquela con Ctrl+K." />
      ) : deLaObra !== null ? (
        <CuerpoDeLaSuperficie />
      ) : (
        <ProveedorDeLaHoja>
          <CuerpoDeLaSuperficie />
        </ProveedorDeLaHoja>
      )}
    </section>
  );
}
