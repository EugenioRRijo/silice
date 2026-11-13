import { Button } from "@carbon/react";
import type { JSX } from "react";
import { CampoTexto } from "../../comun/CampoTexto";
import { cifrasEnTextoEsVe } from "../../indicadores/formatoEsVe";
import type { CampoDeParametro, ClaveDeParametro, ParametrosDeTexto } from "./cliente";

// Lo que antecede a un parámetro mal escrito en el aviso del servidor (`aplicacion/componer_parametros.py`, PREFIJO) y el
// nombre corto de cada campo (NOMBRES): con ellos se marca el campo que falla.
const PREFIJO = "Parámetros del precio unitario.";
const NOMBRES: Record<ClaveDeParametro, string> = {
  fcas: "FCAS",
  bono_alimentacion: "Bono de alimentación",
  administracion: "Administración",
  utilidad: "Utilidad",
};

export const NOTA_DE_LA_OBRA =
  "Son los de «Ajustes de costo» de esta obra. Cambiarlos aquí solo cambia este cálculo: el presupuesto sigue con los de la obra y la partida no los guarda.";
export const NOTA_DE_OMISION =
  "Son los de omisión de Sílice: no hay una obra abierta. Cambiarlos aquí solo cambia este cálculo y la partida no los guarda.";
export const SIN_PARAMETROS = "No se pudieron leer los parámetros: el desglose usa los de omisión de Sílice.";

export type OrigenDeParametros = "obra" | "omision";

// Los valores de unos campos, por su clave.
export function valoresDe(campos: CampoDeParametro[]): ParametrosDeTexto {
  return Object.fromEntries(campos.map((c) => [c.clave, c.valor])) as ParametrosDeTexto;
}

// El motivo del aviso del servidor si es de ese campo («Parámetros del precio unitario. FCAS: <motivo>»), o null.
function motivoDe(aviso: string | null, clave: ClaveDeParametro): string | null {
  const inicio = `${PREFIJO} ${NOMBRES[clave]}: `;
  return aviso !== null && aviso.startsWith(inicio) ? aviso.slice(inicio.length) : null;
}

interface Props {
  // Los campos propuestos (de la obra o de omisión), o null mientras se leen.
  campos: CampoDeParametro[] | null;
  origen: OrigenDeParametros;
  // Lo escrito en cada campo (null mientras se leen).
  valores: ParametrosDeTexto | null;
  // No se pudieron leer: el servidor calcula con los de omisión.
  fallo: boolean;
  // El aviso de la última evaluación: si es de un parámetro, ese campo se marca con él.
  aviso: string | null;
  alCambiar: (clave: ClaveDeParametro, texto: string) => void;
  alRestaurar: () => void;
  // h2 en la pantalla, h3 en el panel de «Agregar partida».
  nivel: 2 | 3;
}

// RF-200 (ola 2, 2026-11-13; bitácora `2026-11-13-ola2-front.md` §6, opción C): los cuatro parámetros con que el servidor
// calcula el precio unitario del desglose en vivo. Se proponen los de la obra abierta (su «Ajustes de costo») o, sin obra,
// los de omisión; se pueden cambiar para ensayar, sin escribir en la obra ni en la partida (como en S10, Presto y Lulo, los
// indirectos son del presupuesto, no del APU del catálogo). La interfaz no calcula: manda lo escrito tal cual.
export function ParametrosDelPrecio({ campos, origen, valores, fallo, aviso, alCambiar, alRestaurar, nivel }: Props): JSX.Element {
  const Titulo = `h${nivel}` as const;
  const cambiados = campos !== null && valores !== null && campos.some((c) => valores[c.clave as ClaveDeParametro] !== c.valor);
  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-parametros">
      <Titulo id="componer-parametros" className="cds--type-heading-compact-02">
        Parámetros del precio unitario
      </Titulo>
      {fallo ? (
        <p className="silice-componer__nota cds--type-body-compact-01">{SIN_PARAMETROS}</p>
      ) : (
        campos !== null &&
        valores !== null && (
          <>
            <p className="silice-componer__nota cds--type-body-compact-01">{origen === "obra" ? NOTA_DE_LA_OBRA : NOTA_DE_OMISION}</p>
            {campos.map((c) => {
              const clave = c.clave as ClaveDeParametro;
              const motivo = motivoDe(aviso, clave);
              return (
                <CampoTexto
                  key={clave}
                  id={`componer-parametro-${clave}`}
                  size="sm"
                  labelText={cifrasEnTextoEsVe(c.rotulo)}
                  value={valores[clave] ?? ""}
                  invalid={motivo !== null}
                  invalidText={motivo ?? undefined}
                  // Carbon no une el mensaje al campo: se une a mano, como en `AgregarPartida` y `LineaDelApu`.
                  {...(motivo !== null ? { "aria-describedby": `componer-parametro-${clave}-error-msg` } : {})}
                  autoComplete="off"
                  onChange={(e) => alCambiar(clave, e.target.value)}
                />
              );
            })}
            {cambiados && (
              <Button kind="ghost" size="sm" onClick={alRestaurar}>
                {origen === "obra" ? "Volver a los de la obra" : "Volver a los de omisión"}
              </Button>
            )}
          </>
        )
      )}
    </section>
  );
}
