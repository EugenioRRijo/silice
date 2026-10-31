import { rutaDe } from "../shell/rutas";
import { claveDeObra } from "../paginas/pendientes/logica";
import { seccionesDeLaObra } from "./oferta";
import type { Oferta } from "./oferta";
import { rutaDeEmpresa, rutaDeObra } from "./secciones";
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

// Todas las palabras escritas aparecen en el texto, sin importar acentos, mayúsculas ni orden de aparición.
function coincide(palabras: readonly string[], texto: string): boolean {
  const limpio = normalizar(texto);
  return palabras.every((p) => limpio.includes(p));
}

// Qué se encuentra con el texto escrito: obras, luego sus secciones, luego las entradas de Empresa y por último las
// pantallas sin sitio en el árbol. Sin texto, las primeras obras de la lista. Nunca más de `MAXIMO_DE_RESULTADOS`. La
// oferta es obligatoria: sin ella no habría con qué decidir qué puede usar la cuenta. Una ruta no sale dos veces (la
// sección «Resumen» de una obra lleva a la misma que la obra).
export function resultadosDe(
  texto: string,
  obras: readonly ObraDeCarpeta[],
  oferta: Oferta,
  // Las obras (carpeta|número) con tramos guardados: solo ellas ofrecen la sección «Tramos».
  viales: ReadonlySet<string> = new Set(),
): Resultado[] {
  const palabras = normalizar(texto).split(/\s+/).filter(Boolean);
  const deLaObra = (o: ObraDeCarpeta): Resultado => ({
    texto: o.obra,
    detalle: o.carpeta_titulo,
    ruta: rutaDeObra(o.carpeta, o.obra_id, "resumen"),
  });
  if (palabras.length === 0) return obras.slice(0, OBRAS_SIN_TEXTO).map(deLaObra);

  const todos: Resultado[] = [
    ...obras.map(deLaObra),
    ...obras.flatMap((o) =>
      seccionesDeLaObra(oferta, viales.has(claveDeObra(o.carpeta, o.obra_id))).map((s) => ({
        texto: `${o.obra} › ${s.titulo}`,
        detalle: s.ayuda,
        ruta: rutaDeObra(o.carpeta, o.obra_id, s.id),
      })),
    ),
    ...oferta.entradas.map((e) => ({ texto: e.titulo, detalle: e.ayuda, ruta: rutaDeEmpresa(e.id) })),
    ...oferta.sueltas.map((p) => ({ texto: p.titulo, detalle: p.enUnaLinea, ruta: rutaDe(p) })),
  ];
  const rutasVistas = new Set<string>();
  return todos
    .filter((r) => coincide(palabras, r.texto) && !rutasVistas.has(r.ruta) && rutasVistas.add(r.ruta))
    .slice(0, MAXIMO_DE_RESULTADOS);
}
