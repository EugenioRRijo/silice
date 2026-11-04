import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { PendienteDeObra, SesionRespuesta } from "../../api/tipos";
import { Marco } from "../../marco/Marco";
import { caso, estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { EstadoDelServidor, Respondedor } from "../../shell/obras/datosDePrueba";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios, useFormularioSucio } from "../../shell/sucio";

// Rediseño F3, Tarea 2: la bandeja de Pendientes en `#/pendientes`, dentro del marco de verdad (barra lateral, «Cambios
// sin guardar», cambio de carpeta) con la API de mentira. La respuesta tiene la forma de `GET /v1/obras/pendientes/todas`
// (Tarea 1, `docs/api.json`) y ya viene ordenada. Los textos fijos son los del plan; obras y carpetas, ficticias.

const RUTA = "/v1/obras/pendientes/todas";
const SUR = "Carpeta Sur.db";

const DEVUELTA: PendienteDeObra = {
  carpeta: SUR,
  obra_id: 3,
  obra: "Galpón Sur",
  grupo: "aprobar",
  urgencia: "bloquea",
  texto: "V2 devuelta con observaciones",
  accion: { texto: "Hacer una versión nueva", pagina: "hoja" },
};
const CEMENTO: PendienteDeObra = {
  carpeta: null,
  obra_id: 7,
  obra: "Casa Demo",
  grupo: "compras",
  urgencia: "bloquea",
  texto: "Falta pedir el cemento",
  accion: { texto: "Abrir el presupuesto", pagina: "hoja" },
};
const PRECIOS: PendienteDeObra = {
  carpeta: null,
  obra_id: 8,
  obra: "Torre B",
  grupo: "precios",
  urgencia: "aviso",
  texto: "3 precios con más de 90 días",
  accion: { texto: "Actualizar precios", pagina: "actualizacion" },
};
const SIN_APU: PendienteDeObra = {
  carpeta: SUR,
  obra_id: 3,
  obra: "Galpón Sur",
  grupo: "calidad",
  urgencia: "aviso",
  texto: "2 partidas sin APU",
  accion: { texto: "Ver el catálogo", pagina: "catalogo" },
};
const CUATRO = [DEVUELTA, CEMENTO, PRECIOS, SIN_APU];

// Las obras de cada carpeta para la barra lateral y la entrada en la obra (la de la empresa es «silice.db»).
function obrasTodas(estado: EstadoDelServidor) {
  const empresa = estado.actual.nombre === "silice.db";
  const fila = (carpeta: string | null, obra_id: number, obra: string) => ({
    carpeta,
    carpeta_titulo: carpeta === null ? "Carpeta de la empresa" : carpeta.replace(/\.db$/, ""),
    obra_id,
    obra,
    version_codigo: null,
  });
  return {
    carpeta_actual: empresa ? null : estado.actual.nombre,
    carpeta_actual_titulo: empresa ? "Carpeta de la empresa" : estado.actual.nombre.replace(/\.db$/, ""),
    obras: [
      fila(null, 7, "Casa Demo"),
      fila(null, 8, "Torre B"),
      fila(SUR, 3, "Galpón Sur"),
      ...(conHomonima ? [fila(SUR, 4, "Casa Demo")] : []),
    ],
  };
}

// D-F3-3: una obra de la carpeta Sur con el mismo nombre que la de la empresa.
let conHomonima = false;

let servidor: ReturnType<typeof servidorFalso>;
// Lo que contesta la ruta de la bandeja; cada prueba lo cambia.
let bandeja: Respondedor;

