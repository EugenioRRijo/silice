// Los textos de la ayuda de Sílice en un solo lugar (F7; especificación 2026-10-26, §5, «Textos como datos»): el «¿Qué es
// esto?» de cada pantalla, las guías por tarea y el glosario. Cada control que se nombra va entre comillas angulares con su
// texto exacto: `catalogo.test.ts` comprueba que existe en el código. Las definiciones siguen cómo usa Sílice cada término
// (docs/ERS.md §1.3, docs/manual_usuario.md y el código); no traen normas ni cifras que el programa no use.

export type GuiaId = "presupuesto" | "aprobacion" | "precios" | "auditar";

export type TerminoId =
  | "administracion-y-utilidad"
  | "apu"
  | "borrador"
  | "cadena-de-sellos"
  | "carpeta"
  | "cotizacion"
  | "dictamen"
  | "etapa"
  | "fcas"
  | "hallazgo"
  | "indices-bcv"
  | "insumo"
  | "iva"
  | "libro"
  | "linea-base"
  | "lista-de-precios"
  | "lista-para-armar"
  | "maprex"
  | "obra"
  | "p50-p80"
  | "paquete"
  | "partida"
  | "precio-atipico"
  | "reajuste"
  | "rendimiento"
  | "tramo"
  | "valor-ganado"
  | "valuacion"
  | "version";

export interface Termino {
  id: TerminoId;
  termino: string;
  definicion: string;
}

