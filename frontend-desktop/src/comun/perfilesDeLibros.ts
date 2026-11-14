// Lo que comparten la auditoría del libro con un APU por hoja (`paginas/auditoria/AuditarApuPorHoja.tsx`) y la
// administración de sus perfiles (`paginas/administracion/PerfilesDeLibros.tsx`); vive aquí desde la ronda 1 de la ola 2
// (hallazgo 2 del árbitro: ninguna página importa de otra, `comun/arquitectura.test.ts`). Solo textos y la forma de la
// respuesta: la pantalla no lee ni interpreta el perfil.

// Un perfil del libro como lo lista `GET /v1/libros/perfiles-apu-por-hoja` y como responde `POST /v1/admin/empresa/perfiles-libros`.
export interface PerfilDisponible {
  nombre: string;
  origen: "paquete" | "local";
  hoja_presupuesto: string | null;
  hojas_presupuesto?: string[];
  motivo: string | null;
}

// «A», «A y B», «A, B y C».
export function enumeradas(nombres: string[]): string {
  return nombres.length <= 1 ? (nombres[0] ?? "") : `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
}
