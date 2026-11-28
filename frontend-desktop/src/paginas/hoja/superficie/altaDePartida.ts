// Máquina de estados pura de la fila de alta de partidas (lote B1-8, ficha-b1 §1.6, §1.8 y §1.10).
// Sin React ni DOM: toda validación local, reparto de errores del servidor (422/404/409), prevención de doble envío,
// apertura automática del pliegue con error en el cálculo y formateo en es-VE viven aquí para probarse aislados.
import type { PartidaHallada } from "../../../comun/logicaBusqueda";
import { unidadEscrita } from "../../../comun/unidades";
import { MENSAJE_CIFRA_VACIA, leerCifra } from "../../../indicadores/cifraEscrita";
import { formatoEsVe } from "../../../indicadores/formatoEsVe";
import type { PartidaCompuesta } from "../../componer/ComponerPartida";
import { pareceCodigo } from "../../componer/codigo";
import type { PartidaPorComponer } from "../ComponerEnPanel";
import { leerResumen } from "../analizadores";
import { campoDelErrorDePartida } from "../logica";
import type { Resumen } from "../logica";

export const ELEGIR_DE_LA_LISTA = "Elija la partida de la lista de sugerencias.";
export const RECARGADO = "Ya se volvió a leer el borrador: puede agregarla otra vez.";
export const AYUDA_PARTIDA = "Busque por código o por una palabra de la descripción, por ejemplo, bloque.";
export const PASOS_SIN_RESULTADO =
  "Pruebe con otra palabra, pulse «Buscar parecidas» o elija «Crear la partida».";
export const AYUDA_CANTIDAD = "Con coma decimal: 50 o 12,5";
export const CANTIDAD_DEL_CALCULO = "Si la deja vacía, Sílice la toma del resultado del cálculo al agregar.";
export const AYUDA_CALCULO = "Por ejemplo 6*3-2 o 2,5*4. Si lo escribe, Sílice puede verificar la cantidad.";
export const AYUDA_NOTA = "Por ejemplo: 6 m × 35 m de muro, menos vanos.";

export type PartidaElegida = Pick<PartidaHallada, "codigo" | "descripcion"> & {
  readonly unidad: string | null;
};

export interface ErroresDeAlta {
  readonly partida: string | null;
  readonly cantidad: string | null;
  readonly calculo: string | null;
  readonly general: string | null;
}

export const SIN_ERRORES: ErroresDeAlta = {
  partida: null,
  cantidad: null,
  calculo: null,
  general: null,
};

export interface PartidaAgregadaRespuesta {
  readonly rev: number;
  readonly resumen: Resumen;
  readonly clave: string;
  readonly aviso: string | null;
}

export interface ResultadoDePartidaAgregada {
  readonly rev: number;
  readonly resumen: Resumen;
  readonly clave: string;
  readonly codigo: string;
  readonly aviso: string | null;
}

interface BaseDeAlta {
  readonly texto: string;
  readonly elegida: PartidaElegida | null;
  readonly cantidad: string;
  readonly calculo: string;
  readonly nota: string;
  readonly calculoVisto: boolean;
  readonly pliegueAbierto: boolean;
  readonly reinicios: number;
}

export type EstadoDeAlta =
  | (BaseDeAlta & { readonly fase: "editando" })
  | (BaseDeAlta & { readonly fase: "enviando" })
  | (BaseDeAlta & { readonly fase: "error"; readonly errores: ErroresDeAlta });

export type EventoDeAlta =
  | { readonly tipo: "cambiarTextoPartida"; readonly texto: string }
  | { readonly tipo: "elegirPartida"; readonly partida: PartidaElegida; readonly enfocarCantidad?: boolean }
  | { readonly tipo: "fijarPartidaInicial"; readonly partida: PartidaCompuesta }
  | { readonly tipo: "cambiarCantidad"; readonly valor: string }
  | { readonly tipo: "cambiarCalculo"; readonly valor: string }
  | { readonly tipo: "verCalculo" }
  | { readonly tipo: "cambiarNota"; readonly valor: string }
  | { readonly tipo: "alternarPliegue"; readonly abierto: boolean }
  | { readonly tipo: "enviar" }
  | { readonly tipo: "exito" }
  | { readonly tipo: "rechazo422"; readonly detalle: string }
  | { readonly tipo: "fueraDeCatalogo"; readonly detalle: string }
  | { readonly tipo: "conflictoRev"; readonly detalle: string }
  | { readonly tipo: "falloGeneral"; readonly mensaje: string }
  | { readonly tipo: "abortadoPorSesionOBorrador" };

