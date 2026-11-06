import { fileURLToPath } from "node:url";
import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as sass from "sass";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { DialogoSalida } from "../../shell/DialogoSalida";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import PaginaHoja from "./index";
import type { BorradorAbierto, FilaPresupuesto, Resumen, VersionesRespuesta, VistaPresupuesto } from "./logica";

// Tarea 11 del plan de montar un presupuesto: la Hoja agrega y quita partidas (rutas de la Tarea 9) y una obra sin
// espacio abre en «Presupuesto». El servidor se simula con la forma del contrato (`api/rutas/hoja.py`, `docs/api.json`):
// `POST …/partidas` `{rev, codigo, cantidad, calculo, nota}` → `{rev, resumen, clave}`; `POST …/partidas/quitar`
// `{rev, clave}` → `{rev, resumen}`; las filas traen `quitable`, `nota` y `calculo`; el resumen, `espacio_vacio`. Los
// textos de los errores son los de `aplicacion/hoja_partidas.py` y `aplicacion/hoja_edicion.py`. Obra y partidas
// ficticias (la vivienda de 80 m²).
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const ID = "id-borrador-vivienda-aaaa";
const RUTA_AGREGAR = `/v1/hoja/borradores/${ID}/partidas`;
const RUTA_QUITAR = `/v1/hoja/borradores/${ID}/partidas/quitar`;
const RUTA_CANTIDADES = `/v1/hoja/borradores/${ID}/cantidades`;
const SIN_RENGLONES = "El presupuesto no tiene renglones todavía.";
const CALCULO_NO_CUADRA = "El cálculo da 16 y la cantidad es 15: corrija uno de los dos.";
const FUERA_DEL_CATALOGO = "La partida «OBRA-04» no está en el catálogo: compóngala primero en Componer.";
const SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.";
const CONFIRMAR_QUITAR = "¿Quitar OBRA-04 del presupuesto? Lo puede descartar antes de guardar.";
const REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo.";
const FILA_AUSENTE = "Esa fila ya no está en el presupuesto.";
const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";
const RECARGADO = "Ya se volvió a leer el borrador: puede agregarla otra vez.";
const CIFRA_EN_LA_FILA_1 =
  "presupuesto, fila 1 (AF-LLAVE): Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.";

// Una respuesta que la prueba suelta cuando quiere (para retener una petición en vuelo).
function diferida() {
  let soltar: (r: Response) => void = () => undefined;
  const promesa = new Promise<Response>((resolver) => {
    soltar = resolver;
  });
  return { promesa, soltar };
}

const SIN_VERSIONES_DE_LA_OBRA: VersionesRespuesta = { proyecto: "VIV-80", moneda: "Bs", por_omision: null, versiones: [] };

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "Bs",
    total: { texto: "0.00", exacto: "0" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: false,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
}

function borradorEnBlanco(extra: Partial<Resumen> = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "VIV-80", version: null, vigente: null, lista: null, espacio_de: null, solo_lectura: false, moneda: "Bs" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

const PARED: FilaPresupuesto = {
  clave: "OBRA-04|a-mano:1",
  partida: "OBRA-04",
  descripcion: "Pared de bloques de arcilla de 15 cm",
  unidad: "m2",
  cantidad: "210",
  cantidad_calculada: "210",
  escrita: false,
  pu: { texto: "85.30", exacto: "85.3" },
  total: { texto: "17913.00", exacto: "17913" },
  estado: { severidad: "ADVERTENCIA", texto: "Advertencia" },
  quitable: true,
  nota: null,
  calculo: null,
};

const LLAVE_DEL_ESPACIO: FilaPresupuesto = {
  clave: "AF-LLAVE|esp_puntos:P1",
  partida: "AF-LLAVE",
  descripcion: "Llave de paso",
  unidad: "unidad",
  cantidad: "3",
  cantidad_calculada: "3",
  escrita: false,
  pu: { texto: "13.20", exacto: "13.198738025" },
  total: { texto: "39.60", exacto: "39.596214075" },
  estado: { severidad: null, texto: "OK" },
  quitable: false,
  nota: null,
  calculo: null,
};

function vista(filas: FilaPresupuesto[], total = { texto: "17913.00", exacto: "17913" }): VistaPresupuesto {
  const impuestos = { subtotal: total.texto, iva: "0.00", total: total.texto, alicuota: "0.16", fuente_alicuota: "Fuente ficticia" };
  return { filas, total, moneda: "Bs", vacio_mensaje: filas.length === 0 ? SIN_RENGLONES : null, impuestos };
}

const HALLADAS = {
  rotulo: "Partidas del catálogo",
  resultados: [
    {
      clave: "partida:OBRA-04",
      codigo: "OBRA-04",
      descripcion: "Pared de bloques de arcilla de 15 cm",
      unidad: "m2",
      dominio: "civil",
      tiene_composicion: true,
    },
  ],
  hay_mas: false,
};

type Cuerpo = Record<string, unknown> & { rev: number };

// Tarea 9 del plan F4: «Parecidas a esta descripción» (`POST /v1/similares`, la ruta de la pantalla que se da de baja) y
// «Componer una partida nueva» en panel (`/v1/composicion/*` y `/v1/carpeta`, como `componer/Moneda.test.tsx`).
const EXCAVACION = {
  codigo: "FIC-01",
  descripcion: "Excavación de zanja ficticia a mano",
  puntaje: "0.9137",
  puntaje_corto: "0.91",
  aviso: null,
  composicion: { unidad: "m3", rendimiento: "8.00", materiales: [], equipos: [], mano_obra: [] },
};
const EVALUACION_VACIA = {
  estado: "vacio",
  aviso: "Comience por la cabecera (código y descripción) y declare al menos un insumo.",
  desglose: null,
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};
const COMPOSICION_GUARDADA = {
  precio_unitario: "120.00",
  mensaje: "Composición guardada para la partida Z-99: precio unitario 120,00.",
  justificada: false,
  avisos: [],
};
const CARPETA_CON_LISTA = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
  aviso: null,
};
const AVISO_DEL_CATALOGO = "Esto cambia el catálogo de la empresa: la partida queda para todas las obras.";
const SESION_REVISA: SesionRespuesta = { ...SESION, login: "rita", roles: ["revisa"], acciones: ["leer_proyecto", "aprobar_version"] };

