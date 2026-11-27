// Datos construidos (ficticios) para las pruebas de «Auditar un libro» (B2). Reproducen los formatos de las 6 alertas de
// la prueba de comprensión (docs/tesis/2026-11-23-guion-prueba-con-usuarios.md, A1 a A6) sobre un libro de demostración;
// ningún dato es de una empresa.
import type { AlertaDePrecio, AuditoriaDelLibro } from "./logicaDelLibro";
import type { CatalogoQueHacer, GuiaQueHacer } from "../../comun/catalogoQueHacer";

function guia(codigo: string, titulo: string, significa: string, queHacer: string, sinAviso: string[] = []): GuiaQueHacer {
  return { codigo, titulo, significa, que_hacer: queHacer, generico: false, sin_aviso_si: sinAviso };
}

export function catalogoDePrueba(): CatalogoQueHacer {
  return {
    reglas: {
      L1: guia("L1", "Referencia desalineada", "Una fórmula lee la celda que no le toca.", "Corrija la referencia de la celda."),
      L4: guia("L4", "Componente fuera del total", "Una suma deja fuera un componente.", "Corrija el rango de la suma."),
      L5: guia("L5", "Referencia rota o externa", "Una fórmula apunta a una celda que ya no existe.", "Escriba de nuevo la fórmula."),
      R2: guia("R2", "Cierre de la curva de inversión", "La curva no cierra.", "Si el libro no trae curva, no hay nada que corregir."),
    },
    alertas: {
      "sin fuente": guia("alerta:sin-fuente", "Sin fuente", "El precio no dice de dónde sale.", "Anote la fuente del precio."),
      "base de la empresa": guia(
        "alerta:base-de-la-empresa",
        "Base de la empresa",
        "El precio se aparta de la base.",
        "Compárelo con la base de la empresa.",
      ),
      "otra versión": guia("alerta:otra-version", "Otra versión", "El precio cambió.", "Confirme el cambio."),
      "USD-Bs": guia("alerta:usd-bs", "USD-Bs", "El precio vale distinto en bolívares.", "Actualice con la tasa vigente.", [
        "dentro del umbral",
      ]),
    },
    generico: {
      codigo: "",
      titulo: "Hallazgo",
      significa: "Sílice encontró algo que no cuadra.",
      que_hacer: "Abra la celda indicada y corríjala.",
      generico: true,
      sin_aviso_si: [],
    },
  };
}

function alerta(parcial: Partial<AlertaDePrecio> & Pick<AlertaDePrecio, "codigo" | "tipo" | "mensaje">): AlertaDePrecio {
  return {
    descripcion: `Insumo ${parcial.codigo}`,
    moneda: "USD",
    precio: "18.00",
    fecha: "2026-10-01",
    fuente: "",
    ...parcial,
  };
}

// A1 a A3 de la prueba de comprensión, más una USD-Bs dentro del umbral (no avisa). Los mensajes tienen la forma exacta que
// manda fusion/alertas.py (es-VE): montos y porcentajes a dos decimales, la tasa del BCV exacta y sin ceros finales
// («tasa 50», «tasa 50,5»); el front los muestra tal cual, sin reformatear.
export function alertasDePrueba(): AlertaDePrecio[] {
  return [
    alerta({
      codigo: "MT-04",
      tipo: "sin fuente",
      fuente: "POR COTIZAR",
      mensaje: "la FUENTE de MT-04 dice «POR COTIZAR»: el precio (INSUMOS!E12) no se puede rastrear",
    }),
    alerta({
      codigo: "MT-08",
      tipo: "base de la empresa",
      variacion: "0.20",
      mensaje:
        "el libro usa 18,00 USD; precio propio de la instalación 15,00 USD del 2026-10-15: +20,00 %, pasa del umbral de 5,00 %",
    }),
    alerta({
      codigo: "MT-08",
      tipo: "USD-Bs",
      variacion: "0.10",
      tasa: "55.00",
      precio_bs: "990.00",
      mensaje:
        "900,00 Bs al 2026-10-01 (tasa 50) y 990,00 Bs al 2026-11-24 (tasa 55): +10,00 %, pasa del umbral de 5,00 %",
    }),
    alerta({
      codigo: "MT-01",
      tipo: "USD-Bs",
      precio: "10.00",
      variacion: "0.01",
      mensaje:
        "500,00 Bs al 2026-10-01 (tasa 50) y 505,00 Bs al 2026-11-24 (tasa 50,5): +1,00 %, dentro del umbral de 5,00 %",
    }),
  ];
}

