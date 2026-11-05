import { describe, expect, test } from "vitest";
import { PAGINAS } from "../shell/rutas";
import { ESPACIOS, SECCIONES_DE_CUENTA, SUBVISTAS, esCuenta, primeraUsable, rutaCanonica, rutaDeCuenta, rutaOPendientes, vistaDeLaSeccion } from "./espacios";
import type { CuentaId } from "./espacios";
import { SECCIONES_DE_OBRA, seccionPorId } from "./secciones";

// Las palabras que el marco no dice (sinJergaInterna.test.ts): palabras enteras, con y sin tilde.
const JERGA_DEL_MARCO = /(?<!\p{L})(m[oó]dulos?|[aá]reas?|p[aá]ginas?|carpetas? de trabajo)(?!\p{L})/iu;

// Plan F6, T1: una sola función dice a qué ruta lleva cada pantalla; quien enlaza (recorridos, buscador, pendientes,
// botones de las pantallas) la usa y no escribe rutas a mano. Oráculos escritos a mano, no derivados de PAGINAS.
describe("rutaCanonica", () => {
  test("una sección de obra, con la obra, va a la ruta de esa obra", () => {
    expect(rutaCanonica("hoja", { carpeta: "demo.db", obraId: 1 })).toBe("/obra/demo.db/1/presupuesto");
    expect(rutaCanonica("tramos", { carpeta: "Carpeta Norte.db", obraId: 7 })).toBe("/obra/Carpeta%20Norte.db/7/tramos");
    expect(rutaCanonica("obras", { carpeta: "demo.db", obraId: 2 })).toBe("/obra/demo.db/2/resumen");
    expect(rutaCanonica("aprobar", { carpeta: "demo.db", obraId: 2 })).toBe("/obra/demo.db/2/aprobaciones");
  });

  test("la obra de la empresa (sin carpeta) se escribe «empresa»", () => {
    expect(rutaCanonica("hoja", { carpeta: null, obraId: 1 })).toBe("/obra/empresa/1/presupuesto");
  });

  test("una sección de obra sin obra va a su dirección corta, que redirige a la obra de la sesión", () => {
    expect(rutaCanonica("hoja")).toBe("/hoja");
    expect(rutaCanonica("mercado")).toBe("/mercado");
  });

  // F6, T5. Contrato 2.1: las siete pantallas que son subvistas viven en /obra/<c>/<o>/<seccion>/<subvista>. Tabla a mano.
  const SUBVISTAS_DEL_CONTRATO: readonly (readonly [string, string])[] = [
    ["tablero", "resumen/tablero"],
    ["componer", "presupuesto/componer"],
    ["revisar", "aprobaciones/revisar"],
    ["entregar", "aprobaciones/entregar"],
    ["actualizacion", "mercado/actualizar"],
    ["reajuste", "control/reajuste"],
    ["escenarios", "control/escenarios"],
  ];

  test.each(SUBVISTAS_DEL_CONTRATO)("%s, con la obra, va a /obra/<c>/<o>/%s", (pagina, ruta) => {
    expect(rutaCanonica(pagina, { carpeta: "demo.db", obraId: 2 })).toBe(`/obra/demo.db/2/${ruta}`);
    expect(rutaCanonica(pagina, { carpeta: "Carpeta Norte.db", obraId: 7 })).toBe(`/obra/Carpeta%20Norte.db/7/${ruta}`);
    expect(rutaCanonica(pagina, { carpeta: null, obraId: 1 })).toBe(`/obra/empresa/1/${ruta}`);
  });

  test.each(SUBVISTAS_DEL_CONTRATO)("%s, sin obra, va a su dirección corta /%s, que redirige a la obra de la sesión", (pagina) => {
    expect(rutaCanonica(pagina)).toBe(`/${pagina}`);
  });

  test("rutaOPendientes sigue la misma regla para las subvistas", () => {
    expect(rutaOPendientes("reajuste", { carpeta: "demo.db", obraId: 2 })).toBe("/obra/demo.db/2/control/reajuste");
    expect(rutaOPendientes("reajuste")).toBe("/reajuste");
  });

  // F6, T6 (contrato 2.3 y 3): Administración vive en la Cuenta, y su primera sección es «Cuentas y permisos»; Acerca de es la Ayuda.
  test("Administración y Acerca de van a la Cuenta, con o sin obra", () => {
    expect(rutaCanonica("administracion")).toBe("/cuenta/cuentas");
    expect(rutaCanonica("acerca")).toBe("/cuenta/ayuda");
    expect(rutaCanonica("administracion", { carpeta: "demo.db", obraId: 1 })).toBe("/cuenta/cuentas");
    expect(rutaCanonica("acerca", { carpeta: null, obraId: 1 })).toBe("/cuenta/ayuda");
    expect(rutaOPendientes("administracion")).toBe("/cuenta/cuentas");
  });

  test("rutaDeCuenta y esCuenta dicen las seis secciones de la Cuenta y nada más", () => {
    expect(["preferencias", "cuentas", "empresa", "carpetas", "sistema", "ayuda"].map((id) => rutaDeCuenta(id as CuentaId))).toEqual([
      "/cuenta/preferencias",
      "/cuenta/cuentas",
      "/cuenta/empresa",
      "/cuenta/carpetas",
      "/cuenta/sistema",
      "/cuenta/ayuda",
    ]);
    expect(["preferencias", "cuentas", "empresa", "carpetas", "sistema", "ayuda"].every(esCuenta)).toBe(true);
    expect(["xyz", "", "toString", "personas"].some(esCuenta)).toBe(false);
  });

  // Contrato §2.2: las pantallas de los tres espacios viven en /<espacio>/<segmento>, con o sin obra.
  test("las pantallas de Precios van a /precios/<segmento>", () => {
    expect(rutaCanonica("precios_empresa")).toBe("/precios/listas");
    expect(rutaCanonica("catalogo")).toBe("/precios/catalogo");
    expect(rutaCanonica("indices")).toBe("/precios/indices");
    expect(rutaCanonica("simulador")).toBe("/precios/simulador");
  });

  test("las pantallas de Auditoría van a /auditoria/<segmento>", () => {
    expect(rutaCanonica("auditoria")).toBe("/auditoria/subir");
    expect(rutaCanonica("libros")).toBe("/auditoria/libros");
    expect(rutaCanonica("historial")).toBe("/auditoria/historial");
    expect(rutaCanonica("auditoria", { carpeta: "demo.db", obraId: 1 })).toBe("/auditoria/subir");
  });

  test("las pantallas de Producción van a /produccion/<segmento>", () => {
    expect(rutaCanonica("produccion")).toBe("/produccion/resumen");
    expect(rutaCanonica("existencias")).toBe("/produccion/existencias");
    expect(rutaCanonica("costos")).toBe("/produccion/costos");
    expect(rutaCanonica("costo_tonelada")).toBe("/produccion/costo-tonelada");
    expect(rutaCanonica("receta_planta")).toBe("/produccion/receta");
    expect(rutaCanonica("producir_mezcla")).toBe("/produccion/mezcla");
    expect(rutaCanonica("costos", { carpeta: "demo.db", obraId: 1 })).toBe("/produccion/costos");
  });

  test("un id desconocido da null (también los que son propiedades de Object)", () => {
    expect(rutaCanonica("inexistente")).toBeNull();
    expect(rutaCanonica("")).toBeNull();
    expect(rutaCanonica("toString")).toBeNull();
  });
});

