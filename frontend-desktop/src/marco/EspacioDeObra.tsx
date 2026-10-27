import { Button } from "@carbon/react";
import { useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { CasosRespuesta } from "../api/tipos";
import { AvisoError } from "../comun/AvisoError";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { ContextoAplicacion } from "../shell/contexto";
import { RUTA_DE_PENDIENTES } from "./secciones";
import { useObraDeLaRuta } from "./useObraDeLaRuta";
import type { VigilanteDeObra } from "./otraPestana";
import type { ObraDeCarpeta } from "./useObras";

interface Props {
  obras: readonly ObraDeCarpeta[];
  casos: CasosRespuesta | null;
  // La obra quedó lista (carpeta y obra fijadas en la sesión del servidor): el marco la recuerda.
  alEntrar: (carpeta: string | null, obraId: number) => void;
  // La pantalla de la sección (`pagina` de SECCIONES_DE_OBRA): la pinta el marco, con sus permisos.
  pantalla: (pagina: string) => ReactNode;
  vigilante?: VigilanteDeObra;
}

// Un aviso de pantalla completa con su h1 (el foco va a él al llegar, como con cualquier pantalla).
function Aviso({ titulo, texto, children }: { titulo: string; texto: string; children: ReactNode }) {
  return (
    <div className="silice-pagina silice-obra-aviso">
      <h1 className="cds--type-heading-04">{titulo}</h1>
      <p className="cds--type-body-compact-01">{texto}</p>
      {children}
    </div>
  );
}

// La obra de la ruta `#/obra/<carpeta>/<obra>/<sección>` como espacio de trabajo (plan del rediseño del marco, Tarea 8;
// especificación 2026-10-26, §2.3 y §8 ter): primero fija carpeta y obra en la sesión (useObraDeLaRuta) y solo
// entonces monta la sección, con la cabecera de la obra encima. Mientras otra pestaña tenga otra obra, la sección no se
// monta: no hay escrituras en la obra equivocada.
export function EspacioDeObra({ obras, casos, alEntrar, pantalla, vigilante }: Props) {
  const estado = useObraDeLaRuta({ vigilante });
  const lista = estado.tipo === "lista" ? estado : null;
  const clave = lista ? JSON.stringify([lista.carpeta, lista.obraId]) : null;

  useEffect(() => {
    if (clave === null) return;
    const [carpeta, obraId] = JSON.parse(clave) as [string | null, number];
    alEntrar(carpeta, obraId);
  }, [clave, alEntrar]);

  switch (estado.tipo) {
    case "cargando":
      return <EsqueletoPagina etiqueta="Abriendo la obra" />;
    case "no_existe":
      return (
        <Aviso titulo="Esa obra ya no existe" texto="La borraron o su carpeta ya no está en esta instalación.">
          <Link className="cds--link" to={RUTA_DE_PENDIENTES}>
            Volver a Pendientes
          </Link>
        </Aviso>
      );
    case "en_otra_pestana":
      return (
        <Aviso
          titulo="Esta obra se abrió en otra pestaña"
          texto="Otra pestaña de Sílice abrió otra obra. Retómela aquí para seguir trabajando en esta."
        >
          <Button kind="primary" size="md" onClick={estado.retomar}>
            Retomar
          </Button>
        </Aviso>
      );
    case "error":
      return (
        <div className="silice-pagina-aviso">
          <AvisoError error="No se pudo abrir la obra. Revise la conexión con Sílice." titulo="No se pudo abrir la obra" />
          <Button kind="tertiary" size="md" onClick={estado.reintentar}>
            Reintentar
          </Button>
        </div>
      );
    case "lista":
      return (
        <ObraAbierta
          carpeta={estado.carpeta}
          obraId={estado.obraId}
          obra={obras.find((o) => o.carpeta === estado.carpeta && o.obra_id === estado.obraId)}
          casos={casos}
        >
          {estado.seccion.pagina !== null && pantalla(estado.seccion.pagina)}
        </ObraAbierta>
      );
  }
}

interface ObraAbiertaProps {
  carpeta: string | null;
  obraId: number;
  obra: ObraDeCarpeta | undefined;
  casos: CasosRespuesta | null;
  children: ReactNode;
}

// La cabecera de la obra (nombre, moneda y versión) y la sección. La sección lee la obra y la carpeta de la ruta desde
// el primer dibujo (no las del marco, que se ponen al día un momento después).
function ObraAbierta({ carpeta, obraId, obra, casos, children }: ObraAbiertaProps) {
  const base = useContext(ContextoAplicacion);
  const moneda = useMonedaDeLaObra(obraId, base?.sesion.acciones.includes("leer_proyecto") ?? false, base?.alExpirar);
  const valor = useMemo(() => {
    if (!base) return null;
    const caso =
      carpeta === null
        ? (casos?.empresa ?? base.caso)
        : (casos?.casos.find((c) => c.nombre === carpeta) ?? { nombre: carpeta, ruta_relativa: "" });
    return { ...base, proyecto: String(obraId), nombreProyecto: obra?.obra ?? null, caso };
  }, [base, carpeta, obraId, obra, casos]);

  return (
    <>
      <section aria-label="Obra abierta" className="silice-obra-abierta">
        <p className="silice-obra-abierta__nombre">{obra?.obra ?? `Obra ${obraId}`}</p>
        <ul className="silice-obra-abierta__datos">
          {moneda !== null && <li>{`Moneda: ${moneda}`}</li>}
          <li>{`Versión: ${obra?.version_codigo ?? "sin versión guardada"}`}</li>
        </ul>
      </section>
      <ContextoAplicacion.Provider value={valor}>{children}</ContextoAplicacion.Provider>
    </>
  );
}

// La moneda de la obra sale de `GET /v1/obras/resumen` (la de la carpeta abierta, que ya es la de la obra). Sin
// `leer_proyecto` la API contestaría 403: no se pide y la cabecera no la dice.
function useMonedaDeLaObra(obraId: number, puedeLeer: boolean, alExpirar: (() => void) | undefined): string | null {
  const [moneda, setMoneda] = useState<{ obraId: number; valor: string | null } | null>(null);
  useEffect(() => {
    if (!puedeLeer) return;
    let vigente = true;
    pedir<{ obras?: { codigo: string; moneda: string }[] }>("/v1/obras/resumen")
      .then((r) => {
        if (vigente) setMoneda({ obraId, valor: r?.obras?.find((o) => o.codigo === String(obraId))?.moneda ?? null });
      })
      .catch((e: unknown) => {
        if (vigente && e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
      });
    return () => {
      vigente = false;
    };
  }, [obraId, puedeLeer, alExpirar]);
  return moneda?.obraId === obraId ? moneda.valor : null;
}
