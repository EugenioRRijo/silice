import type { JSX } from "react";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { celdasResumidas } from "./logicaDelLibro";
import type { AvisoDePrecio } from "./logicaDelLibro";
import { QueHacer } from "../../comun/QueHacer";
import { guiaDeAlerta } from "../../comun/catalogoQueHacer";
import type { CatalogoQueHacer } from "../../comun/catalogoQueHacer";

// «Alertas de precio» (B2, ficha-b2 §1.5 y S4): avisan de precios que conviene confirmar (sin fuente, lejos de la base de la
// empresa, cambiados frente a otra versión, distintos en bolívares). No son errores del libro, así que **no** llevan color de
// gravedad ni ícono de severidad: las dos semánticas van separadas. El mensaje es el del servidor, tal cual.
export function AlertasDePrecio({
  avisos,
  catalogo,
}: {
  avisos: readonly AvisoDePrecio[];
  catalogo: CatalogoQueHacer | null;
}): JSX.Element | null {
  if (avisos.length === 0) return null;
  return (
    <section aria-labelledby="libro-alertas">
      <h3 id="libro-alertas" className="cds--type-heading-compact-01">{`Alertas de precio (${avisos.length})`}</h3>
      <p className="cds--type-body-compact-01">
        No son errores del libro: son precios que conviene confirmar con quien lo hizo.
      </p>
      <ul className="silice-libro__lista" aria-label="Alertas de precio">
        {avisos.map((aviso) => {
          const guia = catalogo ? guiaDeAlerta(catalogo, aviso.tipo) : null;
          return (
            <li key={`${aviso.tipo}-${aviso.mensaje}`} className="silice-libro__tarjeta">
              <p className="silice-libro__encabezado cds--type-label-01">
                <strong>{guia?.titulo ?? aviso.tipo}</strong>
                {aviso.cantidad > 1 && (
                  <>
                    <span aria-hidden="true"> · </span>
                    <span className="silice-cifra">{`${formatoEsVe(String(aviso.cantidad))} precios`}</span>
                  </>
                )}
                <span aria-hidden="true"> · </span>
                <span className="silice-codigo">{celdasResumidas(aviso.codigos)}</span>
              </p>
              <p className="cds--type-body-compact-01">{aviso.mensaje}</p>
              {guia && <QueHacer guia={guia} />}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
