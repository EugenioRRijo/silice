import { Button, Checkbox, InlineNotification } from "@carbon/react";
import { useCallback, useMemo, useState } from "react";
import type { CostoRespuesta } from "../../api/costos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { hoyISO } from "../existencias/formato";
import { DialogoAnular } from "./DialogoAnular";
import { FormularioDeCosto } from "./FormularioDeCosto";
import { CENTROS, CONCEPTOS, mensajeDeCostos, mostrarMonto, nombreDelMes, periodoValido, rotulo, totalesPorCentro } from "./logica";
import { useCostos } from "./useCostos";
import "./costos.scss";

const ACCION = "registrar_costos_produccion";

function estadoDe(c: CostoRespuesta): string {
  if (c.anula_id !== null) return "Anulación";
  return c.anulado ? "Anulado" : "Vigente";
}

// «Costos del período»: lo que cuesta la cantera y la planta cada mes, con su fuente. Registrar y anular van por
// diálogos; anular no borra, deja el costo marcado con su motivo. La lista y los totales los calcula el servidor y la
// pantalla; nada se quita de la tabla hasta que la lista vuelve a leerse.
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
  const costos = useCostos(puede && valido ? periodo : null, conAnulados, version, alExpirar);
  const recargar = useCallback(() => setVersion((n) => n + 1), []);

  const columnas = useMemo<ColumnaDensa[]>(
    () => [
      { clave: "fecha", titulo: "Fecha" },
      { clave: "centro", titulo: "Centro" },
      { clave: "concepto", titulo: "Concepto" },
      { clave: "monto", titulo: "Monto", numerica: true, presentar: mostrarMonto },
      { clave: "moneda", titulo: "Moneda" },
      { clave: "fuente", titulo: "Fuente" },
      { clave: "estado", titulo: "Estado" },
      { clave: "motivo", titulo: "Motivo de la anulación" },
      {
        clave: "accion",
        titulo: "Acción",
        ordenable: false,
        celda: (fila: FilaDensa) => {
          const costo = costos.estado === "listo" ? costos.datos.find((c) => String(c.id) === fila.id) : undefined;
          if (!costo || costo.anulado) return null;
          return (
            <Button kind="ghost" size="sm" onClick={() => setAnulando(costo)}>
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
          Su cuenta no registra costos de producción. Pídale a quien administra Sílice que revise su rol.
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
  const totales = costos.estado === "listo" ? totalesPorCentro(costos.datos) : [];

  return (
    <div className="costos silice-pagina">
      <h1 className="cds--type-heading-04">Costos del período</h1>
      <div className="costos-barra">
        <CampoTexto id="costos-mes" type="month" labelText="Mes" value={periodo} onChange={(e) => setPeriodo(e.target.value)} />
        <Checkbox id="costos-anulados" labelText="Mostrar anulados" checked={conAnulados} onChange={(_, { checked }) => setConAnulados(checked)} />
        <Button kind="primary" size="md" disabled={!valido} onClick={() => setRegistrando(true)}>
          Registrar un costo
        </Button>
      </div>
      {aviso && (
        <InlineNotification kind="success" role="status" lowContrast title={aviso} onClose={() => { setAviso(null); return false; }} />
      )}
      {!valido && <p className="costos-nota cds--type-body-compact-01">Elija el mes de los costos que quiere ver.</p>}
      {valido && costos.estado === "error" && <AvisoError error={mensajeDeCostos(costos.error)} titulo="No se pudieron leer los costos" />}
      {valido && costos.estado === "cargando" && <TablaDensa etiqueta="Costos del período" columnas={columnas} filas={[]} cargando />}
      {valido && costos.estado === "listo" && (
        <>
          {totales.length > 0 && (
            <ul className="costos-totales cds--type-body-compact-01" aria-label="Total por centro y moneda">
              {totales.map((t) => (
                <li key={`${t.centro}|${t.moneda}`}>
                  {rotulo(CENTROS, t.centro)}: {mostrarMonto(t.total)} {t.moneda}
                </li>
              ))}
            </ul>
          )}
          <TablaDensa
            etiqueta={`Costos de ${nombreDelMes(periodo)}`}
            columnas={columnas}
            filas={filas}
            vacio={{
              titulo: "Todavía no hay costos en este mes",
              descripcion: "Registre el primero con su fuente: la factura, el recibo o la nómina de donde sale el monto.",
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
