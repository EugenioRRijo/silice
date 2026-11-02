import { useCallback, useEffect, useRef, useState } from "react";
import { textoDeExito } from "./logicaGuardar";
import type { GuardadoRespuesta } from "./logicaGuardar";
import { useGuardado } from "./useGuardado";

interface Opciones {
  proyecto: string;
  // El borrador abierto (null si todavía no hay uno) y su `rev` según la página.
  id: string | null;
  rev: number;
  alExpirar: () => void;
  // El servidor guardó este borrador (o ya estaba guardado): ya no hay cambios que conservar.
  cerrarGuardado: () => void;
  recargarVersiones: (nueva?: string) => Promise<void>;
  // La página olvida las ofertas de retomar (lo que había se resolvió al guardar).
  olvidarOfertas: () => void;
  // La página elige la versión recién creada (y deja de retomar).
  elegirVersion: (codigo: string) => void;
  // Abrir otra versión por el camino de siempre (con la confirmación de descartar si hay cambios).
  pedirVersion: (codigo: string) => void;
  // Hay una confirmación de cambio de versión a la vista: el foco no se devuelve hasta que se cierre.
  hayConfirmacion: boolean;
}

export type DestinoDelFoco = "version" | "guardar";

// Lo que la página hace alrededor de guardar una versión: el estado del modal, el aviso de éxito, abrir la versión recién creada
// (la que guardó el modal o la que crearon restaurar, cotizar, retirar o convertir) y devolver el foco a su sitio cuando un
// diálogo se cierra.
export function useGuardadoDeLaPagina({
  proyecto,
  id,
  rev,
  alExpirar,
  cerrarGuardado,
  recargarVersiones,
  olvidarOfertas,
  elegirVersion,
  pedirVersion,
  hayConfirmacion,
}: Opciones) {
  const [exito, setExito] = useState<{ proyecto: string; texto: string } | null>(null);
  // El foco vuelve a su sitio cuando el diálogo ya se cerró y el `inert` se quitó (en un navegador real no se puede enfocar
  // dentro de un subárbol inert): quien cierra el diálogo anota adónde, y el efecto de abajo (tras cada commit) lo cumple.
  const devolverFoco = useRef<DestinoDelFoco | null>(null);
  const devolverFocoA = useCallback((destino: DestinoDelFoco) => {
    devolverFoco.current = destino;
  }, []);

  // El servidor creó la versión `nueva` (o ya estaba guardada): el borrador viejo ya no sirve y se abre la nueva, en la misma
  // pestaña. No vuelve a ofrecer retomar nada: lo que había se resolvió al guardar.
  const abrirGuardada = useCallback(
    async (nueva: string) => {
      cerrarGuardado();
      olvidarOfertas();
      await recargarVersiones(nueva);
      elegirVersion(nueva);
      devolverFoco.current = "version";
    },
    [cerrarGuardado, olvidarOfertas, recargarVersiones, elegirVersion],
  );
  // Se creó una versión nueva por una operación de la hoja (restaurar, cotizar, retirar, convertir): se dice qué pasó y se abre.
  const alCrearVersion = useCallback(
    async (nueva: string, texto: string) => {
      setExito({ proyecto, texto });
      await abrirGuardada(nueva);
    },
    [proyecto, abrirGuardada],
  );
  const alGuardada = useCallback(
    async (r: GuardadoRespuesta) => {
      await alCrearVersion(r.codigo, textoDeExito(r, r.proyecto));
    },
    [alCrearVersion],
  );
  const guardado = useGuardado({ id, rev, proyecto, alExpirar, alGuardada });
  const cancelarGuardado = guardado.cerrar;
  const cancelarYDevolverFoco = useCallback(() => {
    devolverFoco.current = "guardar";
    cancelarGuardado();
  }, [cancelarGuardado]);
  useEffect(() => {
    if (hayConfirmacion || guardado.abierto || devolverFoco.current === null) return;
    const destino = devolverFoco.current;
    devolverFoco.current = null;
    const boton = destino === "guardar" ? document.getElementById("hoja-guardar-version") : null;
    (boton ?? document.getElementById("hoja-version"))?.focus();
  });

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

  return {
    guardado,
    exito,
    quitarExito: () => setExito(null),
    cancelarYDevolverFoco,
    abrirDesdeElGuardado,
    alCrearVersion,
    devolverFocoA,
  };
}
