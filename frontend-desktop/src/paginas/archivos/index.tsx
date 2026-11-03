import { Button } from "@carbon/react";
import { useContext, useEffect, useState } from "react";
import { Link, useInRouterContext } from "react-router";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { FranjaDelPaso } from "../../comun/FranjaDelPaso";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { useAplicacion } from "../../shell/contexto";
import { esBorradorAusente } from "../hoja/logica";
import type { Resumen } from "../hoja/logica";
import { ContextoDeLaHoja, ProveedorDeLaHoja, useHojaDeLaObra } from "../hoja/ProveedorDeLaHoja";
import { useDialogoDeOperacion } from "../hoja/useDialogoDeOperacion";
import { CargarComputo } from "./CargarComputo";
import type { ImportacionDeObra } from "./logica";
import { InformeGuardado, RegistroDeImportaciones } from "./RegistroDeImportaciones";
import { SubirArchivo } from "./SubirArchivo";
import { TEXTOS } from "./textos";
import { useRegistro } from "./useRegistro";
import "./archivos.scss";

// Por qué existe (Tarea 11 del plan F4; especificación §3.3): la sección «Archivos y planos» de la obra. Arriba, la acción
// «Subir plano o cómputo» (el diálogo `SubirArchivo`: el plano o, con un .csv, «Cargar cómputo», Tarea 12), que entra en el
// MISMO borrador que Presupuesto y Versiones (`ProveedorDeLaHoja`, Tarea 3); debajo, el registro de lo importado
// (`GET /v1/hoja/importaciones`, Tarea 10), y al final «Describir el espacio a mano», que lleva a la pestaña «Espacio y
// metrajes». Quien revisa (o un borrador de solo lectura) ve el registro y el informe guardado, sin nada que suba. No ofrece
// el libro de la empresa ni las carpetas (baja 22: siguen en Empresa › Auditar). No es de ningún módulo (Tarea 12): con la
// especialidad «edificación» apagada no hay planos ni espacio, y la puerta se llama «Cargar cómputo».
export default function PaginaArchivos() {
  const { proyecto } = useAplicacion();
  const deLaObra = useContext(ContextoDeLaHoja);
  return (
    <section className="silice-pagina silice-archivos">
      <h1 className="cds--type-heading-04">{TEXTOS.titulo}</h1>
      {proyecto === null ? (
        <EstadoVacio titulo={TEXTOS.sinObra} />
      ) : deLaObra !== null ? (
        <Cuerpo proyecto={proyecto} />
      ) : (
        // Montada sola (sin la obra encima), como la Hoja: abre su propio proveedor.
        <ProveedorDeLaHoja>
          <Cuerpo proyecto={proyecto} />
        </ProveedorDeLaHoja>
      )}
    </section>
  );
}