// En orden alfabético (lo vigila la prueba). Los nombres de los controles van con su texto exacto.
export const GLOSARIO: readonly Termino[] = [
  {
    id: "administracion-y-utilidad",
    termino: "Administración y utilidad",
    definicion:
      "Dos fracciones que llevan el costo directo de una partida a su precio unitario: primero la administración, sobre el costo directo, y después la utilidad, sobre ese resultado (en cascada). Se cambian en la pestaña «Ajustes de costo» del Presupuesto.",
  },
  {
    id: "apu",
    termino: "APU (análisis de precio unitario)",
    definicion:
      "El desglose de lo que cuesta una unidad de una partida (un metro, un metro cúbico…): sus materiales, sus equipos y su mano de obra. Su suma es el costo directo; con la administración y la utilidad da el precio unitario.",
  },
  {
    id: "borrador",
    termino: "Borrador",
    definicion:
      "Los cambios del presupuesto que todavía no son una versión. Lo comparten Presupuesto, Componer, Archivos y planos y Versiones; queda guardado al pulsar «Guardar versión…», y si Sílice se reinicia antes, lo no guardado se pierde.",
  },
  {
    id: "cadena-de-sellos",
    termino: "Cadena de sellos",
    definicion:
      "Cada versión guardada queda sellada con una huella ligada a la de la versión anterior, así que un cambio hecho a la base por fuera de Sílice rompe la cadena y Versiones dice dónde. Con la cadena rota no se puede enviar a aprobación ni aprobar: solo devolver.",
  },
  {
    id: "carpeta",
    termino: "Carpeta",
    definicion:
      "Donde Sílice guarda un catálogo, sus precios y sus obras, en un solo archivo de este equipo y con una moneda de trabajo. Quien administra las abre, crea y sube en la Cuenta, sección «Carpetas».",
  },
  {
    id: "cotizacion",
    termino: "Cotización",
    definicion:
      "El precio de un proveedor para un insumo, que vale solo para esta obra y manda sobre el de la lista hasta que se retira. Registrarla o retirarla crea una versión nueva desde la vigente.",
  },
  {
    id: "dictamen",
    termino: "Dictamen",
    definicion:
      "La decisión que registra quien revisa sobre una versión enviada a aprobación: «Aprobada», «Aprobada con observaciones» o «Devuelta». Devolver o aprobar con observaciones pide notas, y el dictamen no se cambia después.",
  },
  {
    id: "etapa",
    termino: "Etapa de la obra",
    definicion:
      "Dónde va la obra: «En elaboración», «En aprobación» o «Aprobada» según sus versiones y, con la línea base declarada, «En ejecución», o «Atrasada» si su SPI (el índice de plazo del valor ganado) baja del umbral de su control.",
  },
  {
    id: "fcas",
    termino: "FCAS (factor de costos asociados al salario)",
    definicion:
      "Lo que se agrega al jornal de la mano de obra por las prestaciones y los demás costos del salario; no se aplica a la mano de obra a destajo. Se escribe como fracción en «Ajustes de costo» (6,00 son unas prestaciones del 600 %), y la calculadora de «Precios de la empresa» lo estima por componentes, pero no lo aplica por sí sola.",
  },
  {
    id: "hallazgo",
    termino: "Hallazgo",
    definicion:
      "Algo que una regla de revisión encontró en un presupuesto o en un libro y conviene mirar. Su severidad dice qué tan grave es («Crítico», «Error», «Advertencia» o «Información»), y ningún hallazgo impide guardar.",
  },
  {
    id: "indices-bcv",
    termino: "Índices y tasa del BCV",
    definicion:
      "Las cifras del Banco Central de Venezuela que usa Sílice: la tasa del dólar, para convertir entre Bs y USD, y el INPC y otras series, para el reajuste y el riesgo. Las importa quien administra en «Índices del BCV».",
  },
  {
    id: "insumo",
    termino: "Insumo",
    definicion:
      "Un material, un equipo o un oficio de mano de obra del catálogo. No tiene un precio fijo: su precio es el de la lista de precios que se use.",
  },
  {
    id: "iva",
    termino: "IVA",
    definicion:
      "El impuesto al valor agregado, con la alícuota general del 16 %. Se calcula sobre el total del presupuesto o de la valuación, nunca dentro del APU.",
  },
  {
    id: "libro",
    termino: "Libro",
    definicion:
      "Un presupuesto en Excel (.xlsx) hecho fuera de Sílice, que se audita en «Auditar un presupuesto». Sílice lo lee tal como es: no lo modifica ni lo guarda, solo guarda el resumen y los hallazgos.",
  },
  {
    id: "linea-base",
    termino: "Línea base",
    definicion:
      "En Control de obra, la versión del contrato contra la que se mide la obra, con su inicio, sus días hábiles y su perspectiva (costo para quien arma, precio para quien revisa); se declara en la pestaña «Línea base». Cuando existe, el Resumen y la Vista general toman el total de esa versión.",
  },
  {
    id: "lista-de-precios",
    termino: "Lista de precios",
    definicion:
      "Los precios de los insumos desde una fecha, en una moneda. Una vez que una versión del presupuesto la usa ya no cambia: los precios nuevos llegan en otra lista.",
  },
  {
    id: "lista-para-armar",
    termino: "Lista para armar",
    definicion:
      "La lista de precios vigente de la carpeta, en su moneda: de ella salen los precios de lo que se compone. La cabecera de cada obra dice cuál es y, si la carpeta no tiene una, Componer ofrece «Crear la lista a partir de MaPreX» o «Convertir la lista que tiene».",
  },
  {
    id: "maprex",
    termino: "MaPreX",
    definicion:
      "La referencia externa de precios de la construcción que Sílice usa para contrastar: la lista de la empresa se revisa contra ella y una carpeta sin lista para armar puede crear la suya a partir de ella.",
  },
  {
    id: "obra",
    termino: "Obra",
    definicion:
      "Lo que se presupuesta y se sigue: tiene su moneda, las versiones de su presupuesto, sus aprobaciones y su control. Se crea con «Nueva obra».",
  },
  {
    id: "p50-p80",
    termino: "P50 y P80",
    definicion:
      "En Riesgo, los totales que no superan el 50 % y el 80 % de las trayectorias simuladas de los precios. La «Reserva para cubrir el P80» es lo que va del total base al P80.",
  },
  {
    id: "paquete",
    termino: "Paquete",
    definicion:
      "Un archivo .silice firmado que lleva al cliente una versión del presupuesto con su auditoría y su cadena de sellos. Quien lo recibe lo abre en «Revisar un paquete», que comprueba la firma y lo vuelve a auditar.",
  },
  {
    id: "partida",
    termino: "Partida",
    definicion:
      "Un trabajo que se mide y se cobra, con su código, su descripción y su unidad. Su precio unitario sale de su APU y, en el presupuesto, se multiplica por la cantidad.",
  },
  {
    id: "precio-atipico",
    termino: "Precio atípico",
    definicion:
      "Una variación de precio muy distinta de la que suele tener ese insumo en las listas de la carpeta. Se marca en morado como advertencia: ayuda a quien revisa, pero no es un error.",
  },
  {
    id: "reajuste",
    termino: "Reajuste",
    definicion:
      "La estimación de cuánto debe cambiar el pago de lo ejecutado según la cláusula del contrato y la variación de los índices de materiales, equipos y mano de obra desde el mes base. Es un indicio: hay que cotejarlo con la Gaceta.",
  },
  {
    id: "rendimiento",
    termino: "Rendimiento",
    definicion:
      "Cuántas unidades de la partida se hacen en un día, con las condiciones en que se obtuvo. El costo diario de equipos y mano de obra se divide entre el rendimiento; el de los materiales, no.",
  },
  {
    id: "tramo",
    termino: "Tramo",
    definicion:
      "Un trozo de la vía entre dos progresivas, con su ancho y su distancia a la planta. Los tramos se cargan desde un .csv y Sílice saca de ellos las cantidades de obra.",
  },
  {
    id: "valor-ganado",
    termino: "Valor ganado",
    definicion:
      "Cómo mide Control de obra el avance: compara lo planificado a la fecha (PV), lo ejecutado al precio del contrato (EV) y su costo (AC). De ahí salen el SPI (EV entre PV, el plazo) y el CPI (EV entre AC, el costo): por debajo de 1, la obra se atrasa o gasta de más.",
  },
  {
    id: "valuacion",
    termino: "Valuación",
    definicion:
      "El registro de las cantidades ejecutadas en un período, con su número, sus fechas y su inspector. Cuenta para el control desde que se registra; para corregirla se anula, y la anulada se conserva.",
  },
  {
    id: "version",
    termino: "Versión",
    definicion:
      "Una foto guardada del presupuesto de una obra, con su motivo y quién la guardó; las anteriores no se borran. La vigente es la última guardada que no se descartó.",
  },
];

