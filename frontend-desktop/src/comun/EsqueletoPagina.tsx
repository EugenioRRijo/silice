import { SkeletonText } from "@carbon/react";

// Marcador mientras llega el archivo de una pagina (carga perezosa). Sin animacion propia.
// Con `titulo` (una pagina entera que aun carga) dibuja antes el h1 de la pagina: nunca hay una pagina sin titulo.
export function EsqueletoPagina({ etiqueta = "Cargando la pantalla", titulo }: { etiqueta?: string; titulo?: string }) {
  const esqueleto = (
    <div className="silice-esqueleto-pagina" role="status" aria-busy="true" aria-label={etiqueta}>
      <SkeletonText heading width="30%" />
      <SkeletonText paragraph lineCount={5} />
    </div>
  );
  if (!titulo) return esqueleto;
  return (
    <section className="silice-pagina">
      <h1 className="cds--type-heading-04" data-esqueleto="">
        {titulo}
      </h1>
      {esqueleto}
    </section>
  );
}
