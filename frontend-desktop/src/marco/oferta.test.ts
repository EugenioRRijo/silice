import { describe, expect, it } from "vitest";
import { PAGINAS } from "../shell/rutas";
import { ofertaDe, seccionesDeLaObra } from "./oferta";

const TODAS = PAGINAS.flatMap((p) => (p.accion === null ? [] : [p.accion]));

describe("ofertaDe: «Tramos» (plan vial)", () => {
  it("la sección Tramos es de toda obra mientras el módulo vial esté encendido", () => {
    const oferta = ofertaDe(TODAS, false);
    expect(oferta.secciones.map((s) => s.id)).toContain("tramos");
    expect(seccionesDeLaObra(oferta).map((s) => s.id)).toEqual([
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
  });

  it("sin obra no hay pantalla «Tramos de la vía» entre las herramientas: el buscador la ofrece dentro de cada obra", () => {
    expect(ofertaDe(TODAS, false).herramientas.map((p) => p.id)).not.toContain("tramos");
  });

  it("quien no edita la hoja no la ve de ningún modo", () => {
    const oferta = ofertaDe(["leer_proyecto", "aprobar_version"], false);
    expect(oferta.secciones.map((s) => s.id)).not.toContain("tramos");
    expect(oferta.herramientas.map((p) => p.id)).not.toContain("tramos");
  });
});

describe("ofertaDe con módulos apagados (plan vial, Tarea 19)", () => {
  it("con vial apagado no hay sección Tramos ni la pantalla entre las herramientas (buscador)", () => {
    const oferta = ofertaDe(TODAS, false, ["vial"]);
    expect(oferta.secciones.map((s) => s.id)).not.toContain("tramos");
    expect(oferta.herramientas.map((p) => p.id)).not.toContain("tramos");
    expect(seccionesDeLaObra(oferta).map((s) => s.id)).not.toContain("tramos");
  });

  it("con producción apagada desaparece el espacio «Costos de producción» y sus pantallas del buscador", () => {
    const oferta = ofertaDe(TODAS, false, ["produccion"]);
    expect(oferta.espacios.map((e) => e.id)).not.toContain("produccion");
    const ids = oferta.herramientas.map((p) => p.id);
    for (const id of ["produccion", "existencias", "costos", "receta_planta", "producir_mezcla", "costo_tonelada"]) {
      expect(ids, id).not.toContain(id);
    }
  });

  it("con riesgo apagado la pantalla de riesgo no se ofrece", () => {
    expect(ofertaDe(TODAS, false, ["riesgo"]).herramientas.map((p) => p.id)).not.toContain("riesgo");
  });

  it("sin nada apagado la oferta es la de siempre", () => {
    expect(ofertaDe(TODAS, false, [])).toEqual(ofertaDe(TODAS, false));
    expect(ofertaDe(TODAS, false).espacios.map((e) => e.id)).toContain("produccion");
  });
});

describe("ofertaDe con edificación apagada (plan vial, Tarea 19, T19-5)", () => {
  // «Espacio y metrajes» es una pestaña de la hoja, no una pantalla: la oculta la Hoja. «Archivos y planos» se sigue
  // ofreciendo (F4, Tarea 12: edificación apaga los planos y el espacio, no los cómputos); dentro, solo se carga el cómputo.
  it("sigue ofreciendo «Archivos y planos» y deja todo como está", () => {
    const apagada = ofertaDe(TODAS, false, ["edificacion"]);
    const siempre = ofertaDe(TODAS, false);
    expect(apagada.secciones.map((s) => s.id)).toContain("archivos");
    expect(apagada.secciones.map((s) => s.id)).toEqual(siempre.secciones.map((s) => s.id));
    expect(apagada.cuenta).toEqual(siempre.cuenta);
    expect(apagada.espacios).toEqual(siempre.espacios);
    expect(apagada.herramientas).toEqual(siempre.herramientas);
  });
});

describe("ofertaDe (F6, T2): las pantallas de los espacios y las subvistas", () => {
  it("las pantallas de los espacios y las subvistas (las 20 que no son sección ni entrada) salen en «herramientas»", () => {
    expect(
      ofertaDe(TODAS, false)
        .herramientas.map((p) => p.id)
        .sort(),
    ).toEqual(
      [
        "tablero", "componer", "revisar", "entregar", "actualizacion", "reajuste", "escenarios",
        "produccion", "existencias", "costos", "costo_tonelada", "receta_planta", "producir_mezcla",
        "auditoria", "libros", "historial",
        "precios_empresa", "catalogo", "indices", "simulador",
      ].sort(),
    );
  });

  it("«herramientas» respeta permisos, modo entrega y módulos apagados", () => {
    const ids = (acciones: string[], entrega = false, apagados: string[] = []) =>
      ofertaDe(acciones, entrega, apagados).herramientas.map((p) => p.id);
    expect(ids(TODAS, true)).not.toContain("simulador");
    expect(ids(TODAS, true)).not.toContain("escenarios");
    expect(ids(TODAS, false, ["produccion"])).not.toContain("costos");
    expect(ids(["leer_proyecto"])).toEqual(expect.arrayContaining(["libros", "historial", "tablero"]));
    expect(ids(["leer_proyecto"])).not.toContain("indices");
  });
});

// F6, T4: los tres espacios de la empresa son la oferta de la barra lateral y del buscador. Oráculos escritos a mano.
describe("ofertaDe (F6, T4): los espacios de la empresa", () => {
  const espacios = (acciones: string[], entrega = false, apagados: string[] = []) =>
    ofertaDe(acciones, entrega, apagados).espacios.map((e) => [e.titulo, e.ruta]);

  it("salen en el orden de la barra lateral, cada uno con la ruta de su primera herramienta usable", () => {
    expect(espacios(TODAS)).toEqual([
      ["Auditar un presupuesto", "/auditoria/subir"],
      ["Precios y catálogo", "/precios/listas"],
      ["Costos de producción", "/produccion/resumen"],
    ]);
  });

  it("quien arma entra a Precios por el Catálogo y quien solo registra costos, a Producción por los costos", () => {
    expect(espacios(["leer_proyecto", "editar_hoja", "operar_arenera"])).toEqual([
      ["Auditar un presupuesto", "/auditoria/subir"],
      ["Precios y catálogo", "/precios/catalogo"],
      ["Costos de producción", "/produccion/resumen"],
    ]);
    expect(espacios(["registrar_costos_produccion"])).toEqual([
      ["Auditar un presupuesto", "/auditoria/subir"],
      ["Costos de producción", "/produccion/costos"],
    ]);
  });

  it("un espacio sin ninguna herramienta usable no se ofrece (permiso o especialidad apagada)", () => {
    expect(espacios([])).toEqual([["Auditar un presupuesto", "/auditoria/subir"]]);
    expect(espacios(TODAS, false, ["produccion"]).map(([titulo]) => titulo)).toEqual(["Auditar un presupuesto", "Precios y catálogo"]);
  });
});

// F6, T5 (contrato 2.1): una sección cuya pantalla principal no es usable pero que tiene una subvista usable se ofrece y
// abre en esa subvista; una sin ninguna pantalla usable no se ofrece.
describe("ofertaDe (F6, T5): secciones con una subvista usable", () => {
  const ids = (acciones: string[]) => ofertaDe(acciones, false).secciones.map((s) => s.id);

  it("quien solo revisa paquetes ve Aprobaciones (abre «Revisar un paquete») y no Control", () => {
    expect(ids(["leer_proyecto", "revisar_paquete"])).toContain("aprobaciones");
    expect(ids(["leer_proyecto", "revisar_paquete"])).not.toContain("control");
  });

  it("quien solo entrega paquetes también ve Aprobaciones", () => {
    expect(ids(["leer_proyecto", "entregar_paquete"])).toContain("aprobaciones");
  });

  it("quien edita la hoja sin controlar la obra ve Control (abre «Escenarios»)", () => {
    expect(ids(["leer_proyecto", "editar_hoja"])).toContain("control");
  });

  it("sin ninguna pantalla usable de la sección, no se ofrece", () => {
    expect(ids(["leer_proyecto"])).not.toContain("aprobaciones");
    expect(ids(["leer_proyecto"])).not.toContain("control");
    // En modo entrega «Escenarios» (Investigación) no cuenta.
    expect(ofertaDe(["leer_proyecto", "editar_hoja"], true).secciones.map((s) => s.id)).not.toContain("control");
  });

  it("el orden de las secciones no cambia", () => {
    expect(seccionesDeLaObra(ofertaDe(["leer_proyecto", "revisar_paquete", "editar_hoja"], false)).map((s) => s.id)).toEqual([
      "resumen",
      "presupuesto",
      "tramos",
      "archivos",
      "versiones",
      "aprobaciones",
      "mercado",
      "control",
    ]);
  });
});

// F6, T6 (contrato de rutas §3): las secciones de la Cuenta que ofrece la barra, el buscador y quien enlaza. Tabla escrita
// a mano: «Carpetas» pide `administrar_cuentas` Y `cambiar_caso`; las demás de administración, solo `administrar_cuentas`;
// «Pantalla y tamaño de letra» y «Ayuda» son de toda cuenta (también en modo entrega).
describe("ofertaDe: las secciones de la Cuenta (F6, T6)", () => {
  const cuenta = (acciones: string[], entrega = false) => ofertaDe(acciones, entrega).cuenta.map((c) => c.id);

  it("toda cuenta tiene preferencias y ayuda, aun sin ninguna acción y en modo entrega", () => {
    expect(cuenta([])).toEqual(["preferencias", "ayuda"]);
    expect(cuenta([], true)).toEqual(["preferencias", "ayuda"]);
  });

  it("administrar_cuentas abre cuentas, empresa y sistema, pero no carpetas", () => {
    expect(cuenta(["administrar_cuentas"])).toEqual(["preferencias", "cuentas", "empresa", "sistema", "ayuda"]);
  });

  it("carpetas pide las dos acciones: ninguna de las dos sola alcanza", () => {
    expect(cuenta(["cambiar_caso"])).not.toContain("carpetas");
    expect(cuenta(["administrar_cuentas"])).not.toContain("carpetas");
    expect(cuenta(["administrar_cuentas", "cambiar_caso"])).toEqual(["preferencias", "cuentas", "empresa", "carpetas", "sistema", "ayuda"]);
  });

  it("activar_modulos no abre nada por sí sola", () => {
    expect(cuenta(["activar_modulos"])).toEqual(["preferencias", "ayuda"]);
  });

  it("cada sección trae una ayuda corta, sin la jerga del marco", () => {
    for (const c of ofertaDe(TODAS, false).cuenta) {
      expect(c.ayuda.length, c.id).toBeGreaterThan(0);
      expect(c.ayuda.length, c.id).toBeLessThanOrEqual(90);
      expect(`${c.titulo} ${c.ayuda}`, c.id).not.toMatch(/m[oó]dulo|[aá]rea|p[aá]gina|carpeta de trabajo|streamlit/i);
    }
  });
});