export type EfectoDeAlta =
  | {
      readonly tipo: "postPartida";
      readonly partida: {
        readonly codigo: string;
        readonly cantidad: string;
        readonly calculo: string;
        readonly nota: string;
      };
    }
  | { readonly tipo: "enfocarErrores" }
  | { readonly tipo: "enfocarCantidad" };

export interface TransicionDeAlta {
  readonly estado: EstadoDeAlta;
  readonly efecto: EfectoDeAlta | null;
}

/** Comprueba si una cadena está vacía según la regla de cifras del servidor. */
export function estaVacioCifra(texto: string): boolean {
  const lectura = leerCifra(texto);
  return "error" in lectura && lectura.error === MENSAJE_CIFRA_VACIA;
}

/** Formatea la partida elegida como «código · descripción» o solo el código si falta la descripción. */
export function textoDePartidaElegida(partida: Pick<PartidaElegida, "codigo" | "descripcion">): string {
  return partida.descripcion.trim() === "" ? partida.codigo : `${partida.codigo} · ${partida.descripcion}`;
}

function normalizarCompuesta(partida: PartidaCompuesta): PartidaElegida {
  return {
    codigo: partida.codigo,
    descripcion: partida.descripcion,
    unidad: partida.unidad === "" ? null : partida.unidad,
  };
}

/** Estado inicial de la fila de alta, opcionalmente precargada con una partida recién compuesta. */
export function estadoInicialDeAlta(partidaInicial: PartidaCompuesta | null = null): EstadoDeAlta {
  const elegida = partidaInicial === null ? null : normalizarCompuesta(partidaInicial);
  return {
    fase: "editando",
    texto: elegida === null ? "" : textoDePartidaElegida(elegida),
    elegida,
    cantidad: "",
    calculo: "",
    nota: "",
    calculoVisto: false,
    pliegueAbierto: false,
    reinicios: 0,
  };
}

/** Etiqueta del campo Cantidad con su unidad escrita cuando hay partida elegida con unidad. */
export function etiquetaDeCantidad(elegida: PartidaElegida | null): string {
  return elegida?.unidad ? `Cantidad (${unidadEscrita(elegida.unidad)})` : "Cantidad";
}

/** Texto de ayuda de Cantidad: avisa si saldrá del cálculo al dejarla vacía. */
export function ayudaDeCantidad(calculoVisto: boolean, calculo: string, cantidad: string): string {
  return calculoVisto && calculo.trim() !== "" && cantidad.trim() === ""
    ? `${CANTIDAD_DEL_CALCULO} ${AYUDA_CANTIDAD}`
    : AYUDA_CANTIDAD;
}

/** Resumen visible del pliegue «Cálculo y nota (opcional)». */
export function resumenDeCalculoYNota(calculo: string, nota: string): string {
  const c = calculo.trim();
  const n = nota.trim();
  if (c === "" && n === "") return "Cálculo y nota (opcional): Sin cálculo ni nota. Cambiar";
  if (c !== "" && n === "") return `Cálculo y nota (opcional): ${c}. Cambiar`;
  if (c === "" && n !== "") return "Cálculo y nota (opcional): con nota de medición. Cambiar";
  return `Cálculo y nota (opcional): ${c} y nota de medición. Cambiar`;
}

/** Rótulo de la opción de crear partida en las sugerencias (decisión D4). */
export function rotuloCrearPartida(texto: string): string {
  return `Crear la partida «${texto}»`;
}

/** Traduce lo escrito en «Partida» al código o descripción inicial para el inspector de creación. */
export function solicitudDeCreacion(texto: string): PartidaPorComponer {
  return pareceCodigo(texto) ? { codigo: texto, descripcion: "" } : { codigo: "", descripcion: texto };
}

