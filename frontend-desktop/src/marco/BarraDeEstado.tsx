import { Folder } from "@carbon/icons-react";
import type { JSX } from "react";
import { Campanita } from "../comun/notificaciones/Campanita";
import { formatoEsVe } from "../indicadores/formatoEsVe";
import "./BarraDeEstado.scss";

export interface PropsDeBarraDeEstado {
  carpeta?: string | null;
  ultimoGuardado?: Date | string | null;
  ahora?: Date;
}

function textoDeCarpeta(carpeta: string): string {
  const limpio = carpeta.trim();
  return /^carpeta\b/i.test(limpio) ? limpio : `Carpeta ${limpio}`;
}

export function formatearUltimoGuardado(
  ultimoGuardado: Date | string,
  ahora: Date = new Date(),
): string | null {
  const instante =
    ultimoGuardado instanceof Date ? ultimoGuardado.getTime() : Date.parse(ultimoGuardado);
  if (Number.isNaN(instante)) return null;
  const segundos = Math.max(0, Math.floor((ahora.getTime() - instante) / 1_000));
  if (segundos === 0) return "Guardado hace unos segundos";
  if (segundos < 60) return `Guardado hace ${formatoEsVe(String(segundos))} s`;
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `Guardado hace ${formatoEsVe(String(minutos))} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `Guardado hace ${formatoEsVe(String(horas))} h`;
  const dias = Math.floor(horas / 24);
  return dias === 1 ? "Guardado hace 1 día" : `Guardado hace ${formatoEsVe(String(dias))} días`;
}

export function BarraDeEstado({
  carpeta,
  ultimoGuardado,
  ahora,
}: PropsDeBarraDeEstado = {}): JSX.Element {
  const tieneCarpeta = carpeta !== undefined && carpeta !== null && carpeta.trim() !== "";
  const textoGuardado =
    ultimoGuardado !== undefined && ultimoGuardado !== null && ultimoGuardado !== ""
      ? formatearUltimoGuardado(ultimoGuardado, ahora)
      : null;

  return (
    <footer className="silice-barra-estado" aria-label="Barra de estado">
      {tieneCarpeta && (
        <span className="silice-barra-estado__carpeta">
          <Folder size={16} className="silice-barra-estado__icono" aria-hidden="true" />
          <span>{textoDeCarpeta(carpeta)}</span>
        </span>
      )}
      {tieneCarpeta && textoGuardado !== null && (
        <span className="silice-barra-estado__sep" aria-hidden="true">
          ·
        </span>
      )}
      {textoGuardado !== null && (
        <span className="silice-barra-estado__guardado">{textoGuardado}</span>
      )}
      <span className="silice-barra-estado__espacio" />
      <Campanita />
    </footer>
  );
}
