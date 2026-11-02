import { useContext, useId, useState } from "react";
import { FranjaDelPaso } from "../../comun/FranjaDelPaso";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { useFocoAlCerrar } from "./AgregarPartida";
import { AprobacionDeVersion } from "./AprobacionDeVersion";
import type { BorradorAbierto } from "./logica";
import { gravesDe, necesitaLaAprobacion, pasoDelPresupuesto } from "./pasoDelPresupuesto";
import type { AccionDelPresupuesto, EntradaDelPaso } from "./pasoDelPresupuesto";
import { usePuedeEditarLaHoja } from "./puedeEditar";
import { textoDelBoton } from "./textos";
import { useAprobacionDeVersion } from "./useAprobacionDeVersion";

// Por qué existe (Tarea 5 del plan F4): la franja «Te falta / Siguiente paso» del Presupuesto y la aprobación de la versión
// abierta comparten la lectura del estado de aprobación y el diálogo de enviar, que abre el botón de la franja. Aquí se
// juntan: la regla del paso (`pasoDelPresupuesto`), su botón (el único principal de la pantalla) y lo que se ve de la
// aprobación (`AprobacionDeVersion`). Lo monta solo el cuerpo de la Hoja, con una `key` por obra y versión: cambiar de
// versión empieza de cero, como antes.

// A estos ids vuelve el foco al cerrar el diálogo que abre el botón. El de guardar lo usa `useGuardadoDeLaPagina`.
const ID_GUARDAR = "hoja-guardar-version";
const ID_ENVIAR = "hoja-enviar-a-aprobacion";
const IDS: Partial<Record<AccionDelPresupuesto, string>> = { guardar: ID_GUARDAR, enviar_a_aprobacion: ID_ENVIAR };

function textoDeEnvio(version: string, retirada: string | null): string {
  const enviado = `Se envió ${version} a aprobación.`;
  return retirada ? `${enviado} Se retiró ${retirada} de la aprobación.` : enviado;
}

interface Props {
  proyecto: string;
  borrador: BorradorAbierto;
  // `HojaDeLaObra.puedeEditar`: el permiso y un borrador que no es de solo lectura.
  puedeEditar: boolean;
  // Lo que hace cada botón fuera de aquí: abrir «Agregar partida» en Partidas, abrir «Guardar versión», ir a Revisión e ir
  // a Partidas para corregir una devuelta.
  alAgregarPartida: () => void;
  alGuardar: () => void;
  alVerRevision: () => void;
  alHacerVersionNueva: () => void;
}

export function FranjaDelPresupuesto({
  proyecto,
  borrador,
  puedeEditar,
  alAgregarPartida,
  alGuardar,
  alVerRevision,
  alHacerVersionNueva,
}: Props) {
  const { base, resumen } = borrador;
  const version = base.version;
  const lectura = useAprobacionDeVersion(proyecto, version);
  const { recargar } = lectura;
  // Enviar obra sobre la versión GUARDADA: su regla es solo el permiso (decisión 16 de la Tarea 2b, Eugenio, 2026-10-31).
  const conPermiso = usePuedeEditarLaHoja(null);
  // Tras enviar, la ficha de la obra (su etapa en la cabecera y en el Resumen) se vuelve a leer (Tarea 3, ronda 2). Sin
  // obra (la Hoja montada sola) no hay ficha.
  const recargarFicha = useContext(ContextoDeLaObra)?.recargarFicha;
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const idZona = useId();
  const enfocarAlCerrar = useFocoAlCerrar();

  const entrada: EntradaDelPaso = {
    version,
    vigente: base.vigente,
    cambios: resumen.cambios,
    graves: gravesDe(resumen.hallazgos),
    aprobacion: lectura.estado === "listo" ? (lectura.datos?.estado ?? null) : null,
    puedeEditar,
    puedeEnviar: conPermiso && lectura.estado !== "fallo",
  };
  const paso = lectura.estado === "leyendo" && necesitaLaAprobacion(entrada) ? null : pasoDelPresupuesto(entrada);

  const acciones: Record<AccionDelPresupuesto, () => void> = {
    agregar_partida: alAgregarPartida,
    guardar: alGuardar,
    ver_revision: alVerRevision,
    version_nueva: () => {
      setAviso("Corrija y guarde: será una versión nueva.");
      alHacerVersionNueva();
    },
    enviar_a_aprobacion: () => setEnviando(true),
  };

  const enviado = (retirada: string | null) => {
    setEnviando(false);
    setAviso(textoDeEnvio(version ?? "", retirada));
    recargar();
    recargarFicha?.();
    enfocarAlCerrar(idZona);
  };
  const cancelarEnvio = () => {
    setEnviando(false);
    enfocarAlCerrar(ID_ENVIAR);
  };

  return (
    <>
      {paso !== null && (
        <FranjaDelPaso
          tipo={paso.tipo}
          texto={paso.texto}
          accion={
            paso.accion === null
              ? undefined
              : { texto: textoDelBoton(paso.accion, version === null), alPulsar: acciones[paso.accion], id: IDS[paso.accion] }
          }
        />
      )}
      {version !== null && (
        <AprobacionDeVersion
          id={idZona}
          proyecto={proyecto}
          version={version}
          cambios={resumen.cambios}
          lectura={lectura}
          aviso={aviso}
          enviando={enviando}
          alEnviado={enviado}
          alCancelarEnvio={cancelarEnvio}
        />
      )}
    </>
  );
}
