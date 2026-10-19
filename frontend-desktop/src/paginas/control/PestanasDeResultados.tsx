import { Button, InlineNotification, RadioButton, RadioButtonGroup, Select, SelectItem, TextInput } from "@carbon/react";
import { useState } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CurvaPlanAvance } from "../../comun/CurvaPlanAvance";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  COLUMNAS_ALERTAS,
  COLUMNAS_DECISIONES,
  COLUMNAS_INDICADORES,
  COLUMNAS_OPCIONES,
  COLUMNAS_REPROYECCION,
  ROTULO_DE_METODO,
  columnasDe,
  conId,
  cuerpoDeOpciones,
  etiquetaDeCodigo,
  textoLlano,
  useAccion,
} from "./logica";
import type { Calculo, Filtros, MetodoDePrecios, OpcionDeRecuperacion } from "./logica";

// --- el corte y los precios del corte, comunes a las tres pestañas ---------------------------

export function BarraDeCorte({
  filtros,
  versiones,
  alAplicar,
}: {
  filtros: Filtros;
  versiones: string[];
  alAplicar: (f: Filtros) => void;
}) {
  const [borrador, setBorrador] = useState(filtros);
  const precios = borrador.precios;
  const cambiarPrecios = (cambio: Partial<typeof precios>) => setBorrador({ ...borrador, precios: { ...precios, ...cambio } });
  return (
    <form
      className="silice-control__corte"
      onSubmit={(e) => {
        e.preventDefault();
        alAplicar(borrador);
      }}
    >
      <TextInput
        id="corte-fecha"
        type="date" labelText="Fecha de corte (vacía: la última valuación)"
        value={borrador.corte}
        onChange={(e) => setBorrador({ ...borrador, corte: e.target.value })}
      />
      <Select
        id="corte-metodo"
        labelText="Precios del corte"
        value={precios.metodo}
        onChange={(e) => cambiarPrecios({ metodo: e.target.value as MetodoDePrecios })}
      >
        {(Object.keys(ROTULO_DE_METODO) as MetodoDePrecios[]).map((m) => (
          <SelectItem key={m} value={m} text={ROTULO_DE_METODO[m]} />
        ))}
      </Select>
      {precios.metodo === "comprobacion" && (
        <Select id="corte-version" labelText="Versión revalorada" value={precios.version} onChange={(e) => cambiarPrecios({ version: e.target.value })}>
          <SelectItem value="" text={versiones.length ? "Elija una" : "El proyecto no tiene versiones revaloradas"} />
          {versiones.map((v) => (
            <SelectItem key={v} value={v} text={v} />
          ))}
        </Select>
      )}
      {precios.metodo === "escalatoria" && (
        <>
          <TextInput id="corte-km" labelText="Km declarado" value={precios.km} onChange={(e) => cambiarPrecios({ km: e.target.value })} />
          <TextInput id="corte-r" labelText="R declarado" value={precios.r} onChange={(e) => cambiarPrecios({ r: e.target.value })} />
          <TextInput id="corte-fuente" labelText="Fuente de Km y R" value={precios.fuente} onChange={(e) => cambiarPrecios({ fuente: e.target.value })} />
        </>
      )}
      <div>
        <Button type="submit" kind="secondary" size="md">
          Calcular al corte
        </Button>
      </div>
    </form>
  );
}

// --- Valor ganado ----------------------------------------------------------------------------

export function ValorGanado({ calculo }: { calculo: Calculo }) {
  const moneda = calculo.moneda ?? "";
  const curva = calculo.curva;
  return (
    <>
      <p className="silice-control__nota cds--type-helper-text-01">
        {`Corte ${calculo.corte} (día hábil ${calculo.dia}). Las fórmulas de valor ganado son definiciones del sistema; el EAC del sistema y la separación del desvío son propios de este trabajo. Sin proyectar inflación futura.`}
      </p>
      {calculo.costos_sin_tasa.map((texto) => (
        <InlineNotification key={texto} kind="warning" lowContrast hideCloseButton role="status" title={texto} />
      ))}
      <TablaDensa
        etiqueta="Indicadores de valor ganado"
        columnas={columnasDe(COLUMNAS_INDICADORES, ["Valor", "En la otra moneda"])}
        filas={conId(calculo.indicadores)}
      />
      {curva.length > 0 && (
        <section className="silice-control__bloque" aria-labelledby="control-curva">
          <h2 id="control-curva" className="cds--type-heading-compact-02">
            PV, EV y AC al cierre de cada período
          </h2>
          <CurvaPlanAvance
            titulo="PV, EV y AC"
            unidad={moneda}
            series={[
              { nombre: "PV", rol: "plan", puntos: curva.map((p) => ({ periodo: p.periodo, valor: p.pv })) },
              { nombre: "EV", rol: "real", puntos: curva.map((p) => ({ periodo: p.periodo, valor: p.ev })) },
              {
                nombre: "AC",
                rol: "real",
                puntos: curva.flatMap((p) => (p.ac === null ? [] : [{ periodo: p.periodo, valor: p.ac }])),
              },
            ]}
          />
        </section>
      )}
      {calculo.spi_no_aplica && (
        <p className="silice-control__nota cds--type-helper-text-01">El corte es anterior a todo trabajo planificado: el SPI no aplica.</p>
      )}
    </>
  );
}

