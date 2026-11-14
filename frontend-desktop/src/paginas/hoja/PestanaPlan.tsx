import { Button, Checkbox, RadioButton, RadioButtonGroup } from "@carbon/react";
import { InlineNotification } from "../../comun/carbonEs";
import { useCallback, useId, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { CurvaPlanAvance, periodoLegible } from "../../comun/CurvaPlanAvance";
import { mensajeDeError } from "../../comun/errores";
import { useAplicacion } from "../../shell/contexto";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { AyudaDePestana } from "./AyudaDePestana";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { enteroDeDigitos, esBorradorAusente, rutaDeVista } from "./logica";
import type { BaseAbierta, Resumen, VistaPlan } from "./logica";
import {
  FRASES_DE_RECHAZO,
  cambiarFraccion,
  claseDeConflicto,
  cuerpoDelPlan,
  rutaDePlan,
  sembrarPlan,
  ubicarErrorDePlan,
} from "./logicaSecciones";
import type { EdicionDelPlan } from "./logicaSecciones";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import type { ErrorDeSeccion } from "./useEdicionDeSeccion";
import { usePuedeEditarLaHoja } from "./puedeEditar";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
  // La base del borrador: con `solo_lectura` (o sin permiso de edición) no se pinta nada que escriba (F4 2b).
  base?: Pick<BaseAbierta, "solo_lectura">;
}

interface PropsContenido extends Props {
  vista: VistaPlan;
  alRelectura: () => void;
}

interface PropsEditor extends PropsContenido {
  // El plan que acaba de rehacerse desde los rendimientos: siembra la matriz en vez de `vista`, que llega después.
  semilla: VistaPlan | null;
  // F4 2b: sin permiso, cada fracción es texto.
  puedeEditar: boolean;
}

// --- plan desde los rendimientos (Tarea 21) ---

type Unidad = "dia" | "semana" | "mes";

// La unidad de un plan por sus etiquetas («Dia n», «Semana n», «Mes n»; las de `aplicacion.plan_rendimientos`). Un plan
// por meses se muestra como meses, no como días (ola 2 del 2026-11-13).
function unidadDelPlan(etiquetas: string[]): Unidad {
  const primera = etiquetas[0] ?? "";
  return primera.startsWith("Semana") ? "semana" : primera.startsWith("Mes") ? "mes" : "dia";
}

function unidadElegida(valor: unknown): Unidad {
  return valor === "semana" || valor === "mes" ? valor : "dia";
}

// `POST …/plan/rendimientos` con `{rev, cuadrillas: {codigo: texto}, paralelas: [codigo], unidad}`.
const rutaDeRendimientos = (id: string) => `${rutaDePlan(id)}/rendimientos`;

interface RespuestaDeRendimientos {
  rev: number;
  resumen: Resumen;
  plan: VistaPlan;
  avisos: string[];
}

interface Hecho {
  periodos: number;
  avisos: string[];
}

interface PropsRendimientos {
  id: string;
  rev: number;
  // Las partidas de la matriz, en el orden del presupuesto (sin plan no hay: van todas con una cuadrilla).
  partidas: string[];
  unidadInicial: Unidad;
  hayPlan: boolean;
  alAusente: () => void;
  alRecargarBorrador: () => Promise<void>;
  alReabrir: () => void;
  alRelectura: () => void;
  // El servidor rehízo el plan: su resumen y la vista nueva.
  alRehacer: (respuesta: RespuestaDeRendimientos) => void;
}