describe("rutaOPendientes", () => {
  test("da la ruta canónica y, si el id no es pantalla, nunca un enlace muerto: lleva a Pendientes", () => {
    expect(rutaOPendientes("existencias")).toBe("/produccion/existencias");
    expect(rutaOPendientes("hoja", { carpeta: "demo.db", obraId: 1 })).toBe("/obra/demo.db/1/presupuesto");
    expect(rutaOPendientes("inexistente")).toBe("/pendientes");
  });
});


// Plan F6, T2: la tabla del contrato (2026-11-04-f6a-contrato-de-rutas, §2 y §3), escrita a mano, contra lo que exporta
// `espacios.ts` y `secciones.ts`. Nada se deriva de PAGINAS salvo para compararlo con la tabla.
//
// Cada fila: id de la pantalla, acción, módulo y el lugar (o lugares) donde vive. Un lugar es `obra/<sección>`,
// `obra/<sección>/<subvista>`, `<espacio>/<segmento>` o `cuenta/<sección>`.
type Fila = readonly [id: string, accion: string | null, modulo: string | undefined, lugares: readonly string[]];

const TABLA_DEL_CONTRATO: readonly Fila[] = [
  // 2.1 Obra: 9 secciones y 7 subvistas.
  ["obras", null, undefined, ["obra/resumen"]],
  ["tablero", "leer_proyecto", undefined, ["obra/resumen/tablero"]],
  ["hoja", "leer_proyecto", undefined, ["obra/presupuesto"]],
  ["componer", "editar_hoja", undefined, ["obra/presupuesto/componer"]],
  ["tramos", "editar_hoja", "vial", ["obra/tramos"]],
  ["archivos", "leer_proyecto", undefined, ["obra/archivos"]],
  ["versiones", "leer_proyecto", undefined, ["obra/versiones"]],
  ["aprobar", "aprobar_version", undefined, ["obra/aprobaciones"]],
  ["revisar", "revisar_paquete", undefined, ["obra/aprobaciones/revisar"]],
  ["entregar", "entregar_paquete", undefined, ["obra/aprobaciones/entregar"]],
  ["mercado", "leer_proyecto", undefined, ["obra/mercado"]],
  ["actualizacion", "editar_hoja", undefined, ["obra/mercado/actualizar"]],
  ["control", "control_de_obra", undefined, ["obra/control"]],
  ["reajuste", "convertir_y_reajustar", undefined, ["obra/control/reajuste"]],
  ["escenarios", "editar_hoja", undefined, ["obra/control/escenarios"]],
  ["riesgo", "ver_riesgo", "riesgo", ["obra/riesgo"]],
  // 2.2 Espacios de la empresa.
  ["produccion", "operar_arenera", "produccion", ["produccion/resumen"]],
  ["existencias", "operar_arenera", "produccion", ["produccion/existencias"]],
  ["costos", "registrar_costos_produccion", "produccion", ["produccion/costos"]],
  ["costo_tonelada", "registrar_costos_produccion", "produccion", ["produccion/costo-tonelada"]],
  ["receta_planta", "operar_arenera", "produccion", ["produccion/receta"]],
  ["producir_mezcla", "operar_arenera", "produccion", ["produccion/mezcla"]],
  ["auditoria", null, undefined, ["auditoria/subir"]],
  ["libros", "leer_proyecto", undefined, ["auditoria/libros"]],
  ["historial", "leer_proyecto", undefined, ["auditoria/historial"]],
  ["precios_empresa", "administrar_precios", undefined, ["precios/listas"]],
  ["catalogo", "leer_proyecto", undefined, ["precios/catalogo"]],
  ["indices", "administrar_precios", undefined, ["precios/indices"]],
  ["simulador", "editar_hoja", undefined, ["precios/simulador"]],
  // 2.3 y 3 Cuenta: «administracion» está repartida en cuatro secciones; «acerca» es «Ayuda».
  ["administracion", "administrar_cuentas", undefined, ["cuenta/cuentas", "cuenta/empresa", "cuenta/carpetas", "cuenta/sistema"]],
  ["acerca", null, undefined, ["cuenta/ayuda"]],
];

