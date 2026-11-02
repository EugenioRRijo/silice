// Un BroadcastChannel de mentira para las pruebas de la vigilancia de pestañas (marco/otraPestana): cada `canal()` es
// una pestaña; lo que una publica le llega, en el acto, a todas las demas del mismo bus y nunca a ella misma (como el
// de verdad, salvo que este entrega sin esperar a la cola de eventos).
interface CanalFalso {
  onmessage: ((evento: MessageEvent) => void) | null;
  postMessage(mensaje: unknown): void;
  close(): void;
}

export function busDePestanas(): { canal: () => CanalFalso } {
  const abiertos = new Set<CanalFalso>();
  return {
    canal() {
      const propio: CanalFalso = {
        onmessage: null,
        postMessage(mensaje: unknown) {
          for (const otro of abiertos) {
            if (otro !== propio) otro.onmessage?.(new MessageEvent("message", { data: mensaje }));
          }
        },
        close() {
          abiertos.delete(propio);
        },
      };
      abiertos.add(propio);
      return propio;
    },
  };
}