// La duración de cada partida sale de su cantidad, el rendimiento de su APU y las cuadrillas; el servidor encadena las
// partidas y reparte las fracciones. Aquí solo se teclea y se envía tal cual (las cuadrillas como texto).
function PlanDesdeRendimientos({
  id,
  rev,
  partidas,
  unidadInicial,
  hayPlan,
  alAusente,
  alRecargarBorrador,
  alReabrir,
  alRelectura,
  alRehacer,
}: PropsRendimientos) {
  const { alExpirar } = useAplicacion();
  const base = useId();
  const [cuadrillas, setCuadrillas] = useState<Record<string, string>>({});
  const [paralelas, setParalelas] = useState<string[]>([]);
  const [unidad, setUnidad] = useState<Unidad>(unidadInicial);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<ErrorDeSeccion<never> | null>(null);
  const [hecho, setHecho] = useState<Hecho | null>(null);

  const fallo = (e: unknown) => {
    if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
    else if (esBorradorAusente(e)) alAusente();
    else if (e instanceof ErrorDeApi && e.estado === 409) {
      const clase = claseDeConflicto(e.detalle);
      setError({ tipo: clase === "rev" ? "conflicto" : clase === "perdido" ? "perdido" : "otro", mensaje: e.detalle, ubicacion: null });
    } else if (e instanceof ErrorDeApi && e.estado === 422) setError({ tipo: "rechazo", mensaje: e.detalle, ubicacion: null });
    else setError({ tipo: "otro", mensaje: mensajeDeError(e), ubicacion: null });
  };

  const enviar = async () => {
    setEnviando(true);
    setError(null);
    setHecho(null);
    try {
      const respuesta = await pedir<RespuestaDeRendimientos>(rutaDeRendimientos(id), {
        metodo: "POST",
        cuerpo: {
          rev,
          cuadrillas: Object.fromEntries(partidas.map((p) => [p, cuadrillas[p] ?? "1"])),
          paralelas: partidas.filter((p, i) => i > 0 && paralelas.includes(p)),
          unidad,
        },
      });
      alRehacer(respuesta);
      setHecho({ periodos: respuesta.plan.etiquetas.length, avisos: respuesta.avisos });
    } catch (e) {
      fallo(e);
    } finally {
      setEnviando(false);
    }
  };

  // Tras un `rev` viejo: se vuelve a leer el borrador y la vista; lo tecleado aquí se conserva.
  const recargar = async () => {
    try {
      await alRecargarBorrador();
      setError(null);
      alRelectura();
    } catch (e) {
      fallo(e);
    }
  };

  const idTitulo = `${base}-titulo`;
  const estado = enviando
    ? "Haciendo el plan desde los rendimientos…"
    : hecho !== null
      ? `Plan hecho desde los rendimientos: ${hecho.periodos} ${hecho.periodos === 1 ? "período" : "períodos"}.`
      : "";
  return (
    <section className="silice-hoja__seccion" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Plan desde los rendimientos
      </h2>
      <p className="cds--type-body-compact-01">
        La duración de cada partida es su cantidad entre el rendimiento de su APU y las cuadrillas, redondeada hacia arriba al
        medio día. Las partidas van una tras otra en el orden del presupuesto, salvo las que marque en paralelo con la anterior.
      </p>
      <p className="cds--type-helper-text-01">
        {hayPlan
          ? "Rehace la matriz de abajo: lo que haya repartido a mano se reemplaza."
          : "Indique las cuadrillas de cada partida y las que van en paralelo, y haga el plan."}
      </p>
      {partidas.length > 0 && (
        <TablaPaginada
          etiqueta="Cuadrillas y partidas en paralelo"
          columnas={[
            { clave: "partida", titulo: "Partida", ordenable: false },
            {
              clave: "cuadrillas",
              titulo: "Cuadrillas",
              ordenable: false,
              celda: (f) => (
                <CampoTexto
                  id={`${base}-cuadrillas-${f.n}`}
                  labelText={`Cuadrillas de ${f.partida}`}
                  hideLabel
                  size="sm"
                  value={cuadrillas[f.partida!] ?? "1"}
                  onChange={(e) => {
                    const texto = e.target.value;
                    setCuadrillas((previas) => ({ ...previas, [f.partida!]: texto }));
                  }}
                />
              ),
            },
            {
              clave: "paralela",
              titulo: "En paralelo con la anterior",
              ordenable: false,
              celda: (f) => (
                <Checkbox
                  id={`${base}-paralela-${f.n}`}
                  labelText={`${f.partida} en paralelo con la anterior`}
                  hideLabel
                  disabled={f.n === "0"}
                  checked={paralelas.includes(f.partida!)}
                  onChange={(_, { checked }) =>
                    setParalelas((previas) => (checked ? [...previas, f.partida!] : previas.filter((p) => p !== f.partida)))
                  }
                />
              ),
            },
          ]}
          filas={partidas.map((partida, i) => ({ id: `rend-${i}`, n: String(i), partida }))}
        />
      )}
      <RadioButtonGroup
        legendText="Períodos del plan"
        name={`${base}-unidad`}
        valueSelected={unidad}
        onChange={(valor) => setUnidad(unidadElegida(valor))}
      >
        <RadioButton id={`${base}-dia`} labelText="Días hábiles" value="dia" />
        <RadioButton id={`${base}-semana`} labelText="Semanas (5 días hábiles)" value="semana" />
        <RadioButton id={`${base}-mes`} labelText="Meses (20 días hábiles)" value="mes" />
      </RadioButtonGroup>
      <p className="cds--type-helper-text-01" aria-live="polite">
        {estado}
      </p>
      {hecho !== null && hecho.avisos.length > 0 && (
        <InlineNotification
          kind="warning"
          lowContrast
          hideCloseButton
          role="status"
          aria-labelledby={`${base}-avisos`}
          title="Revise estas partidas"
        >
          {/* Carbon usa `aria-label` para el botón de cerrar: el nombre de la región va por `aria-labelledby`. */}
          <span id={`${base}-avisos`} className="cds--visually-hidden">
            Avisos del plan
          </span>
          <ul>
            {hecho.avisos.map((aviso) => (
              <li key={aviso}>{aviso}</li>
            ))}
          </ul>
        </InlineNotification>
      )}
      {error !== null && <AvisoDeEdicion error={error} id={`${base}-error`} alRecargar={() => void recargar()} alReabrir={alReabrir} />}
      <div>
        <Button kind="tertiary" size="sm" disabled={enviando} onClick={() => void enviar()}>
          Plan desde los rendimientos
        </Button>
      </div>
    </section>
  );
}

