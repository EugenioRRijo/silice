import { Button, Checkbox } from "@carbon/react";
import { useCallback, useMemo, useState } from "react";
import type { CostoRespuesta, TotalDeCostos } from "../../api/costos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import {
  escalaDeColor,
  slotsPorGrupo,
  useModoEfectivo,
  valorParaDibujar,
} from "../../comun/paletaGraficos";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { hoyISO } from "../existencias/formato";
import { AvisoConFoco } from "./AvisoConFoco";
import { DialogoAnular } from "./DialogoAnular";
import { FormularioDeCosto } from "./FormularioDeCosto";
import {
  CENTROS,
  CONCEPTOS,
  fechaEsVe,
  mensajeDeCostos,
  mostrarMonto,
  nombreDelMes,
  periodoValido,
  rotulo,
} from "./logica";
import { LienzoBarrasProduccion } from "./ResultadoDelCalculo";
import { useCostos } from "./useCostos";
import "./costos.scss";
import "./graficosProduccion.scss";

const ACCION = "registrar_costos_produccion";
const CATALOGO_CENTROS = CENTROS.map((c) => c.texto);

function estadoDe(c: CostoRespuesta): string {
  if (c.anula_id !== null) return "Anulación";
  return c.anulado ? "Anulado" : "Vigente";
}

function GraficoPorMoneda({
  mes,
  moneda,
  filas,
}: {
  mes: string;
  moneda: string;
  filas: readonly TotalDeCostos[];
}) {
  const modo = useModoEfectivo();
  const centros = filas.map((f) => rotulo(CENTROS, f.centro));
  const color = escalaDeColor(modo, slotsPorGrupo(centros, CATALOGO_CENTROS));
  const titulo = `Costos vigentes por centro en ${mes} (${moneda})`;

  return (
    <LienzoBarrasProduccion
      datos={filas.map((f) => {
        const nombre = rotulo(CENTROS, f.centro);
        return { group: nombre, key: nombre, value: valorParaDibujar(f.total) };
      })}
      config={{
        titulo,
        tituloEje: `Monto (${moneda})`,
        color,
        detalleDeClave: (clave) => {
          const fila = filas.find((f) => rotulo(CENTROS, f.centro) === clave);
          if (!fila) return null;
          return {
            encabezado: clave,
            cifra: `${mostrarMonto(fila.total)} ${moneda}`,
            nota: "Total vigente",
            trazo: color.scale[clave],
          };
        },
      }}
    />
  );
}

