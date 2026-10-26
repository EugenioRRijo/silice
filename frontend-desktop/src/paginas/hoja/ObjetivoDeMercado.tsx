import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import type { FilaPresupuesto } from "./logica";

// Tarea 16 del plan de montar un presupuesto: en «Presupuesto», junto al precio unitario de cada partida, el precio de
// venta objetivo que se guardó en «Estudio de mercado» y el margen contra ese precio unitario (diseño §5.1). El margen
// lo calcula la API (`GET /v1/mercado/objetivos` con `pu` y `moneda`); aquí solo se formatea lo que llega con punto.
// Un objetivo en otra moneda que la obra se dice con su moneda y no se compara.

export interface ObjetivoDeMercado {
  codigo: string;
  precio: string;
  moneda: string;
  // (objetivo − precio unitario) / precio unitario, en % con una cifra decimal; null si la API no lo pudo comparar.
  margen: string | null;
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
// cada uno que lo tenga (el que se muestra va a dos decimales). Devuelve las rutas de cada tanda y lo enviado.
export function consultasDeObjetivos(
  filas: Pick<FilaPresupuesto, "partida" | "pu">[],
  moneda: string,
): { rutas: string[]; enviados: Map<string, string> } {
  const enviados = new Map<string, string>();
  const codigos: string[] = [];
  for (const f of filas) {
    if (!codigos.includes(f.partida)) codigos.push(f.partida);
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

// El texto de la celda de una fila (vacío sin objetivo).
export function textoDelObjetivo(
  objetivo: ObjetivoDeMercado | undefined,
  fila: { pu: string | null; enviado: string | undefined },
  moneda: string,
): string {
  if (objetivo === undefined) return "";
  const precio = formatoEsVe(objetivo.precio);
  if (objetivo.moneda !== moneda) {
    return `${precio} ${objetivo.moneda} · en otra moneda que la obra (${moneda}), sin margen`;
  }
  if (fila.pu === null) return `${precio} · sin precio unitario, sin margen`;
  // El margen vale para el precio unitario que se envió por ese código: otro renglón con otro precio no lo hereda.
  if (objetivo.margen !== null && fila.pu === fila.enviado) return `${precio} · margen ${margenEsVe(objetivo.margen)}`;
  return `${precio} · sin margen`;
}

interface Leidos {
  clave: string;
  objetivos: Map<string, ObjetivoDeMercado>;
  error: string | null;
}

// Lee los objetivos de las partidas de la Hoja (otra vez cuando cambian sus códigos o sus precios) y da la columna
// «Objetivo de mercado» y lo que va bajo la tabla: la ayuda (si hay algún objetivo) o el error de la lectura. Si la
// lectura falla, la Hoja sigue igual con la columna vacía.
export function useObjetivosDeMercado(
  filas: FilaPresupuesto[],
  moneda: string,
): { columna: ColumnaDensa; aviso: ReactNode } {
  const { alExpirar } = useAplicacion();
  const { rutas, enviados } = consultasDeObjetivos(filas, moneda);
  const clave = rutas.join("\n");
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

  const objetivos = leidos?.objetivos ?? new Map<string, ObjetivoDeMercado>();
  const columna: ColumnaDensa = {
    clave: "objetivo",
    titulo: "Objetivo de mercado",
    numerica: true,
    ordenable: false,
    celda: (f: FilaDensa) => {
      const texto = textoDelObjetivo(
        objetivos.get(f.partida!),
        { pu: f.pu_exacto ? f.pu_exacto : null, enviado: enviados.get(f.partida!) },
        moneda,
      );
      return texto;
    },
  };
  let aviso: ReactNode = null;
  if (leidos?.error) aviso = <p className="cds--type-helper-text-01">{leidos.error}</p>;
  else if (objetivos.size > 0) aviso = <p className="cds--type-helper-text-01">{AYUDA_OBJETIVO}</p>;
  return { columna, aviso };
}
