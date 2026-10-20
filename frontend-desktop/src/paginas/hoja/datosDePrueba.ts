// Respuestas de ejemplo de las vistas de la hoja para las pruebas (caso ficticio OF-001, cifras de su memoria).
// Solo las importan pruebas; ninguna pagina las usa.
import type { InformeAuditoriaRespuesta } from "../../api/tipos";
import type {
  AtipicosRespuesta,
  PreciosRespuesta,
  TrazabilidadRespuesta,
  VistaApu,
  VistaEquilibrio,
  VistaEspacio,
  VistaParametros,
  VistaPlan,
  VistaPresupuesto,
} from "./logica";

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

export function vistaEquilibrio(extra: Partial<VistaEquilibrio> = {}): VistaEquilibrio {
  return {
    estado: "alcanzado",
    venta: m("2703.86", "2703.860232344044"),
    costo_variable: m("2137.44", "2137.4400000000001"),
    costo_fijo: m("427.49", "427.488"),
    utilidad: m("138.93", "138.93"),
    punto: m("1530.49", "1530.4912345"),
    porcentaje: m("56.60", "56.6012345"),
    periodo: "Dia 23",
    fraccion_periodo: "0.5",
    mensaje: "Se alcanza en Dia 23, al 50 % de ese periodo.",
    ...extra,
  };
}

export function vistaParametros(extra: Partial<VistaParametros> = {}): VistaParametros {
  return {
    campos: [
      { clave: "fcas", rotulo: "FCAS (fracción: 6.00 = prestaciones del 600 %)", valor: "6.00" },
      { clave: "bono_alimentacion", rotulo: "Bono de alimentación (por obrero y día)", valor: "3.5" },
      { clave: "administracion", rotulo: "Administración (fracción del costo directo)", valor: "0.20" },
      { clave: "utilidad", rotulo: "Utilidad (fracción, en cascada sobre la administración)", valor: "0.10" },
    ],
    moneda_proyecto: "USD",
    total: m("2703.86", "2703.860232344044"),
    puede_convertir: true,
    ...extra,
  };
}

export function informeAuditoria(extra: Partial<InformeAuditoriaRespuesta> = {}): InformeAuditoriaRespuesta {
  return {
    codigo_presupuesto: "OF-001-001",
    cumple: false,
    veredicto: "NO CUMPLE",
    total_hallazgos: 2,
    por_severidad: [
      { severidad: "ERROR", total: 1 },
      { severidad: "ADVERTENCIA", total: 1 },
    ],
    reglas_evaluadas: [
      { regla: "R3", nombre: "Origen de la medida", hallazgos: 1 },
      { regla: "R17", nombre: "Conexión de cada punto", hallazgos: 1 },
    ],
    hallazgos: [
      {
        numero: 1,
        regla: "R3",
        severidad: "ERROR",
        partida: null,
        descripcion: "Fuente F1: falta el origen ![x](http://ejemplo.invalid/a.png)",
        impacto: null,
        observado: null,
        esperado: null,
        origen: ["esp_fuentes:F1"],
      },
      {
        numero: 2,
        regla: "R17",
        severidad: "ADVERTENCIA",
        partida: "AF-LLAVE",
        descripcion: "El punto P1 no tiene fuente que lo alimente",
        impacto: null,
        observado: null,
        esperado: null,
        origen: ["esp_puntos:P1"],
      },
    ],
    sin_hallazgos: null,
    ...extra,
  };
}

