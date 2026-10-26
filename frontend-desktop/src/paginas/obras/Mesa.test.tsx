import { renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios, useFormularioSucio } from "../../shell/sucio";
import { json, ligeras, montarShell, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { Rol } from "../../shell/obras/datosDePrueba";
import PaginaObras from "./index";

// Plan de modulos, MOD-4b: la mesa de control, inicio de «Presupuestos y obras» (diseno de modulos §6 y §12.3, §12.6).
// El armazon es el de verdad (selector de obra, «Nueva obra», carpetas, «Cambios sin guardar»); la API es de mentira y
// responde con la forma de `api/rutas/obras.py`. Las cifras son las de la memoria a mano de MOD-4a
// (`tests/unit/test_mesa.py`): A (EV 40.000,00, PV 50.000,00, atrasada 3 dias habiles) y B (EV 30.000,00, PV 25.000,00)
// en Bs; C en USD (EV 100,00, PV 100,00, corte 23/10/2026). Todo es ficticio.

// A y B sumadas; C sin tasa del BCV, fuera de la suma.
const CIFRAS_SIN_TASA = [
  {
    clave: "valor_ganado",
    titulo: "Valor ganado",
    actual: "70000.00",
    meta: "75000.00",
    delta: "-5000.00",
    delta_pct: "-6.7",
    sentido: "rendimiento",
    detalle: null,
  },
  {
    clave: "avance",
    titulo: "Avance contra el plan",
    actual: "0.9333",
    meta: "1.0000",
    delta: "-0.0667",
    delta_pct: null,
    sentido: "rendimiento",
    detalle: "1 obra atrasada; la más atrasada, A: 3 días hábiles",
  },
];

// C convertida con la tasa de 40,00 del 22/10/2026 (la fecha valor de la tasa, un dia antes del corte de C):
// 70.000,00 + 100,00 × 40,00 = 74.000,00; 75.000,00 + 4.000,00 = 79.000,00; -5.000,00 ÷ 79.000,00 × 100 = -6,3 %;
// 74.000,00 ÷ 79.000,00 = 0,9367.
const CIFRAS_CON_TASA = [
  { ...CIFRAS_SIN_TASA[0], actual: "74000.00", meta: "79000.00", delta_pct: "-6.3" },
  { ...CIFRAS_SIN_TASA[1], actual: "0.9367", delta: "-0.0633" },
];

const OB_S2 = {
  codigo: "11",
  nombre: "OB-S2",
  cliente: "Contratista Demo, C.A.",
  etapa: "atrasada",
  etapa_texto: "Atrasada",
  version: "OB-001",
  total: "4876.56",
  moneda: "Bs",
  avance_real: "30.0",
  avance_plan: "37.5",
  que_pasa: "Atrasada 3 días hábiles (SPI 0,80)",
  siguiente: { texto: "Ver las alertas", pagina: "control" },
};
const TORRE_B = {
  codigo: "8",
  nombre: "Torre B",
  cliente: "",
  etapa: "en_elaboracion",
  etapa_texto: "En elaboración",
  version: null,
  total: null,
  moneda: "Bs",
  avance_real: null,
  avance_plan: null,
  que_pasa: null,
  siguiente: { texto: "Abrir la Hoja", pagina: "hoja" },
};
const CASA_DEMO = {
  codigo: "7",
  nombre: "Casa Demo",
  cliente: "Constructora Ficticia, S.A.",
  etapa: "en_aprobacion",
  etapa_texto: "En aprobación",
  version: "CD-001",
  total: "125000.50",
  moneda: "USD",
  avance_real: null,
  avance_plan: null,
  que_pasa: null,
  // La pantalla de aprobar aun no existe en el registro: el boton no se ofrece.
  siguiente: { texto: "Ver el envío", pagina: "aprobar" },
};

function resumen(parcial: Record<string, unknown> = {}) {
  return {
    moneda: "Bs",
    hoy: "2026-10-25",
    cifras: CIFRAS_SIN_TASA,
    conversiones: [],
    fuera_de_suma: ["C"],
    obras: [OB_S2, TORRE_B, CASA_DEMO],
    ...parcial,
  };
}

const item = (obra: string, obra_nombre: string, texto: string, accion: string, pagina: string) => ({
  obra,
  obra_nombre,
  texto,
  accion: { texto: accion, pagina },
});

const PENDIENTES = {
  grupos: [
    { clave: "aprobar", titulo: "Aprobar", items: [item("7", "Casa Demo", "CD-001 espera dictamen", "Ver el envío", "aprobar")] },
    {
      clave: "precios",
      titulo: "Precios",
      items: [
        item("7", "Casa Demo", "Precios de hace 146 días (lista «Base» del 01/06/2026)", "Actualizar precios", "actualizacion"),
        item("7", "Casa Demo", "1 precio sin referencia en CD-001", "Ver el catálogo", "catalogo"),
      ],
    },
    {
      clave: "calidad",
      titulo: "Calidad",
      items: [
        item("7", "Casa Demo", "3 hallazgos de error o críticos en CD-001", "Abrir la Hoja", "hoja"),
        item("7", "Casa Demo", "La lista de CD-001 es 122 días más vieja que la lista para armar.", "Actualizar precios", "actualizacion"),
      ],
    },
  ],
};

type Respuesta = Response | Promise<Response>;
let servidor: ReturnType<typeof servidorFalso>;

// `resumenDe` y `pendientesDe` responden por la mesa; lo demas, el servidor de mentira del armazon.
function instalar(resumenDe: () => Respuesta = () => json(resumen()), pendientesDe: () => Respuesta = () => json(PENDIENTES)) {
  servidor = servidorFalso(undefined, (metodo, ruta) => {
    if (metodo === "GET" && ruta === "/v1/obras/resumen") return resumenDe();
    if (metodo === "GET" && ruta === "/v1/obras/pendientes") return pendientesDe();
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
}

beforeEach(() => {
  instalar();
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

async function montar(rol: Rol) {
  const vista = montarShell(sesionDe(rol), "/obras", ligeras({ obras: PaginaObras }));
  await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
  return vista;
}

const region = (nombre: string) => screen.findByRole("region", { name: nombre });
const filaDe = async (obra: string) => within(await screen.findByRole("table", { name: "Obras de la carpeta de trabajo" })).getByRole("row", { name: new RegExp(obra) });

describe("cifras: valor, meta y desviación juntos (Fiori, IBCS)", () => {
  test("«Valor ganado» con su meta y la variación desfavorable con palabra y flecha", async () => {
    await montar("ana");
    const cifras = await region("Cómo van las obras");
    const valor = await within(cifras).findByRole("group", { name: "Valor ganado" });
    expect(within(valor).getByText("70.000,00")).toBeInTheDocument();
    expect(valor.querySelector(".fiori-kpi__meta")).toHaveTextContent("Meta 75.000,00");
    expect(valor.querySelector(".fiori-kpi__delta-texto")).toHaveTextContent("desfavorable Δ -5.000,00 (-6,7 %)");
    // El color no va solo: la palabra se ve y la flecha baja.
    expect(within(valor).getByText("desfavorable")).toBeVisible();
    expect(valor.querySelector('[data-sentido="baja"]')).not.toBeNull();
  });

  test("«Avance contra el plan» dice cuántas obras van atrasadas y cuál va peor", async () => {
    await montar("ana");
    const cifras = await region("Cómo van las obras");
    const avance = await within(cifras).findByRole("group", { name: "Avance contra el plan" });
    expect(within(avance).getByText("0,9333")).toBeInTheDocument();
    expect(avance.querySelector(".fiori-kpi__meta")).toHaveTextContent("Meta 1,0000");
    expect(within(cifras).getByText("1 obra atrasada; la más atrasada, A: 3 días hábiles")).toBeInTheDocument();
  });

  test("foco 5: una obra sin tasa del BCV se dice aparte y no se suma", async () => {
    await montar("ana");
    const cifras = await region("Cómo van las obras");
    expect(await within(cifras).findByText("Sin tasa del BCV: C no se sumó")).toBeInTheDocument();
  });

  test("foco 5: la conversión se declara con la fecha valor de la tasa, no con la del corte", async () => {
    instalar(() =>
      json(
        resumen({
          cifras: CIFRAS_CON_TASA,
          fuera_de_suma: [],
          conversiones: [{ obra: "C", moneda: "USD", tasa: "40.00", fecha: "2026-10-23", fecha_tasa: "2026-10-22" }],
        }),
      ),
    );
    await montar("ana");
    const cifras = await region("Cómo van las obras");
    const valor = await within(cifras).findByRole("group", { name: "Valor ganado" });
    expect(within(valor).getByText("74.000,00")).toBeInTheDocument();
    expect(within(cifras).getByText("C convertida a Bs con la tasa del BCV de 40,00 del 22/10/2026")).toBeInTheDocument();
    expect(cifras).not.toHaveTextContent("23/10/2026");
    expect(within(cifras).queryByText(/no se sumó/)).toBeNull();
  });
});

describe("la tabla de obras", () => {
  test("OB-S2: etapa, avance, total en es-VE con su moneda, qué pasa y el siguiente paso", async () => {
    await montar("ana");
    const fila = await filaDe("OB-S2");
    expect(within(fila).getByText("Contratista Demo, C.A.")).toBeInTheDocument();
    const etapa = within(fila).getByText("Atrasada");
    // «Atrasada» lleva su icono de advertencia y el texto (no solo color).
    expect(etapa.closest(".silice-mesa__etapa")?.querySelector("svg")).not.toBeNull();
    expect(within(fila).getByText("30,0 % de 37,5 %")).toBeInTheDocument();
    expect(within(fila).getByText("4.876,56 Bs")).toBeInTheDocument();
    expect(within(fila).getByText("Atrasada 3 días hábiles (SPI 0,80)")).toBeInTheDocument();
    expect(within(fila).getByRole("button", { name: "Ver las alertas" })).toBeInTheDocument();
  });

  test("«Ver las alertas» elige la obra (PUT /v1/sesion/proyecto) y abre Control de obra", async () => {
    const u = userEvent.setup();
    await montar("ana");
    await u.click(within(await filaDe("OB-S2")).getByRole("button", { name: "Ver las alertas" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Control de obra" })).toBeInTheDocument();
    expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "11" }]);
  });

  test("«En aprobación» se lee con su texto; su paso («Ver el envío») no se ofrece mientras la pantalla no exista", async () => {
    await montar("ana");
    const fila = await filaDe("Casa Demo");
    expect(within(fila).getByText("En aprobación")).toBeInTheDocument();
    expect(within(fila).getByText("125.000,50 USD")).toBeInTheDocument();
    expect(within(fila).queryByRole("button")).toBeNull();
    expect(screen.queryByRole("button", { name: "Ver el envío" })).toBeNull();
    // Sin avance: lo dice en palabras.
    expect(within(fila).getByText("Sin avance")).toBeInTheDocument();
  });

  test("foco 3: con Componer a medio llenar el botón pregunta y «Quedarme» no navega ni elige obra", async () => {
    const u = userEvent.setup();
    await montar("ana");
    const fila = await filaDe("OB-S2");
    renderHook(() => useFormularioSucio("componer", true));
    await u.click(within(fila).getByRole("button", { name: "Ver las alertas" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Control de obra" })).toBeNull();
    expect(servidor.de("PUT", "/v1/sesion/proyecto")).toEqual([]);
  });
});

describe("pendientes", () => {
  test("grupos en el orden de la API, cada ítem con su obra, su texto y su botón", async () => {
    await montar("ana");
    const columna = await region("Pendientes");
    await within(columna).findByText("1 precio sin referencia en CD-001");
    expect(within(columna).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Aprobar", "Precios", "Calidad"]);
    const precios = within(columna).getByRole("list", { name: "Precios" });
    expect(within(precios).getByText("Precios de hace 146 días (lista «Base» del 01/06/2026)")).toBeInTheDocument();
    expect(within(precios).getByRole("button", { name: "Ver el catálogo" })).toBeInTheDocument();
    expect(within(precios).getByRole("button", { name: "Actualizar precios" })).toBeInTheDocument();
    const calidad = within(columna).getByRole("list", { name: "Calidad" });
    expect(within(calidad).getByText("3 hallazgos de error o críticos en CD-001")).toBeInTheDocument();
    expect(within(calidad).getByText("La lista de CD-001 es 122 días más vieja que la lista para armar.")).toBeInTheDocument();
    expect(within(calidad).getByRole("button", { name: "Abrir la Hoja" })).toBeInTheDocument();
    expect(within(calidad).getAllByText("Casa Demo")).toHaveLength(2);
    // «Aprobar» sale primero; su accion lleva a una pantalla que aun no existe: el texto sin boton.
    const aprobar = within(columna).getByRole("list", { name: "Aprobar" });
    expect(within(aprobar).getByText("CD-001 espera dictamen")).toBeInTheDocument();
    expect(within(aprobar).queryByRole("button")).toBeNull();
  });

  test("la acción de un pendiente elige su obra y abre su pantalla", async () => {
    const u = userEvent.setup();
    await montar("ana");
    const columna = await region("Pendientes");
    await u.click(await within(columna).findByRole("button", { name: "Ver el catálogo" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Catálogo de partidas e insumos" })).toBeInTheDocument();
    expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "7" }]);
  });

  test("con todos los grupos vacíos: «Nada pendiente por ahora.»", async () => {
    instalar(undefined, () =>
      json({ grupos: [{ clave: "aprobar", titulo: "Aprobar", items: [] }, { clave: "precios", titulo: "Precios", items: [] }, { clave: "calidad", titulo: "Calidad", items: [] }] }),
    );
    await montar("ana");
    const columna = await region("Pendientes");
    expect(await within(columna).findByText("Nada pendiente por ahora.")).toBeInTheDocument();
    expect(within(columna).queryByRole("heading", { level: 3 })).toBeNull();
  });
});

describe("foco 5: cada bloque según lo que la cuenta puede leer", () => {
  test("rita: no se piden los pendientes; cifras y obras sí, sin «Siguiente paso» ni «Nueva obra»", async () => {
    await montar("rita");
    await filaDe("OB-S2");
    expect(await region("Cómo van las obras")).toBeInTheDocument();
    expect(servidor.de("GET", "/v1/obras/resumen")).toHaveLength(1);
    expect(servidor.de("GET", "/v1/obras/pendientes")).toEqual([]);
    expect(screen.queryByRole("region", { name: "Pendientes" })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: /Siguiente paso/ })).toBeNull();
    expect(within(screen.getByRole("main")).queryByRole("button", { name: "Nueva obra" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ver las alertas" })).toBeNull();
  });

  test("ana ve la columna «Siguiente paso» y «Nueva obra» (botón principal)", async () => {
    await montar("ana");
    await filaDe("OB-S2");
    expect(screen.getByRole("columnheader", { name: /Siguiente paso/ })).toBeInTheDocument();
    expect(within(screen.getByRole("main")).getByRole("button", { name: "Nueva obra" })).toHaveClass("cds--btn--primary");
  });

  test("un 403 del resumen oculta «Cómo van las obras» y «Obras» (no los pinta vacíos)", async () => {
    instalar(() => json({ detalle: "Su cuenta no puede hacer esto." }, 403));
    await montar("rita");
    await waitFor(() => expect(servidor.de("GET", "/v1/obras/resumen")).toHaveLength(1));
    await new Promise((r) => setTimeout(r, 30));
    expect(screen.queryByRole("heading", { level: 2, name: "Cómo van las obras" })).toBeNull();
    expect(screen.queryByRole("heading", { level: 2, name: "Obras" })).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    // La pagina no queda en blanco: quedan los accesos de su modulo.
    const accesos = await region("Lo que puede hacer aquí");
    expect(within(accesos).getByRole("link", { name: "Tablero del proyecto" })).toBeInTheDocument();
  });

  test("admin: solo «Lo que puede hacer aquí» con «Precios de la empresa» e «Índices del BCV»; no pide la mesa", async () => {
    await montar("admin");
    const accesos = await region("Lo que puede hacer aquí");
    expect(within(accesos).getByRole("link", { name: "Precios de la empresa" })).toBeInTheDocument();
    expect(within(accesos).getByRole("link", { name: "Índices del BCV" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Cómo van las obras" })).toBeNull();
    expect(screen.queryByRole("heading", { level: 2, name: "Pendientes" })).toBeNull();
    expect(servidor.llamadas.filter((l) => l.ruta.startsWith("/v1/obras/"))).toEqual([]);
  });

  test("un 500 en pendientes muestra el aviso en esa columna y las cifras siguen", async () => {
    instalar(undefined, () => json({ detalle: "No se pudo leer la carpeta de trabajo. Intente de nuevo." }, 500));
    await montar("ana");
    const columna = await region("Pendientes");
    const aviso = await within(columna).findByRole("alert");
    expect(aviso).toHaveTextContent("No se pudo leer la carpeta de trabajo. Intente de nuevo.");
    const cifras = await region("Cómo van las obras");
    expect(await within(cifras).findByRole("group", { name: "Valor ganado" })).toBeInTheDocument();
    expect(within(cifras).queryByRole("alert")).toBeNull();
  });

  test("un 503 del resumen muestra el aviso en su bloque y los pendientes siguen", async () => {
    instalar(() => json({ detalle: "No se pudo leer la carpeta de trabajo. Intente de nuevo." }, 503));
    await montar("ana");
    const obras = await region("Obras");
    expect(await within(obras).findByRole("alert")).toHaveTextContent("No se pudo leer la carpeta de trabajo. Intente de nuevo.");
    expect(await within(await region("Pendientes")).findByText("1 precio sin referencia en CD-001")).toBeInTheDocument();
  });
});

describe("sin obras: el vacío enseña qué hacer", () => {
  const SIN_OBRAS = () => json(resumen({ moneda: null, cifras: [], fuera_de_suma: [], obras: [] }));
  const VACIO = "Todavía no hay obras en esta carpeta de trabajo.";

  test("ana: el texto exacto y los dos botones; «Cree su primera obra» abre «Nueva obra»", async () => {
    const u = userEvent.setup();
    instalar(SIN_OBRAS);
    await montar("ana");
    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Probar con datos de demostración" })).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Cree su primera obra" }));
    expect(await screen.findByRole("dialog", { name: "Nueva obra" })).toBeInTheDocument();
  });

  test("«Probar con datos de demostración» estrena la demostración y la abre por el armazón", async () => {
    const u = userEvent.setup();
    instalar(SIN_OBRAS);
    await montar("ana");
    await u.click(await screen.findByRole("button", { name: "Probar con datos de demostración" }));
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/demostracion")).toHaveLength(1));
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "demostracion.db" }]));
  });

  test("rita: solo el texto, sin botones", async () => {
    instalar(SIN_OBRAS);
    await montar("rita");
    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cree su primera obra" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Probar con datos de demostración" })).toBeNull();
  });
});

describe("cargando y forma", () => {
  test("mientras llega el resumen: esqueleto con la forma final y ninguna cifra", async () => {
    instalar(() => new Promise<Response>(() => {}), () => new Promise<Response>(() => {}));
    await montar("ana");
    expect(await screen.findByRole("status", { name: "Cargando las cifras de las obras" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Cargando las obras" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Cargando los pendientes" })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Valor ganado" })).toBeNull();
    expect(screen.queryByText(/70\.000,00/)).toBeNull();
  });

  test("un solo h1", async () => {
    await montar("ana");
    await filaDe("OB-S2");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

// Prueba de fuente (como `sinJergaInterna.test.ts`): la mesa no convierte montos en numeros.
interface Fs {
  readdirSync(carpeta: string): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;

describe("sin conversión a número", () => {
  test("ningún archivo de la mesa convierte un texto en número", () => {
    const fs = nodo.getBuiltinModule("node:fs");
    const carpeta = `${nodo.cwd()}/src/paginas/obras`;
    const fuentes = fs.readdirSync(carpeta).filter((r) => /\.tsx?$/.test(r));
    expect(fuentes).toEqual(expect.arrayContaining(["index.tsx", "logica.ts", "CifrasMesa.tsx", "TablaObras.tsx", "ColumnaPendientes.tsx"]));
    // La aguja se arma por partes para que este mismo archivo no la contenga.
    const aguja = new RegExp(["\\bNumber\\s*\\(", "parse" + "Float", "parse" + "Int"].join("|"));
    const conNumero = fuentes.filter((r) => aguja.test(fs.readFileSync(`${carpeta}/${r}`, "utf-8")));
    expect(conNumero).toEqual([]);
  });
});