// --- Alertas y reproyección ------------------------------------------------------------------

export function AlertasYReproyeccion({ calculo }: { calculo: Calculo }) {
  const t = calculo.terminos;
  return (
    <>
      <section className="silice-control__bloque" aria-labelledby="control-alertas">
        <h2 id="control-alertas" className="cds--type-heading-compact-02">
          Alertas
        </h2>
        <TablaDensa etiqueta="Alertas" columnas={columnasDe(COLUMNAS_ALERTAS, ["Observado", "Umbral"], { Alerta: etiquetaDeCodigo, Umbral: textoLlano })} filas={conId(calculo.alertas)} />
      </section>
      <section className="silice-control__bloque" aria-labelledby="control-terminos">
        <h2 id="control-terminos" className="cds--type-heading-compact-02">
          Término, costo final y punto de equilibrio
        </h2>
        {t && (
          <ul className="cds--type-body-compact-01">
            <li>{`Término por el índice: ${t.indice}`}</li>
            <li>{`Término por el plan reproyectado: ${t.reproyectado}`}</li>
            <li>{`Término del plan base: ${t.plan_base}`}</li>
            <li>{`EAC (sistema): ${t.eac_sistema}`}</li>
          </ul>
        )}
        {calculo.motivo_termino && <p className="silice-control__nota cds--type-helper-text-01">{calculo.motivo_termino}</p>}
        <p className="cds--type-body-compact-01">
          {calculo.equilibrio
            ? `Punto de equilibrio proyectado: ${calculo.equilibrio.punto} (${calculo.equilibrio.mensaje})`
            : "Punto de equilibrio proyectado: no disponible (perspectiva precio o AC/EAC)."}
        </p>
        <p className="silice-control__nota cds--type-helper-text-01">{calculo.estudios}</p>
      </section>
      <section className="silice-control__bloque" aria-labelledby="control-reproyeccion">
        <h2 id="control-reproyeccion" className="cds--type-heading-compact-02">
          Reproyección por partida
        </h2>
        <TablaDensa
          etiqueta="Reproyección por partida"
          columnas={columnasDe(COLUMNAS_REPROYECCION, ["Indice", "Fin (dia habil)"])}
          filas={conId(calculo.reproyeccion)}
        />
      </section>
      {calculo.plan && (
        <section className="silice-control__bloque" aria-labelledby="control-plan">
          <h2 id="control-plan" className="cds--type-heading-compact-02">
            Plan reproyectado
          </h2>
          <TablaDensa
            etiqueta="Plan reproyectado"
            columnas={columnasDe(calculo.plan.columnas, calculo.plan.columnas.slice(1))}
            filas={conId(calculo.plan.filas)}
          />
        </section>
      )}
    </>
  );
}

// --- Recuperación ----------------------------------------------------------------------------

