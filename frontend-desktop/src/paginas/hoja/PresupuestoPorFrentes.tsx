import { Button, Select, SelectItem } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { esBorradorAusente } from "./logica";
import type { Monto, Resumen } from "./logica";

// Libro por frentes (ola 2, línea 3, 2026-11-13): el presupuesto agrupado por frente (una estación, un tramo, un sector),
// como lo trae el libro de la empresa con una hoja de presupuesto por frente. El subtotal de cada frente y el total general
// los calcula el servidor (`GET /v1/hoja/borradores/{id}/vistas/frentes`); aquí solo se escriben en es-VE. El frente de un
// renglón propio se pone a mano (`PUT /v1/hoja/borradores/{id}/frentes`). Se abre a pedido: la pestaña no pide esta vista
// hasta que la persona quiere verla. Con el panel abierto, cada `rev` nuevo de la Hoja (una cantidad editada, un renglón
// quitado) vuelve a pedir la vista, para que «Total general» no quede viejo junto al «Total del presupuesto» (ronda 1 del
// árbitro de la ola 2, hallazgo 5); se pide una vez por `rev`, y no tras «Poner el frente», cuya respuesta ya la trae.
// «Ver», el efecto del `rev` y «Poner el frente» numeran su pedido y solo se aplica la respuesta del último: una vieja que
// llega tarde no deja la vista atrasada (ronda 2, R2-N1). El error de «Poner el frente» se dice siempre (no se puso).

interface Frente {
  frente: string | null;
  renglones: number;
  pendientes: number;
  total: Monto;
}

interface VistaFrentes {
  rev: number;
  frentes: Frente[];
  total: Monto;
  con_frentes: boolean;
}

interface FilaDelPresupuesto {
  clave?: string | null;
  partida?: string | null;
  descripcion?: string | null;
  quitable?: boolean | null;
}

interface Props {
  id: string;
  rev: number;
  filas: FilaDelPresupuesto[];
  moneda: string;
  puedeEditar: boolean;
  // El servidor aceptó un frente: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alAusente: () => void;
}

// El grupo de los renglones sin frente (`frente: null`), como lo rotula el PDF (`aplicacion/frentes.py`, `SIN_FRENTE`): entre
// paréntesis, para que no se confunda con un frente (el servidor no acepta un frente que se llame así; ronda 2, R2-N2).
const SIN_FRENTE = "(sin frente)";

const COLUMNAS: ColumnaDensa[] = [
  { clave: "frente", titulo: "Frente", ordenable: false },
  { clave: "renglones", titulo: "Renglones", ordenable: false },
  { clave: "total", titulo: "Subtotal", numerica: true, ordenable: false, presentar: formatoEsVe },
];

const renglones = (f: Frente) =>
  f.pendientes > 0 ? `${f.renglones} (${f.pendientes} ${f.pendientes === 1 ? "pendiente" : "pendientes"})` : String(f.renglones);

