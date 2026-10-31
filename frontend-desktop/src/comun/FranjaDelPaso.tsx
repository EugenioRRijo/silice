// STUB del rojo (Tarea 2): lo reemplaza la implementación.
interface Props {
  tipo: "falta" | "siguiente";
  texto: string;
  accion?: { texto: string; alPulsar: () => void; deshabilitada?: boolean };
}

export function FranjaDelPaso(p: Props) {
  return <div data-tipo={p.tipo} />;
}