// Los lugares que dan las tablas exportadas, por id de pantalla. Las raíces de una subvista (`id: ""`) son la propia
// sección: se comprueban aparte y no cuentan como un segundo lugar.
function lugaresExportados(): Map<string, string[]> {
  const lugares = new Map<string, string[]>();
  const poner = (pagina: string | null, lugar: string) => {
    if (pagina === null) return;
    lugares.set(pagina, [...(lugares.get(pagina) ?? []), lugar]);
  };
  for (const s of SECCIONES_DE_OBRA) poner(s.pagina, `obra/${s.id}`);
  for (const [seccion, subvistas] of Object.entries(SUBVISTAS)) {
    for (const v of subvistas ?? []) if (v.id !== "") poner(v.pagina, `obra/${seccion}/${v.id}`);
  }
  for (const [espacio, def] of Object.entries(ESPACIOS)) {
    for (const h of def.herramientas) poner(h.pagina, `${espacio}/${h.id}`);
  }
  for (const c of SECCIONES_DE_CUENTA) poner(c.pagina, `cuenta/${c.id}`);
  return lugares;
}

describe("la tabla del contrato (F6, T2): 31 pantallas, cada una en su lugar", () => {
  test("la tabla escrita a mano tiene 31 ids distintos, y son los de PAGINAS (ni uno más ni uno menos)", () => {
    const ids = TABLA_DEL_CONTRATO.map((f) => f[0]);
    expect(ids).toHaveLength(31);
    expect(new Set(ids).size).toBe(31);
    expect([...ids].sort()).toEqual(PAGINAS.map((p) => p.id).sort());
  });

  test("el lugar de cada pantalla es exactamente el del contrato: ni falta ninguna, ni sobra, ni se repite", () => {
    const exportados = lugaresExportados();
    const esperado = Object.fromEntries(TABLA_DEL_CONTRATO.map((f) => [f[0], [...f[3]].sort()]));
    const real = Object.fromEntries([...exportados].map(([id, ls]) => [id, [...ls].sort()]));
    expect(real).toEqual(esperado);
  });

  test("solo «administracion» aparece en más de un lugar (la cuenta repartida en cuatro secciones)", () => {
    const repetidas = [...lugaresExportados()].filter(([, ls]) => ls.length > 1).map(([id]) => id);
    expect(repetidas).toEqual(["administracion"]);
  });

  test("la acción y el módulo de cada pantalla siguen siendo los del contrato (F6 no cambia permisos)", () => {
    const real = Object.fromEntries(PAGINAS.map((p) => [p.id, [p.accion, p.modulo]]));
    const esperado = Object.fromEntries(TABLA_DEL_CONTRATO.map((f) => [f[0], [f[1], f[2]]]));
    expect(real).toEqual(esperado);
  });
});

