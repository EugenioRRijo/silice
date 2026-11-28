import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { ContextoDeDialogos } from "./ContextoDeDialogos";

// Lleva el foco a un elemento cuando ya no queda ningún diálogo abierto: mientras lo hay, la página es `inert` y en un
// navegador real no se puede enfocar nada dentro (como `useDialogoDeOperacion`).
export function useFocoAlCerrar(): (id: string) => void {
  const { abiertos } = useContext(ContextoDeDialogos);
  const destino = useRef<string | null>(null);
  const [pedido, setPedido] = useState(0);
  useEffect(() => {
    if (destino.current === null || abiertos > 0) return;
    const elemento = document.getElementById(destino.current);
    destino.current = null;
    elemento?.focus();
  }, [abiertos, pedido]);
  return useCallback((id: string) => {
    destino.current = id;
    setPedido((n) => n + 1);
  }, []);
}
