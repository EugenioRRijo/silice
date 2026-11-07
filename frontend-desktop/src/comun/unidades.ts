// «m2» y «m3» se leen «m²» y «m³», y «dia» (la forma canónica del servidor) se lee «día»; el valor que manda el
// servidor no cambia, solo cómo se presenta (Tramos, Hoja).
const ESCRITA: Record<string, string> = { m2: "m²", m3: "m³", dia: "día" };

export const unidadEscrita = (unidad: string): string => ESCRITA[unidad] ?? unidad;