// jsdom no dibuja: se compila el SCSS real. La ruta va en una variable (con el literal, Vite reescribe el `new URL` como
// recurso; ver `componer/estilosComponer.test.ts`).
const compilar = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{`${pathname}${search}`}</p>;
}

describe("Hoja: agregar y quitar partidas (Tarea 11)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let versiones: VersionesRespuesta;
  let abierto: BorradorAbierto;
  let filas: FilaPresupuesto[];
  let alAgregar: (cuerpo: Cuerpo) => Response | Promise<Response>;
  let alQuitar: (cuerpo: Cuerpo) => Response | Promise<Response>;
  let alPonerCantidades: (cuerpo: Cuerpo) => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    versiones = SIN_VERSIONES_DE_LA_OBRA;
    abierto = borradorEnBlanco();
    filas = [];
    alAgregar = (cuerpo) => {
      filas = [...filas, PARED];
      return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1, total: PARED.total! }), clave: PARED.clave });
    };
    alQuitar = (cuerpo) => {
      filas = filas.filter((f) => f.clave !== cuerpo.clave);
      return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 0 }) });
    };
    alPonerCantidades = (cuerpo) => {
      const puestas = cuerpo.filas as Array<{ clave: string; cantidad: string }>;
      filas = filas.map((f) => {
        const puesta = puestas.find((p) => p.clave === f.clave);
        return puesta ? { ...f, cantidad: puesta.cantidad } : f;
      });
      return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1 }) });
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(versiones);
      if (url.startsWith("/v1/hoja/borradores") && !url.includes(ID) && metodo === "GET") return json({ borradores: [] });
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (url === `/v1/hoja/borradores/${ID}` && metodo === "GET") return json({ id: ID, base: abierto.base, resumen: abierto.resumen });
      if (url === RUTA_AGREGAR && metodo === "POST") return alAgregar(JSON.parse(String(init?.body)) as Cuerpo);
      if (url === RUTA_QUITAR && metodo === "POST") return alQuitar(JSON.parse(String(init?.body)) as Cuerpo);
      if (url === RUTA_CANTIDADES && metodo === "PUT") return alPonerCantidades(JSON.parse(String(init?.body)) as Cuerpo);
      if (url.endsWith("/vistas/presupuesto")) return json(vista(filas));
      if (url.startsWith("/v1/buscar/partidas")) {
        const q = new URL(url, "http://local").searchParams.get("q") ?? "";
        return json(q.toLowerCase().includes("bloq") ? HALLADAS : { ...HALLADAS, resultados: [] });
      }
      if (url === "/v1/similares" && metodo === "POST") return json({ propuestas: [EXCAVACION], falla: null, mensaje: null });
      if (url === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
      if (url === "/v1/composicion/evaluar") return json(EVALUACION_VACIA);
      if (url.startsWith("/v1/composicion/partidas/")) {
        return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (url.startsWith("/v1/consulta/insumos")) {
        return json({
          tabla: "insumos",
          hay_mas: false,
          resultados: [
            {
              valor: "MAT-1",
              etiqueta: "Cemento gris ficticio (MAT-1, saco)",
              fuente: "Catálogo de la carpeta de trabajo: material",
              descripcion: "Cemento gris ficticio",
              unidad: "saco",
              precio: "18.00",
              moneda: "Bs",
              fecha_precio: "2026-07-01",
            },
          ],
        });
      }
      if (url.startsWith("/v1/composicion/referencia") || url.startsWith("/v1/composicion/similares")) return json([]);
      if (url === "/v1/composicion/prever") {
        return json({ lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-26" }, lista_nueva: false, variantes: [] });
      }
      if (url === "/v1/composicion/guardar") return json(COMPOSICION_GUARDADA);
      if (url === "/v1/carpeta") return json(CARPETA_CON_LISTA);
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => {
    cancelarSalida();
    olvidarFormularios();
    vi.unstubAllGlobals();
  });

  const escrituras = (ruta: string, metodo = "POST"): Cuerpo[] =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === ruta && init?.method === metodo)
      .map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const lecturasDelBorrador = () =>
    fetchFalso.mock.calls.filter(([r, init]) => String(r) === `/v1/hoja/borradores/${ID}` && (init?.method ?? "GET") === "GET").length;

  // La obra con su versión VIV-001 guardada y estos renglones.
  function conVersion(renglones: FilaPresupuesto[]) {
    versiones = {
      ...SIN_VERSIONES_DE_LA_OBRA,
      por_omision: "VIV-001",
      versiones: [{ codigo: "VIV-001", fecha: "2026-10-25", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
    };
    abierto = {
      ...borradorEnBlanco(),
      base: { proyecto: "VIV-80", version: "VIV-001", vigente: "VIV-001", lista: "Lista de la carpeta", espacio_de: "VIV-001", solo_lectura: false, moneda: "Bs" },
    };
    filas = renglones;
  }

  async function escribirCantidad(fila: number, texto: string) {
    const campo = await screen.findByRole("textbox", { name: `Cantidad, Presupuesto fila ${fila}` });
    await userEvent.clear(campo);
    await userEvent.type(campo, texto);
  }
  const vistasPedidas = () => fetchFalso.mock.calls.map(([r]) => String(r)).filter((r) => r.includes("/vistas/"));

  function montar(sesion: SesionRespuesta = SESION) {
    const valor: Aplicacion = {
      sesion,
      proyecto: "VIV-80",
      nombreProyecto: "Vivienda de 80 m²",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/hoja"]}>
          <Routes>
            <Route path="/hoja" element={<PaginaHoja />} />
            <Route path="/componer" element={<p>Pantalla de Componer</p>} />
          </Routes>
          <Ubicacion />
          <DialogoSalida />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  async function abrirDialogo() {
    const boton = await screen.findByRole("button", { name: "Agregar partida" });
    await userEvent.click(boton);
    return screen.findByRole("dialog", { name: "Agregar partida" });
  }

  async function elegirPared(dialogo: HTMLElement) {
    await userEvent.type(within(dialogo).getByRole("combobox", { name: "Partida" }), "bloq");
    await userEvent.click(await screen.findByRole("option", { name: /OBRA-04/ }));
  }

  test("una obra sin espacio abre en «Partidas» y solo pide esa vista", async () => {
    montar();
    const pestana = await screen.findByRole("tab", { name: "Partidas" });
    await waitFor(() => expect(pestana).toHaveAttribute("aria-selected", "true"));
    expect(screen.queryByRole("tab", { name: "Espacio y metrajes" })).toBeNull(); // sin espacio, la pestaña no se ofrece
    await screen.findByText(SIN_RENGLONES);
    expect(vistasPedidas()).toEqual([`/v1/hoja/borradores/${ID}/vistas/presupuesto`]);
  });

  test("una obra con espacio sigue abriendo en «Espacio y metrajes»", async () => {
    abierto = borradorEnBlanco({ espacio_vacio: false });
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(screen.getByRole("tab", { name: "Espacio y metrajes" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Partidas" })).toHaveAttribute("aria-selected", "false");
  });

  test("la obra sin versiones lo dice con «obra» y explica cómo empezar por Presupuesto", async () => {
    montar();
    expect(await screen.findByText("Esta obra aún no tiene versiones")).toBeInTheDocument();
    expect(screen.getByText(/Agregue las partidas en la pestaña «Partidas»/)).toBeInTheDocument();
  });

  test("buscar «bloq», elegir OBRA-04 y escribir 210 manda la partida tal cual y la fila aparece", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull());
    expect(escrituras(RUTA_AGREGAR)).toEqual([{ rev: 0, codigo: "OBRA-04", cantidad: "210", calculo: "", nota: "" }]);
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    const fila = within(tabla).getAllByRole("row")[1]!;
    expect(within(fila).getByText("OBRA-04")).toBeInTheDocument();
    expect(within(fila).getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toHaveValue("210");
    // El estado del borrador recibe el resumen nuevo: un cambio sin guardar.
    expect(within(screen.getByRole("region", { name: "Estado del borrador" })).getByText(/1 cambio sin guardar/)).toBeInTheDocument();
    expect(screen.getByText("Se agregó OBRA-04 al presupuesto.")).toBeInTheDocument();
    // El foco vuelve al botón que abrió el diálogo.
    await waitFor(() => expect(screen.getByRole("button", { name: "Agregar partida" })).toHaveFocus());
  });

  test("el cálculo y la nota viajan como se escribieron, con coma decimal", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" }), "2,5*84");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Nota de medición (opcional)" }), "6 m × 35 m de muro");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() =>
      expect(escrituras(RUTA_AGREGAR)).toEqual([
        { rev: 0, codigo: "OBRA-04", cantidad: "", calculo: "2,5*84", nota: "6 m × 35 m de muro" },
      ]),
    );
  });

  test("el campo «Cálculo» tiene su ayuda y, escrito sin cantidad, dice que la cantidad sale del cálculo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const calculo = within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" });
    expect(calculo).toHaveAccessibleDescription(expect.stringContaining("Por ejemplo 6*3-2 o 2,5*4"));
    await userEvent.type(calculo, "6*35");
    await userEvent.tab();
    expect(within(dialogo).getByRole("textbox", { name: /^Cantidad/ })).toHaveAccessibleDescription(
      expect.stringContaining("Si la deja vacía, Sílice la toma del resultado del cálculo al agregar."),
    );
  });

  test("el 422 del cálculo se muestra junto al campo «Cálculo» y el diálogo sigue abierto", async () => {
    alAgregar = () => json({ detalle: CALCULO_NO_CUADRA }, 422);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "15");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" }), "6*3-2");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));

    const calculo = within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" });
    await waitFor(() => expect(calculo).toHaveAttribute("aria-invalid", "true"));
    expect(calculo).toHaveAccessibleDescription(expect.stringContaining(CALCULO_NO_CUADRA));
    expect(within(dialogo).getByRole("textbox", { name: /^Cantidad/ })).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Presupuesto" })).toBeNull();
    // Ronda 2: el foco va al campo del error, no al cuerpo de la página.
    await waitFor(() => expect(calculo).toHaveFocus());
  });

  test("una cantidad mal escrita sin cálculo se marca en «Cantidad»", async () => {
    alAgregar = () =>
      json({ detalle: "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56." }, 422);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "2.5");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const cantidad = within(dialogo).getByRole("textbox", { name: /^Cantidad/ });
    await waitFor(() => expect(cantidad).toHaveAttribute("aria-invalid", "true"));
    expect(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" })).not.toHaveAttribute("aria-invalid", "true");
  });

  // Pasada de navegador del cierre de F4 (H7): con la partida elegida y la cantidad y el cálculo vacíos, Enter mandaba el
  // formulario y solo el 422 del servidor decía «Escriba un número…». Ahora se dice antes, sin petición: es el mismo texto
  // del servidor (`aplicacion/cifras.py`, MENSAJE_CIFRA_VACIA). Con un cálculo escrito la cantidad vacía sigue valiendo.
  // La regla está en el envío del formulario (Enter o el botón): jsdom no envía con Enter cuando el botón de enviar está
  // fuera del formulario (`form=`), así que aquí se pulsa el botón; Enter se comprobó en el navegador.
  test("con la partida elegida, sin cantidad ni cálculo, no se manda nada y lo dice junto a «Cantidad»", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const cantidad = within(dialogo).getByRole("textbox", { name: /^Cantidad/ });
    await waitFor(() => expect(cantidad).toHaveAttribute("aria-invalid", "true"));
    expect(cantidad).toHaveAccessibleDescription(
      expect.stringContaining("Escriba un número. Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56."),
    );
    await waitFor(() => expect(cantidad).toHaveFocus());
    expect(escrituras(RUTA_AGREGAR)).toEqual([]);
    expect(screen.getByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
  });

  test("sin elegir una partida de la lista no se manda nada y lo dice en el campo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const partida = within(dialogo).getByRole("combobox", { name: "Partida" });
    expect(partida).toHaveAttribute("aria-invalid", "true");
    expect(partida).toHaveAccessibleDescription(expect.stringContaining("Elija la partida de la lista de sugerencias."));
    expect(escrituras(RUTA_AGREGAR)).toEqual([]);
  });

  test("la partida fuera del catálogo (404) se dice en el campo «Partida», tal cual", async () => {
    alAgregar = () => json({ detalle: FUERA_DEL_CATALOGO }, 404);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const partida = within(dialogo).getByRole("combobox", { name: "Partida" });
    await waitFor(() => expect(partida).toHaveAttribute("aria-invalid", "true"));
    expect(partida).toHaveAccessibleDescription(expect.stringContaining(FUERA_DEL_CATALOGO));
  });

  test("sin tasa del BCV (409) el diálogo lo dice tal cual y no agrega nada", async () => {
    alAgregar = () => json({ detalle: SIN_TASA }, 409);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    expect(await within(dialogo).findByText(SIN_TASA)).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
    // Ronda 2: el botón se deshabilitó mientras iba la petición; el foco no se pierde en el cuerpo de la página.
    await waitFor(() => expect(screen.getByRole("dialog", { name: "Agregar partida" })).toHaveFocus());
  });

  // --- ronda 2 del árbitro ---

  test("el POST sale después de la cantidad que esperaba la pausa y con el rev que contestó su PUT", async () => {
    conVersion([LLAVE_DEL_ESPACIO, PARED]);
    const put = diferida();
    alPonerCantidades = () => put.promesa;
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    await escribirCantidad(2, "250");
    // La cantidad salió tras la pausa y sigue en vuelo.
    await waitFor(() => expect(escrituras(RUTA_CANTIDADES, "PUT")).toHaveLength(1));
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "12");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    await new Promise((r) => setTimeout(r, 300));
    expect(escrituras(RUTA_AGREGAR)).toEqual([]);

    filas = [LLAVE_DEL_ESPACIO, { ...PARED, cantidad: "250" }];
    put.soltar(json({ rev: 5, resumen: resumen({ rev: 5, cambios: 1 }) }));
    await waitFor(() =>
      expect(escrituras(RUTA_AGREGAR)).toEqual([{ rev: 5, codigo: "OBRA-04", cantidad: "12", calculo: "", nota: "" }]),
    );
  });

  test("con el rev viejo (409) relee el borrador y la vista, conserva lo escrito y el segundo intento lleva el rev releído", async () => {
    let primera = true;
    const normal = alAgregar;
    alAgregar = (cuerpo) => {
      if (!primera) return normal(cuerpo);
      primera = false;
      abierto = { ...abierto, resumen: resumen({ rev: 7, cambios: 2 }) };
      return json({ detalle: REV_VIEJO }, 409);
    };
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" }), "6*35");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Nota de medición (opcional)" }), "muro norte");
    const leidasAntes = lecturasDelBorrador();
    const vistasAntes = vistasPedidas().length;
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));

    expect(await within(dialogo).findByText(`${REV_VIEJO} ${RECARGADO}`)).toBeInTheDocument();
    await waitFor(() => expect(lecturasDelBorrador()).toBe(leidasAntes + 1));
    await waitFor(() => expect(vistasPedidas().length).toBeGreaterThan(vistasAntes));
    expect(screen.getByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
    expect(within(dialogo).getByRole("combobox", { name: "Partida" })).toHaveValue("OBRA-04 · Pared de bloques de arcilla de 15 cm");
    expect(within(dialogo).getByRole("textbox", { name: /^Cantidad/ })).toHaveValue("210");
    expect(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" })).toHaveValue("6*35");
    expect(within(dialogo).getByRole("textbox", { name: "Nota de medición (opcional)" })).toHaveValue("muro norte");

    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(escrituras(RUTA_AGREGAR).map((c) => c.rev)).toEqual([0, 7]));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull());
  });

  test("al agregar, la cantidad que el servidor rechazó en otra fila sigue escrita y su aviso también", async () => {
    conVersion([LLAVE_DEL_ESPACIO, PARED]);
    alPonerCantidades = () => json({ detalle: CIFRA_EN_LA_FILA_1 }, 422);
    alAgregar = (cuerpo) => {
      filas = [...filas, { ...PARED, clave: "OBRA-04|a-mano:2", cantidad: "12" }];
      return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1 }), clave: "OBRA-04|a-mano:2" });
    };
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    await escribirCantidad(1, "2.5");
    await screen.findByText(/presupuesto, fila 1 \(AF-LLAVE\): Use la coma/);

    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "12");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(screen.getAllByRole("textbox", { name: /^Cantidad, Presupuesto fila/ })).toHaveLength(3));
    expect(screen.getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toHaveValue("2.5");
    expect(screen.getByText(/presupuesto, fila 1 \(AF-LLAVE\): Use la coma/)).toBeInTheDocument();
  });

  // Quita la fila 2 con la respuesta retenida, escribe 4 en la fila 1 mientras va, deja pasar la pausa y suelta `respuesta`.
  async function quitarYEscribirMientrasVa(respuesta: Response) {
    conVersion([LLAVE_DEL_ESPACIO, PARED]);
    const quitada = diferida();
    alQuitar = () => quitada.promesa;
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    await userEvent.click(screen.getByRole("button", { name: "Quitar OBRA-04, Presupuesto fila 2" }));
    const confirmacion = await screen.findByRole("alertdialog", { name: "Quitar partida" });
    await userEvent.click(within(confirmacion).getByRole("button", { name: "Quitar" }));
    await waitFor(() => expect(escrituras(RUTA_QUITAR)).toHaveLength(1));
    await escribirCantidad(1, "4");
    await new Promise((r) => setTimeout(r, 700)); // pasa la pausa con el quitar en vuelo
    quitada.soltar(respuesta);
  }

  test("si el quitar falla (422), lo escrito sale igual y su éxito no borra el aviso del quitar", async () => {
    await quitarYEscribirMientrasVa(json({ detalle: FILA_AUSENTE }, 422));
    await waitFor(() =>
      expect(escrituras(RUTA_CANTIDADES, "PUT")).toEqual([{ rev: 0, filas: [{ clave: LLAVE_DEL_ESPACIO.clave, cantidad: "4" }] }]),
    );
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toHaveValue("4"));
    expect(screen.getByText(FILA_AUSENTE)).toBeInTheDocument();
  });

  test("si el quitar da 401, lo escrito no se reenvía y la sesión se cierra una sola vez", async () => {
    await quitarYEscribirMientrasVa(json({ detalle: "La sesión venció: entre de nuevo." }, 401));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    await new Promise((r) => setTimeout(r, 300));
    expect(alExpirar).toHaveBeenCalledTimes(1);
    expect(escrituras(RUTA_CANTIDADES, "PUT")).toEqual([]);
  });

  test("si el borrador ya no está al quitar, lo escrito no se reenvía", async () => {
    await quitarYEscribirMientrasVa(json({ detalle: FALTA }, 404));
    await waitFor(() => expect(lecturasDelBorrador()).toBeGreaterThan(0));
    await new Promise((r) => setTimeout(r, 300));
    expect(escrituras(RUTA_CANTIDADES, "PUT")).toEqual([]);
  });

  test("lo escrito en otra fila mientras va «Quitar» sale después, una sola vez, y no repite el quitar", async () => {
    conVersion([LLAVE_DEL_ESPACIO, PARED]);
    const quitada = diferida();
    alQuitar = () => quitada.promesa;
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    await userEvent.click(screen.getByRole("button", { name: "Quitar OBRA-04, Presupuesto fila 2" }));
    const confirmacion = await screen.findByRole("alertdialog", { name: "Quitar partida" });
    await userEvent.click(within(confirmacion).getByRole("button", { name: "Quitar" }));
    await waitFor(() => expect(escrituras(RUTA_QUITAR)).toHaveLength(1));

    await escribirCantidad(1, "4");
    await new Promise((r) => setTimeout(r, 700)); // pasa la pausa con el quitar en vuelo
    filas = [LLAVE_DEL_ESPACIO];
    quitada.soltar(json({ rev: 1, resumen: resumen({ rev: 1, cambios: 1 }) }));

    await waitFor(() =>
      expect(escrituras(RUTA_CANTIDADES, "PUT")).toEqual([{ rev: 1, filas: [{ clave: LLAVE_DEL_ESPACIO.clave, cantidad: "4" }] }]),
    );
    await waitFor(() => expect(screen.queryByText("Pared de bloques de arcilla de 15 cm")).toBeNull());
    expect(escrituras(RUTA_QUITAR)).toHaveLength(1);
    expect(screen.getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toHaveValue("4");
  });

  // --- Tarea 9 del plan F4: puerta única ---

  const pedidosDeParecidas = () =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === "/v1/similares" && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as unknown);
  const guardadasEnElCatalogo = () =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === "/v1/composicion/guardar" && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as Record<string, unknown>);

  async function abrirComponer(dialogo: HTMLElement, codigo: string) {
    await userEvent.type(within(dialogo).getByRole("combobox", { name: "Partida" }), codigo);
    await userEvent.click(await screen.findByRole("option", { name: `Componer una partida nueva con el código «${codigo}»` }));
    return screen.findByRole("complementary", { name: "Componer una partida" });
  }

  test("«Buscar parecidas» lista las propuestas para lo escrito y «Usar esta partida» la deja elegida", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByRole("combobox", { name: "Partida" }), "excavación de zanja");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Buscar parecidas" }));
    const usar = await within(dialogo).findByRole("button", { name: "Usar esta partida: FIC-01" });
    expect(pedidosDeParecidas()).toEqual([{ descripcion: "excavación de zanja" }]);
    await userEvent.click(usar);

    expect(within(dialogo).getByRole("combobox", { name: "Partida" })).toHaveValue("FIC-01 · Excavación de zanja ficticia a mano");
    const cantidad = within(dialogo).getByRole("textbox", { name: "Cantidad (m3)" });
    await waitFor(() => expect(cantidad).toHaveFocus());
    await userEvent.type(cantidad, "12");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(escrituras(RUTA_AGREGAR)).toEqual([{ rev: 0, codigo: "FIC-01", cantidad: "12", calculo: "", nota: "" }]));
  });

  // Menor 5 del árbitro de la Tarea 9 (cierre de F4): tras elegir del catálogo el campo dice «código · descripción»; lo que se
  // busca por parecido es la descripción, no el código pegado delante.
  test("tras elegir del catálogo, «Buscar parecidas» manda solo la descripción de la partida", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    expect(within(dialogo).getByRole("combobox", { name: "Partida" })).toHaveValue("OBRA-04 · Pared de bloques de arcilla de 15 cm");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Buscar parecidas" }));
    await within(dialogo).findByRole("button", { name: "Usar esta partida: FIC-01" });
    expect(pedidosDeParecidas()).toEqual([{ descripcion: "Pared de bloques de arcilla de 15 cm" }]);
  });

  test("«Componer una partida nueva con el código «Z-99»» abre el panel sin cambiar la ruta, con el aviso del catálogo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    expect(within(panel).getByRole("note")).toHaveTextContent(AVISO_DEL_CATALOGO);
    const titulo = within(panel).getByRole("heading", { level: 2, name: "Componer una partida" });
    await waitFor(() => expect(titulo).toHaveFocus());
    expect(within(panel).queryByRole("heading", { level: 1 })).toBeNull();
    expect(within(panel).getByRole("heading", { name: "Cabecera de la partida" })).toHaveProperty("tagName", "H3");
    expect(within(panel).getByLabelText("Código")).toHaveValue("Z-99");
    expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/hoja$/);
    expect(screen.queryByText("Pantalla de Componer")).toBeNull();
    // Una tarea a la vez: el diálogo espera detrás, oculto, y en la capa del diálogo (la página está inerte) queda a la vista
    // un solo botón principal, el de guardar la composición.
    expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull();
    const principales = within(panel.parentElement!).getAllByRole("button").filter((b) => b.classList.contains("cds--btn--primary"));
    expect(principales.map((b) => b.textContent)).toEqual(["Guardar composición"]);
    // Pasada de navegador del cierre de F4 (H1): con cualquier letra va por encima del velo, fijo bajo la barra y con su
    // propio desplazamiento (la regla es la de `comun/PanelLateral.scss`).
    expect(panel).toHaveClass("silice-panel-lateral--superpuesto");
  });

  // Pulido F5, Tarea 1 (decisión 6 de la Tarea 9 de F4): una descripción escrita en «Partida» no se ofrece como código.
  test("una descripción escrita en «Partida» no se toma como código: Componer abre con ella en «Descripción» y el «Código» vacío", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByRole("combobox", { name: "Partida" }), "excavación de zanja");
    const opcion = await screen.findByRole("option", { name: "Componer una partida nueva con la descripción «excavación de zanja»" });
    expect(screen.queryByRole("option", { name: /con el código/ })).toBeNull();
    await userEvent.click(opcion);
    const panel = await screen.findByRole("complementary", { name: "Componer una partida" });
    expect(within(panel).getByLabelText("Descripción")).toHaveValue("excavación de zanja");
    expect(within(panel).getByRole("combobox", { name: "Código" })).toHaveValue("");
  });

  test("al guardar la composición el panel se cierra, el foco vuelve al diálogo y la partida nueva queda elegida", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    await userEvent.type(within(panel).getByLabelText("Descripción"), "Zanja ficticia");
    await userEvent.type(within(panel).getByLabelText("Unidad"), "m3");
    await userEvent.type(within(panel).getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await userEvent.click(within(panel).getByRole("button", { name: "Guardar composición" }));

    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull());
    expect(guardadasEnElCatalogo()).toHaveLength(1);
    expect(guardadasEnElCatalogo()[0]).toMatchObject({ codigo: "Z-99", descripcion: "Zanja ficticia", unidad: "m3" });
    const otra = screen.getByRole("dialog", { name: "Agregar partida" });
    const partida = within(otra).getByRole("combobox", { name: "Partida" });
    expect(partida).toHaveValue("Z-99 · Zanja ficticia");
    await waitFor(() => expect(partida).toHaveFocus());
    await userEvent.type(within(otra).getByRole("textbox", { name: "Cantidad (m3)" }), "5");
    await userEvent.click(within(otra).getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(escrituras(RUTA_AGREGAR)).toEqual([{ rev: 0, codigo: "Z-99", cantidad: "5", calculo: "", nota: "" }]));
    expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/hoja$/);
  });

  test("componer con algo escrito no pregunta; Esc cierra el panel sin guardar y lo escrito sigue en el diálogo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Nota de medición (opcional)" }), "muro norte");
    const panel = await abrirComponer(dialogo, "OBRA-99");
    expect(screen.queryByRole("button", { name: "Quedarme" })).toBeNull();
    await waitFor(() => expect(within(panel).getByRole("heading", { level: 2, name: "Componer una partida" })).toHaveFocus());

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull());
    const otra = screen.getByRole("dialog", { name: "Agregar partida" });
    expect(within(otra).getByRole("textbox", { name: /^Cantidad/ })).toHaveValue("210");
    expect(within(otra).getByRole("textbox", { name: "Nota de medición (opcional)" })).toHaveValue("muro norte");
    await waitFor(() => expect(within(otra).getByRole("combobox", { name: "Partida" })).toHaveFocus());
    expect(guardadasEnElCatalogo()).toEqual([]);
  });

  // Pulido F5, Tarea 2 (H6 del cierre de F4): del panel al presupuesto hacían falta tres Esc (el panel, el texto de «Partida»,
  // que contaba como elegido, y el diálogo). Un Esc fuera de un campo cierra Componer; dentro de un campo con cambios, el
  // primero restaura el valor (como las celdas de la Hoja) y el segundo cierra.
  const panelDeComponer = () => screen.queryByRole("complementary", { name: "Componer una partida" });

  test("un Esc fuera de un campo cierra Componer con el foco en «Partida», y el siguiente cierra el diálogo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    await waitFor(() => expect(within(panel).getByRole("heading", { level: 2, name: "Componer una partida" })).toHaveFocus());

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(panelDeComponer()).toBeNull());
    const partida = within(screen.getByRole("dialog", { name: "Agregar partida" })).getByRole("combobox", { name: "Partida" });
    await waitFor(() => expect(partida).toHaveFocus());
    expect(partida).toHaveValue("Z-99");

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull());
    await waitFor(() => expect(screen.getByRole("button", { name: "Agregar partida" })).toHaveFocus());
  });

  test("en un campo de Componer con cambios, el primer Esc restaura su valor y el segundo cierra el panel", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    const descripcion = within(panel).getByLabelText("Descripción");
    await userEvent.click(descripcion);
    await userEvent.type(descripcion, "Zanja ficticia");

    await userEvent.keyboard("{Escape}");
    expect(panelDeComponer()).not.toBeNull();
    expect(descripcion).toHaveValue("");
    expect(descripcion).toHaveFocus();

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(panelDeComponer()).toBeNull());
    await waitFor(() => expect(within(screen.getByRole("dialog", { name: "Agregar partida" })).getByRole("combobox", { name: "Partida" })).toHaveFocus());
  });

  test("en un campo de Componer sin cambios, un solo Esc cierra el panel", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    await userEvent.click(within(panel).getByLabelText("Unidad"));
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(panelDeComponer()).toBeNull());
  });

  test("en el «Código» de Componer, Esc cierra primero las sugerencias, luego restaura el código y luego cierra el panel", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    const codigo = within(panel).getByRole("combobox", { name: "Código" });
    await userEvent.click(codigo);
    await userEvent.type(codigo, "0");
    await within(panel).findByRole("listbox", { name: "Código" });

    await userEvent.keyboard("{Escape}");
    expect(within(panel).queryByRole("listbox", { name: "Código" })).toBeNull();
    expect(codigo).toHaveValue("Z-990");

    await userEvent.keyboard("{Escape}");
    expect(panelDeComponer()).not.toBeNull();
    expect(codigo).toHaveValue("Z-99");

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(panelDeComponer()).toBeNull());
  });

  // Dictamen de Claude (xhigh), MAYOR: la descripcion de un insumo llena tambien la unidad y el precio. El Esc del panel
  // restauraba solo la descripcion y dejaba la fila a medias (unidad y precio de un insumo que ya no estaba). Esc con la lista
  // cerrada no borra lo elegido (DESIGN.md, AC1): el panel no restaura ese campo; el primero no hace nada y el siguiente cierra.
  test("en la descripción de un insumo elegido del catálogo, Esc no deja la fila a medias: conserva descripción, unidad y precio", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    await userEvent.click(within(panel).getByRole("button", { name: "Agregar fila a Materiales" }));
    const descripcion = within(panel).getByRole("combobox", { name: "Descripción, fila 1" });
    await userEvent.click(descripcion);
    await userEvent.type(descripcion, "cemento g");
    await userEvent.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(within(panel).getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("18,00"));
    expect(within(panel).getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("saco");

    await userEvent.keyboard("{Escape}");
    expect(panelDeComponer()).not.toBeNull();
    expect(descripcion).toHaveValue("Cemento gris ficticio");
    expect(within(panel).getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("saco");
    expect(within(panel).getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("18,00");

    await userEvent.keyboard("{Escape}"); // el segundo Esc cierra el panel, como en cualquier campo sin cambios
    await waitFor(() => expect(panelDeComponer()).toBeNull());
  });

  test("en la descripción de un insumo, con la lista abierta, Esc solo la cierra; escribir sin elegir sigue siendo texto del campo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    await userEvent.click(within(panel).getByRole("button", { name: "Agregar fila a Materiales" }));
    const descripcion = within(panel).getByRole("combobox", { name: "Descripción, fila 1" });
    await userEvent.click(descripcion);
    await userEvent.type(descripcion, "cemento g");
    await screen.findByRole("listbox");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(panelDeComponer()).not.toBeNull();
    expect(descripcion).toHaveValue("cemento g");
  });

  test("con el panel abierto el foco circula solo dentro del panel (Tab y Mayús+Tab dan la vuelta)", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    const cerrar = within(panel).getByRole("button", { name: "Cerrar" });
    cerrar.focus();
    // Mayús+Tab desde «Cerrar» (el primero) va al último enfocable del panel, no a la página tapada por el velo.
    await userEvent.tab({ shift: true });
    const ultimo = document.activeElement as HTMLElement;
    expect(ultimo).not.toBe(cerrar);
    expect(panel.contains(ultimo)).toBe(true);
    // Tab desde el último vuelve a «Cerrar».
    await userEvent.tab();
    expect(cerrar).toHaveFocus();
  });

  test("con el panel abierto, Mayús+Tab desde el título del panel también va al último enfocable del panel", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const panel = await abrirComponer(dialogo, "Z-99");
    const titulo = within(panel).getByRole("heading", { level: 2, name: "Componer una partida" });
    await waitFor(() => expect(titulo).toHaveFocus());
    await userEvent.tab({ shift: true });
    expect(panel.contains(document.activeElement)).toBe(true);
    expect(document.activeElement).not.toBe(titulo);
  });

  test("cuenta que revisa: no hay puerta (ni «Agregar partida», ni parecidas, ni componer)", async () => {
    // Quien revisa solo ve versiones guardadas: la obra tiene VIV-001 con un renglón.
    conVersion([PARED]);
    montar(SESION_REVISA);
    expect(await screen.findByRole("table", { name: "Presupuesto" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Agregar (la primera )?partida/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Buscar parecidas" })).toBeNull();
    expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull();
  });

  test("estructura: el diálogo oculto no se pinta y, con el panel, el fondo queda bajo los diálogos del marco", () => {
    const hoja = compilar("./hoja.scss");
    expect(hoja).toMatch(/\.silice-hoja__dialogo\[hidden\]\s*\{[^}]*display:\s*none/);
    // H1 de la pasada: entre el fondo y el panel hay un envoltorio `display: contents` (el que atrapa el foco), así que una
    // regla de hijo directo nunca aplicaba; el panel en la capa lo resuelve su propia clase, no una regla de aquí.
    expect(hoja).not.toMatch(/\.silice-hoja__dialogo-fondo--con-panel\s*>\s*\.silice-panel-lateral/);
    const conPanel = /\.silice-hoja__dialogo-fondo--con-panel\s*\{([^}]*)\}/.exec(hoja)?.[1] ?? "";
    const capa = Number(/z-index:\s*(\d+)/.exec(conPanel)?.[1] ?? "NaN");
    // «Precios distintos a los de la lista» (MarcoDeDialogo) se abre desde el panel y tiene que verse encima. Su capa se lee
    // de su hoja de estilos, no se copia aquí (menor 3 de la Tarea 9, cierre de F4): si cambia, esta prueba lo nota.
    const marco = compilar("../../shell/carpetas/MarcoDeDialogo.scss");
    const fondoDelMarco = /\.silice-dialogo__fondo\s*\{([^}]*)\}/.exec(marco)?.[1] ?? "";
    const capaDelMarco = Number(/z-index:\s*(\d+)/.exec(fondoDelMarco)?.[1] ?? "NaN");
    expect(capaDelMarco).toBeGreaterThan(8000);
    expect(capa).toBeLessThan(capaDelMarco);
    expect(capa).toBeGreaterThan(8000);
  });

  test("Esc cierra el diálogo sin mandar nada y el foco vuelve a «Agregar partida»", async () => {
    montar();
    await abrirDialogo();
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull());
    await waitFor(() => expect(screen.getByRole("button", { name: "Agregar partida" })).toHaveFocus());
    expect(escrituras(RUTA_AGREGAR)).toEqual([]);
  });

  test("«Quitar» pide confirmación y solo entonces quita; la fila del espacio no tiene «Quitar»", async () => {
    versiones = { ...SIN_VERSIONES_DE_LA_OBRA, por_omision: "VIV-001", versiones: [{ codigo: "VIV-001", fecha: "2026-10-25", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }] };
    abierto = {
      ...borradorEnBlanco(),
      base: { proyecto: "VIV-80", version: "VIV-001", vigente: "VIV-001", lista: "Lista de la carpeta", espacio_de: "VIV-001", solo_lectura: false, moneda: "Bs" },
    };
    filas = [LLAVE_DEL_ESPACIO, { ...PARED, calculo: "6*35", nota: "6 m × 35 m de muro" }];
    montar();
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    const [, delEspacio, aMano] = within(tabla).getAllByRole("row");
    expect(within(delEspacio!).queryByRole("button", { name: /^Quitar/ })).toBeNull();
    expect(within(delEspacio!).getByText("Sale del espacio")).toBeInTheDocument();
    expect(within(aMano!).getByText("6*35")).toBeInTheDocument();
    expect(within(aMano!).getByText("6 m × 35 m de muro")).toBeInTheDocument();

    const quitar = within(aMano!).getByRole("button", { name: "Quitar OBRA-04, Presupuesto fila 2" });
    await userEvent.click(quitar);
    const confirmacion = await screen.findByRole("alertdialog", { name: "Quitar partida" });
    expect(confirmacion).toHaveAccessibleDescription(CONFIRMAR_QUITAR);
    // Cancelar no quita nada y devuelve el foco al botón de la fila.
    await userEvent.click(within(confirmacion).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(quitar).toHaveFocus());
    expect(escrituras(RUTA_QUITAR)).toEqual([]);

    await userEvent.click(quitar);
    const otra = await screen.findByRole("alertdialog", { name: "Quitar partida" });
    await userEvent.click(within(otra).getByRole("button", { name: "Quitar" }));
    await waitFor(() => expect(escrituras(RUTA_QUITAR)).toEqual([{ rev: 0, clave: "OBRA-04|a-mano:1" }]));
    await waitFor(() => expect(screen.queryByText("Pared de bloques de arcilla de 15 cm")).toBeNull());
    expect(screen.getByText("Se quitó OBRA-04 del presupuesto.")).toBeInTheDocument();
  });

  test("la columna «Cómo se midió» va tras la cantidad y la de «Quitar» al final", async () => {
    filas = [LLAVE_DEL_ESPACIO, PARED];
    abierto = borradorEnBlanco({ espacio_vacio: true });
    montar();
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Cómo se midió",
      "Precio unitario",
      "Objetivo de mercado",
      "Total",
      "Estado",
      "Quitar",
    ]);
    const aMano = within(tabla).getAllByRole("row")[2]!;
    expect(within(aMano).getByText("Sin cálculo")).toBeInTheDocument();
  });

  test("el total de una obra en bolívares dice «Bs» en el estado y en el presupuesto", async () => {
    filas = [PARED];
    abierto = borradorEnBlanco({ total: { texto: "17913.00", exacto: "17913" } });
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    expect(within(screen.getByRole("region", { name: "Estado del borrador" })).getByText(/Total 17\.913,00 Bs/)).toBeInTheDocument();
    expect(screen.getByText("Total del presupuesto").closest("p")).toHaveTextContent("Total del presupuesto 17.913,00 Bs");
  });

  test("un presupuesto vacío dice el mensaje del servidor y ofrece «Agregar partida»", async () => {
    montar();
    expect(await screen.findByText(SIN_RENGLONES)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar partida" })).toBeInTheDocument();
  });
});
