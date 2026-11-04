import { ESPACIOS, espacioDeLaPagina, rutaOPendientes } from "./espacios";
import { seccionesDeLaObra } from "./oferta";
import type { Oferta } from "./oferta";
import { rutaDeObra } from "./secciones";
import type { ObraDeCarpeta } from "./useObras";

export interface Resultado {
  texto: string;
  detalle: string;
  ruta: string;
}

export const MAXIMO_DE_RESULTADOS = 8;
const OBRAS_SIN_TEXTO = 5;

function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

// El título del espacio donde vive una pantalla, o "" si no es de ninguno.
function tituloDelEspacio(paginaId: string): string {
  const donde = espacioDeLaPagina(paginaId);
  return donde === undefined ? "" : ESPACIOS[donde.espacio].titulo;
}

// Todas las palabras escritas aparecen en el texto, sin importar acentos, mayúsculas ni orden de aparición.
function coincide(palabras: readonly string[], texto: string): boolean {
  const limpio = normalizar(texto);
  return palabras.every((p) => limpio.includes(p));
}

// Qué se encuentra con el texto escrito: obras, luego sus secciones, luego las entradas de Empresa y por último las
// pantallas de los espacios y las subvistas. Sin texto, las primeras obras de la lista. Nunca más de `MAXIMO_DE_RESULTADOS`. La
// oferta es obligatoria: sin ella no habría con qué decidir qué puede usar la cuenta. Una ruta no sale dos veces (la
// sección «Resumen» de una obra lleva a la misma que la obra).
export function resultadosDe(
  texto: string,
  obras: readonly ObraDeCarpeta[],
  oferta: Oferta,
): Resultado[] {
  const palabras = normalizar(texto).split(/\s+/).filter(Boolean);
  const deLaObra = (o: ObraDeCarpeta): Resultado => ({
    texto: o.obra,
    detalle: o.carpeta_titulo,
    ruta: rutaDeObra(o.carpeta, o.obra_id, "resumen"),
  });
  if (palabras.length === 0) return obras.slice(0, OBRAS_SIN_TEXTO).map(deLaObra);

  const todos: (Resultado & { buscable?: string })[] = [
    ...obras.map(deLaObra),
    ...obras.flatMap((o) =>
      seccionesDeLaObra(oferta).map((s) => ({
        texto: `${o.obra} › ${s.titulo}`,
        detalle: s.ayuda,
        ruta: rutaDeObra(o.carpeta, o.obra_id, s.id),
      })),
    ),
    ...oferta.entradas.map((e) => ({ texto: e.titulo, detalle: e.ayuda, ruta: rutaOPendientes(e.pagina) })),
    ...[...oferta.sueltas, ...oferta.herramientas].map((p) => ({
      texto: p.titulo,
      detalle: p.enUnaLinea,
      ruta: rutaOPendientes(p.id),
      // El nombre del espacio también las encuentra: «precios» lleva a cada herramienta de «Precios y catálogo».
      buscable: `${tituloDelEspacio(p.id)} ${p.titulo}`,
    })),
  ];
  const rutasVistas = new Set<string>();
  return todos
    .filter((r) => coincide(palabras, r.buscable ?? r.texto) && !rutasVistas.has(r.ruta) && rutasVistas.add(r.ruta))
    .slice(0, MAXIMO_DE_RESULTADOS)
    .map(({ texto, detalle, ruta }) => ({ texto, detalle, ruta }));
}
