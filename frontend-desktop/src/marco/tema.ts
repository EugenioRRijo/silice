// Tema de la empresa (rediseño del marco, Tarea 1). El repositorio lleva alias neutros en estilos/tokens.scss; los
// colores de la empresa llegan de GET /v1/tema (leidos de <datos>/tema/ en el servidor) y se fijan como variables
// CSS en la raiz. Solo se acepta #rrggbb: cualquier otra cosa se ignora y queda el valor neutro.

export interface TemaRespuesta {
  acento: string | null;
  marco: string | null;
  lateral: string | null;
  tiene_logo: boolean;
  // Avisos de contraste, ya redactados por el servidor (que es quien mide); aqui solo se muestran.
  avisos: string[];
}

export const RUTA_DEL_LOGO = "/v1/tema/logo";

const COLOR = /^#[0-9a-fA-F]{6}$/;
const VARIABLES = {
  acento: "--silice-acento",
  marco: "--silice-marco",
  lateral: "--silice-lateral",
} as const;

export function esColor(valor: unknown): valor is string {
  return typeof valor === "string" && COLOR.test(valor);
}

// La respuesta se valida campo a campo: un servidor viejo o una respuesta rota dan el tema neutro, no un error.
export function leerTema(bruto: unknown): TemaRespuesta {
  const dato = (bruto && typeof bruto === "object" ? bruto : {}) as Record<string, unknown>;
  return {
    acento: esColor(dato.acento) ? dato.acento : null,
    marco: esColor(dato.marco) ? dato.marco : null,
    lateral: esColor(dato.lateral) ? dato.lateral : null,
    tiene_logo: dato.tiene_logo === true,
    avisos: Array.isArray(dato.avisos) ? dato.avisos.filter((a): a is string => typeof a === "string") : [],
  };
}

export function aplicarTema(tema: TemaRespuesta, raiz: HTMLElement): void {
  for (const clave of Object.keys(VARIABLES) as (keyof typeof VARIABLES)[]) {
    const color = tema[clave];
    if (esColor(color)) raiz.style.setProperty(VARIABLES[clave], color);
  }
}