const idDeFraccion = (fila: number, periodo: number) => `hoja-plan-${fila}-${periodo}`;

function CurvaDeInversion({ vista }: { vista: VistaPlan }) {
  return (
    <section className="silice-hoja__seccion">
      <h2 className="cds--type-heading-compact-02">Curva de inversión</h2>
      <CurvaPlanAvance
        titulo="Curva de inversión"
        unidad={vista.moneda}
        series={[
          {
            nombre: "Acumulado",
            rol: "plan",
            puntos: vista.curva.map((p) => ({ periodo: p.periodo, valor: p.acumulado.texto })),
          },
        ]}
      />
      <TablaPaginada
        etiqueta="Curva de inversión: montos"
        columnas={[
          { clave: "periodo", titulo: "Período", ordenable: false },
          {
            clave: "monto",
            titulo: "Monto",
            numerica: true,
            ordenable: false,
            celda: (f) => <Cifra monto={{ texto: f.monto!, exacto: f.monto_exacto! }} />,
          },
          {
            clave: "acumulado",
            titulo: "Acumulado",
            numerica: true,
            ordenable: false,
            celda: (f) => <Cifra monto={{ texto: f.acumulado!, exacto: f.acumulado_exacto! }} />,
          },
          {
            clave: "porcentaje",
            titulo: "% acumulado",
            numerica: true,
            ordenable: false,
            celda: (f) => <Cifra monto={{ texto: f.porcentaje!, exacto: f.porcentaje_exacto! }} />,
          },
        ]}
        filas={vista.curva.map((p, i) => ({
          id: `curva-${i}`,
          periodo: periodoLegible(p.periodo),
          monto: p.monto.texto,
          monto_exacto: p.monto.exacto,
          acumulado: p.acumulado.texto,
          acumulado_exacto: p.acumulado.exacto,
          porcentaje: p.porcentaje.texto,
          porcentaje_exacto: p.porcentaje.exacto,
        }))}
      />
    </section>
  );
}

