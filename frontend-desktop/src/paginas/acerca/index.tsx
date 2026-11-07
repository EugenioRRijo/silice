import { StructuredListBody, StructuredListCell, StructuredListRow, StructuredListWrapper, Tag } from "@carbon/react";
import { AvisoError } from "../../comun/AvisoError";
import { useCarga } from "../../comun/useCarga";
import type { Carga } from "../../comun/useCarga";
import { useAplicacion } from "../../shell/contexto";
import { AyudaDeSilice } from "../../comun/ayuda/AyudaDeSilice";
import "./acerca.scss";

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

const SIN_DATO: Record<string, string> = {
  "sin base": "Sin base",
  ilegible: "Ilegible",
  "sin revisiones": "Sin revisiones",
  "sin alembic_version": "Sin información de versión",
};

export function estadoDeLaBase(revision: string, ultima: string): string {
  const actual = numeroDeVersion(revision);
  const tope = numeroDeVersion(ultima);
  if (actual === null) return SIN_DATO[revision] ?? "Versión desconocida";
  if (tope === null) return `Versión ${actual}`;
  return actual === tope ? `Al día (versión ${actual})` : `Versión ${actual}; la última es la ${tope}`;
}

function Fila({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <StructuredListRow>
      <StructuredListCell noWrap>{rotulo}</StructuredListCell>
      <StructuredListCell className="silice-acerca__valor">{valor}</StructuredListCell>
    </StructuredListRow>
  );
}

// «Ayuda y acerca de Sílice» (RF-99; su h1 es el nombre de su pestaña en la Cuenta). Primero la ayuda (F7: «Empieza aquí», las
// guías por tarea y el glosario, `comun/ayuda/AyudaDeSilice.tsx`), que es texto y se lee aunque falle la lectura de la
// versión; después la versión, las revisiones de las dos bases, la carpeta de datos (solo quien administra) y los módulos
// instalados. Solo lectura.
export default function PaginaAcerca() {
  const { alExpirar } = useAplicacion();
  const carga = useCarga<Acerca>("/v1/acerca", alExpirar);

  return (
    <section className="silice-pagina" aria-labelledby="acerca-titulo">
      <h1 id="acerca-titulo" className="cds--type-heading-04">
        Ayuda y acerca de Sílice
      </h1>
      <AyudaDeSilice />
      <LaVersion carga={carga} />
    </section>
  );
}

function LaVersion({ carga }: { carga: Carga<Acerca> }) {
  if (carga.estado === "error" || carga.estado === "sin_permiso" || carga.estado === "no_disponible") {
    return <AvisoError error={carga.error} titulo="No se pudo cargar la información" />;
  }
  if (carga.estado !== "listo") {
    return (
      <p className="cds--type-body-compact-01" role="status">
        Cargando la versión de Sílice…
      </p>
    );
  }
  const d = carga.datos;
  return (
    <>
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
    </>
  );
}