export interface ParteDeGuia {
  titulo: string;
  pasos: readonly string[];
}

export interface Guia {
  id: GuiaId;
  titulo: string;
  // Quién la hace, con las palabras de los papeles («arma presupuestos», «revisa paquetes», «administra la instalación»).
  quien: string;
  partes: readonly ParteDeGuia[];
  terminos: readonly TerminoId[];
}

export const GUIAS: readonly Guia[] = [
  {
    id: "presupuesto",
    titulo: "Montar un presupuesto",
    quien: "Quien arma presupuestos.",
    partes: [
      {
        titulo: "Crear la obra y agregar sus partidas",
        pasos: [
          "En la barra de la izquierda, pulse «Nueva obra». Escriba el «Nombre de la obra», revise la «Moneda» y pulse «Crear obra». Se abre el «Resumen» de la obra.",
          "En la barra de secciones de la obra, vaya a «Presupuesto». En la pestaña «Partidas», pulse «Agregar partida».",
          "En «Partida», busque por código o por una palabra de la descripción y elija la del catálogo. Si no está, «Buscar parecidas» propone partidas que se le parecen, o elija la última sugerencia, «Componer una partida nueva», para armar su APU en el panel (queda en el catálogo de la empresa, para todas las obras).",
          "Escriba la cantidad (o el «Cálculo (opcional)», por ejemplo 6*3-2) y pulse «Agregar al presupuesto». Repita con cada partida.",
          "Para cambiar una cantidad, escríbala en su celda de la tabla. El código de cada partida abre su APU en el panel de la derecha, y la pestaña «Análisis de precio (APU)» permite ajustarlo.",
        ],
      },
      {
        titulo: "Guardar y descargar",
        pasos: [
          "Lo que cambia queda en el borrador. Cuando esté listo, pulse «Guardar versión…» (la primera vez, «Guardar primera versión…») en la franja de arriba, escriba de dónde salen los datos y confirme: nace una versión.",
          "«Descargar Excel», al lado de la franja, baja el presupuesto en Excel; «Descargar PDF», en un PDF listo para imprimir o enviar, con el APU de cada partida después del presupuesto.",
          "Si las cantidades vienen de un archivo, en «Archivos y planos» pulse «Subir plano o cómputo»: un plano .dxf o .ifc, o un cómputo .csv que se lleva con «Llevar al presupuesto». Después guarde la versión igual.",
        ],
      },
    ],
    terminos: ["partida", "apu", "borrador", "version"],
  },
  {
    id: "aprobacion",
    titulo: "Enviarlo a aprobación",
    quien: "Quien arma presupuestos envía; quien revisa (o quien arma) da el dictamen.",
    partes: [
      {
        titulo: "Enviar la versión",
        pasos: [
          "Guarde la versión. Si tiene hallazgos graves (crítico o error), la franja del Presupuesto pide revisarlos antes de enviar, con «Ir a Revisión».",
          "Cuando la franja diga «Siguiente paso:» con la versión por enviar, pulse «Enviar a aprobación…», escriba si quiere una «Nota para quien revisa (opcional)» y pulse «Enviar a aprobación».",
          "La obra pasa a «En aprobación» y esa versión ya no se edita: lo que guarde después será una versión nueva.",
        ],
      },
      {
        titulo: "Dar el dictamen",
        pasos: [
          "En la obra, vaya a «Aprobaciones» y a la vista «Aprobar». Lea las partidas y el informe de auditoría de la versión enviada.",
          "En «Su dictamen» elija «Aprobada», «Aprobada con observaciones» o «Devuelta»; las «Notas» son obligatorias para devolver o aprobar con observaciones. Pulse «Registrar el dictamen…» y confirme: el dictamen no se cambia después.",
          "Si la devuelven, la franja del Presupuesto lo dice y ofrece «Hacer una versión nueva»: corrija lo observado, guarde y envíela otra vez.",
          "Con la versión aprobada, «Entregar» (en Aprobaciones) prepara el paquete firmado para el cliente con «Generar paquete».",
        ],
      },
    ],
    terminos: ["dictamen", "hallazgo", "cadena-de-sellos", "paquete"],
  },
  {
    id: "precios",
    titulo: "Actualizar precios",
    quien: "Quien arma presupuestos, en la obra; quien administra la instalación, en los precios de la empresa.",
    partes: [
      {
        titulo: "Revalorar un presupuesto con una lista nueva",
        pasos: [
          "En la obra, vaya a «Mercado» y a la vista «Actualizar precios».",
          "Elija el «Presupuesto base» y escriba el «Código de la versión nueva», la «Fecha de vigencia», la «Moneda» y el «Nombre de la lista». Suelte la lista (.csv o .xlsx con las columnas tipo, insumo, unidad y precio).",
          "Si trae insumos que el catálogo no tiene, márquelos en «Dar de alta». Pulse «Revalorar presupuesto».",
          "Revise el «Comparativo por partida» y el «Informe de auditoría de la versión nueva». Si no le sirve, «Descartar versión».",
        ],
      },
      {
        titulo: "Usar un precio del mercado",
        pasos: [
          "En «Mercado», pestaña «Lo que compramos», anote lo que ve con «Anotar observación».",
          "Cuando la propuesta le sirva, pulse «Usar este precio» y «Confirmar»: entra en la lista para armar de la carpeta con la fecha de hoy, y las versiones ya guardadas no cambian.",
          "Un precio de proveedor que vale solo para esta obra va en «Cotizaciones de la obra», con «Registrar una cotización…».",
        ],
      },
      {
        titulo: "Los precios de la empresa",
        pasos: [
          "En la barra de la izquierda, «Precios y catálogo», herramienta «Precios de la empresa».",
          "«Cargar la referencia MaPreX en Bs» trae la referencia. Para la lista propia, llene «Empresa (nombre)», «RIF», «Lista base», «Moneda de la lista», «Fecha de la lista» y la fuente, suelte el archivo de precios y pulse «Crear la lista de la empresa».",
          "Más abajo, elija la lista y la «Fecha de evaluación» para ver los precios vencidos o fuera de rango.",
          "La tasa del BCV y los índices se importan en «Índices del BCV»: «Leer» muestra un informe previo sin guardar nada y «Confirmar la importación» los guarda.",
        ],
      },
    ],
    terminos: ["lista-de-precios", "lista-para-armar", "cotizacion", "maprex", "indices-bcv"],
  },
  {
    id: "auditar",
    titulo: "Auditar un libro",
    quien: "Quien arma presupuestos o quien revisa paquetes.",
    partes: [
      {
        titulo: "Subir y leer la auditoría",
        pasos: [
          "En la barra de la izquierda, pulse «Auditar un presupuesto»: se abre «Subir y auditar Excel».",
          "Suelte el libro .xlsx en la zona de arriba y pulse «Auditar con recorrido guiado» (Sílice lo acompaña paso a paso) o «Auditar por mi cuenta».",
          "Se abre «Libro de la empresa». Revise la «Fecha de devolución»: es la fecha con la que se audita, y con la misma fecha el mismo libro da siempre el mismo resultado.",
          "Compare el total del libro con el «Según Sílice» y revise los hallazgos, de los críticos a los informativos; elija uno para ver su celda marcada en el libro. «Filtrar por severidad» deja ver solo los de una gravedad.",
          "El libro no se modifica ni se guarda. El resumen y los hallazgos quedan en «Historial de auditorías», donde «Ver el detalle» los vuelve a mostrar.",
        ],
      },
    ],
    terminos: ["libro", "hallazgo", "precio-atipico"],
  },
];