const COLUMNAS_PRECIOS: Array<[string, string, boolean]> = [
  ["insumo", "Insumo", false],
  ["codigo", "Código", false],
  ["tipo", "Tipo", false],
  ["precio", "Precio", true],
  ["lista", "Lista", false],
  ["moneda", "Moneda", false],
  ["fecha", "Fecha del precio", false],
  ["tasa", "Tasa", true],
  ["fecha_tasa", "Fecha de la tasa", false],
  ["referencia", "Referencia", false],
  ["cotizacion", "Cotización", false],
  ["moneda_original", "Moneda original", false],
  ["precio_original", "Precio original", true],
  ["fuente_tasa", "Fuente de la tasa", false],
  ["fuente", "Fuente", false],
  ["propio", "Propio/heredado", false],
  ["erosion_usd", "Erosión USD", true],
  ["erosion_bs", "Erosión Bs", true],
  ["erosion_pct", "Erosión %", true],
  ["erosion_indice", "Erosión por índice", true],
  ["estado", "Estado", false],
];

export function preciosRespuesta(extra: Partial<PreciosRespuesta> = {}): PreciosRespuesta {
  return {
    moneda: "USD",
    fecha_evaluacion: "2026-10-20",
    columnas: COLUMNAS_PRECIOS.map(([clave, rotulo, numerica]) => ({ clave, rotulo, numerica })),
    filas: [
      {
        insumo: "Tubo PVC 1/2",
        codigo: "MAT-001",
        tipo: "material",
        precio: m("3.10", "3.1034"),
        lista: "Lista MaPreX",
        moneda: "USD",
        fecha: "2026-07-01",
        tasa: m("633.3644", "633.3644"),
        fecha_tasa: "2026-07-01",
        referencia: "MaPreX jul-2026",
        cotizacion: "",
        moneda_original: "Bs",
        precio_original: m("1963.43", "1963.4296"),
        fuente_tasa: "BCV",
        fuente: "MaPreX",
        propio: "heredado",
        erosion_usd: m("0.12", "0.1234"),
        erosion_bs: m("78.15", "78.1500"),
        erosion_pct: m("3.98", "3.9800"),
        erosion_indice: null,
        estado: "OK",
      },
      {
        insumo: "Llave de paso",
        codigo: "MAT-002",
        tipo: "material",
        precio: m("9.50", "9.5"),
        lista: "Lista MaPreX",
        moneda: "USD",
        fecha: "2026-07-01",
        tasa: null,
        fecha_tasa: null,
        referencia: "",
        cotizacion: "",
        moneda_original: "USD",
        precio_original: m("9.50", "9.5"),
        fuente_tasa: "",
        fuente: "",
        propio: "heredado",
        erosion_usd: null,
        erosion_bs: null,
        erosion_pct: null,
        erosion_indice: null,
        estado: "Sin referencia ni cotización: el precio no tiene fuente",
      },
    ],
    ...extra,
  };
}

export function atipicosRespuesta(extra: Partial<AtipicosRespuesta> = {}): AtipicosRespuesta {
  return {
    disponible: true,
    avisos: [{ nivel: "info", texto: "Se revisaron 2 insumos con serie de precios." }],
    variaciones: [
      {
        insumo: "MAT-001",
        porcentaje: "38.40",
        porcentaje_exacto: "38.4000123",
        desde: "2026-01-01",
        hasta: "2026-07-01",
        severidad: "ADVERTENCIA",
        descripcion: "El precio de MAT-001 varió 38,40 % entre las dos fechas",
      },
    ],
    ...extra,
  };
}

export function trazabilidadRespuesta(extra: Partial<TrazabilidadRespuesta> = {}): TrazabilidadRespuesta {
  return {
    versiones: [
      { codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0 },
      { codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 },
    ],
    registros: [
      {
        objeto: "cantidad",
        clave: "AF-LLAVE|esp_puntos:P1",
        campo: "cantidad",
        antes: "3",
        despues: "5",
        fuente: "Plano revisado en obra",
        responsable: "Ana Pérez <ana>",
        fecha_hora: "2026-10-06 09:30:00",
      },
    ],
    vacio_mensaje: null,
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
  if (nombre === "equilibrio") return vistaEquilibrio();
  if (nombre === "parametros") return vistaParametros();
  if (nombre === "auditoria") return informeAuditoria();
  return null;
}