describe("SECCIONES_DE_OBRA y SUBVISTAS (contrato 2.1 y adenda A.1)", () => {
  test("son nueve secciones, en el orden del contrato; «tablero» no es una de ellas", () => {
    expect(SECCIONES_DE_OBRA.map((s) => s.id)).toEqual([
      "resumen",
      "presupuesto",
      "tramos",
      "archivos",
      "versiones",
      "aprobaciones",
      "mercado",
      "control",
      "riesgo",
    ]);
    expect(seccionPorId("tablero")).toBeUndefined();
    expect(seccionPorId("riesgo")).toMatchObject({
      pagina: "riesgo",
      ayuda: "Cuánto puede subir el presupuesto de la obra si cambian los precios.",
    });
  });

  test("las subvistas son las del contrato, con los textos exactos de la adenda (id vacío = la raíz de la sección)", () => {
    expect(SUBVISTAS).toEqual({
      resumen: [
        { id: "", titulo: "Resumen", pagina: "obras" },
        { id: "tablero", titulo: "Tablero", pagina: "tablero" },
      ],
      presupuesto: [
        { id: "", titulo: "Partidas", pagina: "hoja" },
        { id: "componer", titulo: "Componer", pagina: "componer" },
      ],
      aprobaciones: [
        { id: "", titulo: "Aprobar", pagina: "aprobar" },
        { id: "revisar", titulo: "Revisar un paquete", pagina: "revisar" },
        { id: "entregar", titulo: "Entregar", pagina: "entregar" },
      ],
      mercado: [
        { id: "", titulo: "Estudio", pagina: "mercado" },
        { id: "actualizar", titulo: "Actualizar precios", pagina: "actualizacion" },
      ],
      control: [
        { id: "", titulo: "Control", pagina: "control" },
        { id: "reajuste", titulo: "Reajuste", pagina: "reajuste" },
        { id: "escenarios", titulo: "Escenarios", pagina: "escenarios" },
      ],
    });
  });

  test("la raíz de cada subvista es la pantalla de su sección", () => {
    for (const [seccion, subvistas] of Object.entries(SUBVISTAS)) {
      expect(subvistas?.[0], seccion).toMatchObject({ id: "", pagina: seccionPorId(seccion)?.pagina });
      expect(subvistas?.filter((v) => v.id === ""), seccion).toHaveLength(1);
    }
  });
});

