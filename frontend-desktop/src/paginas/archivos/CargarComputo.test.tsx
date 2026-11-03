import { act, configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { CarpetaRespuesta, SesionRespuesta } from "../../api/tipos";
import { Marco } from "../../marco/Marco";
import { estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import { alertaConTexto } from "../../test/ayudas";
import { cuerpoDeVista } from "../hoja/datosDePrueba";
import PaginaHoja from "../hoja/index";
import type { BorradorAbierto, Resumen } from "../hoja/logica";
import PaginaArchivos from "./index";
import type { ImportacionDeObra } from "./logica";
import type { CalculoRespuesta, ItemComputo, PartidaCatalogo, RendimientoPorDeclarar } from "./tipos";
import { olvidarImportaciones } from "./useImportacion";

// Tarea 12 del plan F4: «Cargar cómputo» dentro de Archivos y planos absorbe Elaborar (bajas 13 a 19). Se monta el marco
// entero, como en `Archivos.test.tsx`, para ver que lo llevado entra en el MISMO borrador que el Presupuesto. Oráculos
// escritos a mano: obra ficticia 7 («Casa Demo»), carpeta en Bs con su lista del 26/10/2026 y un cómputo de 18 ítems.
// Las aserciones de lo que se queda vienen de `Elaborar.test.tsx` y `Llevar.test.tsx` (extraer, partidas civiles,
// rendimientos, pendientes y llevar); las de lo que se va (código, moneda y fecha propios, presupuesto elaborado, plan de
// trabajo, Excel e informe) se borraron con sus bajas y aquí se comprueba que no estén.
configure({ asyncUtilTimeout: 5000 });

const m = (texto: string, exacto = texto) => ({ texto, exacto });

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "Bs",
    total: m("1234.5"),
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
}

const CON_LISTA: CarpetaRespuesta = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de octubre", moneda: "Bs", fecha: "2026-10-26", origen: "maprex" },
  aviso: null,
};
const SIN_LISTA: CarpetaRespuesta = { moneda: "Bs", declarada: true, lista: null, aviso: null };

const PARTIDAS: PartidaCatalogo[] = [
  { codigo: "FIC-C1", descripcion: "Concreto ficticio", unidad: "m3", dominio: "civil" },
  { codigo: "FIC-C2", descripcion: "Encofrado ficticio", unidad: "m2", dominio: "civil" },
  { codigo: "FIC-C3", descripcion: "Excavacion ficticia", unidad: "m3", dominio: "civil" },
  { codigo: "FIC-C4", descripcion: "Tuberia ficticia", unidad: "m", dominio: "civil" },
];

const item = (origen: string, codigo: string, cantidad = "12.5000"): ItemComputo => ({
  codigo_partida: codigo,
  descripcion: `Descripcion ${origen}`,
  unidad: "m3",
  cantidad,
  origen_id: origen,
  origen_tipo: "tabla",
  dominio: "civil",
  regla: null,
  parametros: {},
  especificaciones: {},
});

// 18 ítems: fila-1 lleva «1.125» (uno coma ciento veinticinco, texto de máquina del cómputo) y el resto 12.5000.
const DIECIOCHO: ItemComputo[] = [
  item("fila-1", "FIC-C1", "1.125"),
  ...Array.from({ length: 17 }, (_, n) => item(`fila-${n + 2}`, `FIC-C${(n % 4) + 1}`)),
];

const INFORME = {
  codigo_presupuesto: "7",
  cumple: true,
  veredicto: "CUMPLE",
  total_hallazgos: 0,
  por_severidad: [],
  reglas_evaluadas: [],
  hallazgos: [],
  sin_hallazgos: "Se verifico y no hubo hallazgos.",
};

function calculo(pendientes: CalculoRespuesta["pendientes"] = []): CalculoRespuesta {
  return {
    codigo: "7",
    fecha: "2026-10-26",
    moneda: "Bs",
    pendientes,
    // Lo que la API sigue mandando y la pantalla ya no muestra (bajas 16 a 18).
    ...({
      total: "1000.00",
      total_exacto: "1000.00",
      partidas: [],
      por_severidad: [],
      informe: INFORME,
      plan_por_defecto: [{ periodo: "Dia 1", codigo_partida: "FIC-C1", fraccion: "1" }],
    } as object),
  } as CalculoRespuesta;
}

