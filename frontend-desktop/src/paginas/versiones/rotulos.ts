// Los nombres con que el registro de cambios nombra «qué» cambió. El servidor guarda claves técnicas («parametro»,
// «bono_alimentacion»): forman parte de la huella de la versión y no se tocan; aquí solo se presentan en español llano.
// Una clave que no está en la lista se presenta sin guiones bajos y con mayúscula inicial, nunca cruda.

const OBJETOS: Record<string, string> = {
  apu: "APU",
  cantidad: "Cantidad",
  metraje: "Metraje",
  moneda: "Moneda",
  parametro: "Parámetro",
  plan: "Plan",
  precio: "Precio",
  version: "Versión",
};

const CAMPOS: Record<string, string> = {
  alta: "Alta",
  baja: "Baja",
  cantidad: "Cantidad",
  cotizacion: "Cotización",
  creacion: "Creación",
  descripcion: "Descripción",
  fila: "Fila",
  insumo: "Insumo",
  instantanea: "Instantánea",
  moneda: "Moneda",
  precio: "Precio",
  rendimiento: "Rendimiento",
  restauracion: "Restauración",
  unidad: "Unidad",
  valor: "Valor",
};

// La clave de un parámetro de costo (la clave de la fila cuando el objeto es «parametro»).
const PARAMETROS: Record<string, string> = {
  administracion: "Administración",
  bono_alimentacion: "Bono de alimentación",
  fcas: "FCAS",
  utilidad: "Utilidad",
};

function llano(clave: string): string {
  const texto = clave.replace(/_/g, " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export const rotuloDeObjeto = (objeto: string): string => OBJETOS[objeto] ?? llano(objeto);
export const rotuloDeCampo = (campo: string): string => CAMPOS[campo] ?? llano(campo);
export const rotuloDeParametro = (clave: string): string => PARAMETROS[clave] ?? llano(clave);
