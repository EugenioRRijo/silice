import { Fragment } from "react";
import type { JSX, ReactNode } from "react";
import type { CausaRaizRespuesta, HallazgoLibroRespuesta } from "../../api/tipos";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { IconoDeSeveridad } from "../../severidad/IconoDeSeveridad";
import { estiloDeSeveridad, normalizarSeveridad } from "../../severidad/severidad";
import type { EstiloDeSeveridad } from "../../severidad/severidad";
import { estiloDeHallazgo } from "../../visor/halos";
import {
  causasMultiples,
  celdasResumidas,
  fraseDeLaCausa,
  hallazgosSueltos,
  noAplicables,
  textoDeCasos,
} from "./logicaDelLibro";
import type { AuditoriaDelLibro, CuentaDeHallazgos } from "./logicaDelLibro";
import { QueHacer } from "../../comun/QueHacer";
import { guiaDeRegla } from "../../comun/catalogoQueHacer";
import type { CatalogoQueHacer } from "../../comun/catalogoQueHacer";

// «Qué se encontró» (B2, ficha-b2 §1.5 y §2): primero las causas raíz con varios casos (corregir una arregla todos), después
// los hallazgos uno por uno, de lo más a lo menos grave, y aparte, plegados, los avisos de regla no aplicable. Cada uno dice
// su gravedad con palabra e ícono y lleva su «Qué hacer» a pedido. Los montos y los textos son los del servidor.

function Separados({ partes }: { partes: ReactNode[] }): JSX.Element {
  const presentes = partes.filter((p) => p !== null && p !== false && p !== undefined && p !== "");
  return (
    <>
      {presentes.map((parte, i) => (
        <Fragment key={i}>
          {i > 0 && <span aria-hidden="true"> · </span>}
          {parte}
        </Fragment>
      ))}
    </>
  );
}

function Gravedad({ estilo }: { estilo: EstiloDeSeveridad }): JSX.Element {
  return (
    <span className="silice-libro__gravedad" style={{ ["--halo-color" as string]: `var(${estilo.token})` }}>
      <IconoDeSeveridad nombre={estilo.icono} size={16} className="silice-libro__icono" />
    </span>
  );
}

function NombreDeRegla({ codigo, nombre }: { codigo: string; nombre?: string | undefined }): JSX.Element {
  const limpio = nombre?.trim();
  return limpio ? (
    <span>
      {limpio} (<span className="silice-codigo">{codigo}</span>)
    </span>
  ) : (
    <span className="silice-codigo">{codigo}</span>
  );
}

function TarjetaDeCausa({ causa, catalogo }: { causa: CausaRaizRespuesta; catalogo: CatalogoQueHacer | null }): JSX.Element {
  const estilo = estiloDeSeveridad(normalizarSeveridad(causa.severidad));
  return (
    <li className="silice-libro__tarjeta">
      <p className="silice-libro__encabezado cds--type-label-01">
        <Gravedad estilo={estilo} />
        <Separados
          partes={[
            estilo.texto,
            <span key="casos" className="silice-cifra">
              {textoDeCasos(causa.ocurrencias)}
            </span>,
            <NombreDeRegla key="regla" codigo={causa.codigo} nombre={causa.nombre_regla} />,
          ]}
        />
      </p>
      <p className="cds--type-body-compact-01">{fraseDeLaCausa(causa.descripcion)}</p>
      {causa.observado && causa.esperado && (
        <p className="silice-libro__traza cds--type-label-01 silice-cifra">
          {`Encontrado ${formatoEsVe(causa.observado)} · esperado ${formatoEsVe(causa.esperado)}`}
        </p>
      )}
      {causa.celdas && causa.celdas.length > 0 && (
        <p className="silice-libro__celdas cds--type-label-01">{`Celdas: ${celdasResumidas(causa.celdas)}`}</p>
      )}
      {catalogo && <QueHacer guia={guiaDeRegla(catalogo, causa.codigo)} />}
    </li>
  );
}

function TarjetaDeHallazgo({
  hallazgo,
  catalogo,
}: {
  hallazgo: HallazgoLibroRespuesta;
  catalogo: CatalogoQueHacer | null;
}): JSX.Element {
  const estilo = estiloDeHallazgo(hallazgo);
  return (
    <li className="silice-libro__tarjeta">
      <p className="silice-libro__encabezado cds--type-label-01">
        <Gravedad estilo={estilo} />
        <Separados
          partes={[
            hallazgo.celda ? <span className="silice-codigo">{hallazgo.celda}</span> : "Sin celda",
            estilo.texto,
            <NombreDeRegla key="regla" codigo={hallazgo.codigo} nombre={hallazgo.nombre_regla} />,
            hallazgo.impacto !== null && (
              <span className="silice-cifra">
                <span className="silice-oculto">Impacto </span>
                {formatoEsVe(hallazgo.impacto)}
              </span>
            ),
          ]}
        />
      </p>
      <p className="cds--type-body-compact-01">{hallazgo.descripcion}</p>
      {catalogo && <QueHacer guia={guiaDeRegla(catalogo, hallazgo.codigo)} />}
    </li>
  );
}

interface Props {
  auditoria: AuditoriaDelLibro;
  cuenta: CuentaDeHallazgos;
  catalogo: CatalogoQueHacer | null;
}

export function ProblemasDelLibro({ auditoria, cuenta, catalogo }: Props): JSX.Element {
  const causas = causasMultiples(auditoria);
  const sueltos = hallazgosSueltos(auditoria);
  const fuera = noAplicables(auditoria);
  return (
    <div className="silice-libro__problemas">
      {cuenta.total === 0 && (
        <p className="cds--type-body-compact-01">Sílice revisó el libro y no halló nada que corregir.</p>
      )}

      {causas.length > 0 && (
        <section aria-labelledby="libro-causas">
          <h3 id="libro-causas" className="cds--type-heading-compact-01">{`Por causa raíz (${causas.length})`}</h3>
          <p className="cds--type-body-compact-01">
            Corregir una causa arregla todos sus casos.
          </p>
          <ul className="silice-libro__lista" aria-label="Causas raíz">
            {causas.map((causa) => (
              <TarjetaDeCausa key={`${causa.codigo}-${causa.indices[0]}`} causa={causa} catalogo={catalogo} />
            ))}
          </ul>
        </section>
      )}

      {sueltos.length > 0 && (
        <section aria-labelledby="libro-sueltos">
          <h3 id="libro-sueltos" className="cds--type-heading-compact-01">{`Uno por uno (${sueltos.length})`}</h3>
          <ul className="silice-libro__lista" aria-label="Hallazgos uno por uno">
            {sueltos.map(({ indice, hallazgo }) => (
              <TarjetaDeHallazgo key={indice} hallazgo={hallazgo} catalogo={catalogo} />
            ))}
          </ul>
        </section>
      )}

      {fuera.length > 0 && (
        <details className="silice-libro__plegado">
          <summary>{`Reglas que no aplicaron a este libro (${fuera.length})`}</summary>
          <p className="cds--type-body-compact-01">
            No son errores: la regla no tenía nada que revisar en este libro.
          </p>
          <ul className="silice-libro__lista">
            {fuera.map((h, i) => (
              <li key={i} className="silice-libro__tarjeta">
                <p className="silice-libro__encabezado cds--type-label-01">
                  <NombreDeRegla codigo={h.codigo} nombre={h.nombre_regla} />
                </p>
                <p className="cds--type-body-compact-01">{h.descripcion}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
