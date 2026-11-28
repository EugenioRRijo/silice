import { useMemo } from "react";
import { useCarga } from "./useCarga";

// El «Qué hacer» de cada hallazgo y de cada alerta de precio (B2, ficha-b2 §3.3). Lo escribe el servidor
// (`aplicacion/que_hacer.py`) y llega por `GET /v1/libros/que-hacer`; aquí solo se lee, se valida y se busca por código.
// La pantalla no inventa ningún texto: un código que el catálogo no conoce recibe la guía genérica, marcada como tal.

export interface GuiaQueHacer {
  // El código estable: el de la regla («L4») o `alerta:<tipo>`.
  codigo: string;
  titulo: string;
  significa: string;
  que_hacer: string;
  // `true`: no es una guía propia de ese código.
  generico: boolean;
  // Frases con que el servidor declara que una alerta de ese tipo no avisa de nada.
  sin_aviso_si: string[];
}

export interface CatalogoQueHacer {
  reglas: Record<string, GuiaQueHacer>;
  alertas: Record<string, GuiaQueHacer>;
  generico: GuiaQueHacer;
}

export const RUTA_QUE_HACER = "/v1/libros/que-hacer";

function esRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function leerGuia(valor: unknown, donde: string): GuiaQueHacer {
  if (!esRegistro(valor)) throw new Error(`Guía «Qué hacer» ilegible: ${donde}`);
  const { codigo, titulo, significa, que_hacer, generico, sin_aviso_si } = valor;
  const textosBien = [codigo, titulo, significa, que_hacer].every((t) => typeof t === "string");
  const frasesBien = Array.isArray(sin_aviso_si) && sin_aviso_si.every((f) => typeof f === "string");
  if (!textosBien || typeof generico !== "boolean" || !frasesBien) {
    throw new Error(`Guía «Qué hacer» ilegible: ${donde}`);
  }
  return {
    codigo: codigo as string,
    titulo: titulo as string,
    significa: significa as string,
    que_hacer: que_hacer as string,
    generico,
    sin_aviso_si: sin_aviso_si as string[],
  };
}

function leerGuias(valor: unknown, donde: string): Record<string, GuiaQueHacer> {
  if (!esRegistro(valor)) throw new Error(`Catálogo «Qué hacer» ilegible: ${donde}`);
  return Object.fromEntries(Object.entries(valor).map(([clave, guia]) => [clave, leerGuia(guia, `${donde}.${clave}`)]));
}

// Analizador de la respuesta del servidor: lo que no tiene la forma esperada se rechaza con su lugar.
export function leerCatalogoQueHacer(datos: unknown): CatalogoQueHacer {
  if (!esRegistro(datos)) throw new Error("Catálogo «Qué hacer» ilegible");
  return {
    reglas: leerGuias(datos["reglas"], "reglas"),
    alertas: leerGuias(datos["alertas"], "alertas"),
    generico: leerGuia(datos["generico"], "generico"),
  };
}

function genericaDe(catalogo: CatalogoQueHacer, codigo: string): GuiaQueHacer {
  return { ...catalogo.generico, codigo };
}

export function guiaDeRegla(catalogo: CatalogoQueHacer, codigo: string): GuiaQueHacer {
  return catalogo.reglas[codigo] ?? genericaDe(catalogo, codigo);
}

export function guiaDeAlerta(catalogo: CatalogoQueHacer, tipo: string): GuiaQueHacer {
  return catalogo.alertas[tipo] ?? genericaDe(catalogo, `alerta:${tipo}`);
}

// El catálogo de la pantalla: `null` mientras carga, mientras no hace falta (`activo` falso: no se pide nada hasta que hay un
// resultado) o si no se pudo leer (la pantalla sigue sin los botones «Qué hacer»).
export function useCatalogoQueHacer(alExpirar: () => void, activo: boolean): CatalogoQueHacer | null {
  const carga = useCarga<unknown>(activo ? RUTA_QUE_HACER : null, alExpirar);
  const datos = carga.estado === "listo" ? carga.datos : null;
  return useMemo(() => {
    if (datos === null) return null;
    try {
      return leerCatalogoQueHacer(datos);
    } catch {
      return null;
    }
  }, [datos]);
}
