import { useEffect } from "react";

// Formularios con cambios sin guardar que viven en el navegador (diseno de modulos §12.5): si la persona sale de la
// pantalla por un control de Silice (el sidebar, la barra, un boton de la mesa), `confirmarSalida` (salida.ts) le
// pregunta antes. El borrador de la Hoja vive en el servidor y se retoma: no se registra. Solo en memoria (RT-9).
// Cada registro es una clave propia: dos formularios de la misma pantalla son dos registros, y la pantalla sale una vez.
const registro = new Map<symbol, string>();

// `id` es el id de la pantalla en rutas.ts (su titulo es el que lee el dialogo). Se quita al limpiarse o al desmontar.
export function useFormularioSucio(id: string, sucio: boolean): void {
  useEffect(() => {
    if (!sucio) return;
    const clave = Symbol(id);
    registro.set(clave, id);
    return () => {
      registro.delete(clave);
    };
  }, [id, sucio]);
}

// Las pantallas con algun formulario sucio, en el orden en que se ensuciaron, sin repetir.
export function formulariosSucios(): string[] {
  return [...new Set(registro.values())];
}

// «Salir y descartar»: lo que habia se da por perdido.
export function olvidarFormularios(): void {
  registro.clear();
}
