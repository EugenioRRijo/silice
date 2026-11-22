import { Catalog, DocumentView, Industry, Workspace } from "@carbon/icons-react";
import { useEffect, useState } from "react";
import "./ModeTransitionOverlay.scss";

export type EstacionMayor = "obras" | "auditoria" | "precios" | "produccion";

const METADATOS: Record<EstacionMayor, { codigo: string; titulo: string; subtitulo: string; detalle: string }> = {
  obras: {
    codigo: "Espacio principal · Obras",
    titulo: "Gestión Integral de Obras",
    subtitulo: "Presupuestos APU, rendimientos, control EVM y entregas",
    detalle: "Preparando cartera y presupuestos activos…",
  },
  auditoria: {
    codigo: "01 · Ventana dedicada",
    titulo: "Auditor Forense de Presupuestos",
    subtitulo: "Inspección celda por celda, fórmulas y verificación del libro",
    detalle: "Abriendo mesa de auditoría…",
  },
  precios: {
    codigo: "02 · Ventana dedicada",
    titulo: "Precios, Catálogo e Índices BCV",
    subtitulo: "Listas maestras, detector de atípicos ML y simulador",
    detalle: "Cargando catálogo de insumos y series BCV…",
  },
  produccion: {
    codigo: "03 · Ventana dedicada",
    titulo: "Costos de Producción y Cantera",
    subtitulo: "Existencias de agregados, costo por tonelada y mezclas de planta",
    detalle: "Cargando existencias de patio y costos…",
  },
};

function prefiereMenosMovimiento(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function ContenidoTransicion({ destino, alTerminar }: { destino: EstacionMayor; alTerminar: () => void }) {
  const reducido = prefiereMenosMovimiento();
  const [progreso, setProgreso] = useState(14);

  useEffect(() => {
    if (reducido) {
      const t = window.setTimeout(() => alTerminar(), 0);
      return () => window.clearTimeout(t);
    }
    const t1 = window.setTimeout(() => setProgreso(66), 80);
    const t2 = window.setTimeout(() => setProgreso(100), 210);
    const t3 = window.setTimeout(() => alTerminar(), 340);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [alTerminar, reducido]);

  if (reducido) return null;

  const meta = METADATOS[destino];
  const Icono =
    destino === "auditoria"
      ? DocumentView
      : destino === "precios"
        ? Catalog
        : destino === "produccion"
          ? Industry
          : Workspace;

  return (
    <div className="silice-transicion" role="status" aria-live="polite" aria-label={`Cargando ${meta.titulo}`}>
      <div className="silice-transicion__tarjeta">
        <div className="silice-transicion__acento" aria-hidden="true" />
        <div className="silice-transicion__cabecera">
          <span className="silice-transicion__codigo">{meta.codigo}</span>
          <span className="silice-transicion__porcentaje">{`${progreso} %`}</span>
        </div>
        <div className="silice-transicion__cuerpo">
          <div className="silice-transicion__icono" aria-hidden="true">
            <Icono size={24} />
          </div>
          <div>
            <p className="silice-transicion__titulo">{meta.titulo}</p>
            <p className="silice-transicion__sub">{meta.subtitulo}</p>
          </div>
        </div>
        <div className="silice-transicion__barra-bloque">
          <div className="silice-transicion__pista">
            <div className="silice-transicion__progreso" style={{ inlineSize: `${progreso}%` }} />
          </div>
          <p className="silice-transicion__detalle">{meta.detalle}</p>
        </div>
      </div>
    </div>
  );
}

export function ModeTransitionOverlay({
  destino,
  alTerminar,
}: {
  destino: EstacionMayor | null;
  alTerminar: () => void;
}) {
  if (!destino) return null;
  return <ContenidoTransicion key={destino} destino={destino} alTerminar={alTerminar} />;
}
