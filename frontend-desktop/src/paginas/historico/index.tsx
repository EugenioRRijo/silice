import { Button, InlineNotification, TextInput } from "@carbon/react";
import { useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import { aPorcentaje, fechaValida, rangoInvertido } from "./porcentaje";

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

// «Histórico de cambios de precio» (UC-02, solo lectura): filtros por insumo y fechas; la tabla muestra los
// montos tal como los manda la API y la variación en por ciento.
export default function PaginaHistorico() {
  const { alExpirar } = useAplicacion();
  const [borrador, setBorrador] = useState<Filtros>({ insumo: "", desde: "", hasta: "" });
  const [aplicado, setAplicado] = useState<Filtros>(borrador);
  const carga = useCarga<Cambio[]>(rutaDe(aplicado), alExpirar);
  const invertido = rangoInvertido(borrador.desde, borrador.hasta);

  return (
    <section className="silice-pagina" aria-labelledby="historico-titulo">
      <h1 id="historico-titulo" className="cds--type-heading-04">
        Histórico de cambios de precio
      </h1>
      <p className="cds--type-body-compact-01">
        Cada fila es un insumo que cambió de precio entre la lista anterior y la lista nueva de una actualización.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!invertido && !fechaMala(borrador.desde) && !fechaMala(borrador.hasta)) setAplicado(borrador);
        }}
      >
        <TextInput
          id="hist-insumo"
          size="sm"
          labelText="Insumo (descripción exacta)"
          value={borrador.insumo}
          onChange={(e) => setBorrador({ ...borrador, insumo: e.target.value })}
        />
        <TextInput
          id="hist-desde"
          size="sm"
          labelText="Desde (AAAA-MM-DD)"
          value={borrador.desde}
          invalid={fechaMala(borrador.desde)}
          invalidText="Fecha inválida"
          onChange={(e) => setBorrador({ ...borrador, desde: e.target.value })}
        />
        <TextInput
          id="hist-hasta"
          size="sm"
          labelText="Hasta (AAAA-MM-DD)"
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
        <Button type="submit" size="sm" kind="primary">
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
            { clave: "fecha", titulo: "Fecha" },
            { clave: "insumo", titulo: "Insumo" },
            { clave: "precio_anterior", titulo: "Precio anterior", numerica: true },
            { clave: "precio_nuevo", titulo: "Precio nuevo", numerica: true },
            { clave: "variacion_pct", titulo: "Variación (%)", numerica: true },
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
