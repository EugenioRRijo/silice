import { SkeletonText } from "@carbon/react";

// Marcador mientras llega el archivo de una pagina (carga perezosa). Sin animacion propia.
export function EsqueletoPagina({ etiqueta = "Cargando la pantalla" }: { etiqueta?: string }) {
  return (
    <div className="silice-esqueleto-pagina" role="status" aria-busy="true" aria-label={etiqueta}>
      <SkeletonText heading width="30%" />
      <SkeletonText paragraph lineCount={5} />
    </div>
  );
}
