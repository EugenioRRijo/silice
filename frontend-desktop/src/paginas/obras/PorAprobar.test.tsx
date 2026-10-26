import { renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { botonDeObra, caso, estadoInicial, json, ligeras, montarShell, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { EstadoDelServidor, Rol } from "../../shell/obras/datosDePrueba";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios, useFormularioSucio } from "../../shell/sucio";
import PaginaAprobar from "../aprobar";
import PaginaObras from "./index";

// Tarea 19 (con los cambios por el diseno de modulos): «Abrir» un envio del grupo «Aprobar» de la mesa. Un envio de otra
// carpeta pasa por la confirmacion unica de cambiar de carpeta (`confirmarSalida("carpeta", borradores)`, MOD-2) ANTES de
// `POST /v1/aprobaciones/abrir` y luego abre `/aprobar?envio=`; uno de la carpeta abierta no la cambia. Desde la Tarea 20
// la pantalla «Aprobar una versión» esta en el registro real (`rutas.ts`): ya no se simula. Datos ficticios.
const envio = (casoDelEnvio: string, envio_id: number, obra: string, version: string, proyecto = "3") => ({
  caso: casoDelEnvio,
  envio_id,
  proyecto,
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
// La obra 7 de la carpeta abierta: la API de pendientes tambien la dice («CD-001 espera dictamen»).
const CASA_AQUI = envio("silice.db", 4, "Casa Demo", "CD-001", "7");

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

// Lo que la pantalla real de aprobar lee de un envío (`GET /v1/aprobaciones/{id}`, Tarea 18).
function detalleDe(envio_id: number, obra: string, version: string, proyecto: string) {
  return {
    envio_id,
    proyecto,
    obra,
    version,
    estado: "en_aprobacion",
    moneda: "Bs",
    total: "4876.56",
    partidas: [],
    hallazgos: { error: 0, advertencia: 0, info: 0, lista: [] },
    rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
    cadena: { integra: true, mensaje: "Cadena íntegra." },
    envio: { por: "Ana Pérez <ana>", el: "2026-10-20T09:15:00", nota: "" },
    armo: false,
  };
}
// El rastro de Casa Demo (`GET /v1/aprobaciones?proyecto=7`): su envío n.º 4 de CD-001 sigue abierto.
const RASTRO_CASA = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "CD-001 en aprobación",
  versiones: { "CD-001": { estado: "en_aprobacion", por: "Ana Pérez <ana>", el: "2026-10-20T09:15:00", notas: "", armo: false } },
  eventos: [{ id: 4, tipo: "envio", version: "CD-001", resultado: null, notas: "", por: "Ana Pérez <ana>", el: "2026-10-20T09:15:00", armo: false, cierre_de: null }],
};

let servidor: ReturnType<typeof servidorFalso>;
let alAbrirEnvio: (cuerpo: unknown) => Response;
let enviosDe: () => Response;

function instalar(estado: EstadoDelServidor = estadoInicial()) {
  enviosDe = () => json([GALPON_S2, CASA_AQUI]);
  alAbrirEnvio = (cuerpo) => {
    const pedido = cuerpo as { caso: string };
    estado.actual = caso(pedido.caso);
    return json({ caso: pedido.caso });
  };
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    if (metodo === "GET" && ruta === "/v1/obras/resumen") return json(RESUMEN);
    if (metodo === "GET" && ruta === "/v1/obras/pendientes") return json(PENDIENTES);
    if (metodo === "GET" && ruta === "/v1/aprobaciones/resumen") return json(POR_APROBAR);
    if (metodo === "GET" && ruta === "/v1/aprobaciones/pendientes") return enviosDe();
    if (metodo === "POST" && ruta === "/v1/aprobaciones/abrir") return alAbrirEnvio(cuerpo);
    // La pantalla real de aprobar lee el envío pedido (de la carpeta que tenga abierta el servidor).
    if (metodo === "GET" && ruta === "/v1/aprobaciones/12") return json(detalleDe(12, "Galpón Sur", "GS-001", "3"));
    if (metodo === "GET" && ruta === "/v1/aprobaciones/4") return json(detalleDe(4, "Casa Demo", "CD-001", "7"));
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
  const vista = montarShell(sesionDe(rol), "/obras", ligeras({ obras: PaginaObras, aprobar: PaginaAprobar }));
  await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
  return vista;
}

// El renglon del envio en el grupo «Aprobar» y su boton «Abrir el envío» (el mismo verbo para toda fila del grupo).
async function abrirDe(version: string) {
  const columna = await screen.findByRole("region", { name: "Pendientes" });
  const texto = await within(columna).findByText(`${version} espera dictamen`);
  return within(texto.closest("li")!).getByRole("button", { name: "Abrir el envío" });
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

  test("«Cambiar y descartar» abre la carpeta del envío (POST /abrir), la barra dice la carpeta nueva y lleva a /aprobar?envio=", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-25T10:00:00" }];
    instalar(estado);
    await montar("ana");
    await u.click(await abrirDe("GS-001"));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Cambiar y descartar" }));
    expect(await aprobarAbierta()).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Galpón Sur · GS-001" })).toBeInTheDocument();
    expect(aperturas().map((l) => l.cuerpo)).toEqual([{ caso: "s2.db", envio_id: 12 }]);
    // Los borradores se leyeron antes de abrir (para nombrarlos en la pregunta).
    const orden = servidor.llamadas.map((l) => `${l.metodo} ${l.ruta}`);
    expect(orden.indexOf("GET /v1/hoja/borradores")).toBeLessThan(orden.indexOf("POST /v1/aprobaciones/abrir"));
    // El armazon sabe que cambio la carpeta: vuelve a leerla despues de abrir el envio (su aviso es de la pantalla en que se
    // cambio y se cierra al navegar, D6) y no usa la ruta de cambiar carpeta (la abrio la de aprobar).
    await waitFor(() => {
      const despues = servidor.llamadas.map((l) => `${l.metodo} ${l.ruta}`);
      expect(despues.lastIndexOf("GET /v1/casos")).toBeGreaterThan(despues.indexOf("POST /v1/aprobaciones/abrir"));
    });
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    // Menor del arbitro de T19: el pie del selector de obra de la barra dice la carpeta del envio.
    await u.click(await botonDeObra());
    const panel = await within(screen.getByRole("banner")).findByRole("region", { name: "Obra" });
    expect(await within(panel).findByText("Carpeta: s2")).toBeInTheDocument();
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
    expect(await screen.findByRole("region", { name: "Casa Demo · CD-001" })).toBeInTheDocument();
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

describe("con la pantalla de aprobar registrada, las filas de la carpeta abierta (MOD-4b, decisión 6)", () => {
  test("ana: la fila de su carpeta sale del índice y «Abrir el envío» va directo a /aprobar?envio=, sin cambiar de carpeta", async () => {
    const u = userEvent.setup();
    await montar("ana");
    const columna = await screen.findByRole("region", { name: "Pendientes" });
    // La de la API no se repite ni ofrece otro verbo.
    expect(within(columna).queryByRole("button", { name: "Ver el envío" })).toBeNull();
    expect(await within(columna).findAllByText("CD-001 espera dictamen")).toHaveLength(1);
    await u.click(await abrirDe("CD-001"));
    expect(await aprobarAbierta()).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Casa Demo · CD-001" })).toBeInTheDocument();
    expect(aperturas()).toEqual([]);
  });

  test("ana sin el índice (403): la fila de la API dice «Abrir el envío», elige la obra y la pantalla real resuelve su envío", async () => {
    const u = userEvent.setup();
    enviosDe = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
    // T19, punto 5: sin `envio_id` ni índice, la pantalla de aprobar busca el envío en aprobación de la obra elegida en su
    // rastro (`GET /v1/aprobaciones?proyecto=`).
    const respondedor = servidor;
    servidor = servidorFalso(respondedor.estado, (metodo, ruta, cuerpo) => {
      if (metodo === "GET" && ruta === "/v1/aprobaciones?proyecto=7") return json(RASTRO_CASA);
      if (metodo === "GET" && ruta === "/v1/aprobaciones/4") return json(detalleDe(4, "Casa Demo", "CD-001", "7"));
      if (metodo === "GET" && ruta === "/v1/obras/resumen") return json(RESUMEN);
      if (metodo === "GET" && ruta === "/v1/obras/pendientes") return json(PENDIENTES);
      if (metodo === "GET" && ruta === "/v1/aprobaciones/resumen") return json(POR_APROBAR);
      if (metodo === "GET" && ruta === "/v1/aprobaciones/pendientes") return enviosDe();
      if (metodo === "POST" && ruta === "/v1/aprobaciones/abrir") return alAbrirEnvio(cuerpo);
      return undefined;
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/obras", ligeras({ obras: PaginaObras, aprobar: PaginaAprobar }));
    await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
    const columna = await screen.findByRole("region", { name: "Pendientes" });
    const boton = await within(columna).findByRole("button", { name: "Abrir el envío" });
    expect(within(columna).queryByRole("button", { name: "Ver el envío" })).toBeNull();
    await u.click(boton);
    expect(await aprobarAbierta()).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Casa Demo · CD-001" })).toBeInTheDocument();
    expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "7" }]);
    expect(aperturas()).toEqual([]);
  });
});

describe("T20: «Abrir el envío» lleva a la pantalla real de aprobar", () => {
  test("rita abre el envío de otra carpeta y la pantalla de aprobar lo lee y dice su carpeta", async () => {
    const u = userEvent.setup();
    const detalles: string[] = [];
    const estado = estadoInicial();
    servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
      if (metodo === "GET" && ruta === "/v1/obras/resumen") return json(RESUMEN);
      if (metodo === "GET" && ruta === "/v1/obras/pendientes") return json(PENDIENTES);
      if (metodo === "GET" && ruta === "/v1/aprobaciones/resumen") return json(POR_APROBAR);
      if (metodo === "GET" && ruta === "/v1/aprobaciones/pendientes") return json([GALPON_S2, CASA_AQUI]);
      if (metodo === "POST" && ruta === "/v1/aprobaciones/abrir") {
        estado.actual = caso((cuerpo as { caso: string }).caso);
        return json({ caso: estado.actual.nombre });
      }
      if (metodo === "GET" && ruta === "/v1/aprobaciones/12") {
        detalles.push(ruta);
        return json(detalleDe(12, "Galpón Sur", "GS-001", "3"));
      }
      return undefined;
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("rita"), "/obras", ligeras({ obras: PaginaObras, aprobar: PaginaAprobar }));
    await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
    await u.click(await abrirDe("GS-001"));
    expect(await aprobarAbierta()).toBeInTheDocument();
    const envio = await screen.findByRole("region", { name: "Galpón Sur · GS-001" });
    expect(within(envio).getByText("s2")).toBeInTheDocument();
    expect(detalles).toEqual(["/v1/aprobaciones/12"]);
    expect(aperturas().map((l) => l.cuerpo)).toEqual([{ caso: "s2.db", envio_id: 12 }]);
  });
});