/** Descripción enviada a «Parecidas»: evita pegar el código delante cuando ya hay una partida elegida. */
export function descripcionParaParecidas(elegida: PartidaElegida | null, texto: string): string {
  return elegida !== null && elegida.descripcion.trim() !== "" ? elegida.descripcion : texto;
}

/** Texto único para el Anunciador tras agregar la partida con el total formateado en es-VE. */
export function anuncioDePartidaAgregada(codigo: string, resumen: Resumen, aviso: string | null): string {
  const moneda = resumen.moneda.trim();
  const total = formatoEsVe(resumen.total.texto);
  const monto = moneda !== "" ? `${total} ${moneda}` : total;
  const base = `Se agregó ${codigo} al presupuesto. Total: ${monto}.`;
  return aviso !== null && aviso.trim() !== "" ? `${base} ${aviso.trim()}` : base;
}

/** Valida en frontera la respuesta JSON de POST /v1/hoja/borradores/{id}/partidas. */
export function leerPartidaAgregada(datos: unknown): PartidaAgregadaRespuesta {
  if (typeof datos !== "object" || datos === null || Array.isArray(datos)) {
    throw new Error("Se esperaba un objeto al agregar la partida.");
  }
  const o = datos as Record<string, unknown>;
  if (typeof o.rev !== "number" || !Number.isFinite(o.rev)) {
    throw new Error("Falta un rev válido al agregar la partida.");
  }
  if (typeof o.clave !== "string" || o.clave.trim() === "") {
    throw new Error("Falta la clave de la fila agregada.");
  }
  if (o.aviso !== undefined && o.aviso !== null && typeof o.aviso !== "string") {
    throw new Error("El aviso al agregar la partida debe ser texto o nulo.");
  }
  return {
    rev: o.rev,
    resumen: leerResumen(o.resumen),
    clave: o.clave,
    aviso: o.aviso ?? null,
  };
}

function sinEfecto(estado: EstadoDeAlta): TransicionDeAlta {
  return { estado, efecto: null };
}

function hayAlgunError(errores: ErroresDeAlta): boolean {
  return (
    errores.partida !== null ||
    errores.cantidad !== null ||
    errores.calculo !== null ||
    errores.general !== null
  );
}

function baseDe(estado: EstadoDeAlta): BaseDeAlta {
  return {
    texto: estado.texto,
    elegida: estado.elegida,
    cantidad: estado.cantidad,
    calculo: estado.calculo,
    nota: estado.nota,
    calculoVisto: estado.calculoVisto,
    pliegueAbierto: estado.pliegueAbierto,
    reinicios: estado.reinicios,
  };
}

function conErrores(base: BaseDeAlta, errores: ErroresDeAlta): EstadoDeAlta {
  return hayAlgunError(errores) ? { ...base, fase: "error", errores } : { ...base, fase: "editando" };
}

function limpiarError(estado: EstadoDeAlta, campo: keyof ErroresDeAlta): BaseDeAlta & { readonly errores: ErroresDeAlta | null } {
  const base = baseDe(estado);
  if (estado.fase !== "error") return { ...base, errores: null };
  const siguientes: ErroresDeAlta = { ...estado.errores, [campo]: null };
  return { ...base, errores: hayAlgunError(siguientes) ? siguientes : null };
}

function aplicarLimpieza(
  estado: EstadoDeAlta,
  campo: keyof ErroresDeAlta,
  cambios: Partial<BaseDeAlta>,
): EstadoDeAlta {
  const { errores, ...base } = limpiarError(estado, campo);
  const actualizada: BaseDeAlta = { ...base, ...cambios };
  return errores === null ? { ...actualizada, fase: "editando" } : { ...actualizada, fase: "error", errores };
}

