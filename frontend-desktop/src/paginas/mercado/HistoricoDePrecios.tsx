import { Button } from "@carbon/react";
import { InlineNotification } from "../../comun/carbonEs";
import { useMemo, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { TablaDensa } from "../../comun/TablaDensa";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import { buscadorDeInsumos } from "./logica";
import type { InsumoDelCatalogo } from "./logica";
import { aPorcentaje, fechaValida, rangoInvertido } from "../../comun/porcentaje";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";

interface Cambio {
  insumo: string;
  precio_anterior: string;
  precio_nuevo: string;
  variacion: string;
  fecha: string;
}
interface Filtros {
  insumo: string;
  desde: string;
  hasta: string;
}

function rutaDe({ insumo, desde, hasta }: Filtros): string {
  const q = new URLSearchParams();
  if (insumo.trim()) q.set("insumo", insumo.trim());
  if (fechaValida(desde)) q.set("desde", desde);
  if (fechaValida(hasta)) q.set("hasta", hasta);
  const texto = q.toString();
  return texto ? `/cambios-precio?${texto}` : "/cambios-precio";
}

const fechaMala = (t: string) => t !== "" && !fechaValida(t);

// Por qué existe (Tarea 13 del plan F4; preguntas 4 y 8 del inventario): el histórico de cambios de precio (UC-02) era una
// pantalla suelta; ahora es la pestaña «Histórico de precios» de Mercado (`index.tsx`), el único que la usa. Solo lectura:
// filtros por insumo y fechas; la tabla muestra los montos de la API en es-VE (el texto original queda en el `title`), la
// fecha dd/mm/aaaa y la variación en por ciento. El insumo se elige de la lista del catálogo (autocompletado, decisión de
// Eugenio del 2026-10-21) y al servidor va su descripción, como antes. A la API las fechas se envían AAAA-MM-DD (VB-19).
export function HistoricoDePrecios() {
  const { alExpirar } = useAplicacion();
  const [texto, setTexto] = useState("");
  const [borrador, setBorrador] = useState<Filtros>({ insumo: "", desde: "", hasta: "" });
  const [aplicado, setAplicado] = useState<Filtros>(borrador);
  const buscar = useMemo(() => buscadorDeInsumos(), []);
  const carga = useCarga<Cambio[]>(rutaDe(aplicado), alExpirar);
  const invertido = rangoInvertido(borrador.desde, borrador.hasta);

  return (
    <section className="silice-mercado__historico" aria-labelledby="historico-titulo">
      <h2 id="historico-titulo" className="cds--type-heading-compact-02">
        Histórico de cambios de precio
      </h2>
      <p className="cds--type-body-compact-01">
        Cada fila es un insumo que cambió de precio entre la lista anterior y la lista nueva de una actualización.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!invertido && !fechaMala(borrador.desde) && !fechaMala(borrador.hasta)) setAplicado(borrador);
        }}
      >
        <CampoConBusqueda<InsumoDelCatalogo>
          id="hist-insumo"
          etiqueta="Insumo"
          ayuda="Escriba parte del nombre o el código del insumo; por ejemplo «cemento». Vacío, muestra todos."
          texto={texto}
          alCambiarTexto={(t) => {
            setTexto(t);
            // Lo escrito es una búsqueda: si se cambia después de elegir, ya no vale el insumo elegido.
            if (t !== borrador.insumo) setBorrador({ ...borrador, insumo: "" });
          }}
          buscar={buscar}
          alElegir={(opcion) => {
            setTexto(opcion.valor.descripcion);
            setBorrador({ ...borrador, insumo: opcion.valor.descripcion });
          }}
          vacio={{ titulo: "¿No lo encuentra?", pasos: "Pruebe con otra palabra del nombre o revise el Catálogo de partidas e insumos." }}
          alExpirar={alExpirar}
          tamano="sm"
        />
        <CampoTexto
          id="hist-desde"
          size="sm"
          type="date"
          labelText="Desde"
          value={borrador.desde}
          invalid={fechaMala(borrador.desde)}
          invalidText="Fecha inválida"
          onChange={(e) => setBorrador({ ...borrador, desde: e.target.value })}
        />
        <CampoTexto
          id="hist-hasta"
          size="sm"
          type="date"
          labelText="Hasta"
          value={borrador.hasta}
          invalid={fechaMala(borrador.hasta)}
          invalidText="Fecha inválida"
          onChange={(e) => setBorrador({ ...borrador, hasta: e.target.value })}
        />
        {invertido && (
          <InlineNotification
            kind="warning"
            role="status"
            title="Rango invertido"
            subtitle="La fecha «Desde» es posterior a «Hasta»."
            lowContrast
            hideCloseButton
          />
        )}
        <Button type="submit" size="sm" kind="secondary">
          Filtrar
        </Button>
      </form>
      {(carga.estado === "error" || carga.estado === "sin_permiso" || carga.estado === "no_disponible") && (
        <AvisoError error={carga.error} titulo="No se pudo cargar el histórico" />
      )}
      {carga.estado === "cargando" && <EsqueletoPagina />}
      {carga.estado === "listo" && (
        <TablaDensa
          etiqueta="Cambios de precio"
          columnas={[
            { clave: "fecha", titulo: "Fecha", presentar: fechaEsVe },
            { clave: "insumo", titulo: "Insumo" },
            { clave: "precio_anterior", titulo: "Precio anterior", numerica: true, presentar: formatoEsVe },
            { clave: "precio_nuevo", titulo: "Precio nuevo", numerica: true, presentar: formatoEsVe },
            { clave: "variacion_pct", titulo: "Variación", numerica: true, presentar: (v) => `${formatoEsVe(v)} %` },
          ]}
          filas={carga.datos.map((c, i) => ({
            id: String(i),
            fecha: c.fecha,
            insumo: c.insumo,
            precio_anterior: c.precio_anterior,
            precio_nuevo: c.precio_nuevo,
            variacion_pct: aPorcentaje(c.variacion),
          }))}
          vacio={{ titulo: "No hay cambios de precio registrados con esos filtros" }}
        />
      )}
    </section>
  );
}