function Cuerpo({ proyecto }: { proyecto: string }) {
  const { alExpirar, modulosApagados } = useAplicacion();
  // Regla de la T19 del plan vial: «edificación» apaga los planos y el espacio, no los cómputos.
  const conPlano = !(modulosApagados?.includes("edificacion") ?? false);
  const textoDeSubir = conPlano ? TEXTOS.subir : TEXTOS.cargarComputo;
  const hoja = useHojaDeLaObra();
  // Los enlaces a Presupuesto solo dentro de una obra y de un enrutador (montada sola, en pruebas, no hay adónde ir).
  const obra = useContext(ContextoDeLaObra);
  const enRuta = useInRouterContext();
  const registro = useRegistro(proyecto, alExpirar);
  const dialogo = useDialogoDeOperacion();
  const [elegida, setElegida] = useState<ImportacionDeObra | null>(null);
  const borrador = hoja.estado.estado === "listo" ? hoja.estado.borrador : null;
  const puedeSubir = hoja.puedeEditar && borrador !== null;
  // Pregunta abierta 3 del plan: la franja solo si se pidió describir el espacio y sigue vacío.
  const conFranja = conPlano && puedeSubir && hoja.espacioPedido && borrador?.resumen.espacio_vacio === true;
  const { abierto, cerrar } = dialogo;

  // Si el borrador deja de estar (venció, se reabre), el diálogo no tiene sobre qué trabajar: se cierra.
  useEffect(() => {
    if (abierto && borrador === null) cerrar(false);
  }, [abierto, borrador, cerrar]);

  // El foco vuelve al botón que abrió el diálogo (el de la franja o el de la sección).
  const abrir = () => {
    const activo = document.activeElement;
    dialogo.anclaDelBoton(activo instanceof HTMLButtonElement ? activo : null);
    dialogo.abrir();
  };
  const alAceptar = (r: Resumen) => {
    hoja.aplicar(r);
    registro.recargar();
  };

  return (
    <>
      <div className="silice-archivos__contenido silice-con-panel" inert={hoja.inerte}>
        <div className="silice-archivos__principal">
          {hoja.puedeEditar && <EstadoDelBorrador />}
          {conFranja && (
            // Con el diálogo abierto, su paso lleva el principal: el de la franja pasa a secundario (uno solo a la vista).
            <FranjaDelPaso tipo="falta" texto={TEXTOS.falta} accion={{ texto: TEXTOS.subir, alPulsar: abrir, enSegundoPlano: abierto }} />
          )}
          {puedeSubir && !conFranja && (
            <div>
              <Button kind={abierto ? "secondary" : "primary"} size="md" onClick={abrir}>
                {textoDeSubir}
              </Button>
            </div>
          )}
          <RegistroDeImportaciones carga={registro.carga} alElegir={setElegida} />
          {conPlano && hoja.puedeEditar && obra !== null && enRuta && (
            <p className="cds--type-body-compact-01">
              <Link
                className="cds--link"
                to={rutaDeObra(obra.carpeta, obra.obraId, "presupuesto")}
                onClick={() => {
                  hoja.pedirEspacio();
                  hoja.irAPestana("espacio");
                }}
              >
                {TEXTOS.describir}
              </Link>
            </p>
          )}
        </div>
        <InformeGuardado importacion={elegida} alCerrar={() => setElegida(null)} />
      </div>
      {abierto && borrador !== null && dialogo.anfitrion !== null && (
        <SubirArchivo
          id={borrador.id}
          rev={borrador.resumen.rev}
          anfitrion={dialogo.anfitrion}
          alCerrar={() => cerrar(true)}
          alAusente={() => void hoja.refrescar()}
          alAceptar={alAceptar}
          alRecargar={hoja.refrescar}
          alReabrir={() => {
            cerrar(false);
            hoja.reabrirNuevo();
          }}
          alExpirar={alExpirar}
          conPlano={conPlano}
          cuerpoDelComputo={(archivo, alOcuparse) => <CargarComputo archivo={archivo} alOcuparse={alOcuparse} alLlevar={registro.recargar} />}
        />
      )}
    </>
  );
}

// Lo que impide subir mientras el borrador no está listo, para quien sí podría: cambios sin guardar que esperan decisión
// (se resuelven en Presupuesto, donde vive la oferta de retomar) o un borrador que no se pudo abrir.
function EstadoDelBorrador() {
  const { estado, ofrecidos, reabrirNuevo } = useHojaDeLaObra();
  const obra = useContext(ContextoDeLaObra);
  const enRuta = useInRouterContext();
  if (ofrecidos.length > 0) {
    return (
      <p className="cds--type-body-compact-01">
        {TEXTOS.conOfertas}{" "}
        {obra !== null && enRuta && (
          <Link className="cds--link" to={rutaDeObra(obra.carpeta, obra.obraId, "presupuesto")}>
            {TEXTOS.irAPresupuesto}
          </Link>
        )}
      </p>
    );
  }
  if (estado.estado !== "error") return null;
  if (!esBorradorAusente(estado.error)) return <AvisoError error={estado.error} titulo={TEXTOS.falloDelBorrador} />;
  return (
    <div>
      <AvisoError error={estado.error} titulo={TEXTOS.borradorAusente} />
      <Button kind="tertiary" size="sm" onClick={reabrirNuevo}>
        {TEXTOS.abrirDeNuevo}
      </Button>
    </div>
  );
}
