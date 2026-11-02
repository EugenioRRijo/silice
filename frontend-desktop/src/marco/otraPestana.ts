// Vigilancia de pestañas (especificación 2026-10-26, §8 ter): todas las pestañas comparten la sesión del servidor, y
// con ella la carpeta abierta. La pestaña que abre una obra lo anuncia por `BroadcastChannel("silice-obra")`; la que
// tenía otra obra recibe el aviso y deja de trabajar en ella hasta que la retoma (marco/useObraDeLaRuta). Sin
// `BroadcastChannel` en el navegador no se vigila: anunciar y escuchar no hacen nada.

export const NOMBRE_DEL_CANAL = "silice-obra";

export interface ObraAnunciada {
  carpeta: string | null;
  obraId: number;
}

// Lo que se usa de un BroadcastChannel; las pruebas dan uno de mentira.
export interface CanalDeObra {
  onmessage: ((evento: MessageEvent) => void) | null;
  postMessage(mensaje: unknown): void;
}

export interface VigilanteDeObra {
  // Esta pestaña trabaja ahora en esta obra; las demás que tengan otra reciben el aviso.
  anunciarObra(carpeta: string | null, obraId: number): void;
  // Llama a `cb` cuando otra pestaña anuncia una obra distinta de la que esta anunció. Devuelve cómo dejar de escuchar.
  escucharOtraPestana(cb: (otra: ObraAnunciada) => void): () => void;
}

function esObraAnunciada(dato: unknown): dato is ObraAnunciada {
  if (typeof dato !== "object" || dato === null) return false;
  const { carpeta, obraId } = dato as Record<string, unknown>;
  return (carpeta === null || typeof carpeta === "string") && Number.isInteger(obraId);
}

export function crearVigilante(canal: CanalDeObra | null): VigilanteDeObra {
  const oyentes = new Set<(otra: ObraAnunciada) => void>();
  let propia: ObraAnunciada | null = null;
  if (canal) {
    canal.onmessage = (evento) => {
      const otra: unknown = evento.data;
      if (!esObraAnunciada(otra) || propia === null) return;
      if (otra.carpeta === propia.carpeta && otra.obraId === propia.obraId) return;
      for (const cb of [...oyentes]) cb(otra);
    };
  }
  return {
    anunciarObra(carpeta, obraId) {
      if (!canal) return;
      propia = { carpeta, obraId };
      canal.postMessage(propia);
    },
    escucharOtraPestana(cb) {
      oyentes.add(cb);
      return () => {
        oyentes.delete(cb);
      };
    },
  };
}

// El de la aplicación, con el canal del navegador (uno por pestaña, creado al primer uso).
let delNavegador: VigilanteDeObra | null = null;

export function vigilanteDelNavegador(): VigilanteDeObra {
  delNavegador ??= crearVigilante(typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(NOMBRE_DEL_CANAL));
  return delNavegador;
}

export function anunciarObra(carpeta: string | null, obraId: number): void {
  vigilanteDelNavegador().anunciarObra(carpeta, obraId);
}

export function escucharOtraPestana(cb: (otra: ObraAnunciada) => void): () => void {
  return vigilanteDelNavegador().escucharOtraPestana(cb);
}
