import { StructuredListBody, StructuredListCell, StructuredListRow, StructuredListWrapper, Tag } from "@carbon/react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";

interface Acerca {
  version: string;
  semver: string;
  revision_instalacion: string;
  head_instalacion: string;
  revision_caso: string;
  head_caso: string;
  carpeta_datos: string | null;
  modulos: { nombre: string; instalado: boolean }[];
}

// «ins_0003_auditoria_libro» es el nombre de una migracion: a la persona se le dice si la base esta al dia o en que
// version va (VB-20).
function numeroDeVersion(revision: string): number | null {
  const m = /^[a-z]+_(\d+)/.exec(revision);
  return m ? Number(m[1]) : null;
}

export function estadoDeLaBase(revision: string, ultima: string): string {
  const actual = numeroDeVersion(revision);
  const tope = numeroDeVersion(ultima);
  if (actual === null || tope === null) return revision.charAt(0).toUpperCase() + revision.slice(1);
  return actual === tope ? `Al día (versión ${actual})` : `Versión ${actual}; la última es la ${tope}`;
}

function Fila({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <StructuredListRow>
      <StructuredListCell noWrap>{rotulo}</StructuredListCell>
      <StructuredListCell>{valor}</StructuredListCell>
    </StructuredListRow>
  );
}

// «Acerca de Sílice» (RF-99): versión, revisiones de las dos bases, carpeta de datos (solo quien administra) y
// módulos instalados. Solo lectura.
export default function PaginaAcerca() {
  const { alExpirar } = useAplicacion();
  const carga = useCarga<Acerca>("/v1/acerca", alExpirar);

  if (carga.estado === "error" || carga.estado === "sin_permiso" || carga.estado === "no_disponible") {
    return (
      <section className="silice-pagina" aria-labelledby="acerca-titulo">
        <h1 id="acerca-titulo" className="cds--type-heading-04">
          Acerca de Sílice
        </h1>
        <AvisoError error={carga.error} titulo="No se pudo cargar la información" />
      </section>
    );
  }
  if (carga.estado !== "listo") return <EsqueletoPagina titulo="Acerca de Sílice" />;
  const d = carga.datos;

  return (
    <section className="silice-pagina" aria-labelledby="acerca-titulo">
      <h1 id="acerca-titulo" className="cds--type-heading-04">
        Acerca de Sílice
      </h1>
      <h2 className="cds--type-heading-compact-02">Sílice {d.semver}</h2>
      <p className="cds--type-body-compact-01">Versión: {d.version}</p>
      <StructuredListWrapper isCondensed aria-label="Bases y carpeta de datos">
        <StructuredListBody>
          <Fila rotulo="Base de la instalación" valor={estadoDeLaBase(d.revision_instalacion, d.head_instalacion)} />
          <Fila rotulo="Base del caso abierto" valor={estadoDeLaBase(d.revision_caso, d.head_caso)} />
          {d.carpeta_datos !== null && <Fila rotulo="Carpeta de datos" valor={d.carpeta_datos} />}
        </StructuredListBody>
      </StructuredListWrapper>
      <h3 className="cds--type-heading-compact-02">Módulos</h3>
      <StructuredListWrapper isCondensed aria-label="Módulos">
        <StructuredListBody>
          {d.modulos.map((m) => (
            <StructuredListRow key={m.nombre}>
              <StructuredListCell>{m.nombre}</StructuredListCell>
              <StructuredListCell>
                <Tag size="sm" type={m.instalado ? "green" : "gray"}>
                  {m.instalado ? "instalado" : "no instalado"}
                </Tag>
              </StructuredListCell>
            </StructuredListRow>
          ))}
        </StructuredListBody>
      </StructuredListWrapper>
      <p className="cds--type-label-01">Sílice es software propietario; las licencias de terceros están en LICENCIAS.</p>
    </section>
  );
}
