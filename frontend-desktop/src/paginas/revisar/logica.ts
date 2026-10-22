// «Revisar un paquete»: logica pura de la pagina. La interfaz no calcula montos: recibe de la API el exacto y el
// texto como lo escribe la pantalla clasica, y solo les da formato es-VE.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

// ui/paginas/revisar.py lo dice con Markdown («Elija el archivo `.silice` que recibió.»); aqui va sin marcas.
export const SIN_ARCHIVO = "Elija el archivo .silice que recibió.";

export type TipoDeAviso = "success" | "warning" | "error";

// El banner de estado (paquete.verificar.banner) pintado como la clasica: verde, ambar y, cualquier otro, error.
export function tipoDeBanner(color: string): TipoDeAviso {
  if (color === "verde") return "success";
  if (color === "ambar") return "warning";
  return "error";
}

export function tituloDeLote(titulo: string, cuantos: number): string {
  return `${titulo} (${cuantos})`;
}

// Presenta el exacto de una celda con el texto que la API calculo para el (`*_texto`), en es-VE. El exacto queda como
// valor de la celda (TablaDensa lo pone en el `title` y ordena por el), el texto redondeado es lo que se lee.
export function presentador(pares: [exacto: string, texto: string][]): (valor: string) => string {
  const textos = new Map(pares);
  return (valor) => formatoEsVe(textos.get(valor) ?? valor);
}

export function formularioPaquete(archivo: File, lista?: number): FormData {
  const datos = new FormData();
  datos.append("paquete", archivo);
  if (lista !== undefined) datos.append("lista", String(lista));
  return datos;
}

export function formularioDictamen(archivo: File, resultado: string, notas: string): FormData {
  const datos = formularioPaquete(archivo);
  datos.append("resultado", resultado);
  datos.append("notas", notas);
  return datos;
}

export function formularioExcel(archivo: File, tipo: "presupuesto" | "revision"): FormData {
  const datos = formularioPaquete(archivo);
  datos.append("tipo", tipo);
  return datos;
}

// Las columnas de «Quién cambió qué»: las de la hoja «Cambios» del Excel de la revision.
export const COLUMNAS_CAMBIOS: ColumnaDensa[] = [
  { clave: "version", titulo: "Versión" },
  { clave: "objeto", titulo: "Objeto" },
  { clave: "clave", titulo: "Clave" },
  { clave: "campo", titulo: "Campo" },
  { clave: "antes", titulo: "Antes" },
  { clave: "despues", titulo: "Después" },
  { clave: "fuente", titulo: "Fuente" },
  { clave: "responsable", titulo: "Responsable" },
  { clave: "fecha", titulo: "Fecha" },
  { clave: "marca", titulo: "Marca" },
];

export function filasDeCambios(cambios: Record<string, string>[]): FilaDensa[] {
  return cambios.map((c, i) => {
    const fila: FilaDensa = { id: String(i) };
    for (const { clave } of COLUMNAS_CAMBIOS) fila[clave] = c[clave] ?? "";
    return fila;
  });
}

export const COLUMNAS_HALLAZGOS: ColumnaDensa[] = [
  { clave: "regla", titulo: "Regla" },
  { clave: "severidad", titulo: "Severidad", celda: "severidad" },
  { clave: "descripcion", titulo: "Descripción" },
];

// El campo que la reauditoria compara llega como identificador interno («precio_unitario»): se lee como rotulo.
const ROTULOS_DE_CAMPO: Record<string, string> = { precio_unitario: "Precio unitario", total: "Total" };

export function rotuloDeCampo(campo: string): string {
  return ROTULOS_DE_CAMPO[campo] ?? campo;
}
