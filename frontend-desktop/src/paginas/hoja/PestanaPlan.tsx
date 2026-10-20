import { Button } from "@carbon/react";
import { useCallback, useId, useState } from "react";
import { pedir } from "../../api/cliente";
import { CurvaPlanAvance, periodoLegible } from "../../comun/CurvaPlanAvance";
import { useAplicacion } from "../../shell/contexto";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { enteroDeDigitos, rutaDeVista } from "./logica";
import type { Resumen, VistaPlan } from "./logica";
import { FRASES_DE_RECHAZO, cambiarFraccion, cuerpoDelPlan, rutaDePlan, rutaDePlanSecuencial, sembrarPlan, ubicarErrorDePlan } from "./logicaSecciones";
import type { EdicionDelPlan } from "./logicaSecciones";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import type { Peticion } from "./useEdicionDeSeccion";

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
}

interface PropsContenido extends Props {
  vista: VistaPlan;
  alRelectura: () => void;
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

function EditorDelPlan({ id, rev, vista, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura }: PropsContenido) {
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<EdicionDelPlan, string>({
    borrador: id,
    inicial: sembrarPlan(vista),
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
      <p className="cds--type-body-compact-01">
        Reparta cada partida entre los períodos: cada fila debe sumar exactamente 1. Los montos, los acumulados y los porcentajes de la
        curva se calculan.
      </p>
      <p className="cds--type-helper-text-01">
        Decimales con punto, por ejemplo 2.5: la coma no se acepta. Los cambios se aplican al borrador cuando deja de escribir; no se
        guardan como versión hasta que lo pida.
      </p>
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

const crearPlan = (rev: number, id: string): Peticion => ({ ruta: rutaDePlanSecuencial(id), metodo: "POST", cuerpo: { rev } });

function ContenidoPlan(props: PropsContenido) {
  const { id, rev, vista, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura } = props;
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  // «Crear plan secuencial» (E5) no espera la pausa. Su motor vive aquí para que su aviso siga a la vista cuando el plan
  // aparece (por ejemplo, «ya tiene plan» porque otra ventana lo creó).
  const creacion = useEdicionDeSeccion<null, never>({
    borrador: id,
    inicial: null,
    rev,
    peticion: (r) => crearPlan(r, id),
    ubicar: () => null,
    frase: FRASES_DE_RECHAZO.plan,
    leerFresca: async () => null,
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  return (
    <>
      {creacion.error !== null && (
        <AvisoDeEdicion error={creacion.error} id={idDelError} alRecargar={() => void creacion.recargar()} alReabrir={alReabrir} />
      )}
      {vista.hay_plan ? (
        <EditorDelPlan {...props} />
      ) : (
        <div className="silice-hoja__pestana">
          <p className="cds--type-body-compact-01">{vista.mensaje}</p>
          <AvisoDeEnvio envio={creacion.envio} />
          <div>
            <Button
              kind="tertiary"
              size="sm"
              disabled={creacion.envio === "enviando"}
              onClick={() => void creacion.accionar((r) => crearPlan(r, id))}
            >
              Crear plan secuencial (una partida por periodo)
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

// Pestaña «Plan y curva»: la matriz de fracciones se edita como texto y la curva se recalcula (rebanada 3c-2).
export function PestanaPlan(props: Props) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaPlan> ruta={rutaDeVista(props.id, "plan")} etiqueta="Plan y curva" alAusente={props.alAusente} recarga={lecturas}>
      {(vista) => <ContenidoPlan {...props} vista={vista} alRelectura={alRelectura} />}
    </VistaCarga>
  );
}
