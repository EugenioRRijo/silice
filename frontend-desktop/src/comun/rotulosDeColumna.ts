// Los rótulos en español de las columnas de las tablas del metraje: los MISMOS de `ROTULOS_DE_COLUMNA` en
// aplicacion/hoja.py (la prueba `rotulosDeColumna.test.ts` lee ese archivo y falla si dejan de coincidir). El orden de
// las columnas es el del resumen «clave=valor; …» que arma `_resumen_de_fila`.

export const ROTULOS_DE_COLUMNA: Record<string, Record<string, string>> = {
  origenes: { id: "Código", tipo: "Tipo de origen", referencia: "Referencia" },
  ambientes: {
    id: "Código",
    nombre: "Nombre",
    x0: "Esquina X (m)",
    y0: "Esquina Y (m)",
    largo: "Largo (m)",
    ancho: "Ancho (m)",
    alto: "Alto (m)",
    origen_id: "Origen de la medida",
  },
  fuentes: {
    id: "Código",
    especialidad: "Especialidad",
    tipo: "Tipo de fuente",
    ambiente_id: "Ambiente",
    x: "Posición X (m)",
    y: "Posición Y (m)",
    z: "Altura (m)",
    origen_id: "Origen de la medida",
  },
  puntos: {
    id: "Código",
    nombre: "Nombre",
    especialidad: "Especialidad",
    tipo: "Tipo de punto",
    ambiente_id: "Ambiente",
    superficie: "Superficie",
    x: "Posición X (m)",
    y: "Posición Y (m)",
    z: "Altura (m)",
    fuente_id: "Fuente que lo alimenta",
    circuito_id: "Circuito",
    especificaciones: "Especificaciones",
    origen_id: "Origen de la medida",
  },
  tramos: {
    recorrido_id: "Recorrido",
    punto_id: "Punto",
    circuito_id: "Circuito",
    orden: "Orden del vértice",
    superficie: "Superficie",
    empotrado: "Empotrado",
    pendiente: "Pendiente",
    vertices: "Vértices",
  },
};
