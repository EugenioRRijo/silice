// Lógica pura de la superficie «Presupuesto» (lote B1-1; guía `content-first-noise-reduction`: la frase de respuesta y
// el resumen por fila dan solo lo esencial y dejan el desglose completo a pedido en el inspector).
// Las cifras monetarias y cantidades llegan formateadas del servidor y se copian tal cual; aquí solo se cuentan filas y
// hallazgos con `formatoEsVe`.
import type { HallazgoInformeRespuesta, InformeAuditoriaRespuesta } from "../../../api/tipos";
import { formatoEsVe } from "../../../indicadores/formatoEsVe";
import { clavesDeAuditoria, hallazgosDeOrigen, type FilaPresupuesto, type VistaPresupuesto } from "../logica";

export type SeveridadDeProblema = "CRITICO" | "ERROR" | "ADVERTENCIA";
export type PalabraDeSeveridad = "Crítico" | "Error" | "Advertencia";

export interface ResumenDeProblemaEnFila {
  severidad: SeveridadDeProblema;
  palabra: PalabraDeSeveridad;
  texto: string;
  total: number;
}

export interface FilaDeLaGrilla {
  clave: string;
  partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  puTexto: string;
  totalTexto: string;
  sinPrecio: boolean;
  fila: FilaPresupuesto;
  problemas: HallazgoInformeRespuesta[];
  problema: ResumenDeProblemaEnFila | null;
}

export interface CuentaDeProblemas {
  total: number;
  criticos: number;
  errores: number;
  advertencias: number;
  partidasConProblemas: number;
}

export interface ProblemaEnLista {
  numero: number;
  severidad: SeveridadDeProblema;
  palabra: PalabraDeSeveridad;
  partida: string | null;
  descripcionPartida: string | null;
  descripcion: string;
  claveFila: string | null;
  hallazgo: HallazgoInformeRespuesta;
}

export interface GrupoDeProblemas {
  regla: string;
  nombre: string;
  problemas: ProblemaEnLista[];
}

export type RevisionDeLaSuperficie =
  | { estado: "lista"; informe: InformeAuditoriaRespuesta }
  | { estado: "cargando" }
  | { estado: "error" };

const PALABRA_DE_SEVERIDAD: Record<SeveridadDeProblema, PalabraDeSeveridad> = {
  CRITICO: "Crítico",
  ERROR: "Error",
  ADVERTENCIA: "Advertencia",
};

const PESO_DE_SEVERIDAD: Record<SeveridadDeProblema, number> = {
  CRITICO: 3,
  ERROR: 2,
  ADVERTENCIA: 1,
};

const cifra = (n: number): string => formatoEsVe(String(n));

function severidadDeProblema(severidad: string | null | undefined): SeveridadDeProblema | null {
  if (!severidad) return null;
  const normalizada = severidad.trim().toUpperCase();
  if (normalizada === "CRITICO" || normalizada === "CRÍTICO") return "CRITICO";
  if (normalizada === "ERROR") return "ERROR";
  if (normalizada === "ADVERTENCIA") return "ADVERTENCIA";
  return null;
}

export function filaDelHallazgo<F extends Pick<FilaPresupuesto, "clave">>(
  hallazgo: HallazgoInformeRespuesta,
  filas: readonly F[],
): F | null {
  for (const fila of filas) {
    if (hallazgosDeOrigen([hallazgo], clavesDeAuditoria(fila.clave)).length > 0) {
      return fila;
    }
  }
  return null;
}

export function cuentaDeProblemas(
  informe: InformeAuditoriaRespuesta | null,
  filas?: readonly Pick<FilaPresupuesto, "clave" | "partida">[],
): CuentaDeProblemas {
  if (informe === null) {
    return { total: 0, criticos: 0, errores: 0, advertencias: 0, partidasConProblemas: 0 };
  }
  let criticos = 0;
  let errores = 0;
  let advertencias = 0;
  const problemas: HallazgoInformeRespuesta[] = [];

  for (const h of informe.hallazgos) {
    const sev = severidadDeProblema(h.severidad);
    if (sev === null) continue;
    problemas.push(h);
    if (sev === "CRITICO") criticos += 1;
    else if (sev === "ERROR") errores += 1;
    else advertencias += 1;
  }

  const total = criticos + errores + advertencias;
  let partidasConProblemas = 0;

  if (problemas.length > 0) {
    if (filas !== undefined) {
      for (const fila of filas) {
        if (hallazgosDeOrigen(problemas, clavesDeAuditoria(fila.clave)).length > 0) {
          partidasConProblemas += 1;
        }
      }
    } else {
      const codigos = new Set<string>();
      for (const h of problemas) {
        if (h.partida !== null && h.partida !== "") codigos.add(h.partida);
      }
      partidasConProblemas = codigos.size;
    }
  }

  return { total, criticos, errores, advertencias, partidasConProblemas };
}

