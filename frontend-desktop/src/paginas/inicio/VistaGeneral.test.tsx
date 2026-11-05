import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { Marco } from "../../marco/Marco";
import { caso, estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { EstadoDelServidor, Respondedor } from "../../shell/obras/datosDePrueba";
import { PAGINAS } from "../../shell/rutas";
import type { PaginaDef } from "../../shell/rutas";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";

// F6, T8: la Vista general (`#/inicio/general`), dentro del marco de verdad y con la API de mentira. Las respuestas
// tienen la forma de `GET /v1/obras/resumen/todas` (T7) y de `GET /v1/obras/pendientes/todas`; la interfaz solo las
// formatea. Oráculos escritos a mano: obras, carpetas y cifras ficticias, y los textos que fijan el plan y el diseño visual.

const RUTA_CARTERA = "/v1/obras/resumen/todas";
const RUTA_PENDIENTES = "/v1/obras/pendientes/todas";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";
const RUTA_ARENERA = "/v1/produccion/existencias";
const SUR = "Carpeta Sur.db";

interface Pendiente {
  carpeta: string | null;
  obra_id: number;
  obra: string;
  grupo: string;
  urgencia: "bloquea" | "aviso";
  texto: string;
  accion: { texto: string; pagina: string };
}

const CEMENTO: Pendiente = {
  carpeta: null,
  obra_id: 7,
  obra: "Casa Demo",
  grupo: "compras",
  urgencia: "bloquea",
  texto: "Falta pedir el cemento",
  accion: { texto: "Abrir el presupuesto", pagina: "hoja" },
};
const DEVUELTA: Pendiente = {
  carpeta: SUR,
  obra_id: 3,
  obra: "Galpón Sur",
  grupo: "aprobar",
  urgencia: "bloquea",
  texto: "V2 devuelta con observaciones",
  accion: { texto: "Hacer una versión nueva", pagina: "hoja" },
};
const PRECIOS: Pendiente = {
  carpeta: null,
  obra_id: 8,
  obra: "Torre B",
  grupo: "precios",
  urgencia: "aviso",
  texto: "3 precios con más de 90 días",
  accion: { texto: "Actualizar precios", pagina: "actualizacion" },
};

// Una cartera con las dos monedas. Los montos llegan como texto, y uno llega sin el cero final: la pantalla los lee
// en centésimas y no recalcula nada (la suma de Bs con USD sería 429.637,10: no debe aparecer jamás).
const DOS_MONEDAS = {
  hoy: "2026-11-05",
  por_moneda: [
    { moneda: "Bs", obras: 2, total: "334570.5", en_ejecucion: 1 },
    { moneda: "USD", obras: 1, total: "95066.6", en_ejecucion: 0 },
  ],
  obras: [
    {
      carpeta: null,
      carpeta_titulo: "Carpeta de la empresa",
      obra_id: 7,
      nombre: "Casa Demo",
      moneda: "Bs",
      etapa: "en_ejecucion",
      total: "334570.5",
      avance_real: "62.5",
      avance_plan: "70.0",
    },
    {
      carpeta: null,
      carpeta_titulo: "Carpeta de la empresa",
      obra_id: 8,
      nombre: "Torre B",
      moneda: "Bs",
      etapa: "en_elaboracion",
      total: null,
      avance_real: null,
      avance_plan: null,
    },
    {
      carpeta: SUR,
      carpeta_titulo: "Carpeta Sur",
      obra_id: 3,
      nombre: "Galpón Sur",
      moneda: "USD",
      etapa: "atrasada",
      total: "95066.6",
      avance_real: "10.0",
      avance_plan: "25.5",
    },
  ],
  carpetas_omitidas: 0,
};
const SOLO_BS = {
  ...DOS_MONEDAS,
  por_moneda: [DOS_MONEDAS.por_moneda[0]],
  obras: DOS_MONEDAS.obras.slice(0, 2),
};
const SIN_OBRAS = { hoy: "2026-11-05", por_moneda: [], obras: [], carpetas_omitidas: 0 };

const AUDITORIA = { id: 1, archivo: "presupuesto-1.xlsx", fecha: "2026-10-18T14:32:00", tipo: "libro", errores: 2, advertencias: 5 };

let servidor: ReturnType<typeof servidorFalso>;
let cartera: Respondedor;
let pendientes: Respondedor;
let auditorias: Respondedor;
let apagados: string[];

const lista = (...p: Pendiente[]): Respondedor => () => json({ pendientes: p, carpetas_omitidas: 0 });

function instalar() {
  const estado: EstadoDelServidor = estadoInicial();
  estado.casos = [...estado.casos, caso(SUR)];
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    if (metodo !== "GET") return undefined;
    if (ruta === RUTA_CARTERA) return cartera(metodo, ruta, cuerpo);
    if (ruta === RUTA_PENDIENTES) return pendientes(metodo, ruta, cuerpo);
    if (ruta === RUTA_AUDITORIAS) return auditorias(metodo, ruta, cuerpo);
    if (ruta === RUTA_ARENERA) return json([]);
    if (ruta === "/v1/modulos") {
      const claves = ["produccion", "vial", "riesgo", "edificacion"];
      return json({ modulos: claves.map((clave) => ({ clave, nombre: clave, activo: !apagados.includes(clave), cambiado_por: null, cambiado_el: null })) });
    }
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
}

beforeEach(() => {
  apagados = [];
  cartera = () => json(DOS_MONEDAS);
  pendientes = lista(CEMENTO, DEVUELTA, PRECIOS);
  auditorias = () => json([AUDITORIA]);
  instalar();
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <output data-testid="ruta">{`${pathname}${search}`}</output>;
}
const ruta = () => screen.getByTestId("ruta").textContent;
function IrA({ destino }: { destino: string }) {
  const navegar = useNavigate();
  return <button onClick={() => navegar(destino)}>{`Ir a ${destino}`}</button>;
}

// El registro de pantallas ligeras, pero con la Vista general de verdad: la que `shell/rutas.ts` registra como «inicio».
function conVistaGeneral(): PaginaDef[] {
  const real = PAGINAS.find((p) => p.id === "inicio");
  if (!real) throw new Error("Falta la pantalla «inicio» (la Vista general) en el registro de shell/rutas.ts.");
  return ligeras().map((p) => (p.id === "inicio" ? { ...p, cargar: real.cargar } : p));
}

function montar({ sesion = sesionDe("ana"), en = "/inicio/general", ir }: { sesion?: SesionRespuesta; en?: string; ir?: string } = {}) {
  return render(
    <MemoryRouter initialEntries={[en]}>
      <Marco sesion={sesion} alSalir={vi.fn()} alExpirar={vi.fn()} paginas={conVistaGeneral()} />
      <Ubicacion />
      {ir && <IrA destino={ir} />}
    </MemoryRouter>,
  );
}

const bloque = (nombre: string) => screen.findByRole("region", { name: nombre }, { timeout: 3000 });
const pedidas = (r: string) => servidor.de("GET", r).length;

describe("Vista general: el orden de los bloques", () => {
  test("lo que bloquea va primero, después la cartera, el avance, las auditorías y la arenera", async () => {
    montar();
    await bloque("Cartera por moneda");
    await screen.findByText("presupuesto-1.xlsx");
    await bloque("Arenera: lo que requiere atención");
    const titulos = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    const propios = titulos.filter((t) =>
      ["Lo que requiere atención", "Cartera por moneda", "Obras y avance contra el plan", "Últimas auditorías", "Arenera: lo que requiere atención"].includes(t ?? ""),
    );
    expect(propios).toEqual([
      "Lo que requiere atención",
      "Cartera por moneda",
      "Obras y avance contra el plan",
      "Últimas auditorías",
      "Arenera: lo que requiere atención",
    ]);
  });

  test("un solo h1 «Vista general», y la barra del espacio ofrece Vista general (actual) y Pendientes", async () => {
    montar();
    await bloque("Cartera por moneda");
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1).toHaveLength(1);
    expect(h1[0]).toHaveTextContent("Vista general");
    expect(h1[0]).toHaveClass("cds--type-heading-04");
    const barra = screen.getByRole("navigation", { name: "Inicio" });
    expect(within(barra).getByRole("link", { name: "Vista general" })).toHaveAttribute("aria-current", "page");
    expect(within(barra).getByRole("link", { name: "Pendientes" })).not.toHaveAttribute("aria-current");
  });
});

describe("Vista general: lo que bloquea", () => {
  test("cada pendiente dice su urgencia con palabras, su obra y el paso que lleva a hacerlo", async () => {
    montar();
    const b = await bloque("Lo que requiere atención");
    await within(b).findByText("Falta pedir el cemento");
    expect(within(b).getByText("2 bloquean · 1 aviso")).toBeInTheDocument();
    expect(within(b).getAllByText("Bloquea")).toHaveLength(2);
    expect(within(b).getAllByText("Aviso")).toHaveLength(1);
    expect(within(b).getByText("Casa Demo")).toBeInTheDocument();
    expect(within(b).getByRole("link", { name: "Abrir el presupuesto" })).toHaveAttribute("href", "/obra/empresa/7/presupuesto");
    // Una acción de otra carpeta lleva a la obra de esa carpeta.
    expect(within(b).getByRole("link", { name: "Hacer una versión nueva" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/presupuesto");
    expect(within(b).getByRole("link", { name: "Actualizar precios" })).toHaveAttribute("href", "/obra/empresa/8/mercado/actualizar");
  });

  test("solo los primeros cinco; el pie lleva a la bandeja con el total", async () => {
    const seis = [CEMENTO, DEVUELTA, { ...CEMENTO, texto: "Falta pedir la cabilla" }, PRECIOS, { ...PRECIOS, texto: "Faltan 2 cotizaciones" }, { ...PRECIOS, texto: "Revisar el flete" }];
    pendientes = lista(...seis);
    montar();
    const b = await bloque("Lo que requiere atención");
    await within(b).findByText("Falta pedir el cemento");
    expect(within(b).queryByText("Revisar el flete")).toBeNull();
    expect(within(b).getByText("Faltan 2 cotizaciones")).toBeInTheDocument();
    expect(within(b).getByRole("link", { name: "Ir a la bandeja de pendientes (6)" })).toHaveAttribute("href", "/inicio/pendientes");
  });

  test("sin pendientes dice, en una línea, que no hay nada por hacer", async () => {
    pendientes = lista();
    montar();
    const b = await bloque("Lo que requiere atención");
    expect(await within(b).findByText("No tiene pendientes por hacer.")).toBeInTheDocument();
    expect(within(b).queryByRole("link", { name: /bandeja/ })).toBeNull();
  });
});

describe("Vista general: la cartera por moneda, sin recalcular y sin mezclar", () => {
  test("cada cifra sale de la respuesta tal cual: «334570.5» se ve como 334.570,50", async () => {
    montar();
    const bs = await bloque("Cartera en Bs");
    expect(within(bs).getByText("Obras en Bs")).toBeInTheDocument();
    expect(within(bs).getByText("334.570,50 Bs")).toBeInTheDocument();
    expect(within(bs).getByText("2")).toBeInTheDocument(); // obras
    expect(within(bs).getByText("1")).toBeInTheDocument(); // en ejecución
    const usd = await bloque("Cartera en USD");
    expect(within(usd).getByText("Obras en USD")).toBeInTheDocument();
    expect(within(usd).getByText("95.066,60 USD")).toBeInTheDocument();
  });

  test("con dos monedas no aparece ninguna suma de Bs con USD, ni una moneda dentro de la otra", async () => {
    montar();
    const bs = await bloque("Cartera en Bs");
    const usd = await bloque("Cartera en USD");
    // 334.570,50 + 95.066,60 = 429.637,10: esa cifra no existe en ninguna parte.
    expect(document.body.textContent).not.toContain("429.637");
    expect(document.body.textContent).not.toContain("429637");
    expect(bs.textContent).not.toContain("USD");
    expect(usd.textContent).not.toContain("Bs");
    // Y no hay una tarjeta «Total» que mezcle las dos.
    expect(screen.queryByRole("region", { name: /^Cartera en (?!Bs$|USD$)/ })).toBeNull();
  });

  test("con una sola moneda se pinta solo esa: ni tarjeta vacía ni ceros para la otra", async () => {
    cartera = () => json(SOLO_BS);
    montar();
    await bloque("Cartera en Bs");
    expect(screen.queryByRole("region", { name: "Cartera en USD" })).toBeNull();
    expect(document.body.textContent).not.toContain("0,00");
  });

  test("carpetas_omitidas > 0 se le dice a la persona en español llano", async () => {
    cartera = () => json({ ...DOS_MONEDAS, carpetas_omitidas: 2 });
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("No se pudieron leer 2 carpetas; sus obras no aparecen en la cartera.")).toBeInTheDocument();
  });

  test("una carpeta omitida se dice en singular", async () => {
    cartera = () => json({ ...DOS_MONEDAS, carpetas_omitidas: 1 });
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("No se pudo leer 1 carpeta; sus obras no aparecen en la cartera.")).toBeInTheDocument();
  });

  test("sin carpetas omitidas no hay aviso", async () => {
    montar();
    await bloque("Cartera en Bs");
    expect(screen.queryByText(/No se pudo(ieron)? leer/)).toBeNull();
  });
});

describe("Vista general: el avance ejecutado contra el plan, por obra", () => {
  const tabla = async () => within(await bloque("Obras y avance contra el plan"));

  test("cada obra dice su etapa, su total y el avance real contra el plan", async () => {
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa).toHaveTextContent("En ejecución");
    expect(casa).toHaveTextContent("334.570,50 Bs");
    expect(casa).toHaveTextContent("Real 62,5 % · Plan 70,0 %");
    const galpon = t.getByRole("link", { name: "Galpón Sur" }).closest("tr")!;
    expect(galpon).toHaveTextContent("Atrasada");
    expect(galpon).toHaveTextContent("95.066,60 USD");
    expect(galpon).toHaveTextContent("Real 10,0 % · Plan 25,5 %");
  });

  test("la obra sin avance dice «Sin avance» y la sin versión, «Sin versión»", async () => {
    montar();
    const t = await tabla();
    const torre = (await t.findByRole("link", { name: "Torre B" })).closest("tr")!;
    expect(within(torre).getByText("Sin avance")).toBeInTheDocument();
    expect(within(torre).getByText("Sin versión")).toBeInTheDocument();
    expect(torre).not.toHaveTextContent("Real");
  });

  test("con avance, la barra IBCS dibuja el real relleno y el plan en contorno; sin avance no hay barra", async () => {
    montar();
    const t = await tabla();
    const casa = (await t.findByRole("link", { name: "Casa Demo" })).closest("tr")!;
    expect(casa.querySelector(".fiori-kpi__barra-real")).toHaveStyle({ inlineSize: "62.5%" });
    expect(casa.querySelector(".fiori-kpi__barra-meta")).toHaveStyle({ inlineSize: "70%" });
    const torre = t.getByRole("link", { name: "Torre B" }).closest("tr")!;
    expect(torre.querySelector(".fiori-kpi__barra")).toBeNull();
  });

  test("el nombre de la obra lleva a su Resumen, en la carpeta de la obra", async () => {
    montar();
    const t = await tabla();
    expect(await t.findByRole("link", { name: "Galpón Sur" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/resumen");
    expect(t.getByRole("link", { name: "Casa Demo" })).toHaveAttribute("href", "/obra/empresa/7/resumen");
  });
});

describe("Vista general: sin obras", () => {
  test("quien revisa ve el estado vacío, sin crear nada", async () => {
    cartera = () => json(SIN_OBRAS);
    pendientes = lista();
    montar({ sesion: sesionDe("rita") });
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("No hay obras en esta carpeta")).toBeInTheDocument();
    expect(within(b).getByText("Cuando haya una obra registrada en las carpetas a las que tiene acceso, aparecerá aquí.")).toBeInTheDocument();
    expect(within(b).queryByRole("button", { name: "Nueva obra" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Obras y avance contra el plan" })).toBeNull();
    expect(document.querySelector(".silice-vacio")).not.toBeNull();
  });

  test("quien arma ve cómo empezar y el botón «Nueva obra»", async () => {
    cartera = () => json(SIN_OBRAS);
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByText("Aún no hay obras")).toBeInTheDocument();
    expect(within(b).getByText("Cree la primera obra para armar su presupuesto y seguir su avance.")).toBeInTheDocument();
    expect(within(b).getByRole("button", { name: "Nueva obra" })).toBeInTheDocument();
  });
});

describe("Vista general: un bloque que falla no tumba a los demás", () => {
  test("la cartera con un 500 dice su error y los demás bloques se ven", async () => {
    cartera = () => json({ detalle: "La base de la carpeta no responde. Intente de nuevo." }, 500);
    montar();
    const b = await bloque("Cartera por moneda");
    expect(await within(b).findByRole("alert")).toHaveTextContent("La base de la carpeta no responde. Intente de nuevo.");
    // Lo demás sigue en pie.
    const bloquea = await bloque("Lo que requiere atención");
    expect(await within(bloquea).findByText("Falta pedir el cemento")).toBeInTheDocument();
    expect(await screen.findByText("presupuesto-1.xlsx")).toBeInTheDocument();
    expect(await bloque("Arenera: lo que requiere atención")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Vista general" })).toBeInTheDocument();
  });

  test("los pendientes con un 500 dicen su error y la cartera se ve", async () => {
    pendientes = () => json({ detalle: "Sílice no respondió a tiempo. Intente de nuevo." }, 500);
    montar();
    const b = await bloque("Lo que requiere atención");
    expect(await within(b).findByRole("alert")).toHaveTextContent("Sílice no respondió a tiempo. Intente de nuevo.");
    expect(await bloque("Cartera en Bs")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Casa Demo" })).toBeInTheDocument();
  });

  test("las auditorías con un 500 dicen su error y la cartera y lo que bloquea se ven", async () => {
    auditorias = () => json({ detalle: "El historial no respondió. Intente de nuevo." }, 500);
    montar();
    expect(await screen.findByText("El historial no respondió. Intente de nuevo.")).toBeInTheDocument();
    expect(await bloque("Cartera en Bs")).toBeInTheDocument();
    expect(await within(await bloque("Lo que requiere atención")).findByText("Falta pedir el cemento")).toBeInTheDocument();
  });
});

describe("Vista general: la arenera y los permisos", () => {
  test("quien opera la arenera con su especialidad encendida ve la arenera", async () => {
    montar();
    expect(await bloque("Arenera: lo que requiere atención")).toBeInTheDocument();
    expect(pedidas(RUTA_ARENERA)).toBe(1);
  });

  test("quien no opera la arenera no la ve ni la pide", async () => {
    montar({ sesion: sesionDe("rita") });
    await bloque("Cartera por moneda");
    expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).toBeNull();
    expect(pedidas(RUTA_ARENERA)).toBe(0);
  });

  test("con la especialidad de producción apagada, la arenera no se ve ni se pide", async () => {
    apagados = ["produccion"];
    montar();
    await bloque("Cartera por moneda");
    // `GET /v1/modulos` llega después del primer dibujo: se espera a que la arenera desaparezca o nunca aparezca.
    await waitFor(() => expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).toBeNull());
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).toBeNull();
  });

  test("quien administra y no lee obras no recibe cartera ni auditorías (no se piden), pero sí la arenera", async () => {
    montar({ sesion: sesionDe("admin") });
    expect(await bloque("Arenera: lo que requiere atención")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Vista general" })).toBeInTheDocument();
    expect(pedidas(RUTA_CARTERA)).toBe(0);
    expect(pedidas(RUTA_AUDITORIAS)).toBe(0);
    expect(screen.queryByRole("region", { name: "Cartera por moneda" })).toBeNull();
  });
});

describe("Vista general: los pendientes se vuelven a pedir al volver", () => {
  test("al volver de una obra a la Vista general se piden otra vez y lo resuelto ya no está", async () => {
    const u = userEvent.setup();
    let actuales = [CEMENTO, PRECIOS];
    pendientes = () => json({ pendientes: actuales, carpetas_omitidas: 0 });
    montar({ ir: "/obra/empresa/7/presupuesto" });
    const antes = await bloque("Lo que requiere atención");
    await within(antes).findByText("Falta pedir el cemento");
    expect(pedidas(RUTA_PENDIENTES)).toBe(1);

    await u.click(screen.getByRole("button", { name: "Ir a /obra/empresa/7/presupuesto" }));
    await screen.findByRole("heading", { level: 1, name: "Presupuesto" }, { timeout: 3000 });
    // En la Hoja se resolvió lo del cemento.
    actuales = [PRECIOS];
    await u.click(within(screen.getByRole("banner")).getByRole("link", { name: "Sílice" }));

    const despues = await bloque("Lo que requiere atención");
    await within(despues).findByText("3 precios con más de 90 días");
    expect(ruta()).toBe("/inicio/general");
    expect(pedidas(RUTA_PENDIENTES)).toBe(2);
    expect(screen.queryByText("Falta pedir el cemento")).toBeNull();
  });

  test("al arrancar en «/» (que redirige a la Vista general) se piden una sola vez", async () => {
    montar({ en: "/" });
    const b = await bloque("Lo que requiere atención");
    await within(b).findByText("Falta pedir el cemento");
    await waitFor(() => expect(ruta()).toBe("/inicio/general"));
    expect(pedidas(RUTA_PENDIENTES)).toBe(1);
  });
});

describe("Inicio: las rutas", () => {
  const titulo = (nombre: string) => screen.findByRole("heading", { level: 1, name: nombre }, { timeout: 3000 });

  test.each(["/", "/inicio", "/inicio/no-existe", "/no-existe"])("%s acaba en #/inicio/general, la Vista general", async (de) => {
    montar({ en: de });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general");
  });

  test("#/pendientes redirige a #/inicio/pendientes y muestra la bandeja", async () => {
    montar({ en: "/pendientes" });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
  });

  test("#/pendientes?proyecto=OF-001 conserva la consulta", async () => {
    montar({ en: "/pendientes?proyecto=OF-001" });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes?proyecto=OF-001");
  });

  test("#/inicio/general?x=1 y #/inicio?x=1 conservan la consulta", async () => {
    montar({ en: "/inicio?x=1" });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general?x=1");
  });

  test("la pestaña «Pendientes» de la barra abre la bandeja, con su barra y su cabecera", async () => {
    const u = userEvent.setup();
    montar();
    await bloque("Cartera por moneda");
    await u.click(within(screen.getByRole("navigation", { name: "Inicio" })).getByRole("link", { name: "Pendientes" }));
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
    expect(screen.getByRole("region", { name: "Vista general" })).toBeInTheDocument(); // la cabecera del espacio
    expect(within(screen.getByRole("navigation", { name: "Inicio" })).getByRole("link", { name: "Pendientes" })).toHaveAttribute("aria-current", "page");
  });

  test("el título de la pestaña del navegador dice «Vista general · Sílice»", async () => {
    montar();
    await titulo("Vista general");
    await waitFor(() => expect(document.title).toBe("Vista general · Sílice"));
  });
});