function instalar(preparar: (estado: EstadoDelServidor) => void = () => undefined) {
  const estado = estadoInicial();
  estado.casos = [...estado.casos, caso(SUR)];
  preparar(estado);
  servidor = servidorFalso(estado, (metodo, ruta, cuerpo) => {
    if (metodo !== "GET") return undefined;
    if (ruta === RUTA) return bandeja(metodo, ruta, cuerpo);
    if (ruta === "/v1/obras/todas") return json(obrasTodas(estado));
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
}

const responder = (pendientes: PendienteDeObra[], carpetas_omitidas = 0): Respondedor => () => json({ pendientes, carpetas_omitidas });

beforeEach(() => {
  conHomonima = false;
  bandeja = responder(CUATRO);
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
  const { pathname } = useLocation();
  return <output data-testid="ruta">{pathname}</output>;
}
const ruta = () => screen.getByTestId("ruta").textContent;
function IrA({ destino }: { destino: string }) {
  const navegar = useNavigate();
  return <button onClick={() => navegar(destino)}>{`Ir a ${destino}`}</button>;
}

// Un formulario con cambios sin guardar en otra pantalla (como Componer a medio llenar).
function FormularioSucio() {
  useFormularioSucio("componer", true);
  return null;
}

function montar({
  sesion = sesionDe("ana"),
  sucio = false,
  inicial = "/pendientes",
  ir,
}: { sesion?: SesionRespuesta; sucio?: boolean; inicial?: string; ir?: string } = {}) {
  return render(
    <MemoryRouter initialEntries={[inicial]}>
      <Marco sesion={sesion} alSalir={vi.fn()} alExpirar={vi.fn()} paginas={ligeras()} />
      <Ubicacion />
      {ir && <IrA destino={ir} />}
      {sucio && <FormularioSucio />}
    </MemoryRouter>,
  );
}

const lista = () => screen.findByRole("listbox", { name: "Pendientes por hacer" });
const detalle = () => screen.getByRole("region", { name: "Detalle del pendiente" });
const opciones = async () => within(await lista()).getAllByRole("option");
const pedidas = () => servidor.de("GET", RUTA).length;

describe("Pendientes: la bandeja", () => {
  test("un solo h1 «Pendientes» y ya no el «N por hacer» al lado", async () => {
    montar();
    await lista();
    const titulos = screen.getAllByRole("heading", { level: 1 });
    expect(titulos).toHaveLength(1);
    expect(titulos[0]).toHaveTextContent("Pendientes");
    expect(titulos[0]).toHaveClass("cds--type-heading-04");
    expect(screen.queryByText(/por hacer/)).toBeNull();
    expect(document.querySelector(".silice-bandeja__total")).toBeNull();
  });

  describe("el resumen por urgencia encima de la lista", () => {
    const resumen = () => document.querySelector(".silice-bandeja__resumen");

    test("dos que bloquean y dos avisos: «2 bloquean · 2 avisos», antes de la lista", async () => {
      montar();
      const ul = await lista();
      expect(resumen()).toHaveTextContent(/^2 bloquean · 2 avisos$/);
      // Encima de la lista: el resumen precede a la lista en el documento.
      expect(resumen()!.compareDocumentPosition(ul) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    test("en singular: «1 bloquea · 1 aviso»", async () => {
      bandeja = responder([CEMENTO, PRECIOS]);
      montar();
      await lista();
      expect(resumen()).toHaveTextContent(/^1 bloquea · 1 aviso$/);
    });

    test("un grupo en cero no se nombra", async () => {
      bandeja = responder([CEMENTO, DEVUELTA, CEMENTO]);
      montar();
      await lista();
      expect(resumen()).toHaveTextContent(/^3 bloquean$/);
    });

    test("solo avisos: «1 aviso»", async () => {
      bandeja = responder([PRECIOS]);
      montar();
      await lista();
      expect(resumen()).toHaveTextContent(/^1 aviso$/);
    });

    test("con la lista vacía no hay resumen", async () => {
      bandeja = responder([]);
      montar();
      await screen.findByText("No tiene pendientes.");
      expect(resumen()).toBeNull();
    });

    test("cargando, o con error, tampoco hay resumen", async () => {
      bandeja = () => json({ detalle: "Sílice no respondió a tiempo." }, 500);
      montar();
      await screen.findByText("No se pudieron leer los pendientes");
      expect(resumen()).toBeNull();
    });
  });

  test("la lista es una ul con un elemento por pendiente, en el orden de la API, con texto, obra y urgencia en palabras", async () => {
    // Un aviso antes de un bloquea: la bandeja no reordena.
    bandeja = responder([PRECIOS, CEMENTO]);
    montar();
    const ul = await lista();
    expect(ul.tagName).toBe("UL");
    const [primera, segunda] = await opciones();
    expect(await opciones()).toHaveLength(2);
    expect(primera).toHaveTextContent("3 precios con más de 90 días");
    expect(primera).toHaveTextContent("Torre B");
    expect(primera).toHaveTextContent("Aviso");
    expect(segunda).toHaveTextContent("Falta pedir el cemento");
    expect(segunda).toHaveTextContent("Casa Demo");
    expect(segunda).toHaveTextContent("Bloquea");
  });

  test("el primero queda elegido al cargar y el detalle lo muestra con un solo botón principal", async () => {
    montar();
    const [primera, ...resto] = await opciones();
    expect(primera).toHaveAttribute("aria-selected", "true");
    for (const o of resto) expect(o).toHaveAttribute("aria-selected", "false");
    const region = detalle();
    expect(within(region).getByRole("heading", { level: 2, name: "V2 devuelta con observaciones" })).toHaveClass(
      "cds--type-heading-compact-02",
    );
    expect(region).toHaveTextContent("Galpón Sur");
    expect(region).toHaveTextContent("Bloquea");
    expect(within(region).getAllByRole("button")).toHaveLength(1);
    expect(within(region).getByRole("button", { name: "Hacer una versión nueva" })).toHaveClass("cds--btn--primary");
    expect(screen.getByRole("main").querySelectorAll(".cds--btn--primary")).toHaveLength(1);
  });

  test("elegir otro con un clic cambia el detalle", async () => {
    const u = userEvent.setup();
    montar();
    const [primera, , tercera] = await opciones();
    await u.click(tercera);
    expect(tercera).toHaveAttribute("aria-selected", "true");
    expect(primera).toHaveAttribute("aria-selected", "false");
    expect(within(detalle()).getByRole("heading", { level: 2, name: "3 precios con más de 90 días" })).toBeInTheDocument();
    expect(within(detalle()).getByRole("button", { name: "Actualizar precios" })).toBeInTheDocument();
  });

  test("con el foco en la lista, ↑ y ↓ (e Inicio y Fin) eligen y el detalle sigue", async () => {
    const u = userEvent.setup();
    montar();
    const ul = await lista();
    ul.focus();
    expect(ul).toHaveFocus();
    const [, segunda, , cuarta] = await opciones();
    expect(ul).toHaveAttribute("aria-activedescendant", (await opciones())[0].id);
    await u.keyboard("{ArrowDown}");
    expect(segunda).toHaveAttribute("aria-selected", "true");
    expect(ul).toHaveAttribute("aria-activedescendant", segunda.id);
    expect(within(detalle()).getByRole("heading", { level: 2, name: "Falta pedir el cemento" })).toBeInTheDocument();
    await u.keyboard("{End}");
    expect(cuarta).toHaveAttribute("aria-selected", "true");
    expect(within(detalle()).getByRole("button", { name: "Ver el catálogo" })).toBeInTheDocument();
    await u.keyboard("{ArrowUp}");
    expect(within(detalle()).getByRole("heading", { level: 2, name: "3 precios con más de 90 días" })).toBeInTheDocument();
    expect(ul).toHaveFocus();
  });

  test("el botón abre la sección de la obra (D-F3-2)", async () => {
    const u = userEvent.setup();
    montar();
    await u.click((await opciones())[1]);
    await u.click(within(detalle()).getByRole("button", { name: "Abrir el presupuesto" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Presupuesto" }, { timeout: 3000 })).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
  });

  test("lista vacía: lo dice y enseña qué esperar, sin «Empieza aquí»", async () => {
    bandeja = responder([]);
    montar();
    expect(await screen.findByText("No tiene pendientes.")).toBeInTheDocument();
    expect(screen.getByText("Cuando una obra necesite algo de usted, aparecerá aquí.")).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(screen.queryByText(/Empieza aquí/)).toBeNull();
    expect(screen.queryByText(/por hacer/)).toBeNull();
  });

  test.each([
    [1, "No se pudo leer 1 carpeta; sus pendientes no aparecen."],
    [2, "No se pudieron leer 2 carpetas; sus pendientes no aparecen."],
  ])("con %i carpeta(s) ilegible(s) avisa y muestra los demás (foco 2)", async (omitidas, texto) => {
    bandeja = responder([CEMENTO], omitidas);
    montar();
    expect(await screen.findByText(texto)).toBeInTheDocument();
    expect(await opciones()).toHaveLength(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("una carpeta ilegible y ningún otro pendiente: el aviso y el vacío, nunca en blanco (foco 2)", async () => {
    bandeja = responder([], 1);
    montar();
    expect(await screen.findByText("No se pudo leer 1 carpeta; sus pendientes no aparecen.")).toBeInTheDocument();
    expect(screen.getByText("No tiene pendientes.")).toBeInTheDocument();
  });

  test("mientras llegan, lo dice", async () => {
    bandeja = () => new Promise<Response>(() => {});
    montar();
    expect(await screen.findByRole("status", { name: "Cargando los pendientes" })).toBeInTheDocument();
  });

  test("un error de la API se dice con su detalle y «Reintentar» vuelve a pedir", async () => {
    const u = userEvent.setup();
    let veces = 0;
    bandeja = () => {
      veces += 1;
      return veces === 1 ? json({ detalle: "Sílice no respondió a tiempo. Intente de nuevo." }, 500) : json({ pendientes: CUATRO, carpetas_omitidas: 0 });
    };
    montar();
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("No se pudieron leer los pendientes");
    expect(alerta).toHaveTextContent("Sílice no respondió a tiempo. Intente de nuevo.");
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await opciones()).toHaveLength(4);
    expect(pedidas()).toBe(2);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("un 403 de la API deja la lista vacía, sin error", async () => {
    bandeja = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
    montar();
    expect(await screen.findByText("No tiene pendientes.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("el administrador (sin leer_proyecto) ve la lista vacía, sin error y sin pedirla", async () => {
    montar({ sesion: sesionDe("admin") });
    expect(await screen.findByText("No tiene pendientes.")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 30));
    expect(pedidas()).toBe(0);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("Pendientes: foco 1, quien revisa", () => {
  const ESPERA: PendienteDeObra = {
    carpeta: null,
    obra_id: 7,
    obra: "Casa Demo",
    grupo: "aprobar",
    urgencia: "bloquea",
    texto: "V3 espera dictamen",
    accion: { texto: "Ver el envío", pagina: "aprobar" },
  };

  test("«espera dictamen» lleva a Aprobaciones de la obra, que su cuenta puede abrir", async () => {
    const u = userEvent.setup();
    bandeja = responder([ESPERA]);
    montar({ sesion: sesionDe("rita") });
    await lista();
    await u.click(within(detalle()).getByRole("button", { name: "Ver el envío" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Aprobar una versión" }, { timeout: 3000 })).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/aprobaciones");
  });

  test("una acción que su cuenta no puede usar no se ofrece como botón: se dice por qué", async () => {
    // «Actualizar precios» exige editar_hoja. (Antes el ejemplo era la Hoja, que desde F4 2b quien revisa ve en solo
    // lectura: ese botón sí le sale.)
    bandeja = responder([PRECIOS]);
    montar({ sesion: sesionDe("rita") });
    await lista();
    expect(within(detalle()).queryByRole("button")).toBeNull();
    expect(detalle()).toHaveTextContent("Su cuenta no puede dar este paso.");
  });
});

describe("Pendientes: foco 3, salir sin perder trabajo", () => {
  test("con un formulario a medio llenar, el botón pregunta y «Quedarme» no navega", async () => {
    const u = userEvent.setup();
    montar({ sucio: true });
    await u.click((await opciones())[1]);
    await u.click(within(detalle()).getByRole("button", { name: "Abrir el presupuesto" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(ruta()).toBe("/pendientes");
  });

  test("con la Hoja con cambios, un pendiente de otra carpeta pregunta por ella; «Quedarme» no cambia de carpeta", async () => {
    const u = userEvent.setup();
    instalar((estado) => {
      estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-27T10:00:00" }];
    });
    montar();
    await lista();
    await u.click(within(detalle()).getByRole("button", { name: "Hacer una versión nueva" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Hoja de Casa Demo. Si cambia de carpeta, se perderán.");
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    expect(ruta()).toBe("/pendientes");

    await u.click(within(detalle()).getByRole("button", { name: "Hacer una versión nueva" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Cambiar y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/presupuesto"));
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: SUR }]));
  });
});

describe("Pendientes: foco 4, volver después de resolver algo", () => {
  test("al volver a entrar se pide otra vez y el pendiente resuelto ya no está", async () => {
    const u = userEvent.setup();
    let pendientes = CUATRO;
    bandeja = () => json({ pendientes, carpetas_omitidas: 0 });
    montar();
    await u.click((await opciones())[1]);
    expect(pedidas()).toBe(1);
    await u.click(within(detalle()).getByRole("button", { name: "Abrir el presupuesto" }));
    await screen.findByRole("heading", { level: 1, name: "Presupuesto" }, { timeout: 3000 });
    // En la Hoja se resolvió lo del cemento.
    pendientes = [DEVUELTA, PRECIOS, SIN_APU];
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    await u.click(within(lateral).getByRole("link", { name: /^Pendientes/ }));
    expect(await screen.findByText("1 bloquea · 2 avisos")).toBeInTheDocument();
    expect(pedidas()).toBe(2);
    expect(screen.queryByText("Falta pedir el cemento")).toBeNull();
  });
});

describe("Pendientes: la lectura de la carga inicial no deja datos viejos", () => {
  test("si la carga empezó en otra ruta y se entra en Pendientes antes de que llegue, se pide de nuevo y manda la nueva", async () => {
    const u = userEvent.setup();
    let soltarLaPrimera: (r: Response) => void = () => undefined;
    let veces = 0;
    bandeja = () => {
      veces += 1;
      if (veces === 1) return new Promise<Response>((resolver) => (soltarLaPrimera = resolver));
      return json({ pendientes: [PRECIOS], carpetas_omitidas: 0 });
    };
    montar({ inicial: "/obras" });
    await waitFor(() => expect(pedidas()).toBe(1));
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    await u.click(within(lateral).getByRole("link", { name: /^Pendientes/ }));
    // La lectura de antes de entrar se descarta: entrar en Pendientes pide siempre una nueva.
    await waitFor(() => expect(pedidas()).toBe(2));
    // La vieja llega tarde, con datos que ya no valen.
    soltarLaPrimera(await json({ pendientes: [CEMENTO], carpetas_omitidas: 0 }));
    expect(await opciones()).toHaveLength(1);
    expect(within(await lista()).getByText("3 precios con más de 90 días")).toBeInTheDocument();
    expect(screen.queryByText("Falta pedir el cemento")).toBeNull();
  });
});

describe("Pendientes: cuándo no se repite la lectura", () => {
  test("si se sale de Pendientes con la lectura en curso y se vuelve, se pide de nuevo", async () => {
    const u = userEvent.setup();
    let soltarLaPrimera: (r: Response) => void = () => undefined;
    let veces = 0;
    bandeja = () => {
      veces += 1;
      if (veces === 1) return new Promise<Response>((resolver) => (soltarLaPrimera = resolver));
      return json({ pendientes: [PRECIOS], carpetas_omitidas: 0 });
    };
    montar({ ir: "/obra/empresa/7/presupuesto" });
    await waitFor(() => expect(pedidas()).toBe(1));
    await u.click(screen.getByRole("button", { name: "Ir a /obra/empresa/7/presupuesto" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto"));
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    await u.click(within(lateral).getByRole("link", { name: /^Pendientes/ }));
    await waitFor(() => expect(pedidas()).toBe(2));
    soltarLaPrimera(json({ pendientes: [CEMENTO], carpetas_omitidas: 0 }));
    expect(within(await lista()).getByText("3 precios con más de 90 días")).toBeInTheDocument();
    expect(screen.queryByText("Falta pedir el cemento")).toBeNull();
  });

  test("al arrancar desde «/» (que redirige a Pendientes) se piden una sola vez", async () => {
    montar({ inicial: "/" });
    expect(await opciones()).toHaveLength(4);
    await waitFor(() => expect(ruta()).toBe("/pendientes"));
    expect(pedidas()).toBe(1);
  });
});

// Foco 5 (estructura; la medida a 1366 px es de la Tarea 5, en el navegador). jsdom no calcula CSS: las reglas se leen
// del fuente, como en `marco/estilosMarco.test.ts`.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
// Se lee en cada prueba: sin la hoja de estilos, fallan estas y no las demás.
const estilos = () => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/pendientes/Bandeja.scss`, "utf-8");

function reglaDe(selector: string): string {
  const fuente = estilos();
  const i = fuente.indexOf(`${selector} {`);
  if (i < 0) return "";
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

describe("Pendientes: foco 5, muchos pendientes", () => {
  test("la columna de la lista tiene su propio desplazamiento", () => {
    expect(reglaDe(".silice-bandeja__lista")).toMatch(/overflow-y:\s*auto/);
  });

  // Los grosores de 1 a 3 px de divisores, rayas y foco son los del marco (BarraLateral.scss, Buscador.scss); lo que
  // no puede haber es un ancho fijo.
  test("ningún ancho fijo: ni px ni rem en anchos, y las columnas pueden encogerse", () => {
    expect(estilos()).not.toMatch(/(?:^|[\s;{])(?:min-|max-)?(?:inline-size|width)\s*:\s*[\d.]+(?:px|rem|em)/m);
    expect(reglaDe(".silice-bandeja__rejilla")).toMatch(/grid-template-columns:\s*minmax\(0,\s*2fr\)\s+minmax\(0,\s*3fr\)/);
  });

  // Como BarraSuperior.scss: un `@each` sobre las escalas del mapa de umbrales, sin consultas de medios propias.
  test("por debajo del umbral de cada letra la lista pasa arriba (umbrales del marco, sin números nuevos)", () => {
    expect(estilos()).toMatch(/@use\s+"\.\.\/\.\.\/marco\/umbrales"\s+as\s+u;/);
    expect(estilos()).toMatch(/@each \$escala in map\.keys\(u\.\$umbrales-por-escala\) \{\s*@include u\.por-debajo-del-umbral\(\$escala\)/);
    expect(estilos()).not.toMatch(/@media/);
  });

  // Cierre de F3 (H1): bajo el umbral la rejilla apila lista y detalle; con la bandeja de alto fijo (100vh - 3rem) y la
  // lista con `min-block-size: 0` la lista quedaba en alto 0 y solo se veía el detalle (letra Muy grande, 1056-1910 px).
  test("por debajo del umbral la bandeja toma alto natural y la lista no puede quedar en alto 0", () => {
    const fuente = estilos();
    const abre = fuente.indexOf("@each $escala");
    expect(abre).toBeGreaterThan(-1);
    const bloque = fuente.slice(abre, fuente.indexOf("// La carpeta de una obra"));
    const regla = (selector: string) => {
      const i = bloque.indexOf(`${selector} {`);
      return i < 0 ? "" : bloque.slice(i, bloque.indexOf("}", i));
    };
    expect(regla(".silice-bandeja")).toMatch(/block-size:\s*auto/);
    expect(regla(".silice-bandeja__lista")).toMatch(/(?:^|[;{\s])block-size:\s*auto/);
    expect(regla(".silice-bandeja__lista")).toMatch(/max-block-size:\s*\d+vh/);
    expect(regla(".silice-bandeja__rejilla")).not.toMatch(/minmax\(0,\s*1fr\)\s*auto/);
  });

  test("con 200 pendientes todos van dentro de la columna de la lista y el detalle queda fuera de ella", async () => {
    bandeja = responder(Array.from({ length: 200 }, (_, i) => ({ ...PRECIOS, texto: `Pendiente ficticio ${i + 1}` })));
    const { container } = montar();
    expect(await opciones()).toHaveLength(200);
    const columna = container.querySelector(".silice-bandeja__lista");
    expect(columna).toContainElement(await lista());
    expect(columna).not.toContainElement(detalle());
    expect(screen.getByText("200 avisos")).toBeInTheDocument();
  });
});

describe("Pendientes: obras con el mismo nombre (D-F3-3)", () => {
  const HOMONIMA: PendienteDeObra = { ...CEMENTO, carpeta: SUR, obra_id: 4, texto: "Falta pedir la arena" };

  test("en la lista y en el detalle, dos obras llamadas igual muestran su carpeta; las demás no", async () => {
    conHomonima = true;
    bandeja = responder([CEMENTO, HOMONIMA, PRECIOS]);
    montar();
    const [primera, segunda, tercera] = await opciones();
    await waitFor(() => expect(primera).toHaveTextContent("Carpeta de la empresa"));
    expect(segunda).toHaveTextContent("Carpeta Sur");
    expect(tercera).not.toHaveTextContent("Carpeta");
    expect(detalle()).toHaveTextContent("Carpeta de la empresa");
    await userEvent.setup().click(segunda);
    expect(detalle()).toHaveTextContent("Carpeta Sur");
    await userEvent.setup().click(tercera);
    expect(detalle()).not.toHaveTextContent("Carpeta");
  });

  test("sin obras homónimas no se muestra ninguna carpeta", async () => {
    montar();
    const todas = await opciones();
    await new Promise((r) => setTimeout(r, 30));
    for (const o of todas) expect(o).not.toHaveTextContent("Carpeta");
  });

  test("una obra que no está en la lista del marco no muestra nada extra", async () => {
    conHomonima = true;
    const FUERA: PendienteDeObra = { ...CEMENTO, carpeta: SUR, obra_id: 99 };
    bandeja = responder([FUERA, CEMENTO]);
    montar();
    const [primera, segunda] = await opciones();
    await waitFor(() => expect(segunda).toHaveTextContent("Carpeta de la empresa"));
    expect(primera).not.toHaveTextContent("Carpeta");
  });
});