function resumirProblemasDeFila(problemas: readonly HallazgoInformeRespuesta[]): ResumenDeProblemaEnFila | null {
  let peor: { sev: SeveridadDeProblema; texto: string } | null = null;
  let total = 0;

  for (const h of problemas) {
    const sev = severidadDeProblema(h.severidad);
    if (sev === null) continue;
    total += 1;
    if (peor === null || PESO_DE_SEVERIDAD[sev] > PESO_DE_SEVERIDAD[peor.sev]) {
      peor = { sev, texto: h.descripcion };
    }
  }

  if (peor === null) return null;
  return {
    severidad: peor.sev,
    palabra: PALABRA_DE_SEVERIDAD[peor.sev],
    texto: peor.texto,
    total,
  };
}

export function filasDeLaGrilla(
  vista: VistaPresupuesto,
  informe: InformeAuditoriaRespuesta | null,
): FilaDeLaGrilla[] {
  return vista.filas.map((fila) => {
    const sinPrecio = fila.pu === null || fila.total === null;
    const puTexto = fila.pu !== null ? fila.pu.texto : "Pendiente";
    const totalTexto = fila.total !== null ? fila.total.texto : "Pendiente";

    if (informe !== null) {
      const delRenglon = hallazgosDeOrigen(informe.hallazgos, clavesDeAuditoria(fila.clave));
      const problemas = delRenglon.filter((h) => severidadDeProblema(h.severidad) !== null);
      return {
        clave: fila.clave,
        partida: fila.partida,
        descripcion: fila.descripcion,
        unidad: fila.unidad,
        cantidad: fila.cantidad,
        puTexto,
        totalTexto,
        sinPrecio,
        fila,
        problemas,
        problema: resumirProblemasDeFila(problemas),
      };
    }

    const sevEstado = severidadDeProblema(fila.estado.severidad);
    const problemaSinInforme: ResumenDeProblemaEnFila | null =
      sevEstado !== null
        ? {
            severidad: sevEstado,
            palabra: PALABRA_DE_SEVERIDAD[sevEstado],
            texto: fila.estado.texto || (sinPrecio ? "Pendiente" : PALABRA_DE_SEVERIDAD[sevEstado]),
            total: 1,
          }
        : null;

    return {
      clave: fila.clave,
      partida: fila.partida,
      descripcion: fila.descripcion,
      unidad: fila.unidad,
      cantidad: fila.cantidad,
      puTexto,
      totalTexto,
      sinPrecio,
      fila,
      problemas: [],
      problema: problemaSinInforme,
    };
  });
}

export function gruposDeProblemas(
  informe: InformeAuditoriaRespuesta | null,
  filas: readonly Pick<FilaPresupuesto, "clave" | "partida" | "descripcion">[] = [],
): GrupoDeProblemas[] {
  if (informe === null) return [];

  const nombres = new Map<string, string>();
  for (const r of informe.reglas_evaluadas) {
    const limpio = r.nombre.trim();
    if (limpio !== "") nombres.set(r.regla, limpio);
  }

  const porRegla = new Map<string, GrupoDeProblemas>();
  for (const h of informe.hallazgos) {
    const sev = severidadDeProblema(h.severidad);
    if (sev === null) continue;
    const fila = filaDelHallazgo(h, filas);
    const item: ProblemaEnLista = {
      numero: h.numero,
      severidad: sev,
      palabra: PALABRA_DE_SEVERIDAD[sev],
      partida: fila ? fila.partida : h.partida,
      descripcionPartida: fila ? fila.descripcion : null,
      descripcion: h.descripcion,
      claveFila: fila ? fila.clave : null,
      hallazgo: h,
    };
    const existente = porRegla.get(h.regla);
    if (existente !== undefined) {
      existente.problemas.push(item);
    } else {
      const nombre = nombres.get(h.regla) ?? (h.regla === "PENDIENTE" ? "Partidas sin precio" : h.regla);
      porRegla.set(h.regla, { regla: h.regla, nombre, problemas: [item] });
    }
  }

  return [...porRegla.values()];
}

