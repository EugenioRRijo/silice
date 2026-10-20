import { RadioButton, RadioButtonGroup, Search } from "@carbon/react";
import { useEffect, useState } from "react";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { Cifra } from "./Cifra";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { DetalleApu, GrupoApu, VistaApu } from "./logica";

interface Props {
  id: string;
  moneda: string;
  alAusente: () => void;
}

// Espera tras la última tecla antes de pedir la lista filtrada al servidor.
const PAUSA_DE_BUSQUEDA_MS = 300;
const NUMERICAS = new Set(["cantidad", "precio", "depreciacion", "sueldo"]);

function TablaDelRubro({ grupo, moneda }: { grupo: GrupoApu; moneda: string }) {
  const columnas: ColumnaDensa[] = grupo.columnas.map((c) => ({
    clave: c.clave,
    titulo: c.rotulo,
    ordenable: false,
    ...(NUMERICAS.has(c.clave) ? { numerica: true, presentar: formatoEsVe } : {}),
  }));
  return (
    <section className="silice-hoja__seccion">
      <h3 className="cds--type-heading-compact-01">
        {grupo.rotulo} · {grupo.filas.length} línea(s)
      </h3>
      {grupo.filas.length === 0 ? (
        <p className="cds--type-body-compact-01">Sin líneas.</p>
      ) : (
        <TablaDensa
          etiqueta={grupo.rotulo}
          columnas={columnas}
          filas={grupo.filas.map((f, i) => ({ ...f, id: `${grupo.clave}-${i}` }))}
        />
      )}
      <p className="cds--type-body-compact-01">
        <span>Subtotal de {grupo.rotulo.toLowerCase()}:</span> <Cifra monto={grupo.subtotal} unidad={moneda} />
      </p>
    </section>
  );
}

function Detalle({ detalle, moneda }: { detalle: DetalleApu; moneda: string }) {
  return (
    <>
      <div className="silice-hoja__apu-centro">
        <h2 className="cds--type-heading-compact-02">
          {detalle.codigo} · {detalle.descripcion} · {detalle.unidad}
        </h2>
        {detalle.grupos.map((g) => (
          <TablaDelRubro key={g.clave} grupo={g} moneda={moneda} />
        ))}
        <p className="cds--type-body-compact-01">
          <span>Rendimiento (unidades por día)</span> <strong>{formatoEsVe(detalle.rendimiento)}</strong>
        </p>
      </div>
      <div className="silice-hoja__apu-cierre">
        <section className="silice-hoja__seccion">
          <h3 className="cds--type-heading-compact-01">Cierre de partida</h3>
          <TablaDensa
            etiqueta="Cierre de partida"
            columnas={[
              { clave: "concepto", titulo: "Concepto", ordenable: false },
              {
                clave: "monto",
                titulo: "Monto",
                numerica: true,
                ordenable: false,
                celda: (f) => <Cifra monto={{ texto: f.monto!, exacto: f.monto_exacto! }} unidad={moneda} />,
              },
              { clave: "nota", titulo: "Nota", ordenable: false },
            ]}
            filas={detalle.cierre.map((c, i) => ({
              id: `cierre-${i}`,
              concepto: c.concepto,
              monto: c.monto.texto,
              monto_exacto: c.monto.exacto,
              nota: c.nota,
            }))}
          />
        </section>
        <dl className="silice-hoja__metricas">
          {(
            [
              ["Materiales", detalle.metricas.materiales],
              ["Equipos", detalle.metricas.equipos],
              ["Mano de obra", detalle.metricas.mano_obra],
              ["Precio unitario", detalle.metricas.precio_unitario],
            ] as const
          ).map(([rotulo, monto]) => (
            <div key={rotulo}>
              <dt className="cds--type-helper-text-01">{rotulo}</dt>
              <dd className="cds--type-heading-compact-02">
                <Cifra monto={monto} unidad={moneda} />
              </dd>
            </div>
          ))}
        </dl>
        {detalle.estados.map((e) => (
          <p key={e} className="cds--type-helper-text-01">
            {e}
          </p>
        ))}
      </div>
    </>
  );
}

// Pestaña «APU» en lectura: lista con buscador (lo filtra el servidor), tres rubros y cierre de la partida. El cambio de
// cantidades, de rendimiento y de insumo llega en la rebanada 3c.
export function PestanaApu({ id, moneda, alAusente }: Props) {
  const [escrito, setEscrito] = useState("");
  const [buscar, setBuscar] = useState("");
  const [partida, setPartida] = useState<string | undefined>(undefined);

  useEffect(() => {
    const espera = setTimeout(() => setBuscar(escrito.trim()), PAUSA_DE_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [escrito]);

  return (
    <VistaCarga<VistaApu> ruta={rutaDeVista(id, "apu", { partida, buscar })} etiqueta="APU" alAusente={alAusente}>
      {(vista, actualizando) =>
        vista.vacio_mensaje !== null ? (
          <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>
        ) : (
          <div className="silice-hoja__apu" aria-busy={actualizando}>
            <div className="silice-hoja__apu-lista">
              <Search
                size="sm"
                labelText="Buscar partida"
                placeholder="Código o descripción"
                value={escrito}
                onChange={(e: { target: { value: string } }) => setEscrito(e.target.value)}
              />
              {vista.sin_coincidencias && (
                <p className="cds--type-helper-text-01">Ninguna partida coincide; se muestran todas.</p>
              )}
              <RadioButtonGroup
                legendText="Partidas"
                name="partida-apu"
                orientation="vertical"
                valueSelected={vista.seleccionada ?? undefined}
                onChange={(valor) => setPartida(String(valor))}
              >
                {vista.partidas.map((p) => (
                  <RadioButton key={p.codigo} id={`apu-${p.codigo}`} value={p.codigo} labelText={`${p.codigo} · ${p.descripcion}`} />
                ))}
              </RadioButtonGroup>
            </div>
            {vista.detalle !== null && <Detalle detalle={vista.detalle} moneda={moneda} />}
          </div>
        )
      }
    </VistaCarga>
  );
}
