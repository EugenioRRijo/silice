import { createContext } from "react";

// El borrador de la Hoja abierto en la obra (corrección de la ronda 1 de la ola 2, hallazgo 2): lo que una pantalla que no
// es de la Hoja necesita de él. Componer (RF-200) lee aquí el borrador para proponer los parámetros de «Ajustes de costo»
// de la obra, sin importar el proveedor de la Hoja (ninguna página importa de otra: `comun/arquitectura.test.ts`).
// Lo pone `paginas/hoja/ProveedorDeLaHoja.tsx`; sin Hoja abierta (o con su borrador cargando), `null`.
export const ContextoDelBorradorAbierto = createContext<string | null>(null);

// Las vistas que contesta `GET /v1/hoja/borradores/{id}/vistas/{nombre}`.
export type NombreDeVista = "espacio" | "presupuesto" | "apu" | "plan" | "equilibrio" | "parametros" | "auditoria";

export function rutaDeVista(id: string, nombre: NombreDeVista, parametros: Record<string, string | undefined> = {}): string {
  const consulta = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) if (valor) consulta.set(clave, valor);
  const texto = consulta.toString();
  return `/v1/hoja/borradores/${id}/vistas/${nombre}${texto ? `?${texto}` : ""}`;
}
