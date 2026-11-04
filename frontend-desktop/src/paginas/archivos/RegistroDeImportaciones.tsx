import { Button } from "@carbon/react";
import { AvisoError } from "../../comun/AvisoError";
import { PanelLateral } from "../../comun/PanelLateral";
import { TablaDensa } from "../../comun/TablaDensa";
import type { FilaDensa } from "../../comun/TablaDensa";
import { COLUMNAS_DEL_REGISTRO, filasDeImportaciones } from "./logica";
import type { ImportacionDeObra } from "./logica";
import type { CargaDelRegistro } from "./useRegistro";
import { TEXTOS } from "./textos";

// Por qué existe (Tarea 11 del plan F4): la tabla «Registro de importaciones» de Archivos y planos y el panel con el
// informe guardado de la fila que se elige. La ven también quien revisa (es lectura). Aparte de la pantalla para que esta
// no pase de 250 líneas; solo la usa `paginas/archivos/index.tsx`.
export function RegistroDeImportaciones({ carga, alElegir }: { carga: CargaDelRegistro; alElegir: (i: ImportacionDeObra) => void }) {
  if (carga.estado === "error") return <AvisoError error={carga.error} titulo={TEXTOS.falloDelRegistro} />;
  const importaciones = carga.estado === "listo" ? carga.datos.importaciones : [];
  const filas = filasDeImportaciones({ importaciones });
  // Cada fila lleva su lugar en la respuesta; se elige la importación misma, que no cambia si el registro se vuelve a leer.
  const elegir = (f: FilaDensa) => {
    const elegida = importaciones[filas.findIndex((x) => x.id === f.id)];
    if (elegida !== undefined) alElegir(elegida);
  };
  const columnas = COLUMNAS_DEL_REGISTRO.map((c) => ({
    ...c,
    ordenable: false,
    ...(c.clave === "nombre"
      ? {
          // El nombre abre el informe guardado (como el código de una partida abre su APU, Tarea 7).
          celda: (f: FilaDensa) => (
            <Button kind="ghost" size="sm" aria-label={TEXTOS.verInforme(f.nombre ?? "")} onClick={() => elegir(f)}>
              {f.nombre}
            </Button>
          ),
        }
      : {}),
  }));
  return (
    <section className="silice-archivos__registro">
      <h2 className="cds--type-heading-compact-02">
        {TEXTOS.registro}
      </h2>
      <TablaDensa etiqueta={TEXTOS.registro} columnas={columnas} filas={filas} cargando={carga.estado === "cargando"} vacio={{ titulo: TEXTOS.vacio }} />
    </section>
  );
}

// Lo que el registro guardó de una importación (el resumen): el informe detallado es el del diálogo, mientras se importa.
export function InformeGuardado({ importacion, alCerrar }: { importacion: ImportacionDeObra | null; alCerrar: () => void }) {
  const fila = importacion === null ? null : filasDeImportaciones({ importaciones: [importacion] })[0]!;
  return (
    <PanelLateral titulo={importacion === null ? "" : TEXTOS.informe(importacion.archivo)} abierto={importacion !== null} alCerrar={alCerrar}>
      {fila !== null && (
        <>
          <dl className="silice-archivos__informe">
            {COLUMNAS_DEL_REGISTRO.filter((c) => c.clave !== "nombre").map((c) => (
              <div key={c.clave}>
                <dt className="cds--type-label-01">{c.titulo}</dt>
                <dd className="cds--type-body-compact-01">{fila[c.clave]}</dd>
              </div>
            ))}
          </dl>
          <p className="cds--type-helper-text-01">{TEXTOS.informeGuardado}</p>
        </>
      )}
    </PanelLateral>
  );
}
