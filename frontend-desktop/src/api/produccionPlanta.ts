// La planta de producción (`/v1/produccion`): recetas, producido del período, cálculo del costo por tonelada y su
// publicación al catálogo. Las cantidades y los montos viajan como texto decimal con punto: la coma es cosa de la
// pantalla. La hora la pone el servidor, así que ninguna petición lleva `ahora`.
import { pedir } from "./cliente";

const RUTA = "/v1/produccion";

export interface ComponenteDeReceta {
  codigo: string;
  cantidad_por_t: string; // decimal con punto, por tonelada de mezcla
  unidad: string; // "t" o "l"
  tipo: string; // "propio" o "comprado"
}

export interface RecetaNueva {
  producto: string;
  componentes: ComponenteDeReceta[];
  fuente: string;
  vigente_desde: string; // AAAA-MM-DD
}

export interface RecetaRespuesta extends RecetaNueva {
  id: number;
}

export function recetaVigente(producto: string, fecha: string, senal?: AbortSignal): Promise<RecetaRespuesta> {
  const consulta = `producto=${encodeURIComponent(producto)}&fecha=${encodeURIComponent(fecha)}`;
  return pedir<RecetaRespuesta>(`${RUTA}/recetas/vigente?${consulta}`, { senal });
}

export function registrarReceta(receta: RecetaNueva): Promise<{ id: number }> {
  return pedir<{ id: number }>(`${RUTA}/recetas`, { metodo: "POST", cuerpo: receta });
}

export interface Producido {
  codigo: string;
  toneladas: string; // decimal con punto
}

export function producidoDelPeriodo(periodo: string, senal?: AbortSignal): Promise<Producido[]> {
  return pedir<Producido[]>(`${RUTA}/producido?periodo=${encodeURIComponent(periodo)}`, { senal });
}

export interface CostoDeProducto {
  codigo: string;
  por_tonelada: string; // exacto, como se guardó
  presentado: string; // dos decimales, mitad hacia arriba
}

export interface CalculoDeCosto {
  id: number;
  periodo: string;
  moneda: string;
  huella: string;
  usuario: string;
  registrado: string;
  productos: CostoDeProducto[];
  // Entradas y resultado guardados; los decimales van como texto. Solo se leen para mostrar.
  instantanea: Record<string, unknown>;
}

export function calcularCosto(periodo: string, moneda: string): Promise<CalculoDeCosto> {
  return pedir<CalculoDeCosto>(`${RUTA}/calculos`, { metodo: "POST", cuerpo: { periodo, moneda } });
}

export interface Publicacion {
  id: number;
  nombre: string;
}

// Sin cuerpo: publica el cálculo tal como se guardó.
export function publicarCalculo(id: number): Promise<Publicacion> {
  return pedir<Publicacion>(`${RUTA}/calculos/${id}/publicar`, { metodo: "POST" });
}

export interface EmpresaDeAdministracion {
  empresa: { nombre: string; rif: string; ciudad: string } | null;
}

export function empresaDeAdministracion(senal?: AbortSignal): Promise<EmpresaDeAdministracion> {
  return pedir<EmpresaDeAdministracion>("/v1/admin/empresa", { senal });
}
