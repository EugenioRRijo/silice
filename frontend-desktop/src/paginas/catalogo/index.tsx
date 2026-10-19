import { Search, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import { coincide } from "./filtro";

interface Partida {
  codigo: string;
  descripcion: string;
  unidad: string;
  dominio: string;
}
interface Insumo {
  codigo: string;
  descripcion: string;
  tipo: string;
  unidad: string | null;
  precio_vigente: string | null;
}

// «Catálogo de partidas e insumos» (solo lectura): las dos tablas de la página clásica, con una búsqueda.
export default function PaginaCatalogo() {
  const { alExpirar } = useAplicacion();
  const partidas = useCarga<Partida[]>("/partidas", alExpirar);
  const insumos = useCarga<Insumo[]>("/insumos", alExpirar);
  const [busqueda, setBusqueda] = useState("");

  // 403 y 404 también se dicen, con el detalle de la API tal cual: nunca esqueleto para siempre.
  const falla = [partidas, insumos].find((c) => c.estado === "error" || c.estado === "sin_permiso" || c.estado === "no_disponible");
  if (falla && "error" in falla) {
    return (
      <section className="silice-pagina" aria-labelledby="catalogo-titulo">
        <h1 id="catalogo-titulo" className="cds--type-heading-04">
          Catálogo de partidas e insumos
        </h1>
        <AvisoError error={falla.error} titulo="No se pudo cargar el catálogo" />
      </section>
    );
  }
  if (partidas.estado !== "listo" || insumos.estado !== "listo") return <EsqueletoPagina titulo="Catálogo de partidas e insumos" />;

  const filasPartidas = partidas.datos
    .filter((p) => coincide([p.codigo, p.descripcion, p.unidad, p.dominio], busqueda))
    .map((p) => ({ id: p.codigo, codigo: p.codigo, descripcion: p.descripcion, unidad: p.unidad, dominio: p.dominio }));
  const filasInsumos = insumos.datos
    .filter((i) => coincide([i.codigo, i.descripcion, i.tipo, i.unidad], busqueda))
    .map((i) => ({
      id: i.codigo,
      codigo: i.codigo,
      tipo: i.tipo,
      descripcion: i.descripcion,
      unidad: i.unidad ?? "",
      precio_vigente: i.precio_vigente ?? "",
    }));

  return (
    <section className="silice-pagina" aria-labelledby="catalogo-titulo">
      <h1 id="catalogo-titulo" className="cds--type-heading-04">
        Catálogo de partidas e insumos
      </h1>
      <p className="cds--type-body-compact-01">Partidas e insumos del catálogo, con el precio vigente de cada insumo.</p>
      <Search
        size="sm"
        labelText="Buscar en el catálogo"
        placeholder="Código, descripción, unidad…"
        value={busqueda}
        onChange={(e: { target: { value: string } }) => setBusqueda(e.target.value)}
      />
      <Tabs>
        <TabList aria-label="Catálogo">
          <Tab>Partidas ({filasPartidas.length})</Tab>
          <Tab>Insumos ({filasInsumos.length})</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            <TablaDensa
              etiqueta="Partidas"
              columnas={[
                { clave: "codigo", titulo: "Código" },
                { clave: "descripcion", titulo: "Descripción" },
                { clave: "unidad", titulo: "Unidad" },
                { clave: "dominio", titulo: "Dominio" },
              ]}
              filas={filasPartidas}
              vacio={{ titulo: "No hay partidas para mostrar", descripcion: "El catálogo no tiene partidas con esa búsqueda." }}
            />
          </TabPanel>
          <TabPanel>
            <TablaDensa
              etiqueta="Insumos"
              columnas={[
                { clave: "codigo", titulo: "Código" },
                { clave: "tipo", titulo: "Tipo" },
                { clave: "descripcion", titulo: "Descripción" },
                { clave: "unidad", titulo: "Unidad" },
                { clave: "precio_vigente", titulo: "Precio vigente", numerica: true },
              ]}
              filas={filasInsumos}
              vacio={{ titulo: "No hay insumos para mostrar", descripcion: "El catálogo no tiene insumos con esa búsqueda." }}
            />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </section>
  );
}
