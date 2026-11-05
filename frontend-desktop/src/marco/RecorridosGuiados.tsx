import { Button } from "@carbon/react";
import { useAplicacion } from "../shell/contexto";
import { useNavegarSeguro } from "../shell/navegarSeguro";
import { RECORRIDO_AUDITAR, iniciarRecorrido } from "../shell/recorrido";
import type { Recorrido } from "../shell/recorrido";
import { paginaPorId, usable } from "../shell/rutas";
import { rutaOPendientes } from "./espacios";

// Los recorridos guiados que hay (hoy uno), en el orden en que se ofrecen.
const RECORRIDOS: readonly Recorrido[] = [RECORRIDO_AUDITAR];

// Dónde se empieza un recorrido guiado (plan F6, T6; diseño visual 2.4-E): la Ayuda de la Cuenta ofrece cada uno, y el botón
// lo pone en curso y lleva a la pantalla de su primer paso. Solo se ofrece el que la cuenta puede abrir: si la primera
// pantalla no es suya, el recorrido no se ofrece (no se promete lo que no se puede hacer). Si hay cambios sin guardar,
// pregunta antes de irse, como cualquier enlace.
export function RecorridosGuiados() {
  const { sesion, modulosApagados } = useAplicacion();
  const navegarSeguro = useNavegarSeguro();
  const posibles = RECORRIDOS.filter((r) => {
    const primera = r.pasos[0] === undefined ? undefined : paginaPorId(r.pasos[0].pagina);
    return primera !== undefined && usable(primera, sesion.acciones, sesion.modo_entrega, modulosApagados ?? []);
  });
  if (posibles.length === 0) return null;

  async function empezar(recorrido: Recorrido) {
    const primero = recorrido.pasos[0];
    if (primero === undefined) return;
    // Primero se va (puede preguntar por cambios sin guardar); el recorrido solo se pone en curso si la persona sigue.
    if (await navegarSeguro(rutaOPendientes(primero.pagina))) iniciarRecorrido(recorrido);
  }

  return (
    <section aria-labelledby="ayuda-recorridos" className="silice-cuenta-recorridos">
      <h2 id="ayuda-recorridos" className="cds--type-heading-compact-02">
        Recorridos guiados
      </h2>
      <p className="cds--type-body-compact-01">
        Un recorrido lo lleva paso a paso por las pantallas de una tarea y le dice cuándo la terminó.
      </p>
      <div className="silice-cuenta-recorridos__lista">
        {posibles.map((r) => (
          <Button key={r.titulo} kind="tertiary" size="md" onClick={() => void empezar(r)}>
            {`Empezar el recorrido «${r.titulo}»`}
          </Button>
        ))}
      </div>
    </section>
  );
}
