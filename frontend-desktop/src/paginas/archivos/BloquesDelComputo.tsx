import { Button, Checkbox, RadioButton, RadioButtonGroup, Select, SelectItem } from "@carbon/react";
import { useId, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import type { Carga } from "../../comun/useCarga";
import {
  AVISO_SIN_PARTIDAS_CIVILES,
  TEXTO_PENDIENTES,
  TEXTO_RENDIMIENTOS,
  errorSinPropuestaDeRendimiento,
  errorSinTipo,
  lineaPendiente,
  lineaPropuesta,
  textoDispersion,
  textoPropuestaRendimiento,
} from "./logicaComputo";
import type { SeleccionCivil } from "./logicaComputo";
import type { PartidaCatalogo, PendienteConPropuestas, RendimientoPorDeclarar, TipoRendimiento } from "./tipos";

// Por qué existe (Tarea 12 del plan F4): los tres bloques que «Cargar cómputo» heredó de la pantalla Elaborar (baja 19),
// «Códigos de partida (civil)», «Rendimientos por declarar» y «Pendientes», con su comportamiento de entonces: los
// selectores civiles no eligen nada solos, un rendimiento se declara estimado o medido y un pendiente se resuelve con una
// propuesta del catálogo. Viven aparte de `CargarComputo.tsx` para que ninguno de los dos pase de 250 líneas; solo los usa
// ese diálogo.

type ClaveCivil = keyof SeleccionCivil;
const SELECTORES_CIVIL: { clave: Exclude<ClaveCivil, "relleno">; titulo: string }[] = [
  { clave: "concreto", titulo: "Concreto" },
  { clave: "encofrado", titulo: "Encofrado" },
  { clave: "excavacion", titulo: "Excavación" },
  { clave: "tuberia", titulo: "Tubería" },
];

export interface CodigosElegidos {
  codigos: Partial<Record<ClaveCivil, string>>;
  conRelleno: boolean;
}
export const SIN_CODIGOS: CodigosElegidos = { codigos: {}, conRelleno: false };

// Lo que espera `mapeoCodigos`: los cuatro códigos y el relleno solo si se pidió.
export function seleccionCivil({ codigos, conRelleno }: CodigosElegidos): SeleccionCivil {
  const de = (clave: ClaveCivil) => codigos[clave] ?? "";
  return {
    concreto: de("concreto"),
    encofrado: de("encofrado"),
    excavacion: de("excavacion"),
    tuberia: de("tuberia"),
    relleno: conRelleno ? de("relleno") : null,
  };
}

// Se puede extraer un cómputo civil con el catálogo civil leído y los cuatro códigos (y el relleno, si se pidió).
export function codigosCompletos(elegidos: CodigosElegidos, partidas: readonly PartidaCatalogo[]): boolean {
  const s = seleccionCivil(elegidos);
  return partidas.length > 0 && SELECTORES_CIVIL.every(({ clave }) => s[clave] !== "") && s.relleno !== "";
}

function OpcionesDePartida({ partidas }: { partidas: readonly PartidaCatalogo[] }) {
  return (
    <>
      <SelectItem value="" text="Elija una partida" disabled />
      {partidas.map((p) => (
        <SelectItem key={p.codigo} value={p.codigo} text={`${p.codigo} · ${p.descripcion}`} title={p.descripcion} />
      ))}
    </>
  );
}

export function CodigosCiviles({
  carga,
  partidas,
  elegidos,
  alCambiar,
}: {
  carga: Carga<PartidaCatalogo[]>;
  partidas: readonly PartidaCatalogo[];
  elegidos: CodigosElegidos;
  alCambiar: (e: CodigosElegidos) => void;
}) {
  const idTitulo = useId();
  const elegir = (clave: ClaveCivil, valor: string) => alCambiar({ ...elegidos, codigos: { ...elegidos.codigos, [clave]: valor } });
  return (
    <section aria-labelledby={idTitulo} className="silice-computo__bloque">
      <h4 id={idTitulo} className="cds--type-heading-compact-01">
        Códigos de partida (civil)
      </h4>
      {carga.estado !== "listo" && carga.estado !== "cargando" && <AvisoError error={carga.error} titulo="No se pudo leer el catálogo" />}
      {carga.estado === "cargando" && <p className="cds--type-label-01">Cargando las partidas civiles del catálogo...</p>}
      {carga.estado !== "cargando" && partidas.length === 0 && (
        <p className="silice-computo__aviso cds--type-body-compact-01" role="status">
          {AVISO_SIN_PARTIDAS_CIVILES}
        </p>
      )}
      {partidas.length > 0 && (
        <div className="silice-computo__selectores">
          {SELECTORES_CIVIL.map(({ clave, titulo }) => (
            <Select key={clave} id={`computo-civil-${clave}`} labelText={titulo} size="sm" value={elegidos.codigos[clave] ?? ""} onChange={(e) => elegir(clave, e.target.value)}>
              <OpcionesDePartida partidas={partidas} />
            </Select>
          ))}
          <Checkbox
            id="computo-civil-con-relleno"
            labelText="Incluir relleno (balance R5)"
            checked={elegidos.conRelleno}
            onChange={(_e, { checked }) => alCambiar({ ...elegidos, conRelleno: checked })}
          />
          {elegidos.conRelleno && (
            <Select id="computo-civil-relleno" labelText="Relleno" size="sm" value={elegidos.codigos.relleno ?? ""} onChange={(e) => elegir("relleno", e.target.value)}>
              <OpcionesDePartida partidas={partidas} />
            </Select>
          )}
        </div>
      )}
    </section>
  );
}

// Un 409 de la valoración con rendimientos por declarar (UC-01 3b): se declara cada uno y luego se vuelve a llevar.
export function Rendimientos({
  lista,
  ocupado,
  alRegistrar,
}: {
  lista: RendimientoPorDeclarar[];
  ocupado: boolean;
  alRegistrar: (entrada: RendimientoPorDeclarar, tipo: TipoRendimiento) => void;
}) {
  const idTitulo = useId();
  const [tipos, setTipos] = useState<Record<string, TipoRendimiento>>({});
  const [sinTipo, setSinTipo] = useState<string | null>(null);
  const registrar = (entrada: RendimientoPorDeclarar) => {
    const tipo = tipos[entrada.codigo_partida];
    if (!tipo) {
      setSinTipo(errorSinTipo(entrada.codigo_partida));
      return;
    }
    setSinTipo(null);
    alRegistrar(entrada, tipo);
  };
  return (
    <section aria-labelledby={idTitulo} className="silice-computo__bloque">
      <h4 id={idTitulo} className="cds--type-heading-compact-01">
        Rendimientos por declarar
      </h4>
      <p className="silice-computo__nota cds--type-body-compact-01">{TEXTO_RENDIMIENTOS}</p>
      {lista.map((entrada) => {
        const cod = entrada.codigo_partida;
        if (entrada.propuesta === null) {
          return <AvisoError key={cod} error={errorSinPropuestaDeRendimiento(cod)} titulo="Sin rendimiento que proponer" />;
        }
        return (
          <div key={cod} className="silice-computo__bloque">
            <p className="cds--type-body-compact-01">
              <strong>{cod}</strong>
              {` · ${textoPropuestaRendimiento(entrada)}`}
            </p>
            <p className="silice-computo__nota cds--type-label-01">{textoDispersion(entrada)}</p>
            <RadioButtonGroup
              legendText={`Tipo declarado del rendimiento de ${cod}`}
              name={`computo-tipo-rendimiento-${cod}`}
              role="radiogroup"
              valueSelected={tipos[cod]}
              onChange={(valor) => setTipos({ ...tipos, [cod]: valor as TipoRendimiento })}
            >
              <RadioButton id={`computo-tipo-${cod}-estimado`} labelText="estimado" value="estimado" />
              <RadioButton id={`computo-tipo-${cod}-medido`} labelText="medido" value="medido" />
            </RadioButtonGroup>
            <Button kind="tertiary" size="sm" disabled={ocupado} onClick={() => registrar(entrada)}>
              Registrar el rendimiento
            </Button>
          </div>
        );
      })}
      {sinTipo !== null && <AvisoError error={sinTipo} titulo="Falta el tipo del rendimiento" />}
    </section>
  );
}

// Los ítems sin partida en el catálogo (UC-01 3a): no se pueden llevar así. Cada uno con sus propuestas; aplicar una
// cambia el código del ítem. `alLlevarSinEllos` no llega si ningún otro ítem se puede llevar.
export function Pendientes({
  lista,
  ocupado,
  alAplicar,
  alLlevarSinEllos,
}: {
  lista: PendienteConPropuestas[];
  ocupado: boolean;
  alAplicar: (pendiente: PendienteConPropuestas, elegido: string) => void;
  alLlevarSinEllos?: () => void;
}) {
  const idTitulo = useId();
  const [elegidas, setElegidas] = useState<Record<string, string>>({});
  const clave = (p: PendienteConPropuestas) => `${p.origen_id}|${p.codigo_partida}`;
  return (
    <section aria-labelledby={idTitulo} className="silice-computo__bloque">
      <h4 id={idTitulo} className="cds--type-heading-compact-01">
        Pendientes
      </h4>
      <p className="silice-computo__nota cds--type-body-compact-01">{TEXTO_PENDIENTES}</p>
      {lista.map((p, n) => {
        const elegido = elegidas[clave(p)] ?? p.propuestas[0]?.codigo ?? "";
        return (
          <div key={clave(p)} className="silice-computo__pendiente">
            <p className="cds--type-body-compact-01">{lineaPendiente(p)}</p>
            {p.falla !== null && <p className="silice-computo__nota cds--type-label-01">{p.falla}</p>}
            {p.propuestas.length > 0 && (
              <>
                <ul className="silice-computo__propuestas cds--type-body-compact-01">
                  {p.propuestas.map((s) => (
                    <li key={s.codigo}>{lineaPropuesta(s)}</li>
                  ))}
                </ul>
                <div className="silice-computo__acciones">
                  <Select id={`computo-propuesta-${n}`} labelText={`Propuesta para ${p.origen_id}`} size="sm" value={elegido} onChange={(e) => setElegidas({ ...elegidas, [clave(p)]: e.target.value })}>
                    {p.propuestas.map((s) => (
                      <SelectItem key={s.codigo} value={s.codigo} text={s.codigo} />
                    ))}
                  </Select>
                  <Button kind="tertiary" size="sm" disabled={ocupado} onClick={() => alAplicar(p, elegido)}>
                    Aplicar la propuesta
                  </Button>
                </div>
              </>
            )}
          </div>
        );
      })}
      {alLlevarSinEllos && (
        <div>
          <Button kind="secondary" size="md" disabled={ocupado} onClick={alLlevarSinEllos}>
            Llevar sin los pendientes
          </Button>
        </div>
      )}
    </section>
  );
}