const PENDIENTES: CalculoRespuesta["pendientes"] = [
  {
    codigo_partida: "FIC-X",
    descripcion: "Zanja inexistente",
    unidad: "m",
    cantidad: "7.0000",
    origen_id: "fila-9",
    propuestas: [
      { codigo: "FIC-Z1", descripcion: "Zanja tipo uno", puntaje: 0.9137 },
      { codigo: "FIC-Z2", descripcion: "Zanja tipo dos", puntaje: 0.5 },
    ],
    falla: null,
  },
  {
    codigo_partida: "FIC-Y",
    descripcion: "Muro raro",
    unidad: "m2",
    cantidad: "2.0000",
    origen_id: "fila-10",
    propuestas: [],
    falla: "El modelo de similitud no esta disponible.",
  },
];
const CON_PENDIENTES: ItemComputo[] = [item("fila-1", "FIC-C1"), item("fila-9", "FIC-X", "7.0000"), item("fila-10", "FIC-Y", "2.0000")];

const RENDIMIENTO: RendimientoPorDeclarar = {
  codigo_partida: "FIC-C1",
  propuesta: {
    rendimiento: { valor: "8.5", tipo: "estimado", fecha: "2026-01-02", condiciones: "", referencia_ejecucion: null },
    dispersion: { observaciones: 3, medidos: 1, estimados: 2, media: "8.40", minimo: "7.00", maximo: "9.50" },
  },
};

const COMPUTO_LLEVADO: ImportacionDeObra = {
  tipo: "computo",
  archivo: "computo.csv",
  fecha_hora: "2026-11-02T10:15:00",
  usuario: "Ana Pérez <ana>",
  resumen: "18 partidas llevadas",
  version: null,
  guardada: false,
};

// Lo que el servidor simulado responde; cada prueba lo cambia antes de montar o de pulsar.
let carpeta: CarpetaRespuesta;
let partidasCiviles: () => Response;
let computo: () => Response;
let calcular: () => Response;
let llevar: () => Response;
let declarar: () => Response;
let registro: ImportacionDeObra[];
let apagados: string[];
let llevado: boolean;
let servidor: ReturnType<typeof servidorFalso>;

function borrador(id: string, proyecto: string): BorradorAbierto {
  return {
    id,
    base: { proyecto, version: "002", vigente: "002", lista: "Lista", espacio_de: "002", solo_lectura: false, moneda: "Bs" },
    resumen: resumen(),
    instantanea: { creadas: 0, mensaje: null },
  };
}