describe("ESPACIOS (contrato 2.2) y SECCIONES_DE_CUENTA (contrato 3)", () => {
  test("los tres espacios, con sus herramientas en el orden y con los segmentos del contrato", () => {
    expect(Object.keys(ESPACIOS)).toEqual(["produccion", "auditoria", "precios"]);
    expect(ESPACIOS).toEqual({
      produccion: {
        titulo: "Costos de producción",
        herramientas: [
          { id: "resumen", titulo: "Resumen de arenera", pagina: "produccion" },
          { id: "existencias", titulo: "Existencias", pagina: "existencias" },
          { id: "costos", titulo: "Costos del período", pagina: "costos" },
          { id: "costo-tonelada", titulo: "Costo por tonelada", pagina: "costo_tonelada" },
          { id: "receta", titulo: "Receta de la planta", pagina: "receta_planta" },
          { id: "mezcla", titulo: "Producir mezcla", pagina: "producir_mezcla" },
        ],
      },
      auditoria: {
        titulo: "Auditar un presupuesto",
        herramientas: [
          { id: "subir", titulo: "Subir y auditar Excel", pagina: "auditoria" },
          { id: "libros", titulo: "Libro de la empresa", pagina: "libros" },
          { id: "historial", titulo: "Historial de auditorías", pagina: "historial" },
        ],
      },
      precios: {
        titulo: "Precios y catálogo",
        herramientas: [
          { id: "listas", titulo: "Precios de la empresa", pagina: "precios_empresa" },
          { id: "catalogo", titulo: "Catálogo de partidas e insumos", pagina: "catalogo" },
          { id: "indices", titulo: "Índices del BCV", pagina: "indices" },
          { id: "simulador", titulo: "Simulador de listas", pagina: "simulador" },
        ],
      },
    });
  });

  test("la Cuenta tiene sus seis secciones, con los títulos del contrato", () => {
    expect(SECCIONES_DE_CUENTA.map((c) => [c.id, c.titulo])).toEqual([
      ["preferencias", "Pantalla y tamaño de letra"],
      ["cuentas", "Cuentas y permisos"],
      ["empresa", "Empresa y tema"],
      ["carpetas", "Carpetas"],
      ["sistema", "Especialidades, IA e instalación"],
      ["ayuda", "Ayuda y acerca de Sílice"],
    ]);
  });

  test("ningún título ni ayuda nuevo dice «módulo», «área», «página» ni «carpeta de trabajo»", () => {
    const textos = [
      ...Object.values(ESPACIOS).flatMap((e) => [e.titulo, ...e.herramientas.map((h) => h.titulo)]),
      ...Object.values(SUBVISTAS).flatMap((vs) => (vs ?? []).map((v) => v.titulo)),
      ...SECCIONES_DE_CUENTA.map((c) => c.titulo),
      ...SECCIONES_DE_OBRA.flatMap((s) => [s.titulo, s.ayuda]),
    ];
    expect(textos.length).toBeGreaterThan(40);
    expect(textos.filter((t) => JERGA_DEL_MARCO.test(t))).toEqual([]);
    expect("Carpetas de trabajo").toMatch(JERGA_DEL_MARCO); // la guardia reconoce lo que prohíbe
  });
});

describe("primeraUsable (F6, T2)", () => {
  const ARMA = ["leer_proyecto", "editar_hoja", "aprobar_version", "entregar_paquete", "control_de_obra", "convertir_y_reajustar", "operar_arenera", "registrar_costos_produccion", "cambiar_caso", "ver_riesgo"];
  const ARMA_Y_PRECIOS = [...ARMA, "administrar_precios"];
  const precios = ESPACIOS.precios.herramientas;
  const produccion = ESPACIOS.produccion.herramientas;

  test("quien arma (sin administrar precios) entra a Precios por el Catálogo, no por los precios de la empresa", () => {
    expect(primeraUsable(precios, ARMA, false, [])?.pagina).toBe("catalogo");
  });

  test("con administrar precios, la primera es la de siempre: los precios de la empresa", () => {
    expect(primeraUsable(precios, ARMA_Y_PRECIOS, false, [])?.pagina).toBe("precios_empresa");
  });

  test("con modo entrega el Simulador no es usable: queda como única opción y no se ofrece", () => {
    expect(primeraUsable(precios.filter((h) => h.id === "simulador"), ARMA, true, [])).toBeNull();
    expect(primeraUsable(precios.filter((h) => h.id === "simulador"), ARMA, false, [])?.pagina).toBe("simulador");
    // Entre todas, el modo entrega no cambia la primera, pero tampoco deja pasar el Simulador.
    expect(primeraUsable([...precios].reverse(), ARMA, true, [])?.pagina).toBe("catalogo");
  });

  test("con el módulo de producción apagado, Producción no tiene primera usable", () => {
    expect(primeraUsable(produccion, ARMA, false, ["produccion"])).toBeNull();
    expect(primeraUsable(produccion, ARMA, false, [])?.pagina).toBe("produccion");
  });

  test("quien no tiene ninguna acción solo ve lo de toda cuenta; una lista vacía da null", () => {
    expect(primeraUsable(ESPACIOS.auditoria.herramientas, [], false, [])?.pagina).toBe("auditoria");
    expect(primeraUsable(precios, [], false, [])).toBeNull();
    expect(primeraUsable([], ARMA, false, [])).toBeNull();
  });

  test("quien solo opera la arenera (sin registrar costos) abre Producción en el resumen y salta los costos", () => {
    expect(primeraUsable(produccion, ["operar_arenera"], false, [])?.pagina).toBe("produccion");
    expect(primeraUsable(produccion.filter((h) => h.id === "costos"), ["operar_arenera"], false, [])).toBeNull();
  });
});

