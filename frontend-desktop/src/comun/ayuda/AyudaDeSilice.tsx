import { Fragment, useEffect } from "react";
import { useLocation } from "react-router";
import { useAplicacion } from "../../shell/contexto";
import { EnlaceDeAyuda } from "./EnlaceDeAyuda";
import { PASOS_DE_EMPIEZA_AQUI, PRIMERA_VEZ, TITULO_DEL_PAPEL } from "./empiezaAqui";
import type { Papel, PasoId } from "./empiezaAqui";
import { PasoDeEmpiezaAqui } from "./BloqueEmpiezaAqui";
import { idDeTema, rutaDeTema } from "./temas";
import { GLOSARIO, GUIAS, terminoPorId } from "./textos";
import "./ayuda.scss";

const PAPELES: readonly Papel[] = ["administra", "arma", "revisa"];
const PASOS = Object.keys(PASOS_DE_EMPIEZA_AQUI) as PasoId[];

const INDICE: readonly { tema: string; titulo: string }[] = [
  { tema: "empieza-aqui", titulo: "Empieza aquí" },
  { tema: "guias", titulo: "Guías por tarea" },
  { tema: "glosario", titulo: "Glosario" },
];

// Con `?tema=` el foco va a esa parte (temas.ts). El marco no mueve el foco al h1 cuando solo cambia la consulta, ni en la
// primera carga, así que no compiten. `key` hace que volver a pulsar el mismo enlace del índice vuelva a llevar el foco.
function useFocoAlTema() {
  const { search, key } = useLocation();
  const tema = new URLSearchParams(search).get("tema");
  useEffect(() => {
    if (tema === null) return;
    const destino = document.getElementById(idDeTema(tema));
    if (destino === null) return;
    destino.focus({ preventScroll: true });
    destino.scrollIntoView?.({ block: "start" });
  }, [tema, key]);
}

function Encabezado({ tema, children }: { tema: string; children: string }) {
  return (
    <h2 id={idDeTema(tema)} tabIndex={-1} className="cds--type-heading-compact-02">
      {children}
    </h2>
  );
}

// La ayuda de Sílice (F7, tareas A2 a A4) en la Cuenta, sección «Ayuda y acerca de Sílice»: un índice, «Empieza aquí» (la
// primera vez y lo primero de cada papel), las guías por tarea y el glosario. Es texto: no pide nada al servidor, así que se
// lee aunque la información de la versión no cargue. Los enlaces a la Cuenta solo se ofrecen a quien puede usarla.
export function AyudaDeSilice() {
  const { sesion } = useAplicacion();
  useFocoAlTema();
  return (
    <div className="silice-ayuda">
      <nav aria-label="En esta ayuda" className="silice-ayuda__indice cds--type-body-compact-01">
        {INDICE.map((i) => (
          <EnlaceDeAyuda key={i.tema} a={rutaDeTema(i.tema)}>
            {i.titulo}
          </EnlaceDeAyuda>
        ))}
      </nav>

      <section aria-labelledby={idDeTema("empieza-aqui")} className="silice-ayuda__parte">
        <Encabezado tema="empieza-aqui">Empieza aquí</Encabezado>
        <h3 className="cds--type-heading-compact-01">{PRIMERA_VEZ.titulo}</h3>
        {PRIMERA_VEZ.parrafos.map((p) => (
          <p key={p} className="cds--type-body-compact-01">
            {p}
          </p>
        ))}
        {PAPELES.map((papel) => (
          <Fragment key={papel}>
            <h3 className="cds--type-heading-compact-01">{TITULO_DEL_PAPEL[papel]}</h3>
            <ol className="silice-empieza-aqui__pasos cds--type-body-compact-01">
              {PASOS.filter((id) => PASOS_DE_EMPIEZA_AQUI[id].papel === papel).map((id) => (
                <PasoDeEmpiezaAqui key={id} id={id} acciones={sesion.acciones} />
              ))}
            </ol>
          </Fragment>
        ))}
      </section>

      <section aria-labelledby={idDeTema("guias")} className="silice-ayuda__parte">
        <Encabezado tema="guias">Guías por tarea</Encabezado>
        {GUIAS.map((g) => (
          <article key={g.id} aria-labelledby={idDeTema(`guia-${g.id}`)} className="silice-ayuda__guia">
            <h3 id={idDeTema(`guia-${g.id}`)} tabIndex={-1} className="cds--type-heading-compact-01">
              {g.titulo}
            </h3>
            <p className="silice-ayuda__quien cds--type-body-compact-01">{g.quien}</p>
            {g.partes.map((parte) => (
              <Fragment key={parte.titulo}>
                <h4 className="cds--type-body-compact-01 silice-ayuda__parte-de-guia">{parte.titulo}</h4>
                <ol className="silice-ayuda__pasos cds--type-body-compact-01">
                  {parte.pasos.map((paso) => (
                    <li key={paso}>{paso}</li>
                  ))}
                </ol>
              </Fragment>
            ))}
            <p className="cds--type-body-compact-01">
              {"En el glosario: "}
              {g.terminos.map((id, i) => (
                <Fragment key={id}>
                  {i > 0 && ", "}
                  <EnlaceDeAyuda a={rutaDeTema(`glosario-${id}`)}>{terminoPorId(id).termino}</EnlaceDeAyuda>
                </Fragment>
              ))}
            </p>
          </article>
        ))}
      </section>

      <section aria-labelledby={idDeTema("glosario")} className="silice-ayuda__parte">
        <Encabezado tema="glosario">Glosario</Encabezado>
        <dl className="silice-ayuda__glosario cds--type-body-compact-01">
          {GLOSARIO.map((t) => (
            <Fragment key={t.id}>
              <dt id={idDeTema(`glosario-${t.id}`)} tabIndex={-1}>
                {t.termino}
              </dt>
              <dd>{t.definicion}</dd>
            </Fragment>
          ))}
        </dl>
      </section>
    </div>
  );
}
