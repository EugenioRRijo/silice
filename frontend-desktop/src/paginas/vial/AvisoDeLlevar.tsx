import { InlineNotification } from "../../comun/carbonEs";
import type { JSX, ReactNode } from "react";
import { mensajeDeError } from "../../comun/errores";

interface Props {
  error: unknown;
  titulo: string;
  alCerrar: () => void;
}

// Un código entre comillas angulares («C-000.000.001»): mayúsculas, cifras, punto, guion y barra, sin espacios. Los nombres
// de lista («Lista de referencia…») no encajan y se parten con normalidad.
const CODIGO = /(«[A-Z0-9][A-Z0-9.\-/]*»)/g;
const MARCA_QUE_HACER = "Qué hacer:";

// Cada código en un trozo que no se parte (antes se cortaba «C-» / «000.000.001» al borde de la línea).
function conCodigos(texto: string): ReactNode[] {
  return texto.split(CODIGO).map((trozo, i) =>
    i % 2 === 1 ? (
      <span key={i} className="silice-codigo-sin-partir">
        {trozo}
      </span>
    ) : (
      trozo
    ),
  );
}

// «Encabezado: a; b; c.» con tres o más elementos se lee como lista; si no, se queda como párrafo.
function Frase({ texto }: { texto: string }): JSX.Element {
  const i = texto.indexOf(": ");
  if (i > 0) {
    const elementos = texto.slice(i + 2).replace(/\.$/, "").split("; ");
    if (elementos.length >= 3) {
      return (
        <>
          <p>{conCodigos(`${texto.slice(0, i)}:`)}</p>
          <ul className="silice-llevar__lista">
            {elementos.map((e, k) => (
              <li key={k}>{conCodigos(e)}</li>
            ))}
          </ul>
        </>
      );
    }
  }
  return <p>{conCodigos(texto)}</p>;
}

// El aviso de «No se llevó nada al presupuesto». El texto es el del servidor, sin cambios (tiene pruebas): aquí solo se
// presenta. Si trae «Qué hacer:» ese bloque sube, resaltado, justo después de la primera frase; las frases siguientes van en
// párrafos y las enumeraciones de partidas en listas. Un aviso corto, sin eso, es un solo párrafo con el texto tal cual.
export function AvisoDeLlevar({ error, titulo, alCerrar }: Props): JSX.Element {
  const texto = mensajeDeError(error);
  const posicion = texto.indexOf(MARCA_QUE_HACER);
  const antes = (posicion >= 0 ? texto.slice(0, posicion) : texto).trim();
  const queHacer = posicion >= 0 ? texto.slice(posicion + MARCA_QUE_HACER.length).trim() : null;
  const frases = antes.split(/(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ«])/);
  const estructurado = queHacer !== null || frases.some((f) => /: .+; .+; /.test(f));
  const cuerpo = estructurado ? (
    <div className="silice-llevar">
      {frases.slice(0, 1).map((f, i) => (
        <Frase key={i} texto={f} />
      ))}
      {queHacer !== null && (
        <p className="silice-llevar__que-hacer">
          <strong>{MARCA_QUE_HACER}</strong> {conCodigos(queHacer)}
        </p>
      )}
      {frases.slice(1).map((f, i) => (
        <Frase key={i} texto={f} />
      ))}
    </div>
  ) : (
    <div className="silice-llevar">
      <p>{conCodigos(texto)}</p>
    </div>
  );
  return (
    <InlineNotification
      kind="error"
      role="alert"
      title={titulo}
      lowContrast
      onClose={() => {
        alCerrar();
        return false; // el padre decide si desaparece
      }}
    >
      {cuerpo}
    </InlineNotification>
  );
}
