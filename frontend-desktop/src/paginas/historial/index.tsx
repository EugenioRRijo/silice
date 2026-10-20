import { Button, Select, SelectItem, TextInput } from "@carbon/react";
import { useState } from "react";
import { Link } from "react-router";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { fechaValida } from "../historico/porcentaje";
import type { AuditoriaGuardadaRespuesta } from "../inicio/UltimasAuditorias";
import { resultadoEnUnaLinea } from "../inicio/UltimasAuditorias";
import { useCarga } from "../inicio/useCarga";
import { Detalle } from "./Detalle";
import "./historial.scss";
import {
  FILTROS_VACIOS,
  fechaEsVe,
  filtrar,
  filtrosInvalidos,
  type FiltrosHistorial,
  type ResultadoFiltro,
  type TipoFiltro,
} from "./logica";

// La API devuelve hasta 100 (su maximo): los filtros de la pagina actuan sobre esas.
const RUTA_LISTA = "/v1/auditorias-libro?limite=100";
const MAXIMO = 100;

const fechaMala = (t: string) => t !== "" && !fechaValida(t);

// «Historial de auditorías» (UC-30, solo lectura): las auditorias de «Libro de la empresa» y las revisiones de PDF
// que quedaron guardadas, con filtros por fecha, tipo y resultado, y el detalle de cada una. El libro y el PDF no se
// guardan (RNF-28): lo que hay es el resumen y los hallazgos, y por eso no hay nada que descargar.
export default function PaginaHistorial() {
  const { alExpirar } = useAplicacion();
  const carga = useCarga<AuditoriaGuardadaRespuesta[]>(RUTA_LISTA, alExpirar);
  const [filtros, setFiltros] = useState<FiltrosHistorial>(FILTROS_VACIOS);
  const [abierta, setAbierta] = useState<number | null>(null);
  const aviso = filtrosInvalidos(filtros);

  return (
    <section className="silice-pagina silice-historial" aria-labelledby="historial-titulo">
      <h1 id="historial-titulo" className="cds--type-heading-04">
        Historial de auditorías
      </h1>
      <p className="cds--type-body-compact-01">
        Cada vez que audita un libro de la empresa o revisa un PDF, el resultado queda aquí. El libro y el PDF no se
        guardan: solo el resumen, los hallazgos y la huella que identifica el archivo.
      </p>

      {carga.estado === "cargando" && <TablaDensa etiqueta="Auditorías guardadas" columnas={COLUMNAS} filas={[]} cargando />}
      {(carga.estado === "error" || carga.estado === "sin_permiso" || carga.estado === "no_disponible") && (
        <AvisoError error={carga.error} titulo="No se pudo leer el historial" />
      )}
      {carga.estado === "listo" && carga.datos.length === 0 && (
        <EstadoVacio
          titulo="Todavía no hay auditorías guardadas"
          descripcion="Audite un libro de la empresa o revise un PDF: el resumen y los hallazgos quedarán aquí."
        >
          <Link to="/libros">Ir a Libro de la empresa</Link>
        </EstadoVacio>
      )}
      {carga.estado === "listo" && carga.datos.length > 0 && (
        <>
          <form className="silice-historial__filtros" onSubmit={(e) => e.preventDefault()} aria-label="Filtros">
            <TextInput
              id="historial-desde"
              size="sm"
              labelText="Desde (AAAA-MM-DD)"
              value={filtros.desde}
              invalid={fechaMala(filtros.desde)}
              invalidText="Fecha inválida"
              onChange={(e) => setFiltros({ ...filtros, desde: e.target.value.trim() })}
            />
            <TextInput
              id="historial-hasta"
              size="sm"
              labelText="Hasta (AAAA-MM-DD)"
              value={filtros.hasta}
              invalid={fechaMala(filtros.hasta)}
              invalidText="Fecha inválida"
              onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value.trim() })}
            />
            <Select
              id="historial-tipo"
              size="sm"
              labelText="Tipo"
              value={filtros.tipo}
              onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value as TipoFiltro })}
            >
              <SelectItem value="todos" text="Todos" />
              <SelectItem value="libro" text="Libro" />
              <SelectItem value="pdf" text="PDF" />
            </Select>
            <Select
              id="historial-resultado"
              size="sm"
              labelText="Resultado"
              value={filtros.resultado}
              onChange={(e) => setFiltros({ ...filtros, resultado: e.target.value as ResultadoFiltro })}
            >
              <SelectItem value="todos" text="Todos" />
              <SelectItem value="con_errores" text="Con errores" />
              <SelectItem value="solo_advertencias" text="Solo advertencias" />
              <SelectItem value="limpia" text="Sin errores ni advertencias" />
            </Select>
          </form>
          {aviso !== null && (
            <p className="cds--type-body-compact-01" role="status">
              {aviso}
            </p>
          )}
          <Lista datos={carga.datos} filtros={filtros} alQuitar={() => setFiltros(FILTROS_VACIOS)} alVer={setAbierta} />
        </>
      )}

      {abierta !== null && (
        <Detalle key={abierta} id={abierta} alExpirar={alExpirar} alCerrar={() => setAbierta(null)} />
      )}
    </section>
  );
}

const COLUMNAS = [
  { clave: "archivo", titulo: "Archivo" },
  { clave: "tipo", titulo: "Tipo" },
  { clave: "fecha", titulo: "Fecha y hora", presentar: fechaEsVe },
  { clave: "resultado", titulo: "Resultado", ordenable: false },
  { clave: "ver", titulo: "Detalle", ordenable: false },
];

function Lista({
  datos,
  filtros,
  alQuitar,
  alVer,
}: {
  datos: AuditoriaGuardadaRespuesta[];
  filtros: FiltrosHistorial;
  alQuitar: () => void;
  alVer: (id: number) => void;
}) {
  const visibles = filtrar(datos, filtros);
  const cuenta =
    datos.length === 1
      ? "Mostrando 1 de 1 auditoría guardada."
      : `Mostrando ${visibles.length} de ${datos.length} auditorías guardadas.`;
  if (visibles.length === 0) {
    return (
      <EstadoVacio
        titulo="Ninguna auditoría coincide con esos filtros"
        descripcion="Cambie las fechas, el tipo o el resultado, o quite los filtros para ver todas."
      >
        <Button kind="tertiary" size="sm" onClick={alQuitar}>
          Quitar los filtros
        </Button>
      </EstadoVacio>
    );
  }
  return (
    <>
      <p className="cds--type-label-01">
        {cuenta}
        {datos.length >= MAXIMO && ` Se muestran las ${MAXIMO} más recientes; las anteriores no aparecen aquí.`}
      </p>
      <TablaDensa
        etiqueta="Auditorías guardadas"
        columnas={COLUMNAS.map((c) =>
          c.clave === "ver"
            ? {
                ...c,
                celda: (fila) => (
                  <Button
                    kind="ghost"
                    size="sm"
                    aria-label={`Ver el detalle de ${fila.archivo}`}
                    onClick={() => alVer(Number(fila.id))}
                  >
                    Ver el detalle
                  </Button>
                ),
              }
            : c,
        )}
        filas={visibles.map((a) => ({
          id: String(a.id),
          archivo: a.archivo,
          tipo: a.tipo === "pdf" ? "PDF" : "Libro",
          fecha: a.fecha,
          resultado: resultadoEnUnaLinea(a.errores, a.advertencias),
          ver: "",
        }))}
      />
    </>
  );
}
