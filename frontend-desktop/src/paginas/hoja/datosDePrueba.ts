// Respuestas de ejemplo de las vistas de la hoja para las pruebas (caso ficticio OF-001, cifras de su memoria).
// Solo las importan pruebas; ninguna pagina las usa.
import type { VistaApu, VistaEspacio, VistaPlan, VistaPresupuesto } from "./logica";

const m = (texto: string, exacto = texto) => ({ texto, exacto });

export function columnas(claves: Array<[string, string, Array<[string, string]> | null]>) {
  return claves.map(([clave, rotulo, lista]) => ({
    clave,
    rotulo,
    lista: lista === null ? null : lista.map(([valor, r]) => ({ valor, rotulo: r })),
  }));
}

export function vistaEspacio(extra: Partial<VistaEspacio> = {}): VistaEspacio {
  return {
    ayuda: "Describa el espacio en metros (eje z hacia arriba desde el piso terminado).",
    tablas: [
      {
        clave: "origenes",
        rotulo: "Orígenes de medida",
        con_estado: false,
        columnas: columnas([
          ["id", "Código", null],
          ["tipo", "Tipo de origen", [["supuesto", "Supuesto"], ["plano", "Plano"]]],
          ["referencia", "Referencia", null],
        ]),
      },
      {
        clave: "ambientes",
        rotulo: "Ambientes",
        con_estado: true,
        columnas: columnas([
          ["id", "Código", null],
          ["nombre", "Nombre", null],
          ["largo", "Largo (m)", null],
        ]),
      },
      {
        clave: "fuentes",
        rotulo: "Fuentes",
        con_estado: true,
        columnas: columnas([
          ["id", "Código", null],
          ["especialidad", "Especialidad", [["agua", "Agua"]]],
        ]),
      },
      {
        clave: "puntos",
        rotulo: "Puntos",
        con_estado: true,
        columnas: columnas([
          ["id", "Código", null],
          ["superficie", "Superficie", [["pared", "Pared"], ["techo", "Techo"]]],
        ]),
      },
      {
        clave: "tramos",
        rotulo: "Vértices de recorridos",
        con_estado: false,
        columnas: columnas([
          ["recorrido_id", "Recorrido", null],
          ["empotrado", "Empotrado", [["", ""], ["si", "Sí"], ["no", "No"]]],
        ]),
      },
    ],
    filas: {
      origenes: [{ id: "O1", tipo: "supuesto", referencia: "motivo=ejemplo" }],
      ambientes: [
        { id: "BAN-01", nombre: "Baño", largo: "2" },
        { id: "COC-01", nombre: "Cocineta", largo: "2" },
      ],
      fuentes: [{ id: "F1", especialidad: "agua" }],
      puntos: [{ id: "P1", superficie: "pared" }],
      tramos: [],
    },
    estado: {
      "esp_ambientes:BAN-01": {
        severidad: "ADVERTENCIA",
        texto: "ADVERTENCIA: ambiente BAN-01: la medida es un supuesto declarado (origen O1)",
      },
      "esp_ambientes:COC-01": { severidad: null, texto: "OK" },
      "esp_fuentes:F1": { severidad: "ERROR", texto: "ERROR: fuente F1: falta el origen" },
      "esp_puntos:P1": { severidad: null, texto: "OK" },
    },
    derivadas: [
      { partida: "AF-LLAVE", descripcion: "Llave de paso", unidad: "unidad", cantidad: m("3.00", "3"), origen: "esp_puntos:P1" },
      {
        partida: "AF-TUB-PVC-1/2",
        descripcion: "Tubería PVC 1/2",
        unidad: "m",
        cantidad: m("8.25", "8.250000000000000000000000000"),
        origen: "esp_fuentes:F1",
      },
    ],
    total: m("2703.86", "2703.86023234404403"),
    moneda: "USD",
    pendientes: 0,
    vacio_mensaje: null,
    ...extra,
  };
}

export function vistaPresupuesto(extra: Partial<VistaPresupuesto> = {}): VistaPresupuesto {
  return {
    filas: [
      {
        clave: "AF-LLAVE|esp_puntos:P1",
        partida: "AF-LLAVE",
        descripcion: "Llave de paso",
        unidad: "unidad",
        cantidad: "3",
        cantidad_calculada: "3",
        escrita: false,
        pu: m("13.20", "13.198738025"),
        total: m("39.60", "39.596214075"),
        estado: { severidad: null, texto: "OK" },
      },
      {
        clave: "AF-SALIDA|esp_puntos:P2",
        partida: "AF-SALIDA",
        descripcion: "Salida de agua",
        unidad: "unidad",
        cantidad: "5",
        cantidad_calculada: "3",
        escrita: true,
        pu: null,
        total: null,
        estado: { severidad: "ERROR", texto: "PENDIENTE: sin APU en el catálogo (AF-SALIDA)" },
      },
    ],
    total: m("2703.86", "2703.8602323440440333"),
    moneda: "USD",
    vacio_mensaje: null,
    ...extra,
  };
}