// F6, T5: qué pantalla abre una sección de la obra según el cuarto segmento de la ruta (contrato 2.1 y 1). `redirigeA` es
// la subvista (`""` = la raíz) a la que hay que llevar la dirección con replace, o null si ya es la buena. Oráculos a mano.
describe("vistaDeLaSeccion (F6, T5)", () => {
  const seccion = (id: string) => seccionPorId(id)!;
  const TODO = ["leer_proyecto", "editar_hoja", "aprobar_version", "revisar_paquete", "entregar_paquete", "control_de_obra", "convertir_y_reajustar"];

  test("sin cuarto segmento abre la pantalla principal de la sección", () => {
    expect(vistaDeLaSeccion(seccion("control"), undefined, TODO, false, [])).toEqual({ pagina: "control", redirigeA: null });
    expect(vistaDeLaSeccion(seccion("presupuesto"), undefined, TODO, false, [])).toEqual({ pagina: "hoja", redirigeA: null });
    expect(vistaDeLaSeccion(seccion("tramos"), undefined, TODO, false, [])).toEqual({ pagina: "tramos", redirigeA: null });
  });

  test("una subvista conocida abre su pantalla, aunque la cuenta no pueda usarla (la ruta dirá «Sin permiso»)", () => {
    expect(vistaDeLaSeccion(seccion("control"), "reajuste", TODO, false, [])).toEqual({ pagina: "reajuste", redirigeA: null });
    expect(vistaDeLaSeccion(seccion("control"), "escenarios", TODO, false, [])).toEqual({ pagina: "escenarios", redirigeA: null });
    expect(vistaDeLaSeccion(seccion("resumen"), "tablero", [], false, [])).toEqual({ pagina: "tablero", redirigeA: null });
    expect(vistaDeLaSeccion(seccion("aprobaciones"), "entregar", ["leer_proyecto"], false, [])).toEqual({ pagina: "entregar", redirigeA: null });
  });

  test("una subvista desconocida lleva a la primera usable de la sección, que casi siempre es la raíz", () => {
    expect(vistaDeLaSeccion(seccion("control"), "xyz", TODO, false, [])).toEqual({ pagina: "control", redirigeA: "" });
    expect(vistaDeLaSeccion(seccion("mercado"), "tablero", TODO, false, [])).toEqual({ pagina: "mercado", redirigeA: "" });
  });

  test("si la raíz no es usable abre la primera subvista usable; sin ninguna usable, la raíz con su aviso", () => {
    // Quien solo revisa paquetes: Aprobaciones abre «Revisar un paquete».
    expect(vistaDeLaSeccion(seccion("aprobaciones"), undefined, ["revisar_paquete"], false, [])).toEqual({ pagina: "revisar", redirigeA: "revisar" });
    expect(vistaDeLaSeccion(seccion("aprobaciones"), "xyz", ["revisar_paquete"], false, [])).toEqual({ pagina: "revisar", redirigeA: "revisar" });
    // Quien edita la hoja pero no controla la obra: Control abre «Escenarios» (reajustar exige otra acción).
    expect(vistaDeLaSeccion(seccion("control"), undefined, ["editar_hoja"], false, [])).toEqual({ pagina: "escenarios", redirigeA: "escenarios" });
    expect(vistaDeLaSeccion(seccion("control"), undefined, [], false, [])).toEqual({ pagina: "control", redirigeA: null });
    expect(vistaDeLaSeccion(seccion("control"), "xyz", [], false, [])).toEqual({ pagina: "control", redirigeA: "" });
  });

  test("con modo entrega las pantallas de Investigación no cuentan como usables", () => {
    expect(vistaDeLaSeccion(seccion("control"), undefined, ["editar_hoja"], true, [])).toEqual({ pagina: "control", redirigeA: null });
  });

  test("una sección sin subvistas: cualquier cuarto segmento lleva a su raíz", () => {
    expect(vistaDeLaSeccion(seccion("versiones"), "xyz", TODO, false, [])).toEqual({ pagina: "versiones", redirigeA: "" });
    expect(vistaDeLaSeccion(seccion("riesgo"), "componer", TODO, false, [])).toEqual({ pagina: "riesgo", redirigeA: "" });
  });

  test("nombres como «toString» no son subvistas", () => {
    expect(vistaDeLaSeccion(seccion("control"), "toString", TODO, false, [])).toEqual({ pagina: "control", redirigeA: "" });
  });
});
