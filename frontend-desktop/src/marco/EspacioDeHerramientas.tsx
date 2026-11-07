import { Suspense } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation, useParams } from "react-router";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { AyudaDeLaPantalla } from "../comun/ayuda/AyudaDeLaPantalla";
import { LimiteDeError } from "../shell/LimiteDeError";
import { paginaPorId, usable } from "../shell/rutas";
import { BarraDeEspacio, pestanasUsables } from "./BarraDeEspacio";
import { ESPACIOS, primeraUsable, rutaDeHerramienta } from "./espacios";
import type { EspacioId } from "./espacios";

interface Props {
  espacio: EspacioId;
  // La pantalla de la herramienta (`pagina` de ESPACIOS): la pinta el marco, con sus permisos y avisos.
  pantalla: (pagina: string) => ReactNode;
  acciones: readonly string[];
  modoEntrega: boolean;
  apagados: readonly string[];
}

// A dónde lleva un espacio sin herramienta, o con una que no existe: la primera que la cuenta puede usar o, si no puede
// ninguna, la primera definida, que muestra el aviso de siempre (sin permiso o apagada) y no vuelve a redirigir.
export function RaizDelEspacio({ espacio, acciones, modoEntrega, apagados }: Omit<Props, "pantalla">) {
  const { search } = useLocation();
  const { herramientas } = ESPACIOS[espacio];
  const destino = primeraUsable(herramientas, acciones, modoEntrega, apagados) ?? herramientas[0];
  return <Navigate to={`${rutaDeHerramienta(espacio, destino.id)}${search}`} replace />;
}

// Producción, Auditoría o Precios como espacio de trabajo (plan F6, T4; diseño visual 2.1): su título arriba, sin h1 (el
// único h1 es el de la pantalla), debajo la barra con sus herramientas y, en el lienzo, la pantalla de la herramienta. La
// cabecera y la barra no se vuelven a montar al cambiar de herramienta (el marco da la misma clave a todo el espacio), así
// que el enlace pulsado conserva el foco; el límite de error y la espera son de cada herramienta.
export function EspacioDeHerramientas({ espacio, pantalla, acciones, modoEntrega, apagados }: Props) {
  const { herramienta: id } = useParams();
  const { titulo, herramientas } = ESPACIOS[espacio];
  const herramienta = herramientas.find((h) => h.id === id);
  if (herramienta === undefined) {
    return <RaizDelEspacio espacio={espacio} acciones={acciones} modoEntrega={modoEntrega} apagados={apagados} />;
  }
  const pestanas = pestanasUsables(herramientas, (h) => rutaDeHerramienta(espacio, h.id), acciones, modoEntrega, apagados);
  // F7, A1: el «¿Qué es esto?» de la herramienta, solo si la cuenta puede usarla (si no, la pantalla dice por qué).
  const pagina = paginaPorId(herramienta.pagina);
  const conAyuda = pagina !== undefined && usable(pagina, acciones, modoEntrega, apagados);
  return (
    <>
      <section aria-label={titulo} className="silice-espacio-cabecera">
        <p className="silice-espacio-cabecera__titulo">{titulo}</p>
      </section>
      {/* Sin ninguna herramienta usable no hay barra que ofrecer: la pantalla dice por qué (sin permiso o apagada). */}
      {pestanas.length > 0 && <BarraDeEspacio etiqueta={titulo} pestanas={pestanas} activa={herramienta.id} nivel="espacio" />}
      {conAyuda && <AyudaDeLaPantalla pagina={herramienta.pagina} />}
      <LimiteDeError key={herramienta.id}>
        <Suspense fallback={<EsqueletoPagina />}>{pantalla(herramienta.pagina)}</Suspense>
      </LimiteDeError>
    </>
  );
}