function EditorDelPlan({ id, rev, vista, semilla, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura, puedeEditar }: PropsEditor) {
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<EdicionDelPlan, string>({
    borrador: id,
    inicial: sembrarPlan(semilla ?? vista),
    rev,
    peticion: (r, plan) => ({ ruta: rutaDePlan(id), metodo: "PUT", cuerpo: cuerpoDelPlan(r, plan) }),
    ubicar: ubicarErrorDePlan,
    frase: FRASES_DE_RECHAZO.plan,
    leerFresca: async () => sembrarPlan(await pedir<VistaPlan>(rutaDeVista(id, "plan"))),
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const { error } = edicion;
  const partidaInvalida = error?.ubicacion ?? null;
  const filas = edicion.estado.filas;
  const etiquetas = edicion.estado.etiquetas;
  const irAPartida = () => {
    const i = filas.findIndex((f) => f.partida === partidaInvalida);
    if (i >= 0) document.getElementById(idDeFraccion(i + 1, 0))?.focus();
  };

  return (
    <div className="silice-hoja__pestana">
      <AvisoDeEnvio envio={edicion.envio} />
      {error !== null && (
        <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void edicion.recargar()} alReabrir={alReabrir}>
          {partidaInvalida !== null && filas.some((f) => f.partida === partidaInvalida) && (
            <Button kind="ghost" size="sm" onClick={irAPartida}>
              {`Ir a la partida ${partidaInvalida}`}
            </Button>
          )}
        </AvisoDeEdicion>
      )}
      <TablaPaginada
        etiqueta="Plan de trabajo"
        desplazable
        columnas={[
          { clave: "partida", titulo: "Partida", ordenable: false },
          ...etiquetas.map((etiqueta, j) => ({
            clave: `e${j}`,
            titulo: periodoLegible(etiqueta),
            numerica: true,
            ordenable: false,
            celda: (f: { id: string } & Record<string, string>) => {
              const n = enteroDeDigitos(f.n!);
              return (
                <CampoDeCelda
                  soloLectura={!puedeEditar}
                  id={idDeFraccion(n, j)}
                  etiqueta={`${periodoLegible(etiqueta)}, Plan de trabajo fila ${n}`}
                  valor={f[`e${j}`]!}
                  invalido={partidaInvalida !== null && partidaInvalida === f.partida}
                  textoInvalido={j === 0 ? "Revise esta partida" : ""}
                  descripcionId={idDelError}
                  alCambiar={(texto) => edicion.cambiar((previo) => cambiarFraccion(previo, f.partida!, etiqueta, texto))}
                  alRestaurar={() =>
                    edicion.cambiar((previo) =>
                      cambiarFraccion(
                        previo,
                        f.partida!,
                        etiqueta,
                        edicion.aceptado().filas.find((a) => a.partida === f.partida)?.valores[etiqueta] ?? "",
                      ),
                    )
                  }
                />
              );
            },
          })),
        ]}
        filas={filas.map((f, i) => ({
          id: `plan-${i}`,
          n: String(i + 1),
          partida: f.partida,
          ...Object.fromEntries(etiquetas.map((e, j) => [`e${j}`, f.valores[e] ?? ""])),
        }))}
      />
      <CurvaDeInversion vista={vista} />
    </div>
  );
}

function ContenidoPlan(props: PropsContenido) {
  const { id, rev, vista, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura } = props;
  const puedeEditar = usePuedeEditarLaHoja(props.base ?? null);
  // Cada plan rehecho desde los rendimientos vuelve a montar la matriz con el plan que contestó el servidor (la matriz solo
  // se siembra al montar).
  const [rehecho, setRehecho] = useState<{ n: number; plan: VistaPlan } | null>(null);
  const rendimientos = (
    <PlanDesdeRendimientos
      id={id}
      rev={rev}
      partidas={vista.partidas ?? vista.filas.map((f) => f.partida)}
      unidadInicial={unidadDelPlan(vista.etiquetas)}
      hayPlan={vista.hay_plan}
      alAusente={alAusente}
      alRecargarBorrador={alRecargarBorrador}
      alReabrir={alReabrir}
      alRelectura={alRelectura}
      alRehacer={(respuesta) => {
        setRehecho((previo) => ({ n: (previo?.n ?? 0) + 1, plan: respuesta.plan }));
        alAceptar(respuesta.resumen);
        alRelectura();
      }}
    />
  );
  // Cada pieza ocupa siempre el mismo lugar: «Plan desde los rendimientos» no se vuelve a montar cuando el plan aparece, y
  // sus avisos siguen a la vista.
  return (
    <div className="silice-hoja__pestana">
      <AyudaDePestana id="plan" puedeEditar={puedeEditar} />
      {!vista.hay_plan && (
        <div className="silice-hoja__seccion">
          <p className="cds--type-body-compact-01">{vista.mensaje}</p>
        </div>
      )}
      {puedeEditar && rendimientos}
      {vista.hay_plan && (
        <EditorDelPlan key={rehecho?.n ?? 0} {...props} semilla={rehecho?.plan ?? null} puedeEditar={puedeEditar} />
      )}
    </div>
  );
}

// Pestaña «Plan y equilibrio» (antes «Plan y curva», Tarea 4): la matriz de fracciones se edita como texto y la curva se recalcula (rebanada 3c-2); el plan se
// puede rehacer desde los rendimientos (Tarea 21).
export function PestanaPlan(props: Props) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaPlan> ruta={rutaDeVista(props.id, "plan")} etiqueta="el plan de trabajo" alAusente={props.alAusente} recarga={lecturas}>
      {(vista) => <ContenidoPlan {...props} vista={vista} alRelectura={alRelectura} />}
    </VistaCarga>
  );
}