beforeEach(() => {
  carpeta = CON_LISTA;
  partidasCiviles = () => json(PARTIDAS);
  computo = () => json(DIECIOCHO);
  calcular = () => json(calculo());
  llevar = () => json({ borrador_id: "b-1" });
  declarar = () => json({ codigo_partida: "FIC-C1", valor: "8.5", tipo: "estimado", fecha: "2026-10-26", condiciones: "" });
  registro = [];
  apagados = [];
  llevado = false;
  olvidarImportaciones();
  let abiertos = 0;
  const estado = estadoInicial();
  estado.proyectos = estado.proyectos.map((p) => ({ ...p, version_vigente: 2 }));
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    const url = new URL(ruta, "http://silice.local");
    const camino = url.pathname;
    if (camino === "/v1/modulos") {
      return json({
        modulos: ["produccion", "vial", "edificacion", "riesgo"].map((clave) => ({
          clave,
          nombre: clave,
          activo: !apagados.includes(clave),
          cambiado_por: null,
          cambiado_el: null,
        })),
      });
    }
    if (camino === "/v1/carpeta" && metodo === "GET") return json(carpeta);
    if (camino === "/partidas" && metodo === "GET") return partidasCiviles();
    if (/^\/computos\/[a-z]+$/.test(camino) && metodo === "POST") return computo();
    if (camino === "/presupuestos/calcular" && metodo === "POST") return calcular();
    if (camino === "/presupuestos/calcular/declarar-rendimiento" && metodo === "POST") return declarar();
    if (camino === "/v1/hoja/llevar" && metodo === "POST") {
      const respuesta = llevar();
      if (respuesta.ok) {
        llevado = true;
        registro = [COMPUTO_LLEVADO, ...registro];
      }
      return respuesta;
    }
    if (camino === "/v1/hoja/versiones") {
      const proyecto = url.searchParams.get("proyecto") ?? "";
      return json({
        proyecto,
        moneda: "Bs",
        por_omision: "002",
        versiones: [{ codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 }],
      });
    }
    if (camino === "/v1/hoja/importaciones") return json({ importaciones: registro });
    if (camino === "/v1/hoja/borradores" && metodo === "POST") {
      abiertos += 1;
      return json(borrador(`b-${abiertos}`, (cuerpo as { proyecto: string }).proyecto), 201);
    }
    const propio = /^\/v1\/hoja\/borradores\/([^/]+)$/.exec(camino);
    if (propio && metodo === "DELETE") return new Response(null, { status: 204 });
    if (propio && metodo === "GET") {
      const b = borrador(propio[1]!, "7");
      return json({ id: b.id, base: b.base, resumen: llevado ? resumen({ rev: 1, cambios: 18 }) : b.resumen });
    }
    if (camino.endsWith("/cambios")) return json({ cambios: [] });
    const vista = cuerpoDeVista(camino);
    return vista === null ? undefined : json(vista);
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

function Ubicacion() {
  const { pathname } = useLocation();
  return <output data-testid="ruta">{pathname}</output>;
}

function montar(sesion: SesionRespuesta = sesionDe("ana")) {
  render(
    <MemoryRouter initialEntries={["/obra/empresa/7/archivos"]}>
      <Marco sesion={sesion} alSalir={vi.fn()} alExpirar={vi.fn()} paginas={ligeras({ hoja: PaginaHoja, archivos: PaginaArchivos })} />
      <Ubicacion />
    </MemoryRouter>,
  );
  return userEvent.setup({ applyAccept: false });
}

type Usuario = ReturnType<typeof userEvent.setup>;
const ruta = () => screen.getByTestId("ruta").textContent;
const principales = () => [...document.querySelectorAll(".cds--btn--primary")].map((b) => b.textContent);
const llamadas = (metodo: string, camino: string) => servidor.llamadas.filter((l) => l.metodo === metodo && l.ruta === camino);
const cuerpoDe = (metodo: string, camino: string, n = 0) => llamadas(metodo, camino)[n]?.cuerpo as Record<string, unknown>;
const pausa = () =>
  act(async () => {
    await new Promise((r) => setTimeout(r, 30));
  });

function campoDeArchivo(dialogo: HTMLElement): HTMLInputElement {
  const campo = dialogo.querySelector<HTMLInputElement>('input[type="file"]');
  expect(campo, "el campo de archivo del diálogo").not.toBeNull();
  return campo!;
}

async function abrirElDialogo(u: Usuario, nombre = "Subir plano o cómputo") {
  await u.click(await screen.findByRole("button", { name: nombre }));
  return screen.findByRole("dialog", { name: nombre });
}

// Abre el diálogo y elige el cómputo: el flujo de «Cargar cómputo» queda a la vista.
async function elegirElComputo(u: Usuario, nombre = "computo.csv", dialogo?: HTMLElement) {
  const caja = dialogo ?? (await abrirElDialogo(u));
  await u.upload(campoDeArchivo(caja), new File(["a,b"], nombre));
  await within(caja).findByLabelText("Tipo de obra del archivo");
  return caja;
}

async function elegirCuatro(u: Usuario, dialogo: HTMLElement) {
  await u.selectOptions(await within(dialogo).findByLabelText("Concreto"), "FIC-C1");
  await u.selectOptions(within(dialogo).getByLabelText("Encofrado"), "FIC-C2");
  await u.selectOptions(within(dialogo).getByLabelText("Excavación"), "FIC-C3");
  await u.selectOptions(within(dialogo).getByLabelText("Tubería"), "FIC-C4");
}

// Telecom no pide códigos: extrae directo.
async function extraerTelecom(u: Usuario, dialogo: HTMLElement) {
  await u.selectOptions(within(dialogo).getByLabelText("Tipo de obra del archivo"), "telecom");
  await u.click(within(dialogo).getByRole("button", { name: "Extraer cómputo" }));
  await within(dialogo).findByRole("table", { name: "Cómputo extraído" });
}

const botonLlevar = (dialogo: HTMLElement) => within(dialogo).getByRole("button", { name: "Llevar al presupuesto" });

describe("Cargar cómputo (Tarea 12 de F4)", () => {
  test("un .csv abre «Cargar cómputo» con el tipo de obra civil elegido y sin código, moneda ni fecha propios (bajas 13 y 14)", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    expect(within(dialogo).getByRole("heading", { name: "Cargar cómputo" })).toBeInTheDocument();
    const tipo = within(dialogo).getByLabelText("Tipo de obra del archivo") as HTMLSelectElement;
    expect(tipo.value).toBe("civil");
    expect(within(tipo).getAllByRole("option").map((o) => o.textContent)).toEqual(["Civil", "Telecomunicaciones", "Industrial", "Sistemas"]);
    expect(within(dialogo).queryByLabelText("Código del presupuesto")).toBeNull();
    expect(within(dialogo).queryByLabelText("Moneda")).toBeNull();
    expect(within(dialogo).queryByLabelText("Fecha")).toBeNull();
    // Con un .csv no se ofrece el flujo del plano.
    expect(within(dialogo).queryByRole("button", { name: "Leer plano" })).toBeNull();
  });

  test("con civil, «Extraer cómputo» espera los cuatro códigos y llama a /computos/civil con el archivo y el mapeo", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    const extraer = within(dialogo).getByRole("button", { name: "Extraer cómputo" });
    await within(dialogo).findByLabelText("Concreto");
    for (const nombre of ["Concreto", "Encofrado", "Excavación", "Tubería"]) {
      const selector = within(dialogo).getByLabelText(nombre) as HTMLSelectElement;
      expect(selector.value, nombre).toBe("");
      expect(within(selector).getByRole("option", { name: "Elija una partida" })).toBeDisabled();
    }
    expect(extraer).toBeDisabled();
    await elegirCuatro(u, dialogo);
    expect(extraer).toBeEnabled();
    await u.click(extraer);
    const tabla = await within(dialogo).findByRole("table", { name: "Cómputo extraído" });
    const datos = cuerpoDe("POST", "/computos/civil") as unknown as FormData;
    expect((datos.get("archivo") as File).name).toBe("computo.csv");
    expect(JSON.parse(String(datos.get("codigos")))).toEqual({ concreto: "FIC-C1", encofrado: "FIC-C2", excavacion: "FIC-C3", tuberia: "FIC-C4" });
    // La cantidad en es-VE, con sus decimales y el texto de la API a un toque.
    expect(within(tabla).getByText("1,125")).toHaveAttribute("title", "1.125");
    expect(within(tabla).getAllByRole("row")).toHaveLength(19);
  });

  test("la casilla de relleno agrega su selector y la clave relleno", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await elegirCuatro(u, dialogo);
    await u.click(within(dialogo).getByLabelText("Incluir relleno (balance R5)"));
    expect(within(dialogo).getByRole("button", { name: "Extraer cómputo" })).toBeDisabled();
    await u.selectOptions(within(dialogo).getByLabelText("Relleno"), "FIC-C2");
    await u.click(within(dialogo).getByRole("button", { name: "Extraer cómputo" }));
    await within(dialogo).findByRole("table", { name: "Cómputo extraído" });
    const datos = cuerpoDe("POST", "/computos/civil") as unknown as FormData;
    expect(JSON.parse(String(datos.get("codigos"))).relleno).toBe("FIC-C2");
  });

  test("civil sin partidas civiles en el catálogo avisa y no deja extraer", async () => {
    partidasCiviles = () => json([]);
    const u = montar();
    const dialogo = await elegirElComputo(u);
    expect(await within(dialogo).findByText(/El catálogo no tiene partidas del dominio civil todavía/)).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: "Extraer cómputo" })).toBeDisabled();
    expect(within(dialogo).queryByLabelText("Concreto")).toBeNull();
  });

  test("otro tipo de obra extrae sin códigos; un error al extraer se muestra con su detalle y quita la tabla", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    expect((cuerpoDe("POST", "/computos/telecom") as unknown as FormData).has("codigos")).toBe(false);
    computo = () => json({ detail: "Falta la columna cantidad." }, 400);
    await u.click(within(dialogo).getByRole("button", { name: "Extraer cómputo" }));
    expect(await alertaConTexto()).toHaveTextContent("Falta la columna cantidad.");
    expect(within(dialogo).queryByRole("table", { name: "Cómputo extraído" })).toBeNull();
    expect(within(dialogo).queryByRole("button", { name: "Llevar al presupuesto" })).toBeNull();
  });

  test("un solo botón principal en cada paso: «Extraer cómputo» y, con el cómputo, «Llevar al presupuesto»", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    expect(principales()).toEqual(["Extraer cómputo"]);
    await extraerTelecom(u, dialogo);
    expect(principales()).toEqual(["Llevar al presupuesto"]);
  });

  test("«Llevar al presupuesto» valora con la obra, la carpeta y su lista, lleva las 18 partidas con el archivo y refresca el borrador", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    const lecturas = () => llamadas("GET", "/v1/hoja/borradores/b-1").length;
    const registros = () => servidor.llamadas.filter((l) => l.ruta.startsWith("/v1/hoja/importaciones")).length;
    const antes = { borrador: lecturas(), registro: registros() };
    await u.click(botonLlevar(dialogo));
    expect(await within(dialogo).findByText("Se llevaron 18 partidas al presupuesto.")).toBeInTheDocument();
    expect(cuerpoDe("POST", "/presupuestos/calcular")).toEqual({
      codigo: "7",
      fecha: "2026-10-26",
      moneda: "Bs",
      items: DIECIOCHO,
      proyecto: "7",
    });
    const cuerpo = cuerpoDe("POST", "/v1/hoja/llevar") as { proyecto: string; archivo: string; partidas: unknown[] };
    expect(cuerpo.proyecto).toBe("7");
    expect(cuerpo.archivo).toBe("computo.csv");
    expect(cuerpo.partidas).toHaveLength(18);
    expect(cuerpo.partidas[0]).toEqual({ codigo: "FIC-C1", cantidad: "1.125", calculo: "" });
    expect(cuerpo.partidas[17]).toEqual({ codigo: "FIC-C1", cantidad: "12.5000", calculo: "" });
    expect(Object.keys(cuerpo).sort()).toEqual(["archivo", "partidas", "proyecto"]);
    await waitFor(() => expect(lecturas()).toBeGreaterThan(antes.borrador));
    await waitFor(() => expect(registros()).toBeGreaterThan(antes.registro));
    // El llevar es un solo paso: no se ofrece repetirlo sobre el mismo cómputo.
    expect(within(dialogo).queryByRole("button", { name: "Llevar al presupuesto" })).toBeNull();
    expect(within(dialogo).getByRole("link", { name: "Ver en Partidas" })).toBeInTheDocument();
    expect(llamadas("POST", "/v1/hoja/borradores")).toHaveLength(1);
  });

  test("no existen «Exportar a Excel», «Plan de trabajo», «Informe de auditoría» ni «Presupuesto elaborado» (bajas 15 a 18)", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    await u.click(botonLlevar(dialogo));
    await within(dialogo).findByText("Se llevaron 18 partidas al presupuesto.");
    expect(screen.queryByRole("button", { name: "Exportar a Excel" })).toBeNull();
    for (const titulo of ["Plan de trabajo", "Informe de auditoría", "Presupuesto elaborado"]) {
      expect(screen.queryByRole("heading", { name: titulo }), titulo).toBeNull();
      expect(screen.queryByText(titulo), titulo).toBeNull();
    }
    expect(screen.queryByRole("button", { name: "Elaborar presupuesto" })).toBeNull();
  });

  test("«Ver en Partidas» lleva a Presupuesto con la pestaña «Partidas» elegida, sobre el mismo borrador", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    await u.click(botonLlevar(dialogo));
    await u.click(await within(dialogo).findByRole("link", { name: "Ver en Partidas" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto"));
    expect(await screen.findByRole("tab", { name: "Partidas" })).toHaveAttribute("aria-selected", "true");
    await pausa();
    expect(llamadas("POST", "/v1/hoja/borradores")).toHaveLength(1);
  });

  // Menor 1 de la Tarea 12: `POST /v1/hoja/llevar` lleva al borrador vivo MÁS RECIENTE de la ficha y la obra. Si es otro
  // (abierto en otra ventana), lo llevado no se ve en este Presupuesto: se dice.
  test("si la API lo llevó a otro borrador de la obra (otra ventana), lo dice junto al aviso de lo llevado", async () => {
    llevar = () => json({ borrador_id: "b-otra-ventana" });
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    await u.click(botonLlevar(dialogo));
    const aviso = await within(dialogo).findByRole("status");
    expect(aviso).toHaveTextContent("Se llevaron 18 partidas al presupuesto.");
    expect(aviso).toHaveTextContent(
      "Ojo: fueron a otro borrador de esta obra, el más reciente (quizá abierto en otra ventana), no al que tiene abierto aquí, así que no se ven en este Presupuesto.",
    );
  });

  test("si la API lo llevó al borrador abierto, no hay aviso de otro borrador", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    await u.click(botonLlevar(dialogo));
    expect(await within(dialogo).findByText("Se llevaron 18 partidas al presupuesto.")).toBeInTheDocument();
    expect(within(dialogo).queryByText(/otro borrador de esta obra/)).toBeNull();
  });

  test("si la API no lo lleva, dice su detalle, no refresca nada y deja volver a intentarlo", async () => {
    llevar = () => json({ detalle: "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar." }, 409);
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    const lecturas = llamadas("GET", "/v1/hoja/borradores/b-1").length;
    await u.click(botonLlevar(dialogo));
    expect(await alertaConTexto()).toHaveTextContent("No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.");
    expect(within(dialogo).queryByText(/Se llevaron/)).toBeNull();
    expect(botonLlevar(dialogo)).toBeEnabled();
    await pausa();
    expect(llamadas("GET", "/v1/hoja/borradores/b-1")).toHaveLength(lecturas);
  });

  describe("rendimientos por declarar", () => {
    test("los muestra y no lleva nada hasta registrarlos; registrado, «Llevar al presupuesto» lo lleva", async () => {
      calcular = () => json({ detalle: "Faltan rendimientos.", rendimientos_por_declarar: [RENDIMIENTO] }, 409);
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      expect(await within(dialogo).findByRole("heading", { name: "Rendimientos por declarar" })).toBeInTheDocument();
      expect(within(dialogo).getByText(/rendimiento propuesto 8,5 unidades por día \(estimado del 02\/01\/2026\)/)).toBeInTheDocument();
      expect(
        within(dialogo).getByText("Dispersión del histórico: 3 observaciones (1 medidas, 2 estimadas), media 8,40, rango [7,00; 9,50]."),
      ).toBeInTheDocument();
      expect(llamadas("POST", "/v1/hoja/llevar")).toHaveLength(0);

      // Sin tipo, no se registra.
      await u.click(within(dialogo).getByRole("button", { name: "Registrar el rendimiento" }));
      expect(await within(dialogo).findByText("Declare si el rendimiento de FIC-C1 es estimado o medido.")).toBeInTheDocument();
      expect(llamadas("POST", "/presupuestos/calcular/declarar-rendimiento")).toHaveLength(0);

      const grupo = within(dialogo).getByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-C1" });
      await u.click(within(grupo).getByLabelText("estimado"));
      await u.click(within(dialogo).getByRole("button", { name: "Registrar el rendimiento" }));
      await waitFor(() => expect(within(dialogo).queryByRole("heading", { name: "Rendimientos por declarar" })).toBeNull());
      // La fecha del rendimiento es la de la lista de la carpeta, no la de hoy.
      expect(cuerpoDe("POST", "/presupuestos/calcular/declarar-rendimiento")).toEqual({
        codigo_partida: "FIC-C1",
        tipo: "estimado",
        fecha: "2026-10-26",
      });
      expect(llamadas("POST", "/v1/hoja/llevar")).toHaveLength(0);

      calcular = () => json(calculo());
      await u.click(botonLlevar(dialogo));
      expect(await within(dialogo).findByText("Se llevaron 18 partidas al presupuesto.")).toBeInTheDocument();
      expect(llamadas("POST", "/v1/hoja/llevar")).toHaveLength(1);
    });

    test("sin propuesta es un error con su texto y sin botón de registro", async () => {
      calcular = () => json({ detalle: "Faltan.", rendimientos_por_declarar: [{ codigo_partida: "FIC-C2", propuesta: null }] }, 409);
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      expect(
        await within(dialogo).findByText(
          "FIC-C2: la partida no tiene ningún rendimiento registrado que proponer; declárelo con sus condiciones en «Componer una partida».",
        ),
      ).toBeInTheDocument();
      expect(within(dialogo).queryByRole("button", { name: "Registrar el rendimiento" })).toBeNull();
    });

    test("declararlo como medido puede dar 422: se muestra el detalle y el bloque sigue", async () => {
      calcular = () => json({ detalle: "Faltan.", rendimientos_por_declarar: [RENDIMIENTO] }, 409);
      declarar = () => json({ detalle: "Un rendimiento medido exige una ejecucion de referencia." }, 422);
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      const grupo = await within(dialogo).findByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-C1" });
      await u.click(within(grupo).getByLabelText("medido"));
      await u.click(within(dialogo).getByRole("button", { name: "Registrar el rendimiento" }));
      expect(await alertaConTexto()).toHaveTextContent("Un rendimiento medido exige una ejecucion de referencia.");
      expect(within(dialogo).getByRole("heading", { name: "Rendimientos por declarar" })).toBeInTheDocument();
    });
  });

  describe("pendientes (ítems sin partida en el catálogo)", () => {
    test("los muestra con sus propuestas y no lleva nada; aplicar una propuesta cambia el código que se vuelve a valorar", async () => {
      computo = () => json(CON_PENDIENTES);
      calcular = () => json(calculo(PENDIENTES));
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      const bloque = await within(dialogo).findByRole("region", { name: "Pendientes" });
      expect(within(bloque).getByText("fila-9 · FIC-X · Zanja inexistente")).toBeInTheDocument();
      expect(within(bloque).getByText("fila-10 · FIC-Y · Muro raro")).toBeInTheDocument();
      expect(within(bloque).getByText("El modelo de similitud no esta disponible.")).toBeInTheDocument();
      expect(within(bloque).getByText("FIC-Z1 · Zanja tipo uno (0,91)")).toBeInTheDocument();
      expect(within(bloque).getByText("FIC-Z2 · Zanja tipo dos (0,50)")).toBeInTheDocument();
      expect(within(bloque).getAllByRole("button", { name: "Aplicar la propuesta" })).toHaveLength(1);
      expect(llamadas("POST", "/v1/hoja/llevar")).toHaveLength(0);

      await u.selectOptions(within(bloque).getByLabelText("Propuesta para fila-9"), "FIC-Z2");
      await u.click(within(bloque).getByRole("button", { name: "Aplicar la propuesta" }));
      await waitFor(() => expect(within(dialogo).queryByText("fila-9 · FIC-X · Zanja inexistente")).toBeNull());
      expect(llamadas("POST", "/v1/hoja/llevar")).toHaveLength(0);

      calcular = () => json(calculo());
      await u.click(botonLlevar(dialogo));
      expect(await within(dialogo).findByText("Se llevaron 3 partidas al presupuesto.")).toBeInTheDocument();
      const items = cuerpoDe("POST", "/presupuestos/calcular", 1).items as ItemComputo[];
      expect(items.map((i) => i.codigo_partida)).toEqual(["FIC-C1", "FIC-Z2", "FIC-Y"]);
    });

    test("«Llevar sin los pendientes» lleva el resto, con su archivo", async () => {
      computo = () => json(CON_PENDIENTES);
      calcular = () => json(calculo(PENDIENTES));
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      await u.click(await within(dialogo).findByRole("button", { name: "Llevar sin los pendientes" }));
      expect(await within(dialogo).findByText("Se llevó 1 partida al presupuesto.")).toBeInTheDocument();
      expect(cuerpoDe("POST", "/v1/hoja/llevar")).toEqual({
        proyecto: "7",
        partidas: [{ codigo: "FIC-C1", cantidad: "12.5000", calculo: "" }],
        archivo: "computo.csv",
      });
    });
  });

    // Menor 4 del árbitro de la Tarea 12 (cierre de F4): aplicar una propuesta cambia el código de un ítem; «Llevar sin los
    // pendientes» lo vuelve a valorar antes de llevar (como Elaborar), en vez de llevar un código que nadie valoró.
    test("tras aplicar una propuesta, «Llevar sin los pendientes» vuelve a valorar y lleva lo que la valoración deja", async () => {
      computo = () => json(CON_PENDIENTES);
      calcular = () => json(calculo(PENDIENTES));
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      const bloque = await within(dialogo).findByRole("region", { name: "Pendientes" });
      await u.selectOptions(within(bloque).getByLabelText("Propuesta para fila-9"), "FIC-Z2");
      await u.click(within(bloque).getByRole("button", { name: "Aplicar la propuesta" }));
      await waitFor(() => expect(within(dialogo).queryByText("fila-9 · FIC-X · Zanja inexistente")).toBeNull());
      calcular = () => json(calculo(PENDIENTES.filter((p) => p.origen_id === "fila-10")));
      await u.click(within(dialogo).getByRole("button", { name: "Llevar sin los pendientes" }));
      expect(await within(dialogo).findByText("Se llevaron 2 partidas al presupuesto.")).toBeInTheDocument();
      expect(llamadas("POST", "/presupuestos/calcular")).toHaveLength(2);
      const items = cuerpoDe("POST", "/presupuestos/calcular", 1).items as ItemComputo[];
      expect(items.map((i) => i.codigo_partida)).toEqual(["FIC-C1", "FIC-Z2", "FIC-Y"]);
      expect((cuerpoDe("POST", "/v1/hoja/llevar") as { partidas: { codigo: string }[] }).partidas.map((p) => p.codigo)).toEqual([
        "FIC-C1",
        "FIC-Z2",
      ]);
    });

    test("si al volver a valorar aparecen rendimientos por declarar, «Llevar sin los pendientes» los muestra y no lleva nada", async () => {
      computo = () => json(CON_PENDIENTES);
      calcular = () => json(calculo(PENDIENTES));
      const u = montar();
      const dialogo = await elegirElComputo(u);
      await extraerTelecom(u, dialogo);
      await u.click(botonLlevar(dialogo));
      await within(dialogo).findByRole("region", { name: "Pendientes" });
      calcular = () => json({ detalle: "Faltan.", rendimientos_por_declarar: [RENDIMIENTO] }, 409);
      await u.click(within(dialogo).getByRole("button", { name: "Llevar sin los pendientes" }));
      expect(await within(dialogo).findByRole("heading", { name: "Rendimientos por declarar" })).toBeInTheDocument();
      expect(llamadas("POST", "/v1/hoja/llevar")).toHaveLength(0);
    });

  test("sin lista en la carpeta, «Llevar al presupuesto» está deshabilitado y la franja dice el motivo", async () => {
    carpeta = SIN_LISTA;
    const u = montar();
    const dialogo = await elegirElComputo(u);
    const franja = await within(dialogo).findByRole("region", { name: "Siguiente paso" });
    expect(franja).toHaveTextContent("Te falta: la carpeta no tiene lista de precios para armar");
    await extraerTelecom(u, dialogo);
    expect(botonLlevar(dialogo)).toBeDisabled();
    expect(llamadas("POST", "/presupuestos/calcular")).toHaveLength(0);
  });

  test("sin moneda en la carpeta, igual: no se lleva", async () => {
    carpeta = { moneda: null, declarada: false, lista: null, aviso: null };
    const u = montar();
    const dialogo = await elegirElComputo(u);
    expect(await within(dialogo).findByRole("region", { name: "Siguiente paso" })).toHaveTextContent(
      "Te falta: la carpeta no tiene lista de precios para armar",
    );
    await extraerTelecom(u, dialogo);
    expect(botonLlevar(dialogo)).toBeDisabled();
  });

  test("el diálogo no se cierra mientras se lleva", async () => {
    let soltar: (r: Response) => void = () => {};
    const u = montar();
    const dialogo = await elegirElComputo(u);
    await extraerTelecom(u, dialogo);
    calcular = () => new Promise<Response>((r) => (soltar = r)) as unknown as Response;
    await u.click(botonLlevar(dialogo));
    await waitFor(() => expect(within(dialogo).getByRole("button", { name: "Cerrar" })).toBeDisabled());
    await u.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Subir plano o cómputo" })).toBeInTheDocument();
    soltar(json(calculo()));
    expect(await within(dialogo).findByText("Se llevaron 18 partidas al presupuesto.")).toBeInTheDocument();
    // Se cierra cuando termina también la relectura del borrador, como tras fusionar un plano.
    await waitFor(() => expect(within(dialogo).getByRole("button", { name: "Cerrar" })).toBeEnabled());
  });

  test("cuenta que revisa: ni «Subir plano o cómputo» ni «Cargar cómputo» (Foco 3)", async () => {
    registro = [COMPUTO_LLEVADO];
    montar(sesionDe("rita"));
    await screen.findByRole("table", { name: "Registro de importaciones" });
    await pausa();
    expect(screen.queryByRole("button", { name: "Subir plano o cómputo" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Cargar cómputo" })).toBeNull();
    expect(principales()).toEqual([]);
  });

  test("cuenta que revisa con «edificación» apagada: tampoco ve «Cargar cómputo»", async () => {
    apagados = ["edificacion"];
    registro = [COMPUTO_LLEVADO];
    montar(sesionDe("rita"));
    await screen.findByRole("table", { name: "Registro de importaciones" });
    await pausa();
    expect(screen.queryByRole("button", { name: "Cargar cómputo" })).toBeNull();
    expect(principales()).toEqual([]);
  });
});

// Decisión del orquestador sobre la decisión 10 de la Tarea 11 (reversible): «edificación» apaga los planos y el espacio,
// no los cómputos (regla de la T19 del plan vial). La sección se ve; dentro solo se carga el cómputo y nada habla de planos.
describe("Archivos y planos con «edificación» apagada", () => {
  beforeEach(() => {
    apagados = ["edificacion"];
  });

  test("ofrece «Cargar cómputo» como único botón principal, sin franja del espacio ni «Describir el espacio a mano»", async () => {
    montar();
    expect(await screen.findByRole("button", { name: "Cargar cómputo" })).toBeInTheDocument();
    await pausa();
    expect(principales()).toEqual(["Cargar cómputo"]);
    expect(screen.queryByRole("button", { name: "Subir plano o cómputo" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Describir el espacio a mano" })).toBeNull();
  });

  // Menor del árbitro de la Tarea 12 (cierre de F4): el diálogo ya se titula «Cargar cómputo» (h2); el flujo no lo repite.
  test("con el .csv elegido, «Cargar cómputo» es un solo título (el h2 del diálogo), sin un h3 que lo repita", async () => {
    const u = montar();
    const dialogo = await elegirElComputo(u, "computo.csv", await abrirElDialogo(u, "Cargar cómputo"));
    expect(within(dialogo).getAllByRole("heading", { name: "Cargar cómputo" }).map((h) => h.tagName)).toEqual(["H2"]);
  });

  test("el diálogo acepta solo el .csv, su texto no menciona planos y rechaza un .dxf", async () => {
    const u = montar();
    const dialogo = await abrirElDialogo(u, "Cargar cómputo");
    expect(within(dialogo).getByRole("button", { name: "Suelte aquí el cómputo .csv, o haga clic para elegirlo" })).toBeInTheDocument();
    expect(dialogo.textContent ?? "").not.toMatch(/plano/i);
    expect(within(dialogo).queryByRole("button", { name: "Leer plano" })).toBeNull();
    expect(campoDeArchivo(dialogo).getAttribute("accept")).toBe(".csv");
    await u.upload(campoDeArchivo(dialogo), new File(["0\nEOF"], "of001.dxf"));
    expect(await alertaConTexto()).toHaveTextContent("Solo se aceptan archivos .csv.");
    expect(llamadas("POST", "/v1/hoja/borradores/b-1/plano")).toHaveLength(0);
  });

  test("un .csv sigue el flujo del cómputo y lo lleva al presupuesto", async () => {
    const u = montar();
    const dialogo = await abrirElDialogo(u, "Cargar cómputo");
    await elegirElComputo(u, "movimiento.csv", dialogo);
    await extraerTelecom(u, dialogo);
    await u.click(botonLlevar(dialogo));
    expect(await within(dialogo).findByText("Se llevaron 18 partidas al presupuesto.")).toBeInTheDocument();
    expect((cuerpoDe("POST", "/v1/hoja/llevar") as { archivo: string }).archivo).toBe("movimiento.csv");
    expect(dialogo.textContent ?? "").not.toMatch(/plano/i);
  });
});
