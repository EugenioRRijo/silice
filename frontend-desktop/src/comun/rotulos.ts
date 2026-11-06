// Los nombres con que el registro de cambios nombra «qué» cambió. El servidor guarda claves técnicas («parametro»,
// «bono_alimentacion»): forman parte de la huella de la versión y no se tocan; aquí solo se presentan en español llano.
// Una clave que no está en la lista se presenta sin guiones bajos y con mayúscula inicial, nunca cruda.

import { cifraSiLoEs } from "../indicadores/formatoEsVe";

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
  ambiente_id: "Ambiente",
  ancho: "Ancho (m)",
  alto: "Alto (m)",
  baja: "Baja",
  catalogo: "Catálogo",
  circuito_id: "Circuito",
  cantidad: "Cantidad",
  cotizacion: "Cotización",
  creacion: "Creación",
  descripcion: "Descripción",
  empotrado: "Empotrado",
  especialidad: "Especialidad",
  especificaciones: "Especificaciones",
  fila: "Fila",
  fuente_id: "Fuente que lo alimenta",
  insumo: "Insumo",
  instantanea: "Instantánea",
  largo: "Largo (m)",
  moneda: "Moneda",
  nombre: "Nombre",
  orden: "Orden del vértice",
  origen_id: "Origen de la medida",
  pendiente: "Pendiente",
  precio: "Precio",
  punto_id: "Punto",
  recorrido_id: "Recorrido",
  referencia: "Referencia",
  rendimiento: "Rendimiento",
  restauracion: "Restauración",
  superficie: "Superficie",
  tipo: "Tipo",
  unidad: "Unidad",
  valor: "Valor",
  vertices: "Vértices",
  x: "Posición X (m)",
  x0: "Esquina X (m)",
  y: "Posición Y (m)",
  y0: "Esquina Y (m)",
  z: "Altura (m)",
};

// Los parámetros de control de la obra (`core/budget/control.py`, `ParametrosControl`): el servidor los registra con
// objeto «parametro», clave «control|{nombre}» y campo «{nombre}». La pantalla de Control usa estos mismos rótulos.
export const PARAMETROS_DE_CONTROL: Record<string, string> = {
  spi_error: "Umbral de SPI para error",
  cpi_error: "Umbral de CPI para error",
  retraso_error: "Retraso del término para error",
  precio_info: "Desvío de precio que avisa",
  equilibrio_puntos: "Subida del punto de equilibrio que advierte",
  eta_cuadrilla: "Eficiencia de la cuadrilla adicional",
  cuadrillas_max: "Cuadrillas máximas por frente",
  eta_horas_extra: "Eficiencia de la hora extra",
  horas_extra_dia: "Horas extra por día",
  recargo_horas_extra: "Recargo de las horas extra",
  fcas_en_horas_extra: "FCAS sobre las horas extra",
  penalizacion_diaria: "Penalización diaria por retraso",
  fuente_penalizacion: "Fuente de la penalización",
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
export const rotuloDeCampo = (campo: string): string => CAMPOS[campo] ?? PARAMETROS_DE_CONTROL[campo] ?? llano(campo);

const PREFIJO_DE_CONTROL = "control|";

export function rotuloDeParametro(clave: string): string {
  if (clave.startsWith(PREFIJO_DE_CONTROL)) {
    const nombre = clave.slice(PREFIJO_DE_CONTROL.length);
    return `Control de obra: ${PARAMETROS_DE_CONTROL[nombre] ?? llano(nombre)}`;
  }
  return PARAMETROS[clave] ?? llano(clave);
}

// El antes/después de un cambio: una cifra va con coma decimal; el servidor guarda «catalogo» e «instantanea» como valores
// del campo «instantanea»; todo lo demás (un código, un nombre) se muestra tal cual.
export function valorDeCambio(campo: string, valor: string): string {
  if (campo === "instantanea" && (valor === "catalogo" || valor === "instantanea")) return CAMPOS[valor] ?? valor;
  return cifraSiLoEs(valor);
}