function conPuntoFinal(texto: string): string {
  return texto.endsWith(".") ? texto : `${texto}.`;
}

function unirEnEspanol(partes: readonly string[]): string {
  const [primera, segunda, tercera] = partes;
  if (primera === undefined) return "";
  if (segunda === undefined) return primera;
  if (tercera === undefined) return `${primera} y ${segunda}`;
  return `${primera}, ${segunda} y ${tercera}`;
}

function desglosePorSeveridad(cuenta: CuentaDeProblemas): string {
  const partes: string[] = [];
  if (cuenta.criticos > 0) {
    partes.push(cuenta.criticos === 1 ? "1 crítico" : `${cifra(cuenta.criticos)} críticos`);
  }
  if (cuenta.errores > 0) {
    partes.push(cuenta.errores === 1 ? "1 error" : `${cifra(cuenta.errores)} errores`);
  }
  if (cuenta.advertencias > 0) {
    partes.push(cuenta.advertencias === 1 ? "1 advertencia" : `${cifra(cuenta.advertencias)} advertencias`);
  }
  return unirEnEspanol(partes);
}

function fraseSinProblemas(informe: InformeAuditoriaRespuesta): string {
  const delServidor = informe.sin_hallazgos?.trim() ?? "";
  if (delServidor !== "") return conPuntoFinal(delServidor);
  const nReglas = informe.reglas_evaluadas.length;
  if (nReglas === 0) return "Sílice no halló problemas.";
  const textoReglas = nReglas === 1 ? "1 regla" : `${cifra(nReglas)} reglas`;
  return `Sílice revisó ${textoReglas} y no halló problemas.`;
}

function fraseConProblemas(cuenta: CuentaDeProblemas): string {
  const desglose = desglosePorSeveridad(cuenta);
  if (cuenta.partidasConProblemas === 0) {
    return cuenta.total === 1
      ? `El presupuesto tiene 1 problema: ${desglose}.`
      : `El presupuesto tiene ${cifra(cuenta.total)} problemas: ${desglose}.`;
  }
  if (cuenta.partidasConProblemas === 1) {
    return cuenta.total === 1
      ? `1 partida tiene 1 problema: ${desglose}.`
      : `1 partida tiene problemas: ${desglose}.`;
  }
  return cuenta.total === 1
    ? `${cifra(cuenta.partidasConProblemas)} partidas tienen 1 problema: ${desglose}.`
    : `${cifra(cuenta.partidasConProblemas)} partidas tienen problemas: ${desglose}.`;
}

export function fraseDeRespuesta(
  vista: VistaPresupuesto,
  revision: InformeAuditoriaRespuesta | RevisionDeLaSuperficie | null,
): string {
  if (vista.filas.length === 0) {
    return vista.vacio_mensaje?.trim() || "Esta obra aún no tiene partidas";
  }

  const moneda = vista.moneda.trim();
  // El servidor manda el total con punto decimal («2703.86»); la frase lo dice en es-VE, como el resto de la Hoja.
  const total = formatoEsVe(vista.total.texto);
  const monto = moneda !== "" ? `${total} ${moneda}` : total;
  const nPartidas = vista.filas.length;
  const partidas = nPartidas === 1 ? "1 partida" : `${cifra(nPartidas)} partidas`;
  const encabezado = `El presupuesto suma ${monto} sin IVA en ${partidas}.`;

  if (revision === null) return encabezado;
  if ("estado" in revision) {
    if (revision.estado === "cargando") return encabezado;
    if (revision.estado === "error") return `${encabezado} No se pudo revisar el presupuesto.`;
  }

  const informe = "estado" in revision ? revision.informe : revision;
  const cuenta = cuentaDeProblemas(informe, vista.filas);
  const cierre = cuenta.total === 0 ? fraseSinProblemas(informe) : fraseConProblemas(cuenta);
  return `${encabezado} ${cierre}`;
}
