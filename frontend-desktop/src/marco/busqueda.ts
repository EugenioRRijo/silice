import { PAGINAS, rutaDe } from "../shell/rutas";
import { ofertaDe, type Oferta } from "./oferta";
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

// Sin oferta, se asume la de una cuenta que lo puede todo (para pruebas y usos sin sesión): el componente siempre pasa la suya.
const OFERTA_COMPLETA: Oferta = ofertaDe(
  PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion])),
  false,
);

// Qué se encuentra con el texto escrito: obras, luego sus secciones, luego las entradas de Empresa y por último las
// pantallas sin sitio en el árbol. Sin texto, las primeras obras de la lista. Nunca más de `MAXIMO_DE_RESULTADOS`.
export function resultadosDe(texto: string, obras: readonly ObraDeCarpeta[], oferta: Oferta = OFERTA_COMPLETA): Resultado[] {
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
      oferta.secciones.map((s) => ({
        texto: `${o.obra} › ${s.titulo}`,
        detalle: s.ayuda,
        ruta: rutaDeObra(o.carpeta, o.obra_id, s.id),
      })),
    ),
    ...oferta.entradas.map((e) => ({ texto: e.titulo, detalle: e.ayuda, ruta: rutaDeEmpresa(e.id) })),
    ...oferta.sueltas.map((p) => ({ texto: p.titulo, detalle: p.enUnaLinea, ruta: rutaDe(p) })),
  ];
  return todos.filter((r) => coincide(palabras, r.texto)).slice(0, MAXIMO_DE_RESULTADOS);
}
