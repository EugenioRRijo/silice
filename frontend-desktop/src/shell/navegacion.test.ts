import { describe, expect, test } from "vitest";
import { areaActual, moduloAlEntrar, moduloDeRuta, navegacion, type EntradaNav } from "./navegacion";
import { MODULOS, PAGINAS, fueraDeModulos, type ModuloId, type PaginaDef } from "./rutas";

// Acciones por rol copiadas a mano de ACCIONES_POR_ROL (Shell.test.tsx), que salen de seguridad/permisos.py.
const ANA = [
  "editar_hoja",
  "convertir_y_reajustar",
  "control_de_obra",
  "decidir_recuperacion",
  "entregar_paquete",
  "operar_arenera",
  "leer_proyecto",
  "cambiar_caso",
];
const RITA = ["leer_proyecto", "revisar_paquete"];
const ADMIN = [
  "operar_arenera",
  "cambiar_caso",
  "administrar_cuentas",
  "administrar_empresa",
  "administrar_precios",
  "administrar_red_y_api",
  "cambiar_carpeta_de_datos",
];

// [area, tipo, titulo] de cada entrada.
function forma(entradas: readonly EntradaNav[]): [string, string, string][] {
  return entradas.map((e) => [e.area, e.tipo, e.titulo]);
}

// Ids de las pantallas de cada entrada: en un enlace, su pantalla; en un panel, las del panel en orden.
function idsPorArea(entradas: readonly EntradaNav[]): Record<string, string[]> {
  return Object.fromEntries(
    entradas.map((e) => [e.area, e.tipo === "enlace" ? [e.pagina.id] : e.grupos.flatMap((g) => g.paginas.map((p) => p.id))]),
  );
}

function idsDe(entradas: readonly EntradaNav[]): string[] {
  return Object.values(idsPorArea(entradas)).flat();
}

