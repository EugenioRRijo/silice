import { useCallback, useState } from "react";
import { PESTANAS, pestanaInicial, pestanasVisibles } from "./logica";
import type { PestanaDef, PestanaId } from "./logica";
import type { EstadoBorrador } from "./useBorrador";

// Por qué existe (Tarea 4 del plan F4): la pestaña del Presupuesto vive en el proveedor de la Hoja, no en el cuerpo, para que
// pasar a Archivos y planos o a Versiones y volver no la pierda. Aparte del proveedor, que ya es largo, porque es un estado
// con su propia regla: la pestaña con que abre cada obra, y «Espacio y metrajes», que solo se ve si la obra tiene espacio o
// se pidió describirlo (pregunta 3 del plan; la pide Archivos y planos, Tarea 11), y nunca con la especialidad
// «edificación» apagada en la instalación (plan vial, Tarea 19). Lo usa solo `ProveedorDeLaHoja`.
export interface PestanaDeLaHoja {
  // La pestaña abierta, ya resuelta: si la elegida dejó de existir (la obra ya no tiene espacio, o edificación está
  // apagada), vale «Partidas».
  pestana: PestanaId;
  irAPestana: (id: PestanaId) => void;
  // Las pestañas que se pintan, con la regla de arriba ya aplicada (todas mientras no hay borrador).
  visibles: readonly PestanaDef[];
  // Se pidió describir el espacio a mano: «Espacio y metrajes» se ve mientras la obra esté abierta.
  espacioPedido: boolean;
  pedirEspacio: () => void;
}

export function usePestanaDeLaHoja(proyecto: string, estado: EstadoBorrador, edificacionApagada = false): PestanaDeLaHoja {
  const [elegida, setElegida] = useState<PestanaId>("partidas");
  // La pestaña con que abre la obra se fija una vez, con su primer borrador; cambiar de versión no mueve a la persona de
  // la pestaña en que está. Ajuste durante el render (react.dev, «You might not need an effect»).
  const [fijadaPara, setFijadaPara] = useState<string | null>(null);
  const [pedidoPor, setPedidoPor] = useState<string | null>(null);
  if (estado.estado === "listo" && fijadaPara !== proyecto) {
    setFijadaPara(proyecto);
    setElegida(pestanaInicial(estado.borrador.resumen));
  }
  const irAPestana = useCallback((id: PestanaId) => setElegida(id), []);
  const pedirEspacio = useCallback(() => setPedidoPor(proyecto), [proyecto]);
  const espacioPedido = pedidoPor === proyecto;
  const visibles =
    estado.estado === "listo" ? pestanasVisibles(estado.borrador.resumen, espacioPedido, edificacionApagada) : PESTANAS;
  const pestana = visibles.some((p) => p.id === elegida) ? elegida : "partidas";
  return { pestana, irAPestana, visibles, espacioPedido, pedirEspacio };
}