export interface AyudaDePantalla {
  // El título de la pantalla (el de su h1): nombra la región que se abre.
  titulo: string;
  parrafos: readonly string[];
  guia?: GuiaId;
  terminos?: readonly TerminoId[];
}

// El «¿Qué es esto?» de cada pantalla de la obra, de los espacios de la empresa y de Pendientes, por el id de la pantalla
// (`shell/rutas.ts`). El Presupuesto («hoja») no está: cada una de sus pestañas ya trae el suyo (`paginas/hoja/textos.ts`).
export const AYUDA_DE_PANTALLAS: Readonly<Record<string, AyudaDePantalla>> = {
  // La obra.
  obras: {
    titulo: "Resumen de la obra",
    parrafos: [
      "La obra de un vistazo: su total, el avance real contra el plan, la versión que rige y su etapa. La franja de arriba dice el siguiente paso y su botón lo abre; debajo, «Pendientes de esta obra» reúne lo que espera de usted.",
    ],
    guia: "presupuesto",
    terminos: ["etapa", "linea-base", "version"],
  },
  tablero: {
    titulo: "Tablero de la obra",
    parrafos: [
      "Las cifras de la versión guardada en gráficos y tablas: el control de la obra, su curva, el desglose del contrato, las partidas que más pesan y las versiones del presupuesto. Aquí solo se lee: lo que se cambia, se cambia en Presupuesto.",
    ],
    terminos: ["version", "valor-ganado"],
  },
  componer: {
    titulo: "Componer una partida",
    parrafos: [
      "Arma el APU de una partida: su cabecera, su rendimiento y sus insumos en «Materiales», «Equipos» y «Mano de obra». Sílice calcula el precio unitario mientras usted escribe, y «Guardar composición» la guarda en el catálogo.",
      "Los precios salen de la lista para armar de la carpeta, a la «Fecha» de la composición.",
    ],
    guia: "presupuesto",
    terminos: ["apu", "rendimiento", "insumo", "lista-para-armar"],
  },
  tramos: {
    titulo: "Tramos de la vía",
    parrafos: [
      "Los tramos de la vía de cada versión, con las cantidades de obra que salen de ellos. Se cargan desde un archivo .csv; «Llevar al presupuesto» pasa esas cantidades al borrador, y debajo están los «Reportes en Excel».",
    ],
    terminos: ["tramo", "borrador"],
  },
  archivos: {
    titulo: "Archivos y planos",
    parrafos: [
      "Para traer las cantidades de un archivo en vez de escribirlas: «Subir plano o cómputo» acepta un plano .dxf o .ifc o un cómputo .csv y lleva sus partidas al borrador. Sin la especialidad de edificación, el botón es «Cargar cómputo» y solo acepta .csv.",
      "El «Registro de importaciones» dice qué se trajo, cuándo y quién. Lo traído no queda guardado hasta guardar la versión.",
    ],
    guia: "presupuesto",
    terminos: ["borrador"],
  },
  versiones: {
    titulo: "Versiones",
    parrafos: [
      "Cada vez que se guarda el presupuesto nace una versión, y las anteriores no se borran. Aquí están todas, con su motivo, sus cambios y su estado de aprobación; arriba se dice si la cadena de sellos está íntegra.",
      "«Abrir» la lleva al Presupuesto, «Ver cambios» muestra qué cambió y «Restaurar…» crea una versión nueva, copia de la elegida.",
    ],
    terminos: ["version", "cadena-de-sellos"],
  },
  aprobar: {
    titulo: "Aprobar una versión",
    parrafos: [
      "Aquí quien revisa abre la versión de esta obra que se envió a aprobación, lee sus partidas y su informe de auditoría y registra su dictamen: «Aprobada», «Aprobada con observaciones» o «Devuelta». El dictamen no se cambia después.",
    ],
    guia: "aprobacion",
    terminos: ["dictamen", "cadena-de-sellos"],
  },
  revisar: {
    titulo: "Revisar un paquete",
    parrafos: [
      "Para el presupuesto que le entregaron: suelte el paquete .silice y Sílice comprueba su firma, lo vuelve a auditar y le deja guardar su «Dictamen». La pestaña «Presupuesto en Excel» audita un Excel hecho con la plantilla del formato.",
    ],
    terminos: ["paquete", "hallazgo"],
  },
  entregar: {
    titulo: "Entregar paquete",
    parrafos: [
      "Prepara el paquete .silice de una versión para el cliente, firmado con la clave de la empresa: lleva el presupuesto, su auditoría y su cadena de sellos. Una versión sin aprobar sale rotulada «Versión NO aprobada», y con la cadena rota no se genera.",
    ],
    guia: "aprobacion",
    terminos: ["paquete", "cadena-de-sellos"],
  },
  mercado: {
    titulo: "Estudio de mercado",
    parrafos: [
      "Anote los precios que ve en el mercado y compárelos: «Lo que compramos» es para los insumos y «Lo que cobramos», para las partidas. Sílice propone un precio y usted decide si lo usa.",
      "«Histórico de precios» muestra los cambios de precio registrados y «Cotizaciones de la obra», los precios de proveedor que valen solo para esta obra.",
    ],
    guia: "precios",
    terminos: ["cotizacion", "lista-para-armar"],
  },
  actualizacion: {
    titulo: "Actualizar precios",
    parrafos: [
      "Vuelve a valorar un presupuesto guardado con una lista de precios nueva (.csv o .xlsx): crea una versión nueva y muestra el «Comparativo por partida» y su informe de auditoría. Si no le sirve, «Descartar versión».",
    ],
    guia: "precios",
    terminos: ["lista-de-precios", "version"],
  },
  control: {
    titulo: "Control de obra",
    parrafos: [
      "Sigue la obra en ejecución. Primero se declara la «Línea base» (la versión del contrato y su calendario); después se registran las «Valuaciones» y los costos, y Sílice calcula el valor ganado al corte, las alertas y las opciones para recuperarse.",
    ],
    terminos: ["linea-base", "valuacion", "valor-ganado"],
  },
  reajuste: {
    titulo: "Reajuste de precios",
    parrafos: [
      "Estima cuánto debe cambiar el pago de lo ejecutado según la cláusula de reajuste del contrato y los índices. Declare la fórmula en «1. La cláusula» y lo ejecutado en «2. Períodos y lo ejecutado»; «Calcular» pone lado a lado la escalatoria y la comprobación.",
      "El resultado es un indicio: hay que cotejarlo con la Gaceta.",
    ],
    terminos: ["reajuste", "indices-bcv"],
  },
  escenarios: {
    titulo: "Escenarios de sensibilidad",
    parrafos: [
      "Prueba qué pasaría con el total de un presupuesto guardado si cambian el FCAS, el bono de alimentación, la administración, la utilidad o el precio de algún insumo. El presupuesto no se altera y el escenario no se guarda.",
    ],
    terminos: ["fcas", "administracion-y-utilidad"],
  },
  riesgo: {
    titulo: "Riesgo de la obra",
    parrafos: [
      "Cuánto puede subir el presupuesto si los precios se mueven como en los meses pasados: «Proyectar» simula muchas trayectorias y da el P50, el P80 y la reserva para cubrir el P80. «Comprobar hacia atrás» mide cuántas veces acertó esa cuenta en el pasado.",
    ],
    terminos: ["p50-p80", "indices-bcv"],
  },

  // Costos de producción.
  produccion: {
    titulo: "Inicio de producción",
    parrafos: [
      "Lo que necesita atención en la arenera: los materiales con existencia negativa o por debajo de su mínima. Desde aquí se va a las existencias, a la receta de la planta, a producir una mezcla y a los costos.",
    ],
  },
  existencias: {
    titulo: "Existencias de la arenera",
    parrafos: [
      "Cuánto hay de cada material de la arenera a una fecha. En «Registrar» se anotan las entradas, los despachos, los conteos físicos y los materiales nuevos; en «Importar báscula», el reporte de la báscula, y en «Pesajes sospechosos» se resuelven los pesajes que no cuadran.",
    ],
  },
  costos: {
    titulo: "Costos del período",
    parrafos: [
      "Los costos de un mes de la cantera y de la planta, cada uno con su fuente (factura, recibo o nómina). «Registrar un costo» agrega uno; «Anular» lo deja marcado con su motivo, sin borrarlo.",
    ],
  },
  costo_tonelada: {
    titulo: "Costo por tonelada",
    parrafos: [
      "Calcula el costo propio por tonelada de cada agregado y mezcla del mes con los costos, lo producido y las recetas. Cada cálculo queda guardado, y quien administra puede publicarlo como precio propio de la empresa.",
    ],
  },
  receta_planta: {
    titulo: "Receta de la planta",
    parrafos: [
      "Lo que lleva una tonelada de cada mezcla. «Ver la receta vigente» muestra la que rige en una fecha y «Registrar una receta nueva» agrega otra sin cambiar las anteriores: cada producción usa la que rige en su fecha.",
    ],
  },
  producir_mezcla: {
    titulo: "Producir mezcla",
    parrafos: [
      "Registra las toneladas que produjo la planta de una mezcla con receta vigente. Antes de guardar muestra lo que consumirá del inventario, según la receta que rige en la fecha.",
    ],
  },

  // Auditar un presupuesto.
  auditoria: {
    titulo: "Inicio de auditoría",
    parrafos: [
      "Suelte el Excel de un presupuesto y Sílice recalcula cada partida y le dice lo que no cuadra. El archivo no se guarda: solo quedan el resumen y los hallazgos. Con «Auditar con recorrido guiado», Sílice lo acompaña paso a paso.",
    ],
    guia: "auditar",
    terminos: ["libro", "hallazgo"],
  },
  libros: {
    titulo: "Libro de la empresa",
    parrafos: [
      "El libro tal como es, con las celdas de cada hallazgo marcadas y, a la derecha, la lista de hallazgos por severidad: elija uno para ver su celda. La «Fecha de devolución» es la fecha con la que se audita.",
    ],
    guia: "auditar",
    terminos: ["libro", "hallazgo", "precio-atipico"],
  },
  historial: {
    titulo: "Historial de auditorías",
    parrafos: [
      "Las auditorías guardadas de libros y de PDF, con su resultado. Filtre por fechas, tipo o resultado y pulse «Ver el detalle» para ver sus hallazgos. El archivo no se guarda: solo el resumen, los hallazgos y la huella que lo identifica.",
    ],
    guia: "auditar",
    terminos: ["hallazgo"],
  },

  // Precios y catálogo.
  precios_empresa: {
    titulo: "Precios de la empresa",
    parrafos: [
      "La lista de precios propia de la empresa. Cargue la referencia MaPreX en bolívares, cree la lista de la empresa desde una lista base y un archivo, y revise los precios vencidos o fuera de rango. Abajo está la calculadora del FCAS.",
    ],
    guia: "precios",
    terminos: ["maprex", "lista-de-precios", "fcas"],
  },
  catalogo: {
    titulo: "Catálogo de partidas e insumos",
    parrafos: [
      "Las partidas y los insumos del catálogo de la carpeta, con el precio vigente de cada insumo. Aquí solo se consulta: las partidas se agregan o se componen desde el Presupuesto.",
    ],
    terminos: ["partida", "insumo"],
  },
  indices: {
    titulo: "Índices del BCV",
    parrafos: [
      "Importa la tasa de referencia del BCV, el INPC o una serie en .csv. «Leer» muestra un informe previo sin guardar nada y «Confirmar la importación» guarda los valores; el mismo archivo dos veces no escribe nada.",
    ],
    guia: "precios",
    terminos: ["indices-bcv"],
  },
  simulador: {
    titulo: "Simulador de listas",
    parrafos: [
      "Genera una lista de precios de prueba a partir de la vigente, con variaciones al azar que se repiten con la misma «Semilla». Sirve para practicar; no es una fuente de mercado.",
    ],
    terminos: ["lista-de-precios"],
  },

  // Inicio.
  pendientes: {
    titulo: "Pendientes",
    parrafos: [
      "Lo que las obras esperan de usted, en todas sus carpetas: primero lo que bloquea y después lo que solo avisa. Elija uno para ver su detalle y el botón que abre la pantalla donde se resuelve.",
    ],
    terminos: ["obra", "carpeta"],
  },
};

export function guiaPorId(id: GuiaId): Guia {
  return GUIAS.find((g) => g.id === id)!;
}

export function terminoPorId(id: TerminoId): Termino {
  return GLOSARIO.find((t) => t.id === id)!;
}