/** Transición pura de la máquina de estados de la fila de alta. */
export function siguiente(estado: EstadoDeAlta, evento: EventoDeAlta): TransicionDeAlta {
  if (estado.fase === "enviando") {
    switch (evento.tipo) {
      case "exito":
        return sinEfecto({
          fase: "editando",
          texto: "",
          elegida: null,
          cantidad: "",
          calculo: "",
          nota: "",
          calculoVisto: false,
          pliegueAbierto: false,
          reinicios: estado.reinicios + 1,
        });
      case "rechazo422": {
        const campo = campoDelErrorDePartida(evento.detalle, { cantidad: estado.cantidad, calculo: estado.calculo });
        const base: BaseDeAlta = {
          ...baseDe(estado),
          pliegueAbierto: campo === "calculo" ? true : estado.pliegueAbierto,
        };
        const errores: ErroresDeAlta =
          campo === null
            ? { ...SIN_ERRORES, general: evento.detalle }
            : { ...SIN_ERRORES, [campo]: evento.detalle };
        return { estado: conErrores(base, errores), efecto: { tipo: "enfocarErrores" } };
      }
      case "fueraDeCatalogo":
        return {
          estado: conErrores(baseDe(estado), { ...SIN_ERRORES, partida: evento.detalle }),
          efecto: { tipo: "enfocarErrores" },
        };
      case "conflictoRev":
        return {
          estado: conErrores(baseDe(estado), { ...SIN_ERRORES, general: `${evento.detalle} ${RECARGADO}` }),
          efecto: { tipo: "enfocarErrores" },
        };
      case "falloGeneral":
        return {
          estado: conErrores(baseDe(estado), { ...SIN_ERRORES, general: evento.mensaje }),
          efecto: { tipo: "enfocarErrores" },
        };
      case "abortadoPorSesionOBorrador":
        return sinEfecto({ ...baseDe(estado), fase: "editando" });
      default:
        return sinEfecto(estado);
    }
  }

  switch (evento.tipo) {
    case "cambiarTextoPartida":
      return sinEfecto(aplicarLimpieza(estado, "partida", { texto: evento.texto, elegida: null }));

    case "elegirPartida": {
      const siguienteEstado = aplicarLimpieza(estado, "partida", {
        elegida: evento.partida,
        texto: textoDePartidaElegida(evento.partida),
      });
      return {
        estado: siguienteEstado,
        efecto: evento.enfocarCantidad === true ? { tipo: "enfocarCantidad" } : null,
      };
    }

    case "fijarPartidaInicial": {
      const elegida = normalizarCompuesta(evento.partida);
      const siguienteEstado = aplicarLimpieza(estado, "partida", {
        elegida,
        texto: textoDePartidaElegida(elegida),
      });
      return { estado: siguienteEstado, efecto: { tipo: "enfocarCantidad" } };
    }

    case "cambiarCantidad":
      return sinEfecto(aplicarLimpieza(estado, "cantidad", { cantidad: evento.valor }));

    case "cambiarCalculo":
      return sinEfecto(aplicarLimpieza(estado, "calculo", { calculo: evento.valor }));

    case "verCalculo":
      if (estado.calculoVisto) return sinEfecto(estado);
      return sinEfecto({ ...estado, calculoVisto: true });

    case "cambiarNota":
      return sinEfecto({ ...estado, nota: evento.valor });

    case "alternarPliegue":
      if (estado.pliegueAbierto === evento.abierto) return sinEfecto(estado);
      return sinEfecto({ ...estado, pliegueAbierto: evento.abierto });

    case "enviar": {
      if (estado.elegida === null) {
        return {
          estado: conErrores(baseDe(estado), { ...SIN_ERRORES, partida: ELEGIR_DE_LA_LISTA }),
          efecto: { tipo: "enfocarErrores" },
        };
      }
      if (estaVacioCifra(estado.cantidad) && estaVacioCifra(estado.calculo)) {
        return {
          estado: conErrores(baseDe(estado), { ...SIN_ERRORES, cantidad: MENSAJE_CIFRA_VACIA }),
          efecto: { tipo: "enfocarErrores" },
        };
      }
      return {
        estado: { ...baseDe(estado), fase: "enviando" },
        efecto: {
          tipo: "postPartida",
          partida: {
            codigo: estado.elegida.codigo,
            cantidad: estado.cantidad,
            calculo: estado.calculo,
            nota: estado.nota,
          },
        },
      };
    }

    default:
      return sinEfecto(estado);
  }
}
