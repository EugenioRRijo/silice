import { InlineNotification } from "@carbon/react";
import { nombreDeCarpeta } from "../../shell/Selectores";
import type { ResumenDeCarpeta } from "./cliente";

// Prueba en vivo 2026-10-25: la carpeta abierta no tenia lista de precios vigente y solo se supo al guardar, despues
// de llenar unos 40 campos. Se dice arriba, al abrir. Solo con un resumen sano (sin error ni migracion pendiente).
// La lista de «Precios de la empresa» no sirve aqui: es de alcance empresa y `Catalogo.lista_vigente` no la cuenta.
export function AvisoSinLista({ carpeta }: { carpeta: ResumenDeCarpeta | null }) {
  if (!carpeta || carpeta.error !== null || carpeta.por_migrar || carpeta.lista_vigente !== null) return null;
  return (
    <InlineNotification
      kind="warning"
      lowContrast
      hideCloseButton
      role="status"
      title="Esta carpeta de trabajo no tiene lista de precios vigente"
      subtitle={`Puede componer la partida y ver su desglose, pero no podrá guardarla en la carpeta «${nombreDeCarpeta(carpeta.nombre)}». Para guardarla, elija en la barra superior otra carpeta de trabajo que tenga lista de precios, por ejemplo la de demostración, antes de empezar: al cambiar de carpeta se vacía el formulario.`}
    />
  );
}