export function PresupuestoPorFrentes({ id, rev, filas, moneda, puedeEditar, alAceptar, alAusente }: Props): JSX.Element {
  const { alExpirar } = useAplicacion();
  const [abierto, setAbierto] = useState(false);
  const [vista, setVista] = useState<VistaFrentes | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ocupado, setOcupado] = useState(false);
  const propias = filas.filter((f) => f.quitable && f.clave);
  const [renglon, setRenglon] = useState("");
  const [frente, setFrente] = useState("");
  const elegido = renglon || propias[0]?.clave || "";

  // El `rev` para el que se pidió (o llegó) la vista que se muestra; `null` mientras el panel no se abrió.
  const pedidaPara = useRef<number | null>(null);
  // El número del último pedido de la vista (de cualquiera de los tres caminos).
  const ultimo = useRef(0);

  const fallar = useCallback(
    (razon: unknown) => {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else if (esBorradorAusente(razon)) alAusente();
      else setError(razon);
    },
    [alExpirar, alAusente],
  );

  async function abrir() {
    setAbierto(true);
    setError(null);
    setOcupado(true);
    pedidaPara.current = rev;
    const pedido = ++ultimo.current;
    try {
      const nueva = await pedir<VistaFrentes>(`/v1/hoja/borradores/${id}/vistas/frentes`);
      if (pedido === ultimo.current) setVista(nueva);
    } catch (razon) {
      if (pedido === ultimo.current) fallar(razon);
    } finally {
      setOcupado(false);
    }
  }

  useEffect(() => {
    if (!abierto || pedidaPara.current === null || pedidaPara.current === rev) return;
    pedidaPara.current = rev;
    const pedido = ++ultimo.current;
    let vigente = true;
    pedir<VistaFrentes>(`/v1/hoja/borradores/${id}/vistas/frentes`)
      .then((nueva) => {
        if (vigente && pedido === ultimo.current) setVista(nueva);
      })
      .catch((razon: unknown) => {
        if (vigente && pedido === ultimo.current) fallar(razon);
      });
    return () => {
      vigente = false;
    };
  }, [abierto, rev, id, fallar]);

  async function poner() {
    if (!elegido) return;
    setError(null);
    setOcupado(true);
    const pedido = ++ultimo.current;
    try {
      const r = await pedir<{ rev: number; resumen: Resumen; frentes: VistaFrentes }>(`/v1/hoja/borradores/${id}/frentes`, {
        metodo: "PUT",
        cuerpo: { rev, filas: [{ clave: elegido, frente }] },
      });
      setFrente("");
      // Si mientras tanto se pidió la vista de un `rev` posterior, esta respuesta ya es vieja: la Hoja va por delante.
      if (pedido !== ultimo.current) return;
      pedidaPara.current = r.rev;
      setVista(r.frentes);
      alAceptar(r.resumen);
    } catch (razon) {
      fallar(razon);
    } finally {
      setOcupado(false);
    }
  }

  if (!abierto) {
    return (
      <div className="silice-hoja__frentes">
        <Button kind="tertiary" size="sm" onClick={() => void abrir()}>
          Ver el presupuesto por frente
        </Button>
      </div>
    );
  }
  return (
    <section className="silice-hoja__frentes" aria-labelledby="hoja-frentes-titulo">
      <h3 id="hoja-frentes-titulo" className="cds--type-heading-compact-01">
        Presupuesto por frente
      </h3>
      <AvisoError error={error} titulo="No se pudo leer o cambiar el presupuesto por frente" />
      {vista && (
        <>
          {!vista.con_frentes && (
            <p className="cds--type-body-compact-01">
              Ningún renglón tiene frente: póngalo abajo, o lleve a la Hoja un libro con una hoja de presupuesto por frente.
            </p>
          )}
          <TablaDensa
            etiqueta="Presupuesto por frente"
            columnas={COLUMNAS}
            filas={vista.frentes.map((f, i) => ({
              id: `frente-${i}`,
              frente: f.frente ?? SIN_FRENTE,
              renglones: renglones(f),
              total: f.total.texto,
            }))}
          />
          <p className="silice-hoja__total cds--type-heading-compact-01">{`Total general: ${formatoEsVe(vista.total.texto)} ${moneda}`}</p>
        </>
      )}
      {vista && puedeEditar && propias.length > 0 && (
        <div className="silice-hoja__frentes-edicion">
          <Select id="hoja-frente-renglon" labelText="Renglón" value={elegido} onChange={(e) => setRenglon(e.target.value)} disabled={ocupado}>
            {propias.map((f, i) => (
              <SelectItem key={f.clave!} value={f.clave!} text={`${i + 1}. ${f.partida ?? ""} · ${f.descripcion ?? ""}`} />
            ))}
          </Select>
          <CampoTexto
            id="hoja-frente-nombre"
            labelText="Frente"
            helperText="Vacío quita el frente del renglón."
            value={frente}
            maxLength={80}
            onChange={(e) => setFrente(e.target.value)}
            disabled={ocupado}
          />
          <Button kind="secondary" size="sm" disabled={ocupado} onClick={() => void poner()}>
            Poner el frente
          </Button>
        </div>
      )}
      <Button kind="ghost" size="sm" disabled={ocupado} onClick={() => setAbierto(false)}>
        Ocultar el presupuesto por frente
      </Button>
    </section>
  );
}