// Seis casos de la misma regla L1: una sola causa raíz (A6).
const CASOS_L1 = ["F10", "F11", "F12", "F13", "F14", "F15"].map((celda, i) => ({
  codigo: "L1",
  nombre_regla: "Referencia desalineada",
  severidad: "ERROR",
  descripcion: `PRESUPUESTO!${celda} (partida ${i + 1}) lee APU-01!E14 (valor 0) como rendimiento; encontrado 0, esperado 120`,
  celda: `PRESUPUESTO!${celda}`,
  impacto: null,
  accion: "a confirmar",
}));

// El libro de demostración: A4 (L4), A5 (L5), A6 (seis casos de L1), un aviso de regla no aplicable (R2) y las alertas
// A1 a A3. Son 9 hallazgos y uno no aplica (no cuenta): 8 hallazgos, todos errores.
export function auditoriaDePrueba(parcial: Partial<AuditoriaDelLibro> = {}): AuditoriaDelLibro {
  const hallazgos = [
    {
      codigo: "L4",
      nombre_regla: "Componente fuera del total",
      severidad: "ERROR",
      descripcion:
        "Costo directo de APU-02 (partida 2): la fórmula APU-02!G36 =SUM(G32:G34) deja fuera transporte y disposición (APU-02!G35, 10 USD/u). Efecto: la partida queda corta en 1.265,00 USD sin IVA.",
      celda: "APU-02!G36",
      impacto: "1265.00",
      accion: "a confirmar",
    },
    {
      codigo: "L5",
      nombre_regla: "Referencia rota o externa",
      severidad: "ERROR",
      descripcion:
        "2 fórmula(s) de RESUMEN con #REF! (la celda u hoja que citaban se borró): B4, B6. Efecto: esas celdas muestran #REF! o un valor que ya no se puede rastrear.",
      celda: "RESUMEN!B4",
      impacto: null,
      accion: "a confirmar",
    },
    ...CASOS_L1,
    {
      codigo: "R2",
      nombre_regla: "Cierre de la curva de inversión",
      severidad: "INFO",
      descripcion: "regla no aplicable: el libro no trae curva de inversión",
      celda: "",
      impacto: null,
      accion: "informado",
    },
  ];
  return {
    libro: { nombre: "Presupuesto cliente A.xlsx", sha256: "a".repeat(64) },
    fecha_libro: "2026-10-01",
    fecha_devolucion: "2026-11-24",
    cumple: false,
    por_severidad: { ERROR: 8, INFO: 1 },
    totales_libro: { TOTALGEN: "2418730.00" },
    totales_silice: { TOTALGEN: "2376044.50" },
    indicadores: [],
    hallazgos,
    causas: [
      {
        codigo: "L4",
        nombre_regla: "Componente fuera del total",
        severidad: "ERROR",
        descripcion: hallazgos[0].descripcion,
        ocurrencias: 1,
        indices: [0],
        celdas: ["APU-02!G36"],
      },
      {
        codigo: "L5",
        nombre_regla: "Referencia rota o externa",
        severidad: "ERROR",
        descripcion: hallazgos[1].descripcion,
        ocurrencias: 1,
        indices: [1],
        celdas: ["RESUMEN!B4"],
      },
      {
        codigo: "L1",
        nombre_regla: "Referencia desalineada",
        severidad: "ERROR",
        descripcion: hallazgos[2].descripcion,
        ocurrencias: 6,
        indices: [2, 3, 4, 5, 6, 7],
        celdas: CASOS_L1.map((c) => c.celda),
        observado: "0",
        esperado: "120",
      },
    ],
    no_aplicables: [8],
    alertas: alertasDePrueba(),
    aviso_historial: null,
    ...parcial,
  };
}

export function auditoriaSinHallazgos(): AuditoriaDelLibro {
  return auditoriaDePrueba({
    cumple: true,
    hallazgos: [],
    causas: [],
    no_aplicables: [],
    por_severidad: {},
    alertas: [],
  });
}
