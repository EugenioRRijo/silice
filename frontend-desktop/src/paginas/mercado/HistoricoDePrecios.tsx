import type { LineChartOptions } from "@carbon/charts-react";
import { Button } from "@carbon/react";
import { lazy, Suspense, useMemo, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification } from "../../comun/carbonEs";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import {
  coloresDeSerie,
  ESCALA_DE_ETIQUETAS,
  escalaDeColor,
  formatoNumeroEsVe,
  slotsPorGrupo,
  useModoEfectivo,
  valorParaDibujar,
} from "../../comun/paletaGraficos";
import {
  aPorcentaje,
  fechaValida,
  rangoInvertido,
} from "../../comun/porcentaje";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { unidadEscrita } from "../../comun/unidades";
import { useCarga } from "../../comun/useCarga";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { buscadorDeInsumos } from "./logica";
import type { InsumoDelCatalogo } from "./logica";

const GraficoCarbon = lazy(() => import("../../comun/GraficoCarbon"));

interface Cambio {
  insumo: string;
  precio_anterior: string;
  precio_nuevo: string;
  variacion: string;
  fecha: string;
}

interface Filtros {
  insumo: string;
  unidad: string | null;
  desde: string;
  hasta: string;
}

interface PuntoCronologico {
  clave: string;
  cambio: Cambio;
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

function escaparTexto(valor: string): string {
  return valor
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function variacionFirmada(fraccion: string): string {
  const pct = aPorcentaje(fraccion);
  const signo = !pct.startsWith("-") && pct !== "0" ? "+" : "";
  return `${signo}${formatoEsVe(pct)} %`;
}

function puntosOrdenados(cambios: readonly Cambio[]): PuntoCronologico[] {
  const ordenados = [...cambios].sort((a, b) => a.fecha.localeCompare(b.fecha));
  const apariciones = new Map<string, number>();
  return ordenados.map((cambio) => {
    const dia = fechaEsVe(cambio.fecha);
    const par = `${cambio.insumo}|${dia}`;
    const n = (apariciones.get(par) ?? 0) + 1;
    apariciones.set(par, n);
    return { clave: n > 1 ? `${dia} (${n})` : dia, cambio };
  });
}

function GraficoHistorico({
  cambios,
  catalogo,
  aplicado,
  columnas,
  filasTabla,
}: {
  cambios: readonly Cambio[];
  catalogo: readonly string[];
  aplicado: Filtros;
  columnas: ColumnaDensa[];
  filasTabla: {
    id: string;
    fecha: string;
    insumo: string;
    precio_anterior: string;
    precio_nuevo: string;
    variacion_pct: string;
  }[];
}) {
  const modo = useModoEfectivo();
  const puntos = useMemo(() => puntosOrdenados(cambios), [cambios]);
  const insumosPresentes = useMemo(() => {
    const conjunto = new Set(puntos.map((p) => p.cambio.insumo));
    const enOrden = catalogo.filter((nombre) => conjunto.has(nombre));
    for (const nombre of conjunto)
      if (!enOrden.includes(nombre)) enOrden.push(nombre);
    return enOrden;
  }, [puntos, catalogo]);

  const unico = insumosPresentes.length === 1 ? insumosPresentes[0]! : null;
  const unidadCatalogo =
    unico !== null && aplicado.insumo === unico && aplicado.unidad
      ? unidadEscrita(aplicado.unidad)
      : null;
  const tituloGrafico =
    unico !== null
      ? `Precio registrado de ${unico} (${unidadCatalogo ? `por ${unidadCatalogo}` : "precio unitario"})`
      : "Precio registrado por insumo (precio unitario)";

  const color = escalaDeColor(modo, slotsPorGrupo(insumosPresentes, catalogo));
  const clavesUnicas = new Set(puntos.map((p) => p.clave));
  const primero = puntos[0]!.cambio;
  const ultimo = puntos[puntos.length - 1]!.cambio;
  const ultimosPorInsumo = insumosPresentes.map((insumo) => {
    const delInsumo = puntos.filter((p) => p.cambio.insumo === insumo);
    return delInsumo[delInsumo.length - 1]!.cambio;
  });

  const opciones: LineChartOptions = {
    title: tituloGrafico,
    height: "260px",
    curve: "curveMonotoneX",
    points:
      clavesUnicas.size <= 16
        ? { enabled: true, radius: 4 }
        : { enabled: false },
    axes: {
      bottom: { mapsTo: "key", scaleType: ESCALA_DE_ETIQUETAS },
      left: {
        mapsTo: "value",
        title: unidadCatalogo
          ? `Precio por ${unidadCatalogo}`
          : "Precio unitario",
        ticks: { formatter: formatoNumeroEsVe },
        ...(unico !== null
          ? {
              thresholds: [
                {
                  value: valorParaDibujar(primero.precio_anterior),
                  label: `Lista anterior: ${formatoEsVe(primero.precio_anterior)}`,
                  fillColor: coloresDeSerie(modo).neutro2,
                },
              ],
            }
          : {}),
      },
    },
    color,
    tooltip: {
      valueFormatter: formatoNumeroEsVe,
      customHTML: (data: unknown, porOmision: string) => {
        const entrada: unknown = Array.isArray(data) ? data[0] : data;
        const clave =
          typeof entrada === "object" &&
          entrada !== null &&
          "key" in entrada &&
          typeof entrada.key === "string"
            ? entrada.key
            : null;
        if (clave === null) return porOmision;
        const enFecha = puntos.filter((p) => p.clave === clave);
        if (enFecha.length === 0) return porOmision;
        const renglones = enFecha.map(({ cambio }) => {
          const trazo = color.scale[cambio.insumo];
          const marca = trazo
            ? `<span style="display:inline-block;inline-size:0.75rem;border-block-start:2px solid ${escaparTexto(trazo)}"></span>`
            : "";
          return (
            `<li style="display:flex;gap:0.5rem;align-items:center">${marca}` +
            `<strong>${escaparTexto(formatoEsVe(cambio.precio_nuevo))}</strong>` +
            `<span>${escaparTexto(cambio.insumo)} · anterior ${escaparTexto(formatoEsVe(cambio.precio_anterior))} (${escaparTexto(variacionFirmada(cambio.variacion))})</span></li>`
          );
        });
        return `<div style="padding:0.5rem 0.75rem"><p style="margin:0 0 0.25rem;font-weight:600">${escaparTexto(clave)}</p><ul style="list-style:none;margin:0;padding:0">${renglones.join("")}</ul></div>`;
      },
    },
  };

  const lectura =
    unico !== null
      ? `Qué muestra: la evolución del precio de ${unico} en cada actualización y su precio anterior de referencia (${formatoEsVe(primero.precio_anterior)}). Qué leer: el último cambio se registró el ${fechaEsVe(ultimo.fecha)} a ${formatoEsVe(ultimo.precio_nuevo)} (${variacionFirmada(ultimo.variacion)} frente a ${formatoEsVe(ultimo.precio_anterior)}).`
      : `Qué muestra: el precio nuevo de cada insumo en las fechas en que se actualizó la lista (${formatoEsVe(String(insumosPresentes.length))} insumos). Qué leer: la actualización más reciente corresponde a ${ultimo.insumo} el ${fechaEsVe(ultimo.fecha)}, con precio ${formatoEsVe(ultimo.precio_nuevo)} (${variacionFirmada(ultimo.variacion)} frente a ${formatoEsVe(ultimo.precio_anterior)}).`;

  return (
    <figure
      aria-label={tituloGrafico}
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr)",
        gap: "0.5rem",
        margin: 0,
        padding: "1rem",
        border: "1px solid var(--silice-linea)",
        borderRadius: "0.75rem",
        background: "var(--silice-hoja)",
      }}
    >
      <div role="group" aria-label={`Gráfico: ${tituloGrafico}`}>
        <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
          <GraficoCarbon
            tipo="linea"
            datos={puntos.map((p) => ({
              group: p.cambio.insumo,
              key: p.clave,
              value: valorParaDibujar(p.cambio.precio_nuevo),
            }))}
            opciones={opciones}
          />
        </Suspense>
      </div>
      <ul
        aria-label="Último precio por insumo"
        className="cds--type-helper-text-01"
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "flex",
          flexWrap: "wrap",
          gap: "0.25rem 1.5rem",
          color: "var(--silice-t1)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {ultimosPorInsumo.map((u) => (
          <li
            key={u.insumo}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span
              aria-hidden="true"
              style={{
                display: "inline-block",
                inlineSize: "0.75rem",
                borderBlockStart: `2px solid ${color.scale[u.insumo] ?? ""}`,
              }}
            />
            <span>
              <strong>{u.insumo}</strong>
              {` (${fechaEsVe(u.fecha)}): ${formatoEsVe(u.precio_nuevo)} (${variacionFirmada(u.variacion)})`}
            </span>
          </li>
        ))}
      </ul>
      <p
        className="silice-mercado__nota cds--type-body-compact-01"
        style={{ margin: 0, lineHeight: 1.45 }}
      >
        {lectura}
      </p>
      <details>
        <summary
          className="cds--type-body-compact-01"
          style={{ cursor: "pointer", color: "var(--silice-t2)" }}
        >
          Ver como tabla
        </summary>
        <TablaDensa
          etiqueta="Cambios de precio"
          columnas={columnas}
          filas={filasTabla}
        />
      </details>
    </figure>
  );
}

