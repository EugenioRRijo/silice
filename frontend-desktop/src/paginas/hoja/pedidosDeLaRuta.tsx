import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import type { PartidaCompuesta } from "../componer/ComponerPartida";

// Lo que otras pantallas piden al Presupuesto por el estado de la ruta (`navigate(..., { state })`). Lo atienden las dos
// pantallas del Presupuesto: la superficie (`index.tsx`, donde la partida llega a la fila de alta) y la vista por pestañas
// (`pestanas.tsx`, donde abre el diálogo de siempre).

// La partida que trae el estado de la ruta desde Componer (`{ agregarPartida: {codigo, descripcion, unidad} }`), o null si
// el estado no la trae o no tiene esa forma.
function partidaDelEstado(estado: unknown): PartidaCompuesta | null {
  if (typeof estado !== "object" || estado === null || !("agregarPartida" in estado)) return null;
  const p: unknown = estado.agregarPartida;
  if (typeof p !== "object" || p === null) return null;
  const { codigo, descripcion, unidad } = p as Record<string, unknown>;
  if (typeof codigo !== "string" || codigo.trim() === "") return null;
  return { codigo, descripcion: typeof descripcion === "string" ? descripcion : "", unidad: typeof unidad === "string" ? unidad : "" };
}

// Atiende «Agregar X al presupuesto» de Componer: lee la partida del estado de la ruta, la pasa a quien la pide y limpia el
// estado (volver a montar la página o recargarla no vuelve a abrir el diálogo). Va aparte porque solo existe dentro de un
// router: la Hoja también se monta sin él (pruebas de pestañas sueltas).
export function PedidoDesdeComponer({ alPedir }: { alPedir: (partida: PartidaCompuesta) => void }) {
  const ubicacion = useLocation();
  const navegar = useNavigate();
  useEffect(() => {
    const pedida = partidaDelEstado(ubicacion.state);
    if (pedida === null) return;
    void navegar(`${ubicacion.pathname}${ubicacion.search}`, { replace: true, state: null });
    alPedir(pedida);
  }, [ubicacion.state, ubicacion.pathname, ubicacion.search, navegar, alPedir]);
  return null;
}

// «Ver en el presupuesto» de Archivos y planos (`{ enfocarGrilla: true }`): lleva el foco a la grilla cuando llega la vista.
// Lee el pedido y limpia el estado de la ruta, como `PedidoDesdeComponer`.
export function PedidoDeFocoEnLaGrilla({ alPedir }: { alPedir: () => void }) {
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const pedido = typeof ubicacion.state === "object" && ubicacion.state !== null && "enfocarGrilla" in ubicacion.state;
  useEffect(() => {
    if (!pedido) return;
    void navegar(`${ubicacion.pathname}${ubicacion.search}`, { replace: true, state: null });
    alPedir();
  }, [pedido, ubicacion.pathname, ubicacion.search, navegar, alPedir]);
  return null;
}