describe("navegacion por modulo (oraculos escritos a mano)", () => {
  test("ana en Presupuestos y obras: Inicio, Obras, Partidas, Mercado y Control (sin Aprobaciones: aun no tiene pantallas)", () => {
    const e = navegacion("obras", ANA, false);
    expect(forma(e)).toEqual([
      ["inicio", "enlace", "Inicio"],
      ["obras", "panel", "Obras"],
      ["partidas", "panel", "Partidas"],
      ["mercado", "panel", "Mercado"],
      ["control", "panel", "Control"],
    ]);
    expect(idsPorArea(e)).toEqual({
      inicio: ["obras"],
      obras: ["hoja", "elaborar", "tablero", "entregar"],
      partidas: ["componer", "catalogo", "similares"],
      mercado: ["actualizacion", "historico", "simulador"],
      control: ["control", "reajuste", "escenarios"],
    });
  });

  test("ana en Presupuestos y obras con el modo entrega: sin Similares, Simulador ni Escenarios", () => {
    const e = navegacion("obras", ANA, true);
    expect(idsPorArea(e)).toEqual({
      inicio: ["obras"],
      obras: ["hoja", "elaborar", "tablero", "entregar"],
      partidas: ["componer", "catalogo"],
      mercado: ["actualizacion", "historico"],
      control: ["control", "reajuste"],
    });
  });

  test("rita en Presupuestos y obras: cada area de una sola pantalla es un enlace con el titulo del area", () => {
    const e = navegacion("obras", RITA, false);
    expect(forma(e)).toEqual([
      ["inicio", "enlace", "Inicio"],
      ["obras", "enlace", "Obras"],
      ["partidas", "enlace", "Partidas"],
      ["mercado", "enlace", "Mercado"],
    ]);
    expect(idsPorArea(e)).toEqual({ inicio: ["obras"], obras: ["tablero"], partidas: ["catalogo"], mercado: ["historico"] });
  });

  test("admin en Presupuestos y obras: Inicio y el panel de Mercado con Precios de la empresa e Indices", () => {
    const e = navegacion("obras", ADMIN, false);
    expect(forma(e)).toEqual([
      ["inicio", "enlace", "Inicio"],
      ["mercado", "panel", "Mercado"],
    ]);
    expect(idsPorArea(e)).toEqual({ inicio: ["obras"], mercado: ["precios_empresa", "indices"] });
  });

  test("ana en Auditoria: Inicio, Auditar y Historial (sin Paquetes)", () => {
    const e = navegacion("auditoria", ANA, false);
    expect(forma(e)).toEqual([
      ["inicio", "enlace", "Inicio"],
      ["auditar", "enlace", "Auditar"],
      ["historial", "enlace", "Historial"],
    ]);
    expect(idsPorArea(e)).toEqual({ inicio: ["auditoria"], auditar: ["libros"], historial: ["historial"] });
  });

  test("rita en Auditoria: Inicio, Auditar, Paquetes e Historial", () => {
    const e = navegacion("auditoria", RITA, false);
    expect(forma(e)).toEqual([
      ["inicio", "enlace", "Inicio"],
      ["auditar", "enlace", "Auditar"],
      ["paquetes", "enlace", "Paquetes"],
      ["historial", "enlace", "Historial"],
    ]);
    expect(idsPorArea(e)).toEqual({ inicio: ["auditoria"], auditar: ["libros"], paquetes: ["revisar"], historial: ["historial"] });
  });

  test("ana y admin en Produccion: Inicio y Existencias; rita no tiene Produccion", () => {
    for (const acciones of [ANA, ADMIN]) {
      const e = navegacion("produccion", acciones, false);
      expect(forma(e)).toEqual([
        ["inicio", "enlace", "Inicio"],
        ["existencias", "enlace", "Existencias"],
      ]);
      expect(idsPorArea(e)).toEqual({ inicio: ["produccion"], existencias: ["existencias"] });
    }
    expect(navegacion("produccion", RITA, false)).toEqual([]);
  });

  test("los paneles llevan un solo grupo sin titulo", () => {
    for (const e of navegacion("obras", ANA, false)) {
      if (e.tipo !== "panel") continue;
      expect(e.grupos).toHaveLength(1);
      expect(e.grupos[0].titulo).toBeNull();
    }
  });

  test("sin acciones no hay entradas en ningun modulo", () => {
    for (const m of MODULOS) expect(navegacion(m.id, [], false)).toEqual([]);
    expect(navegacion("obras", ANA, false, [])).toEqual([]);
  });

  // Foco de revision 4: ninguna pantalla se pierde ni sale dos veces.
  test.each([
    [
      "ana",
      ANA,
      false,
      [
        "auditoria",
        "libros",
        "historial",
        "obras",
        "hoja",
        "elaborar",
        "tablero",
        "entregar",
        "componer",
        "catalogo",
        "similares",
        "actualizacion",
        "historico",
        "simulador",
        "control",
        "reajuste",
        "escenarios",
        "produccion",
        "existencias",
        "acerca",
      ],
    ],
    [
      "ana en modo entrega",
      ANA,
      true,
      [
        "auditoria",
        "libros",
        "historial",
        "obras",
        "hoja",
        "elaborar",
        "tablero",
        "entregar",
        "componer",
        "catalogo",
        "actualizacion",
        "historico",
        "control",
        "reajuste",
        "produccion",
        "existencias",
        "acerca",
      ],
    ],
    ["rita", RITA, false, ["auditoria", "libros", "revisar", "historial", "obras", "tablero", "catalogo", "historico", "acerca"]],
    ["admin", ADMIN, false, ["obras", "precios_empresa", "indices", "produccion", "existencias", "administracion", "acerca"]],
  ] as const)("%s: las entradas de sus modulos mas el pie son exactamente sus pantallas, cada una una vez", (_, acciones, entrega, esperadas) => {
    const ids = [
      ...MODULOS.flatMap((m) => idsDe(navegacion(m.id, acciones, entrega))),
      ...fueraDeModulos(acciones, entrega).map((p) => p.id),
    ];
    expect(new Set(ids).size).toBe(ids.length);
    expect([...ids].sort()).toEqual([...esperadas].sort());
  });
});