export function vistaApu(extra: Partial<VistaApu> = {}): VistaApu {
  return {
    partidas: [
      { codigo: "AF-CODO-1/2", descripcion: "Codo PVC 1/2" },
      { codigo: "AF-LLAVE", descripcion: "Llave de paso de agua fria instalada" },
    ],
    sin_coincidencias: false,
    seleccionada: "AF-LLAVE",
    detalle: {
      codigo: "AF-LLAVE",
      descripcion: "Llave de paso de agua fria instalada",
      unidad: "unidad",
      rendimiento: "20",
      grupos: [
        {
          clave: "materiales",
          rotulo: "Materiales",
          columnas: [
            { clave: "descripcion", rotulo: "Descripción" },
            { clave: "unidad", rotulo: "Unidad" },
            { clave: "cantidad", rotulo: "Cantidad" },
            { clave: "precio", rotulo: "Precio" },
          ],
          filas: [{ descripcion: "Llave de bola PVC 1/2", unidad: "pieza", cantidad: "1", precio: "7.7483" }],
          subtotal: m("7.75", "7.7483"),
        },
        {
          clave: "equipos",
          rotulo: "Equipos",
          columnas: [
            { clave: "descripcion", rotulo: "Descripción" },
            { clave: "cantidad", rotulo: "Cantidad" },
            { clave: "precio", rotulo: "Precio" },
            { clave: "depreciacion", rotulo: "Depreciación" },
          ],
          filas: [{ descripcion: "Herramientas menores", cantidad: "1", precio: "14.3046", depreciacion: "1" }],
          subtotal: m("0.72", "0.71523"),
        },
        {
          clave: "mano de obra",
          rotulo: "Mano de obra",
          columnas: [
            { clave: "descripcion", rotulo: "Descripción" },
            { clave: "cantidad", rotulo: "Cantidad" },
            { clave: "sueldo", rotulo: "Sueldo" },
            { clave: "modalidad", rotulo: "Modalidad" },
          ],
          filas: [
            { descripcion: "Plomero de 1ra N5", cantidad: "1", sueldo: "2.1877", modalidad: "jornal" },
            { descripcion: "Ayudante N2", cantidad: "1", sueldo: "1.7816", modalidad: "jornal" },
          ],
          subtotal: m("1.97", "1.970255"),
        },
      ],
      cierre: [
        { concepto: "Materiales", monto: m("7.75", "7.7483"), nota: "completos" },
        { concepto: "Equipos", monto: m("0.72", "0.71523"), nota: "entre el rendimiento" },
        { concepto: "Mano de obra", monto: m("1.97", "1.970255"), nota: "FCAS 6 y bono 5.81, entre el rendimiento" },
        { concepto: "= Costo directo", monto: m("10.43", "10.433785"), nota: "" },
        { concepto: "+ Administracion", monto: m("1.57", "1.56506775"), nota: "15.0 % del costo directo" },
        { concepto: "= Con administracion", monto: m("12.00", "11.99885275"), nota: "" },
        { concepto: "+ Utilidad", monto: m("1.20", "1.199885275"), nota: "10.0 % en cascada" },
        { concepto: "= Precio unitario", monto: m("13.20", "13.198738025"), nota: "" },
      ],
      metricas: {
        materiales: m("7.75", "7.7483"),
        equipos: m("0.72", "0.71523"),
        mano_obra: m("1.97", "1.970255"),
        precio_unitario: m("13.20", "13.198738025"),
      },
      estados: [],
      solo_lectura_insumos: false,
    },
    vacio_mensaje: null,
    ...extra,
  };
}

export function vistaPlan(extra: Partial<VistaPlan> = {}): VistaPlan {
  return {
    hay_plan: true,
    etiquetas: ["Dia 1", "Dia 2"],
    filas: [
      { partida: "AF-CODO-1/2", valores: { "Dia 1": "1", "Dia 2": "0" } },
      { partida: "AF-LLAVE", valores: { "Dia 1": "0", "Dia 2": "1" } },
    ],
    curva: [
      { periodo: "Dia 1", monto: m("11.18"), acumulado: m("11.18"), porcentaje: m("0.41", "0.4134") },
      { periodo: "Dia 2", monto: m("9.87"), acumulado: m("21.05"), porcentaje: m("0.78", "0.7785") },
    ],
    moneda: "USD",
    mensaje: null,
    ...extra,
  };
}

// El cuerpo que daría el servidor a `GET /v1/hoja/borradores/{id}/vistas/{nombre}`, o null si la ruta no es de una vista.
export function cuerpoDeVista(url: string): unknown {
  const nombre = /\/vistas\/([a-z]+)/.exec(url)?.[1];
  if (nombre === "espacio") return vistaEspacio();
  if (nombre === "presupuesto") return vistaPresupuesto();
  if (nombre === "apu") return vistaApu();
  if (nombre === "plan") return vistaPlan();
  return null;
}