function ResumenGraficoTotales({
  periodo,
  totales,
}: {
  periodo: string;
  totales: readonly TotalDeCostos[];
}) {
  const modo = useModoEfectivo();
  const mes = nombreDelMes(periodo);
  const paletaCompleta = escalaDeColor(
    modo,
    slotsPorGrupo(CATALOGO_CENTROS, CATALOGO_CENTROS),
  );
  const monedas = [...new Set(totales.map((t) => t.moneda))];
  const frases = totales.map(
    (t) =>
      `${rotulo(CENTROS, t.centro)} acumula ${mostrarMonto(t.total)} ${t.moneda}`,
  );
  const explicacion =
    monedas.length > 1
      ? `Qué muestra: los costos vigentes acumulados por centro en ${mes}, separados por moneda sin mezclar escalas (los anulados no suman). Qué leer: ${frases.join("; ")}.`
      : `Qué muestra: los costos vigentes acumulados por centro en ${mes}, en ${monedas[0]!} (los anulados no suman). Qué leer: ${frases.join("; ")}.`;

  return (
    <figure
      className="prod-grafica"
      aria-label={`Costos vigentes por centro en ${mes}`}
    >
      <div className={monedas.length > 1 ? "prod-graficas-monedas" : undefined}>
        {monedas.map((m) => (
          <GraficoPorMoneda
            key={m}
            mes={mes}
            moneda={m}
            filas={totales.filter((t) => t.moneda === m)}
          />
        ))}
      </div>
      <ul
        className="costos-totales cds--type-body-compact-01"
        aria-label="Total por centro y moneda"
      >
        {totales.map((t) => {
          const nombre = rotulo(CENTROS, t.centro);
          return (
            <li
              key={`${t.centro}|${t.moneda}`}
              className="prod-grafica__rotulo"
            >
              <span
                className="prod-grafica__muestra"
                style={{ backgroundColor: paletaCompleta.scale[nombre] }}
                aria-hidden="true"
              />
              <span>
                {nombre}: {mostrarMonto(t.total)} {t.moneda}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="prod-grafica__lectura cds--type-body-compact-01">
        {explicacion}
      </p>
      <details className="prod-grafica__tabla">
        <summary className="cds--type-body-compact-01">Ver como tabla</summary>
        <TablaDensa
          etiqueta={`Totales por centro de ${mes}`}
          columnas={[
            { clave: "centro", titulo: "Centro", ordenable: false },
            { clave: "moneda", titulo: "Moneda", ordenable: false },
            {
              clave: "total",
              titulo: "Total vigente",
              numerica: true,
              ordenable: false,
              presentar: mostrarMonto,
            },
          ]}
          filas={totales.map((t) => ({
            id: `${t.centro}|${t.moneda}`,
            centro: rotulo(CENTROS, t.centro),
            moneda: t.moneda,
            total: t.total,
          }))}
        />
      </details>
    </figure>
  );
}

// «Costos del período»: lo que cuesta la cantera y la planta cada mes, con su fuente. Registrar y anular van por
// diálogos; anular no borra, deja el costo marcado con su motivo. La lista y los totales por centro y moneda los manda
// el servidor (la pantalla no suma montos, solo les da formato); nada se quita de la tabla hasta que la lista vuelve a
// leerse, y entonces el foco pasa al aviso para no perderse con la fila que desaparece.
export default function CostosDelPeriodo() {
  const { alExpirar, sesion } = useAplicacion();
  const puede = sesion.acciones.includes(ACCION);
  const [periodo, setPeriodo] = useState(() => hoyISO().slice(0, 7));
  const [conAnulados, setConAnulados] = useState(false);
  const [version, setVersion] = useState(0);
  const [registrando, setRegistrando] = useState(false);
  const [anulando, setAnulando] = useState<CostoRespuesta | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const valido = periodoValido(periodo);
  const costos = useCostos(
    puede && valido ? periodo : null,
    conAnulados,
    version,
    alExpirar,
  );
  const recargar = useCallback(() => setVersion((n) => n + 1), []);
  const datos = costos.estado === "listo" ? costos.datos : null;

  const columnas = useMemo<ColumnaDensa[]>(
    () => [
      {
        clave: "fecha",
        titulo: "Fecha",
        celda: (f) => fechaEsVe(f["fecha"] ?? ""),
      },
      { clave: "centro", titulo: "Centro" },
      { clave: "concepto", titulo: "Concepto" },
      {
        clave: "monto",
        titulo: "Monto",
        numerica: true,
        presentar: mostrarMonto,
      },
      { clave: "moneda", titulo: "Moneda" },
      { clave: "fuente", titulo: "Fuente" },
      { clave: "estado", titulo: "Estado" },
      { clave: "motivo", titulo: "Motivo de la anulación" },
      {
        clave: "accion",
        titulo: "Acción",
        ordenable: false,
        celda: (fila: FilaDensa) => {
          const costo =
            costos.estado === "listo"
              ? costos.datos.find((c) => String(c.id) === fila.id)
              : undefined;
          if (!costo || costo.anulado) return null;
          return (
            <Button
              kind="ghost"
              size="sm"
              aria-label={`Anular ${rotulo(CONCEPTOS, costo.concepto)} de ${rotulo(CENTROS, costo.centro).toLowerCase()} del ${fechaEsVe(costo.fecha)} por ${mostrarMonto(costo.monto)} ${costo.moneda}`}
              onClick={() => setAnulando(costo)}
            >
              Anular
            </Button>
          );
        },
      },
    ],
    [costos],
  );

  if (!puede) {
    return (
      <div className="costos silice-pagina">
        <h1 className="cds--type-heading-04">Costos del período</h1>
        <p className="costos-nota cds--type-body-compact-01">
          Su cuenta no registra costos de producción. Pídale a quien administra
          Sílice que revise su rol.
        </p>
      </div>
    );
  }

  const filas: FilaDensa[] =
    costos.estado === "listo"
      ? costos.datos.map((c) => ({
          id: String(c.id),
          fecha: c.fecha,
          centro: rotulo(CENTROS, c.centro),
          concepto: rotulo(CONCEPTOS, c.concepto),
          monto: c.monto,
          moneda: c.moneda,
          fuente: c.nota ? `${c.fuente} (${c.nota})` : c.fuente,
          estado: estadoDe(c),
          motivo: c.motivo,
          accion: "",
        }))
      : [];
  const totales = costos.estado === "listo" ? costos.totales : [];

  return (
    <div className="costos silice-pagina">
      <h1 className="cds--type-heading-04">Costos del período</h1>
      <div className="costos-barra">
        <CampoTexto
          id="costos-mes"
          type="month"
          labelText="Mes"
          value={periodo}
          onChange={(e) => {
            setPeriodo(e.target.value);
            setAviso(null);
          }}
        />
        <Checkbox
          id="costos-anulados"
          labelText="Mostrar anulados"
          checked={conAnulados}
          onChange={(_, { checked }) => {
            setConAnulados(checked);
            setAviso(null);
          }}
        />
        <Button
          kind="primary"
          size="md"
          disabled={!valido}
          onClick={() => setRegistrando(true)}
        >
          Registrar un costo
        </Button>
      </div>
      <AvisoConFoco
        aviso={aviso}
        alCerrar={() => setAviso(null)}
        refoco={datos}
      />
      {!valido && (
        <p className="costos-nota cds--type-body-compact-01">
          Elija el mes de los costos que quiere ver.
        </p>
      )}
      {valido && costos.estado === "error" && (
        <AvisoError
          error={mensajeDeCostos(costos.error)}
          titulo="No se pudieron leer los costos"
        />
      )}
      {valido && costos.estado === "cargando" && (
        <TablaDensa
          etiqueta="Costos del período"
          columnas={columnas}
          filas={[]}
          cargando
        />
      )}
      {valido && costos.estado === "listo" && (
        <>
          {totales.length > 0 && (
            <ResumenGraficoTotales periodo={periodo} totales={totales} />
          )}
          <TablaDensa
            etiqueta={`Costos de ${nombreDelMes(periodo)}`}
            columnas={columnas}
            filas={filas}
            vacio={{
              titulo: "Todavía no hay costos en este mes",
              descripcion:
                "Registre el primero con su fuente: la factura, el recibo o la nómina de donde sale el monto.",
            }}
          />
        </>
      )}
      {registrando && (
        <FormularioDeCosto
          periodo={periodo}
          alCerrar={() => setRegistrando(false)}
          alRegistrar={() => {
            setRegistrando(false);
            setAviso("Costo registrado.");
            recargar();
          }}
          alExpirar={alExpirar}
        />
      )}
      {anulando && (
        <DialogoAnular
          costo={anulando}
          alCerrar={() => setAnulando(null)}
          alAnular={() => {
            setAnulando(null);
            setAviso("Costo anulado.");
            recargar();
          }}
          alExpirar={alExpirar}
        />
      )}
    </div>
  );
}