export function Recuperacion({
  proyecto,
  filtros,
  calculo,
  puedeDecidir,
  alDecidir,
}: {
  proyecto: string;
  filtros: Filtros;
  calculo: Calculo;
  puedeDecidir: boolean;
  alDecidir: () => void;
}) {
  const { alExpirar } = useAplicacion();
  const calculando = useAccion(alExpirar);
  const eligiendo = useAccion(alExpirar, alDecidir);
  const [objetivo, setObjetivo] = useState("");
  const [horas, setHoras] = useState("0");
  const [opciones, setOpciones] = useState<OpcionDeRecuperacion[] | null>(null);
  const [elegida, setElegida] = useState("");
  const [declaracion, setDeclaracion] = useState("");
  const [fuente, setFuente] = useState("");

  const calcular = () =>
    calculando.ejecutar(async () => {
      const r = await pedir<{ opciones: OpcionDeRecuperacion[] }>("/v1/control/recuperacion/opciones", {
        metodo: "POST",
        cuerpo: cuerpoDeOpciones(proyecto, filtros, objetivo, horas),
      });
      setOpciones(r.opciones);
      setElegida("");
      return "";
    });
  const aplican = (opciones ?? []).filter((o) => o.aplica);
  const actual = aplican.find((o) => o.clave === elegida);
  const elegir = () =>
    eligiendo.ejecutar(async () => {
      const r = await pedir<{ version: string }>("/v1/control/recuperacion/elegir", {
        metodo: "POST",
        cuerpo: {
          ...cuerpoDeOpciones(proyecto, filtros, objetivo, horas),
          opcion: elegida,
          fuente,
          declaracion_independencia: declaracion,
        },
      });
      setOpciones(null);
      return `Versión ${r.version} creada con el plan de la opción elegida.`;
    });

  return (
    <>
      <p className="silice-control__nota cds--type-helper-text-01">
        Las opciones se calculan a pedido, cada una sola, con el rendimiento y la cuadrilla de cada APU y un factor de
        eficiencia declarado (supuesto, no dato). Elegir una crea una versión nueva; la línea base no cambia.
      </p>
      <div className="silice-control__formulario">
        <TextInput id="rec-objetivo" labelText="Día hábil objetivo (vacío: el fin del plan base)" value={objetivo} onChange={(e) => setObjetivo(e.target.value)} />
        <TextInput id="rec-horas" labelText="Horas extra que el obrero ya acumula en el año" value={horas} onChange={(e) => setHoras(e.target.value)} />
        <div>
          <Button kind="secondary" size="md" disabled={calculando.estado.enviando} onClick={() => void calcular()}>
            Calcular opciones
          </Button>
        </div>
        <AvisoError error={calculando.estado.error} titulo="No se pudieron calcular las opciones" />
      </div>
      {opciones && (
        <section className="silice-control__bloque" aria-labelledby="control-opciones">
          <h2 id="control-opciones" className="cds--type-heading-compact-02">
            Opciones de recuperación
          </h2>
          <TablaDensa
            etiqueta="Opciones de recuperación"
            columnas={columnasDe(COLUMNAS_OPCIONES, COLUMNAS_OPCIONES.slice(1, 7))}
            filas={conId(opciones.map((o) => o.fila))}
          />
          {opciones.map(
            (o) =>
              o.requisitos.length > 0 && (
                <p key={o.clave} className="silice-control__nota cds--type-helper-text-01">
                  {`${o.titulo}: requiere ${o.requisitos.join("; ")}`}
                </p>
              ),
          )}
          {aplican.length === 0 ? (
            <p className="cds--type-body-compact-01">Ninguna opción aplica a este corte.</p>
          ) : !puedeDecidir ? (
            <p className="cds--type-body-compact-01">
              Su cuenta puede ver las opciones, pero no elegir una (decide quien arma la obra).
            </p>
          ) : (
            <div className="silice-control__formulario">
              <RadioButtonGroup legendText="Opción a aplicar" name="rec-elegida" valueSelected={elegida} onChange={(v) => setElegida(String(v))} orientation="vertical">
                {aplican.map((o) => (
                  <RadioButton key={o.clave} id={`rec-${o.clave}`} labelText={o.titulo} value={o.clave} />
                ))}
              </RadioButtonGroup>
              {actual?.requiere_declaracion && (
                <TextInput
                  id="rec-independencia"
                  labelText="Declaro que estas partidas no dependen de las que están en curso (con su fuente)"
                  value={declaracion}
                  onChange={(e) => setDeclaracion(e.target.value)}
                />
              )}
              <TextInput id="rec-fuente" labelText="Fuente de la decisión" value={fuente} onChange={(e) => setFuente(e.target.value)} />
              <div>
                <Button kind="primary" size="md" disabled={!elegida || eligiendo.estado.enviando} onClick={() => void elegir()}>
                  Elegir y crear la versión
                </Button>
              </div>
              <AvisoError error={eligiendo.estado.error} titulo="No se creó la versión" />
            </div>
          )}
        </section>
      )}
      {eligiendo.estado.exito && (
        <InlineNotification kind="success" lowContrast hideCloseButton role="status" title={eligiendo.estado.exito} />
      )}
      {calculo.decisiones.length > 0 ? (
        <section className="silice-control__bloque" aria-labelledby="control-decisiones">
          <h2 id="control-decisiones" className="cds--type-heading-compact-02">
            Decisiones tomadas
          </h2>
          <TablaDensa etiqueta="Decisiones tomadas" columnas={columnasDe(COLUMNAS_DECISIONES)} filas={conId(calculo.decisiones)} />
        </section>
      ) : (
        <EstadoVacio titulo="Aún no se ha tomado ninguna decisión de recuperación" />
      )}
    </>
  );
}
