import { renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { caso, estadoInicial, json, ligeras, montarShell, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { EstadoDelServidor, Rol } from "../../shell/obras/datosDePrueba";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios, useFormularioSucio } from "../../shell/sucio";
import PaginaObras from "./index";

// Tarea 19 (con los cambios por el diseno de modulos): «Abrir» un envio del grupo «Aprobar» de la mesa. Un envio de otra
// carpeta pasa por la confirmacion unica de cambiar de carpeta (`confirmarSalida("carpeta", borradores)`, MOD-2) ANTES de
// `POST /v1/aprobaciones/abrir` y luego abre `/aprobar?envio=`; uno de la carpeta abierta no la cambia. La pantalla
// «Aprobar una versión» es de la Tarea 20: aqui se registra una de mentira con la linea que T20 agregara a `rutas.ts` (el
// plan, «Cambios por el diseno de modulos», T20), porque la mesa solo ofrece botones de pantallas que existen. Datos ficticios.
vi.mock("../../shell/rutas", async (importOriginal) => {
  const real = await importOriginal<typeof import("../../shell/rutas")>();
  const aprobar: import("../../shell/rutas").PaginaDef = {
    id: "aprobar",
    titulo: "Aprobar una versión",
    enUnaLinea: "Revise y dé su dictamen sobre una versión",
    seccion: "Revisión",
    accion: "aprobar_version",
    ubicacion: { modulo: "obras", area: "aprobaciones" },
    cargar: async () => ({ default: () => null }),
  };
  const PAGINAS = [...real.PAGINAS, aprobar];
  return {
    ...real,
    PAGINAS,
    paginaPorId: (id: string, paginas: readonly import("../../shell/rutas").PaginaDef[] = PAGINAS) => real.paginaPorId(id, paginas),
    visible: (
      pagina: import("../../shell/rutas").PaginaDef,
      acciones: readonly string[],
      modoEntrega: boolean,
      paginas: readonly import("../../shell/rutas").PaginaDef[] = PAGINAS,
    ) => real.visible(pagina, acciones, modoEntrega, paginas),
  };
});

// La pantalla de aprobar de mentira: dice que envio le pidieron.
function PaginaAprobarFalsa() {
  const { search } = useLocation();
  return (
    <>
      <h1>Aprobar una versión</h1>
      <p>Envío pedido: {search}</p>
    </>
  );
}

const envio = (casoDelEnvio: string, envio_id: number, obra: string, version: string) => ({
  caso: casoDelEnvio,
  envio_id,
  proyecto: "3",
  obra,
  version,
  total: "4876.56",
  moneda: "Bs",
  estado: "en_aprobacion",
  enviado_por: "Ana Pérez <ana>",
  enviado_el: "2026-10-20T09:15:00",
  dictamen_por: null,
  dictamen_el: null,
  nota: "",
  notas: "",
  armo: false,
});
const GALPON_S2 = envio("s2.db", 12, "Galpón Sur", "GS-001");
const CASA_AQUI = envio("silice.db", 4, "Casa Demo", "CD-001");

const RESUMEN = { moneda: "Bs", hoy: "2026-10-26", cifras: [], conversiones: [], fuera_de_suma: [], obras: [] };
const POR_APROBAR = {
  clave: "por_aprobar",
  titulo: "Por aprobar",
  actual: "2",
  meta: "0",
  delta: "4",
  delta_pct: null,
  sentido: "costo",
  detalle: "La más antigua: Galpón Sur GS-001, 4 días hábiles",
  marcada: true,
};
const ver = { texto: "Ver el envío", pagina: "aprobar" };
const PENDIENTES = {
  grupos: [{ clave: "aprobar", titulo: "Aprobar", items: [{ obra: "7", obra_nombre: "Casa Demo", texto: "CD-001 espera dictamen", accion: ver }] }],
};

let servidor: ReturnType<typeof servidorFalso>;
let alAbrirEnvio: (cuerpo: unknown) => Response;

function instalar(estado: EstadoDelServidor = estadoInicial()) {
  alAbrirEnvio = (cuerpo) => {
    const pedido = cuerpo as { caso: string };
    estado.actual = caso(pedido.caso);
    return json({ caso: pedido.caso });
  };
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    if (metodo === "GET" && ruta === "/v1/obras/resumen") return json(RESUMEN);
    if (metodo === "GET" && ruta === "/v1/obras/pendientes") return json(PENDIENTES);
    if (metodo === "GET" && ruta === "/v1/aprobaciones/resumen") return json(POR_APROBAR);
    if (metodo === "GET" && ruta === "/v1/aprobaciones/pendientes") return json([GALPON_S2, CASA_AQUI]);
    if (metodo === "POST" && ruta === "/v1/aprobaciones/abrir") return alAbrirEnvio(cuerpo);
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
  const vista = montarShell(sesionDe(rol), "/obras", ligeras({ obras: PaginaObras, aprobar: PaginaAprobarFalsa }));
  await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
  return vista;
}

// El renglon del envio en el grupo «Aprobar» y su boton «Abrir».
async function abrirDe(version: string) {
  const columna = await screen.findByRole("region", { name: "Pendientes" });
  const texto = await within(columna).findByText(`${version} espera dictamen`);
  return within(texto.closest("li")!).getByRole("button", { name: "Abrir" });
}

const aperturas = () => servidor.de("POST", "/v1/aprobaciones/abrir");
const aprobarAbierta = () => screen.findByRole("heading", { level: 1, name: "Aprobar una versión" });

describe("foco 2: abrir un envío de otra carpeta", () => {
  test("con un borrador con cambios en la Hoja pide la confirmación ANTES de POST /abrir y «Quedarme» no abre nada", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-25T10:00:00" }];
    instalar(estado);
    await montar("ana");
    await u.click(await abrirDe("GS-001"));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Hoja de Casa Demo. Si cambia de carpeta, se perderán.");
    expect(aperturas()).toEqual([]);
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(aperturas()).toEqual([]);
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
  });

  test("«Cambiar y descartar» abre la carpeta del envío (POST /abrir), avisa del cambio y lleva a /aprobar?envio=", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-25T10:00:00" }];
    instalar(estado);
    await montar("ana");
    await u.click(await abrirDe("GS-001"));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Cambiar y descartar" }));
    expect(await aprobarAbierta()).toBeInTheDocument();
    expect(screen.getByText("Envío pedido: ?envio=12")).toBeInTheDocument();
    expect(aperturas().map((l) => l.cuerpo)).toEqual([{ caso: "s2.db", envio_id: 12 }]);
    // Los borradores se leyeron antes de abrir (para nombrarlos en la pregunta).
    const orden = servidor.llamadas.map((l) => `${l.metodo} ${l.ruta}`);
    expect(orden.indexOf("GET /v1/hoja/borradores")).toBeLessThan(orden.indexOf("POST /v1/aprobaciones/abrir"));
    // El armazon sabe que cambio la carpeta: lo dice y no usa la ruta de cambiar carpeta (la abrio la de aprobar).
    expect(await screen.findByText("Ahora trabaja con la carpeta de trabajo «s2».")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
  });

  test("rita (sin borradores que perder) abre el envío de otra carpeta sin preguntar y sin leer borradores", async () => {
    const u = userEvent.setup();
    await montar("rita");
    await u.click(await abrirDe("GS-001"));
    expect(await aprobarAbierta()).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(aperturas().map((l) => l.cuerpo)).toEqual([{ caso: "s2.db", envio_id: 12 }]);
    expect(servidor.de("GET", "/v1/hoja/borradores")).toEqual([]);
  });

  test("rita con un formulario a medio llenar: pregunta antes de abrir la carpeta del envío", async () => {
    const u = userEvent.setup();
    await montar("rita");
    const boton = await abrirDe("GS-001");
    renderHook(() => useFormularioSucio("revisar", true));
    await u.click(boton);
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Revisar un paquete. Si cambia de carpeta, se perderán.");
    expect(aperturas()).toEqual([]);
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(aperturas()).toEqual([]);
  });

  test("un envío de la carpeta abierta no la cambia: sin POST /abrir, directo a /aprobar?envio=", async () => {
    const u = userEvent.setup();
    await montar("rita");
    await u.click(await abrirDe("CD-001"));
    expect(await aprobarAbierta()).toBeInTheDocument();
    expect(screen.getByText("Envío pedido: ?envio=4")).toBeInTheDocument();
    expect(aperturas()).toEqual([]);
  });

  test("si el envío ya no está (404), se dice en la columna y la mesa sigue", async () => {
    const u = userEvent.setup();
    await montar("rita");
    alAbrirEnvio = () => json({ detalle: "No se encontró ese envío." }, 404);
    await u.click(await abrirDe("GS-001"));
    const columna = screen.getByRole("region", { name: "Pendientes" });
    const aviso = await within(columna).findByRole("alert");
    expect(aviso).toHaveTextContent("No se pudo abrir el envío");
    expect(aviso).toHaveTextContent("No se encontró ese envío.");
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
    expect(screen.queryByText("Ahora trabaja con la carpeta de trabajo «s2».")).toBeNull();
  });

  test("el botón se describe con la obra y el envío", async () => {
    await montar("rita");
    expect(await abrirDe("GS-001")).toHaveAccessibleDescription(
      "Galpón Sur GS-001 espera dictamen 4.876,56 Bs · enviada por Ana Pérez el 20/10/2026 · carpeta s2",
    );
  });
});

describe("con la pantalla de aprobar registrada, el «Ver el envío» de la API se ofrece (MOD-4b, decisión 6)", () => {
  test("ana: «Ver el envío» de su carpeta elige la obra y abre la pantalla", async () => {
    const u = userEvent.setup();
    await montar("ana");
    const columna = await screen.findByRole("region", { name: "Pendientes" });
    await u.click(await within(columna).findByRole("button", { name: "Ver el envío" }));
    expect(await aprobarAbierta()).toBeInTheDocument();
    await waitFor(() => expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "7" }]));
    expect(aperturas()).toEqual([]);
  });
});
