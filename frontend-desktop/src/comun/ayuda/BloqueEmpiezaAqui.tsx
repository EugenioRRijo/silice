import { EnlaceDeAyuda } from "./EnlaceDeAyuda";
import { PASOS_DE_EMPIEZA_AQUI } from "./empiezaAqui";
import type { PasoId } from "./empiezaAqui";
import { rutaDeTema } from "./temas";
import "./ayuda.scss";

// Un paso de «Empieza aquí»: qué hacer, en negrita, para qué y con qué control, y el enlace que lleva a hacerlo (solo si la
// cuenta puede usar su destino). Lo pintan igual la Vista general y la Ayuda.
export function PasoDeEmpiezaAqui({ id, acciones }: { id: PasoId; acciones: readonly string[] }) {
  const paso = PASOS_DE_EMPIEZA_AQUI[id];
  const enlace = paso.enlace !== undefined && (paso.enlace.accion === undefined || acciones.includes(paso.enlace.accion)) ? paso.enlace : null;
  return (
    <li>
      <strong>{paso.titulo}</strong>
      {`. ${paso.texto}`}
      {enlace !== null && (
        <>
          {" "}
          <EnlaceDeAyuda a={enlace.ruta}>{enlace.texto}</EnlaceDeAyuda>
        </>
      )}
    </li>
  );
}

// «Empieza aquí» en la Vista general (F7, tarea A4): va primero, porque en una instalación o una carpeta que se estrena no
// hay nada que bloquee, y desaparece cuando ya no hace falta (`pasosDeEmpiezaAqui`). No trae botones: la única acción de la
// pantalla sigue siendo la del estado vacío de la cartera («Nueva obra»), y el resto son enlaces a donde se hace.
export function EmpiezaAqui({ pasos, acciones }: { pasos: readonly PasoId[]; acciones: readonly string[] }) {
  if (pasos.length === 0) return null;
  return (
    <section className="silice-inicio__bloque silice-empieza-aqui" aria-labelledby="inicio-empieza-aqui">
      <h2 id="inicio-empieza-aqui" className="cds--type-heading-compact-02">
        Empieza aquí
      </h2>
      <ol className="silice-empieza-aqui__pasos cds--type-body-compact-01">
        {pasos.map((id) => (
          <PasoDeEmpiezaAqui key={id} id={id} acciones={acciones} />
        ))}
      </ol>
      <EnlaceDeAyuda a={rutaDeTema("empieza-aqui")}>Ver las guías y el glosario</EnlaceDeAyuda>
    </section>
  );
}
