import { Pagination } from "@carbon/react";
import { useState } from "react";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { FILAS_POR_PAGINA, LIMITE_SIN_PAGINAR } from "./logica";

interface Props {
  etiqueta: string;
  columnas: ColumnaDensa[];
  filas: FilaDensa[];
  vacio?: { titulo: string; descripcion?: string };
  // Las tablas anchas se desplazan dentro de su región (con teclado), no la página.
  desplazable?: boolean;
}

// `TablaDensa` con paginación de 50 filas cuando pasa de 100 (RNF-11 mide 500 puntos) y, si se pide, en una región
// desplazable con foco.
export function TablaPaginada({ etiqueta, columnas, filas, vacio, desplazable = false }: Props) {
  const [pagina, setPagina] = useState(1);
  const [tamano, setTamano] = useState(FILAS_POR_PAGINA);
  const paginar = filas.length > LIMITE_SIN_PAGINAR;
  const visibles = paginar ? filas.slice((pagina - 1) * tamano, pagina * tamano) : filas;
  const tabla = <TablaDensa etiqueta={etiqueta} columnas={columnas} filas={visibles} vacio={vacio} />;
  return (
    <>
      {desplazable ? (
        <div
          role="region"
          aria-label={`${etiqueta}: desplazar horizontalmente`}
          tabIndex={0}
          className="silice-hoja__desplazable"
        >
          {tabla}
        </div>
      ) : (
        tabla
      )}
      {paginar && (
        <Pagination
          size="sm"
          page={pagina}
          pageSize={tamano}
          pageSizes={[50, 100]}
          totalItems={filas.length}
          itemsPerPageText="Filas por página"
          itemRangeText={(min, max, total) => `${min}–${max} de ${total}`}
          onChange={({ page, pageSize }) => {
            setPagina(page);
            setTamano(pageSize);
          }}
        />
      )}
    </>
  );
}
