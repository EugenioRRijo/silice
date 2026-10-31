import { useEffect, useId, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { LineaDeEquivalencia } from "../../comun/LineaDeEquivalencia";
import type { Equivalencia } from "../../comun/LineaDeEquivalencia";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import type { FilaPresupuesto } from "./logica";

// Tarea 16 del plan de montar un presupuesto: en «Presupuesto», junto al precio unitario de cada partida, el precio de
// venta objetivo que se guardó en «Estudio de mercado» y el margen contra ese precio unitario (diseño §5.1). El margen
// lo calcula la API (`GET /v1/mercado/objetivos` con `pu` y `moneda`); aquí solo se formatea lo que llega con punto.
// Un objetivo en otra moneda que la obra llega convertido por la API con la tasa del BCV del día en que se fijó (Tarea
// D3b): se muestra su línea de equivalencia y el margen sobre el convertido; sin tasa de ese día, el motivo.

export interface ObjetivoDeMercado {
  codigo: string;
  precio: string;
  moneda: string;
  // (objetivo − precio unitario) / precio unitario, en % con una cifra decimal; null si la API no lo pudo comparar.
  margen: string | null;
  // La cuenta de un objetivo en otra moneda que la obra (null en la misma moneda o sin tasa de su día).
  equivalencia?: Equivalencia | null;
  // «sin tasa del BCV del dd/mm/aaaa» si estaba en otra moneda y no hay tasa de ese día.
  sin_tasa?: string | null;
}

interface RespuestaObjetivos {
  objetivos: ObjetivoDeMercado[];
}

export const AYUDA_OBJETIVO =
  "Objetivo de mercado: el precio de venta que guardó en «Estudio de mercado». El margen lo compara con el precio unitario " +
  "(con utilidad, sin IVA): negativo si el objetivo queda por debajo.";

// Los límites de `partidas` y `pu` en la API (`api/rutas/mercado.py`): una Hoja grande se pide por tandas.
const LARGO_PARTIDAS = 2000;
const LARGO_PU = 4000;

// Lo que se pide: los códigos sin repetir, en el orden de la Hoja, y el precio unitario EXACTO del primer renglón de
// cada uno que lo tenga (el que se muestra va a dos decimales). Devuelve las rutas de cada tanda y lo enviado. Un
// conjunto lleva los códigos ya vistos (buscarlos en una lista era cuadrático en una Hoja grande).
export function consultasDeObjetivos(
  filas: Pick<FilaPresupuesto, "partida" | "pu">[],
  moneda: string,
): { rutas: string[]; enviados: Map<string, string> } {
  const enviados = new Map<string, string>();
  const codigos = new Set<string>();
  for (const f of filas) {
    codigos.add(f.partida);
    if (f.pu !== null && !enviados.has(f.partida)) enviados.set(f.partida, f.pu.exacto);
  }
  const rutas: string[] = [];
  let partidas: string[] = [];
  let pu: string[] = [];
  const largo = (partes: string[]) => partes.join(",").length;
  const cerrar = () => {
    if (partidas.length === 0) return;
    const consulta = new URLSearchParams({ partidas: partidas.join(","), pu: pu.join(","), moneda });
    rutas.push(`/v1/mercado/objetivos?${consulta.toString()}`);
    partidas = [];
    pu = [];
  };
  for (const codigo of codigos) {
    const exacto = enviados.get(codigo);
    const conPrecio = exacto === undefined ? pu : [...pu, `${codigo}:${exacto}`];
    if (partidas.length > 0 && (largo([...partidas, codigo]) > LARGO_PARTIDAS || largo(conPrecio) > LARGO_PU)) cerrar();
    partidas.push(codigo);
    if (exacto !== undefined) pu.push(`${codigo}:${exacto}`);
  }
  cerrar();
  return { rutas, enviados };
}

// «-4.6» → «−4,6 %» (el menos tipográfico), «10.0» → «+10,0 %», «0.0» → «0,0 %»: el signo se lee, no depende del color.
export function margenEsVe(margen: string): string {
  const m = /^([-+]?)([0-9]+(?:\.[0-9]+)?)$/.exec(margen.trim());
  if (!m) return margen;
  const [, signo, cifra] = m;
  const conSigno = !/[1-9]/.test(cifra!) ? "" : signo === "-" ? "\u2212" : "+";
  return `${conSigno}${formatoEsVe(cifra!)}\u00a0%`;
}

// La celda de una fila (vacía sin objetivo). El margen vale para el precio unitario que se envió por ese código: otro
// renglón con otro precio no lo hereda.
export function celdaDelObjetivo(
  objetivo: ObjetivoDeMercado | undefined,
  fila: { pu: string | null; enviado: string | undefined },
  moneda: string,
): ReactNode {
  if (objetivo === undefined) return "";
  const precio = formatoEsVe(objetivo.precio);
  const margen =
    objetivo.margen !== null && fila.pu === fila.enviado ? ` · margen ${margenEsVe(objetivo.margen)}` : " · sin margen";
  if (objetivo.moneda !== moneda) {
    if (objetivo.equivalencia) {
      return (
        <>
          <LineaDeEquivalencia equivalencia={objetivo.equivalencia} />
          {fila.pu === null ? " · sin precio unitario, sin margen" : margen}
        </>
      );
    }
    // `sin_tasa` es el motivo que da la API; si faltara (contrato roto), un texto neutro y no «null».
    const motivo = objetivo.sin_tasa ? objetivo.sin_tasa : `en otra moneda que la obra (${moneda})`;
    return `${precio} ${objetivo.moneda} · ${motivo}, sin margen`;
  }
  if (fila.pu === null) return `${precio} · sin precio unitario, sin margen`;
  return `${precio}${margen}`;
}

interface Leidos {
  clave: string;
  objetivos: ReadonlyMap<string, ObjetivoDeMercado>;
  error: string | null;
}

const SIN_OBJETIVOS: ReadonlyMap<string, ObjetivoDeMercado> = new Map();

// Lee los objetivos de las partidas de la Hoja (otra vez cuando cambian sus códigos o sus precios) y da la columna
// «Objetivo de mercado» y lo que va bajo la tabla: la ayuda (si hay algún objetivo), que describe la cabecera, y la
// región `role="status"` del error de la lectura, montada vacía desde el principio para que el lector de pantalla
// anuncie lo que entre. Si la lectura falla, la Hoja sigue igual con la columna vacía. Lo leído vale solo para los
// códigos y precios con que se pidió: mientras llega la respuesta a otros, la columna queda vacía y sin error. Con
// `activo` falso (quien revisa, F4 2b: el estudio de mercado es de quien arma) no se pide nada.
export function useObjetivosDeMercado(
  filas: FilaPresupuesto[],
  moneda: string,
  activo = true,
): { columna: ColumnaDensa; aviso: ReactNode } {
  const { alExpirar } = useAplicacion();
  const idAyuda = useId();
  // Se arma una vez por filas y moneda, no en cada pintura (editar una cantidad vuelve a pintar la Hoja).
  const { rutas, enviados } = useMemo(() => consultasDeObjetivos(filas, moneda), [filas, moneda]);
  const clave = activo ? rutas.join("\n") : "";
  const [leidos, setLeidos] = useState<Leidos | null>(null);

  useEffect(() => {
    if (clave === "") return;
    let vigente = true;
    Promise.all(clave.split("\n").map((ruta) => pedir<RespuestaObjetivos>(ruta))).then(
      (respuestas) => {
        if (!vigente) return;
        const objetivos = new Map<string, ObjetivoDeMercado>();
        for (const r of respuestas) for (const o of r?.objetivos ?? []) objetivos.set(o.codigo, o);
        setLeidos({ clave, objetivos, error: null });
      },
      (e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) {
          alExpirar();
          return;
        }
        const detalle = e instanceof ErrorDeApi ? e.detalle : "no hubo respuesta del servidor.";
        setLeidos({ clave, objetivos: new Map(), error: `No se pudieron leer los objetivos de mercado: ${detalle}` });
      },
    );
    return () => {
      vigente = false;
    };
  }, [clave, alExpirar]);

  const vigentes = leidos !== null && leidos.clave === clave ? leidos : null;
  const objetivos = vigentes?.objetivos ?? SIN_OBJETIVOS;
  const error = vigentes?.error ?? null;
  const conAyuda = objetivos.size > 0;
  const columna = useMemo<ColumnaDensa>(
    () => ({
      clave: "objetivo",
      titulo: "Objetivo de mercado",
      numerica: true,
      ordenable: false,
      descripcion: conAyuda ? idAyuda : undefined,
      celda: (f: FilaDensa) =>
        celdaDelObjetivo(
          objetivos.get(f.partida!),
          { pu: f.pu_exacto ? f.pu_exacto : null, enviado: enviados.get(f.partida!) },
          moneda,
        ),
    }),
    [objetivos, enviados, moneda, conAyuda, idAyuda],
  );
  const aviso: ReactNode = (
    <>
      {conAyuda && (
        <p id={idAyuda} className="cds--type-helper-text-01">
          {AYUDA_OBJETIVO}
        </p>
      )}
      <p role="status" className="cds--type-helper-text-01">
        {error ?? ""}
      </p>
    </>
  );
  return { columna, aviso };
}
