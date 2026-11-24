// El tipo de insumo como lo dice la pantalla y no la clave del servidor (árbitro 13/11, M5).
export const TIPOS_DE_INSUMO: Record<string, string> = {
  material: "Material",
  equipo: "Equipo",
  mano_obra: "Mano de obra",
};

export const tipoDeInsumoEscrito = (tipo: string): string => TIPOS_DE_INSUMO[tipo] ?? tipo;