describe("moduloAlEntrar", () => {
  test("respeta el modulo guardado si la cuenta lo puede usar", () => {
    expect(moduloAlEntrar("obras", ANA, false)).toBe("obras");
    expect(moduloAlEntrar("auditoria", ANA, false)).toBe("auditoria");
    expect(moduloAlEntrar("produccion", ADMIN, false)).toBe("produccion");
  });

  // Decision 3 ratificada por Eugenio: arma -> Presupuestos y obras, revisa -> Auditoria, administra -> Presupuestos y obras.
  test("sin modulo guardado, entra por su rol", () => {
    expect(moduloAlEntrar(null, ANA, false)).toBe("obras");
    expect(moduloAlEntrar(null, RITA, false)).toBe("auditoria");
    expect(moduloAlEntrar(null, ADMIN, false)).toBe("obras");
  });

  test("un modulo guardado que ya no es visible cae al de su rol", () => {
    expect(moduloAlEntrar("produccion", RITA, false)).toBe("auditoria");
    expect(moduloAlEntrar("auditoria", ADMIN, false)).toBe("obras");
  });

  test("una cuenta sin ninguna accion de entrada cae al primer modulo visible", () => {
    expect(moduloAlEntrar(null, ["leer_proyecto", "operar_arenera"], false)).toBe("auditoria");
    expect(moduloAlEntrar(null, ["operar_arenera"], false)).toBe("produccion");
  });

  test("sin ningun modulo visible: null", () => {
    expect(moduloAlEntrar(null, [], false)).toBeNull();
    expect(moduloAlEntrar("obras", ["administrar_cuentas"], false)).toBeNull();
  });
});

describe("moduloDeRuta (foco de revision 1)", () => {
  test("el modulo sale de la pantalla, no del ultimo usado", () => {
    expect(moduloDeRuta("/componer", "auditoria")).toBe("obras");
    expect(moduloDeRuta("/auditoria", "obras")).toBe("auditoria");
    expect(moduloDeRuta("/existencias", null)).toBe("produccion");
  });

  test("fuera de los modulos, o en una ruta sin pantalla, queda el ultimo usado", () => {
    expect(moduloDeRuta("/administracion", "produccion")).toBe("produccion");
    expect(moduloDeRuta("/acerca", null)).toBeNull();
    expect(moduloDeRuta("/", "obras")).toBe("obras");
    expect(moduloDeRuta("/no-existe", "auditoria")).toBe("auditoria");
  });

  test("consulta, ancla y subruta no cambian el modulo", () => {
    expect(moduloDeRuta("/hoja?codigo=DEMO-1", "auditoria" as ModuloId)).toBe("obras");
    expect(moduloDeRuta("/hoja/detalle", "auditoria")).toBe("obras");
  });

  test("con un registro de prueba", () => {
    const x = { id: "x", titulo: "X", enUnaLinea: "Haga X", seccion: "Trabajo", accion: null, ubicacion: { modulo: "produccion", area: "existencias" }, cargar: PAGINAS[0].cargar } as PaginaDef;
    expect(moduloDeRuta("/x", "obras", [x])).toBe("produccion");
  });
});

describe("areaActual", () => {
  const e = navegacion("obras", ANA, false);
  test("encuentra el area de la ruta", () => {
    expect(areaActual("/obras", e)).toBe("inicio");
    expect(areaActual("/hoja", e)).toBe("obras");
    expect(areaActual("/componer", e)).toBe("partidas");
    expect(areaActual("/escenarios", e)).toBe("control");
  });
  test("ruta de otro modulo o desconocida: null", () => {
    expect(areaActual("/libros", e)).toBeNull();
    expect(areaActual("/nada", e)).toBeNull();
    expect(areaActual("/", e)).toBeNull();
  });
  test("barra final, subruta, consulta y ancla no cambian el area", () => {
    expect(areaActual("/componer/", e)).toBe("partidas");
    expect(areaActual("/componer/detalle", e)).toBe("partidas");
    expect(areaActual("/componer?codigo=DEMO-1", e)).toBe("partidas");
    expect(areaActual("/componer#arriba", e)).toBe("partidas");
  });
});