// Por qué existe (Tarea 13 del plan F4; preguntas 4 y 8 del inventario): el histórico de cambios de precio (UC-02) era una
// pantalla suelta; ahora es la pestaña «Histórico de precios» de Mercado (`index.tsx`), el único que la usa. Solo lectura:
// filtros por insumo y fechas; el gráfico traza la evolución con la paleta común y la tabla muestra los montos de la API en
// es-VE (el texto original queda en el `title`), la fecha dd/mm/aaaa y la variación en por ciento.
export function HistoricoDePrecios() {
  const { alExpirar } = useAplicacion();
  const [texto, setTexto] = useState("");
  const [borrador, setBorrador] = useState<Filtros>({
    insumo: "",
    unidad: null,
    desde: "",
    hasta: "",
  });
  const [aplicado, setAplicado] = useState<Filtros>(borrador);
  const buscar = useMemo(() => buscadorDeInsumos(), []);
  const carga = useCarga<Cambio[]>(rutaDe(aplicado), alExpirar);
  const invertido = rangoInvertido(borrador.desde, borrador.hasta);

  const [catalogoInsumos, setCatalogoInsumos] = useState<string[]>([]);
  const [vistos, setVistos] = useState<Cambio[] | null>(null);
  if (carga.estado === "listo" && carga.datos !== vistos) {
    setVistos(carga.datos);
    const nuevos = [...new Set(carga.datos.map((c) => c.insumo))].filter(
      (n) => !catalogoInsumos.includes(n),
    );
    if (nuevos.length > 0) setCatalogoInsumos([...catalogoInsumos, ...nuevos]);
  }

  const catalogoEfectivo = useMemo(() => {
    const lista = [...catalogoInsumos];
    if (carga.estado === "listo") {
      for (const c of carga.datos)
        if (!lista.includes(c.insumo)) lista.push(c.insumo);
    }
    return lista;
  }, [catalogoInsumos, carga]);

  const columnas = useMemo<ColumnaDensa[]>(
    () => [
      {
        clave: "fecha",
        titulo: "Fecha",
        celda: (f) => fechaEsVe(f["fecha"] ?? ""),
      },
      { clave: "insumo", titulo: "Insumo" },
      {
        clave: "precio_anterior",
        titulo: "Precio anterior",
        numerica: true,
        presentar: formatoEsVe,
      },
      {
        clave: "precio_nuevo",
        titulo: "Precio nuevo",
        numerica: true,
        presentar: formatoEsVe,
      },
      {
        clave: "variacion_pct",
        titulo: "Variación",
        numerica: true,
        presentar: (v) => `${formatoEsVe(v)} %`,
      },
    ],
    [],
  );

  const filasTabla = useMemo(
    () =>
      carga.estado === "listo"
        ? carga.datos.map((c, i) => ({
            id: String(i),
            fecha: c.fecha,
            insumo: c.insumo,
            precio_anterior: c.precio_anterior,
            precio_nuevo: c.precio_nuevo,
            variacion_pct: aPorcentaje(c.variacion),
          }))
        : [],
    [carga],
  );

  return (
    <section
      className="silice-mercado__historico"
      aria-labelledby="historico-titulo"
    >
      <h2 id="historico-titulo" className="cds--type-heading-compact-02">
        Histórico de cambios de precio
      </h2>
      <p className="cds--type-body-compact-01">
        Cada fila es un insumo que cambió de precio entre la lista anterior y la
        lista nueva de una actualización.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (
            !invertido &&
            !fechaMala(borrador.desde) &&
            !fechaMala(borrador.hasta)
          )
            setAplicado(borrador);
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
            if (t !== borrador.insumo)
              setBorrador({ ...borrador, insumo: "", unidad: null });
          }}
          buscar={buscar}
          alElegir={(opcion) => {
            setTexto(opcion.valor.descripcion);
            setBorrador({
              ...borrador,
              insumo: opcion.valor.descripcion,
              unidad: opcion.valor.unidad,
            });
          }}
          vacio={{
            titulo: "¿No lo encuentra?",
            pasos:
              "Pruebe con otra palabra del nombre o revise el Catálogo de partidas e insumos.",
          }}
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
      {(carga.estado === "error" ||
        carga.estado === "sin_permiso" ||
        carga.estado === "no_disponible") && (
        <AvisoError
          error={carga.error}
          titulo="No se pudo cargar el histórico"
        />
      )}
      {carga.estado === "cargando" && <EsqueletoPagina />}
      {carga.estado === "listo" &&
        (carga.datos.length === 0 ? (
          <TablaDensa
            etiqueta="Cambios de precio"
            columnas={columnas}
            filas={[]}
            vacio={{
              titulo: "No hay cambios de precio registrados con esos filtros",
              descripcion:
                "Pruebe con otro insumo o amplíe el rango de fechas.",
            }}
          />
        ) : (
          <GraficoHistorico
            cambios={carga.datos}
            catalogo={catalogoEfectivo}
            aplicado={aplicado}
            columnas={columnas}
            filasTabla={filasTabla}
          />
        ))}
    </section>
  );
}
