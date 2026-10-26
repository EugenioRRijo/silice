import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { cancelarSalida } from "../salida";
import { olvidarFormularios, useFormularioSucio } from "../sucio";
import { useAplicacion } from "../contexto";
import { botonDeObra, estadoInicial, json, ligeras, montarShell, servidorFalso, sesionDe } from "../obras/datosDePrueba";
import PaginaAdministracion from "../../paginas/administracion/index";
import { DialogoCarpetas } from "./DialogoCarpetas";
import { GestionCarpetas } from "./GestionCarpetas";

// Plan de modulos, MOD-3b (absorbe T6 del plan de montar): las carpetas de trabajo (diseno de la bienvenida, BCP-5 §4.3
// a §4.7 y pruebas F5 a F9) y la confirmacion al cambiar de carpeta (foco 3 del plan). Oraculos escritos a mano: los
// nombres ficticios de `obras/datosDePrueba.tsx` y los textos fijos de `aplicacion/casos.py`.

let servidor: ReturnType<typeof servidorFalso>;

beforeEach(() => {
  servidor = servidorFalso();
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

function ComponerSucio() {
  useFormularioSucio("componer", true);
  return <h1>Componer una partida</h1>;
}

const dialogo = () => screen.getByRole("dialog", { name: "Carpetas de trabajo" });
const salida = () => screen.queryByRole("dialog", { name: "Cambios sin guardar" });

async function abrirCarpetas(u: ReturnType<typeof userEvent.setup>) {
  await u.click(await botonDeObra());
  await u.click(await screen.findByRole("button", { name: "Cambiar carpeta…" }));
  return screen.findByRole("dialog", { name: "Carpetas de trabajo" });
}

// Los nombres de la lista de carpetas del dialogo, tal como se leen.
async function carpetasDeLaLista(): Promise<string[]> {
  const lista = await within(dialogo()).findByRole("list", { name: "Carpetas de trabajo de la instalación" });
  return within(lista)
    .getAllByRole("listitem")
    .map((li) => li.querySelector(".silice-carpetas__nombre")?.textContent ?? "");
}

describe("foco 3: cambiar de carpeta con trabajo sin guardar", () => {
  test("con Componer a medio llenar, abrir «s2» pregunta; «Quedarme» no llama POST /v1/casos/actual", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/componer", ligeras({ componer: ComponerSucio }));
    await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida. Si cambia de carpeta, se perderán.",
    );
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(salida()).toBeNull();
    await new Promise((r) => setTimeout(r, 30));
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    expect(screen.getByRole("heading", { level: 1, name: "Componer una partida" })).toBeInTheDocument();
  });

  test("con un borrador de «Casa Demo» con 2 cambios y nada sucio pregunta por «Hoja de Casa Demo»", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    estado.borradores = [
      { id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-25T10:00:00" },
      { id: "b-2", proyecto: "8", version: null, cambios: 0, rev: 0, tocado: "2026-10-25T10:00:00" },
    ];
    servidor = servidorFalso(estado);
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Hoja de Casa Demo. Si cambia de carpeta, se perderán.",
    );
    await u.click(within(pregunta).getByRole("button", { name: "Cambiar y descartar" }));
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "s2.db" }]));
  });

  test("sin nada que perder cambia directo, avisa sin la frase del reinicio y la barra dice la carpeta nueva", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "s2.db" }]));
    expect(salida()).toBeNull();
    const aviso = await screen.findByText("Ahora trabaja con la carpeta de trabajo «s2».");
    expect(aviso.closest(".cds--inline-notification")).not.toHaveTextContent(/reinici/i);
    expect(screen.queryByRole("dialog", { name: "Carpetas de trabajo" })).not.toBeInTheDocument();
    await u.click(await botonDeObra());
    expect(await screen.findByText("Carpeta: s2")).toBeInTheDocument();
  });

  test("al cambiar de carpeta se olvida la obra elegida", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana", { eleccion: { caso: null, proyecto: "7", aviso: null } }), "/hoja");
    await waitFor(async () => expect(await botonDeObra()).toHaveTextContent("Obra: Casa Demo"));
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    await waitFor(async () => expect(await botonDeObra()).toHaveTextContent("Obra: sin elegir"));
  });

  test("si la API rechaza el cambio muestra su detalle y deja la carpeta anterior", async () => {
    const u = userEvent.setup();
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) =>
      metodo === "POST" && ruta === "/v1/casos/actual" ? json({ detalle: "La carpeta de trabajo no se pudo preparar." }, 503) : undefined,
    );
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    expect(await within(dialogo()).findByText("La carpeta de trabajo no se pudo preparar.")).toBeInTheDocument();
    await u.click(within(dialogo()).getByRole("button", { name: "Cerrar" }));
    await u.click(await botonDeObra());
    expect(await screen.findByText("Carpeta: silice")).toBeInTheDocument();
  });

  test("un 401 al cambiar de carpeta avisa que la sesión venció", async () => {
    const u = userEvent.setup();
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) =>
      metodo === "POST" && ruta === "/v1/casos/actual" ? json({ detalle: "Sin sesión." }, 401) : undefined,
    );
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    const { alExpirar } = montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});

describe("diálogo «Carpetas de trabajo» (F5 a F9)", () => {
  test("F5: solo con cambiar de carpeta; las pestañas se recorren con el teclado; Esc lo cierra y devuelve el foco", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    const caja = await abrirCarpetas(u);
    expect(caja).toHaveAttribute("aria-modal", "true");
    const pestanas = within(caja).getAllByRole("tab");
    expect(pestanas.map((p) => p.textContent)).toEqual(["Crear", "Subir un archivo", "Demostración"]);
    pestanas[0]!.focus();
    await u.keyboard("{ArrowRight}");
    expect(within(caja).getByRole("tab", { name: "Subir un archivo" })).toHaveFocus();
    await u.keyboard("{ArrowRight}");
    expect(within(caja).getByRole("tab", { name: "Demostración" })).toHaveFocus();
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Carpetas de trabajo" })).not.toBeInTheDocument();
    expect(await botonDeObra()).toHaveFocus();
  });

  test("F5: «Cerrar» también devuelve el foco al botón de la barra", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Cerrar" }));
    expect(await botonDeObra()).toHaveFocus();
  });

  test("F5: crear sin moneda pide elegirla y no llama a la API", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    expect(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" })).toHaveValue("");
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Obra nueva");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(await within(dialogo()).findByText("Elija la moneda de trabajo de la carpeta.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/casos")).toEqual([]);
  });

  test("F5: crear con Bs llama POST /v1/casos, POST /v1/casos/actual y PUT /v1/carpeta/moneda, en ese orden, con el nombre final", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Obra*1");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(await within(dialogo()).findByText("Se creó la carpeta de trabajo «Obra_1» y ya trabaja con ella.")).toBeInTheDocument();
    // Sin las preferencias del armazón (`PUT /v1/sesion/preferencias` al entrar en el módulo), que no son de la carpeta.
    const escrituras = servidor.llamadas
      .filter((l) => l.metodo !== "GET" && !l.ruta.startsWith("/v1/sesion/"))
      .map((l) => `${l.metodo} ${l.ruta} ${JSON.stringify(l.cuerpo)}`);
    expect(escrituras).toEqual([
      'POST /v1/casos {"nombre":"Obra*1"}',
      'POST /v1/casos/actual {"nombre":"Obra_1.db"}',
      'PUT /v1/carpeta/moneda {"moneda":"Bs"}',
    ]);
  });

  test("F5: «ya existe» (409) se muestra en línea, tal cual lo dice la API", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "s1");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "USD");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(
      await within(dialogo()).findByText("Ya existe la carpeta de trabajo s1.db: ábrala de la lista o elija otro nombre."),
    ).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    expect(servidor.de("PUT", "/v1/carpeta/moneda")).toEqual([]);
  });

  test("F9: la lista se vuelve a pedir al abrir el diálogo y después de crear; la carpeta nueva se ve", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await waitFor(() => expect(servidor.de("GET", "/v1/casos").length).toBeGreaterThan(0));
    const antes = servidor.de("GET", "/v1/casos").length;
    await abrirCarpetas(u);
    await waitFor(() => expect(servidor.de("GET", "/v1/casos").length).toBeGreaterThan(antes));
    expect(await carpetasDeLaLista()).toEqual(["silice", "s1", "s2"]);
    const alAbrirlo = servidor.de("GET", "/v1/casos").length;
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Nueva");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    await waitFor(() => expect(servidor.de("GET", "/v1/casos").length).toBeGreaterThan(alAbrirlo));
    await waitFor(async () => expect(await carpetasDeLaLista()).toEqual(["silice", "s1", "s2", "Nueva"]));
  });

  test("la lista marca la carpeta abierta y la de la empresa; la abierta no se ofrece para abrir", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    const lista = await within(dialogo()).findByRole("list", { name: "Carpetas de trabajo de la instalación" });
    const silice = within(lista).getAllByRole("listitem")[0]!;
    expect(silice).toHaveAttribute("aria-current", "true");
    expect(silice).toHaveTextContent("Abierta");
    expect(silice).toHaveTextContent("Carpeta de la empresa");
    expect(within(silice).queryByRole("button")).toBeNull();
    expect(within(lista).getByRole("button", { name: "Abrir s1" })).toBeInTheDocument();
  });

  test("F6: subir acepta solo .db, dice el nombre y los MiB, anuncia el progreso y muestra 413, 422 y 409 tal cual", async () => {
    const u = userEvent.setup({ applyAccept: false });
    const respuestas = [
      json({ detalle: "El archivo pasa de 20 MiB." }, 413),
      json({ detalle: "El archivo no es una carpeta de trabajo de Sílice válida: no se guardó." }, 422),
      json({ detalle: "Ya hay una carpeta de trabajo llamada s1.db: cambie el nombre antes de subirla." }, 409),
    ];
    let soltar: () => void = () => {};
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) => {
      if (metodo !== "POST" || ruta !== "/v1/casos/subida") return undefined;
      const respuesta = respuestas.shift()!;
      return new Promise<Response>((resolver) => {
        soltar = () => resolver(respuesta);
      });
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Subir un archivo" }));
    const campo = () => dialogo().querySelector<HTMLInputElement>('input[type="file"]')!;
    await u.upload(campo(), new File(["x"], "libro.xlsx"));
    expect(within(dialogo()).getByText("Solo se aceptan archivos .db.")).toBeInTheDocument();
    expect(within(dialogo()).getByRole("button", { name: "Subir" })).toBeDisabled();
    // 1,5 MiB exactos: 1.572.864 bytes.
    await u.upload(campo(), new File([new Uint8Array(1_572_864)], "s1.db"));
    expect(within(dialogo()).getByText("s1.db · 1,5 MiB")).toBeInTheDocument();
    const listaAntes = await carpetasDeLaLista();
    for (const esperado of [
      "El archivo pasa de 20 MiB.",
      "El archivo no es una carpeta de trabajo de Sílice válida: no se guardó.",
      "Ya hay una carpeta de trabajo llamada s1.db: cambie el nombre antes de subirla.",
    ]) {
      await u.click(within(dialogo()).getByRole("button", { name: "Subir" }));
      expect(await within(dialogo()).findByText("Subiendo el archivo…")).toBeInTheDocument();
      soltar();
      expect(await within(dialogo()).findByText(esperado)).toBeInTheDocument();
    }
    expect(await carpetasDeLaLista()).toEqual(listaAntes);
    const cuerpo = servidor.de("POST", "/v1/casos/subida")[0]!.cuerpo as FormData;
    expect((cuerpo.get("archivo") as File).name).toBe("s1.db");
  });

  test("F6: una subida aceptada dice el nombre final y el aviso, y la carpeta aparece en la lista", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    servidor = servidorFalso(estado, (metodo, ruta) => {
      if (metodo !== "POST" || ruta !== "/v1/casos/subida") return undefined;
      estado.casos = [...estado.casos, { nombre: "copia.db", ruta_relativa: "casos/copia.db" }];
      return json(
        { nombre: "copia.db", ruta_relativa: "casos/copia.db", aviso: "Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo." },
        201,
      );
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Subir un archivo" }));
    await u.upload(dialogo().querySelector<HTMLInputElement>('input[type="file"]')!, new File(["x"], "copia.db"));
    await u.click(within(dialogo()).getByRole("button", { name: "Subir" }));
    expect(await within(dialogo()).findByText("Se subió la carpeta de trabajo «copia».")).toBeInTheDocument();
    expect(within(dialogo()).getByText("Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo.")).toBeInTheDocument();
    await waitFor(async () => expect(await carpetasDeLaLista()).toContain("copia"));
  });

  test("F7: la demostración dice que los datos son inventados; 201 la abre", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Demostración" }));
    expect(within(dialogo()).getByText("Datos de ejemplo inventados para aprender; no son una obra real.")).toBeInTheDocument();
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir la demostración" }));
    await waitFor(() =>
      expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "demostracion.db" }]),
    );
    expect(await screen.findByText("Ahora trabaja con la carpeta de trabajo «demostracion».")).toBeInTheDocument();
  });

  test("F7: si ya existía (200) también la abre", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    estado.casos = [...estado.casos, { nombre: "demostracion.db", ruta_relativa: "casos/demostracion.db" }];
    servidor = servidorFalso(estado);
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Demostración" }));
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir la demostración" }));
    await waitFor(() =>
      expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "demostracion.db" }]),
    );
  });

  test("ninguna cadena visible del diálogo dice «caso» ni «proyecto»", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await carpetasDeLaLista();
    for (const pestana of ["Crear", "Subir un archivo", "Demostración"]) {
      await u.click(within(dialogo()).getByRole("tab", { name: pestana }));
      for (const patron of [/\bcaso\b/i, /\bproyecto\b/i]) {
        expect(within(dialogo()).queryByText(patron)).toBeNull();
        expect(within(dialogo()).queryByLabelText(patron)).toBeNull();
      }
    }
  });
});

// Ronda 2 del arbitro de MOD-3b (MAYOR): «Crear y abrir» pregunta ANTES de crear, con la misma confirmacion que abrir
// otra carpeta; y si la moneda no se declara, lo dice sin decir que la carpeta no se creo, y reintenta solo la moneda.
describe("crear una carpeta: primero se pregunta, la moneda se reintenta sola", () => {
  const escrituras = () =>
    servidor.llamadas.filter(
      (l) =>
        (l.metodo === "POST" && (l.ruta === "/v1/casos" || l.ruta === "/v1/casos/actual")) ||
        (l.metodo === "PUT" && l.ruta === "/v1/carpeta/moneda"),
    );

  test("con Componer a medio llenar, crear con Bs pregunta antes; «Quedarme» no crea, no abre ni declara nada", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/componer", ligeras({ componer: ComponerSucio }));
    await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Nueva");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida. Si cambia de carpeta, se perderán.",
    );
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(escrituras()).toEqual([]);
    expect(within(dialogo()).queryByText(/Se creó/)).toBeNull();
  });

  test("si la moneda no se declara (503) lo dice sin «No se pudo crear» y «Declarar la moneda» repite solo el PUT", async () => {
    const u = userEvent.setup();
    let fallar = true;
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) => {
      if (metodo === "PUT" && ruta === "/v1/carpeta/moneda" && fallar) {
        fallar = false;
        return json({ detalle: "La carpeta de trabajo está ocupada: repita en unos segundos." }, 503);
      }
      return undefined;
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Nueva");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(
      await within(dialogo()).findByText(
        "La carpeta «Nueva» se creó y ya trabaja con ella, pero no se pudo declarar su moneda: La carpeta de trabajo está ocupada: repita en unos segundos.",
      ),
    ).toBeInTheDocument();
    expect(within(dialogo()).queryByText(/No se pudo crear/)).toBeNull();
    const antes = escrituras().length;
    await u.click(within(dialogo()).getByRole("button", { name: "Declarar la moneda" }));
    expect(await within(dialogo()).findByText("Se creó la carpeta de trabajo «Nueva» y ya trabaja con ella.")).toBeInTheDocument();
    const despues = escrituras().slice(antes);
    expect(despues.map((l) => `${l.metodo} ${l.ruta} ${JSON.stringify(l.cuerpo)}`)).toEqual([
      'PUT /v1/carpeta/moneda {"moneda":"Bs"}',
    ]);
    expect(servidor.de("POST", "/v1/casos")).toHaveLength(1);
  });
});

// Menores del arbitro tras aprobar la ronda 2 de MOD-3b: la demostracion tambien pregunta antes de crearse; la rama
// «se creo, pero no se pudo abrir»; y en Administracion (donde abrir vuelve a montar la pagina) «Quedarme» no crea nada y
// la moneda que falto declarar no se pierde con el remontaje.
describe("menores tras la ronda 2", () => {
  const escrituras = () =>
    servidor.llamadas.filter(
      (l) =>
        (l.metodo === "POST" && l.ruta.startsWith("/v1/casos")) || (l.metodo === "PUT" && l.ruta === "/v1/carpeta/moneda"),
    );
  // Ana con Administración: arma (crea y declara la moneda) y administra la instalación.
  const anaAdministra = () =>
    sesionDe("ana", { acciones: [...sesionDe("ana").acciones, "administrar_cuentas"], roles: ["arma", "administrador"] });
  const conAdministracion = () => ligeras({ administracion: PaginaAdministracion });

  async function crearEnAdministracion(u: ReturnType<typeof userEvent.setup>) {
    await screen.findByRole("heading", { level: 1, name: "Administración" });
    await u.click(screen.getByRole("tab", { name: "Carpetas de trabajo" }));
    await u.type(await screen.findByRole("textbox", { name: "Nombre de la carpeta" }), "Nueva");
    await u.selectOptions(screen.getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(screen.getByRole("button", { name: "Crear y abrir" }));
  }

  test("con Componer a medio llenar, «Abrir la demostración» pregunta antes; «Quedarme» no la crea", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/componer", ligeras({ componer: ComponerSucio }));
    await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Demostración" }));
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir la demostración" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(escrituras()).toEqual([]);
  });

  test("si la carpeta se crea pero no se puede abrir (503), lo dice con su nombre y no dice «No se pudo crear»", async () => {
    const u = userEvent.setup();
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) =>
      metodo === "POST" && ruta === "/v1/casos/actual" ? json({ detalle: "La carpeta de trabajo no se pudo preparar." }, 503) : undefined,
    );
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Nueva");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(
      await within(dialogo()).findByText(
        "La carpeta «Nueva» se creó, pero no se pudo abrir: La carpeta de trabajo no se pudo preparar. Ábrala de la lista cuando quiera.",
      ),
    ).toBeInTheDocument();
    expect(within(dialogo()).queryByText(/No se pudo crear/)).toBeNull();
    expect(servidor.de("PUT", "/v1/carpeta/moneda")).toEqual([]);
  });

  test("en Administración, con un borrador de la Hoja con cambios, crear pregunta antes y «Quedarme» no crea nada", async () => {
    const u = userEvent.setup();
    const estado = estadoInicial();
    estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-25T10:00:00" }];
    servidor = servidorFalso(estado);
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(anaAdministra(), "/administracion", conAdministracion());
    await crearEnAdministracion(u);
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Hoja de Casa Demo. Si cambia de carpeta, se perderán.",
    );
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(escrituras()).toEqual([]);
  });

  test("en Administración la moneda que falló sigue a la vista tras volver a montar la página y se reintenta sola", async () => {
    const u = userEvent.setup();
    let fallar = true;
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) => {
      if (metodo === "PUT" && ruta === "/v1/carpeta/moneda" && fallar) {
        fallar = false;
        return json({ detalle: "La carpeta de trabajo está ocupada: repita en unos segundos." }, 503);
      }
      return undefined;
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(anaAdministra(), "/administracion", conAdministracion());
    await crearEnAdministracion(u);
    expect(
      await screen.findByText(
        "La carpeta «Nueva» se creó y ya trabaja con ella, pero no se pudo declarar su moneda: La carpeta de trabajo está ocupada: repita en unos segundos.",
      ),
    ).toBeInTheDocument();
    // La pagina se volvio a montar (abrir la carpeta) y sigue en la pestaña de las carpetas.
    expect(screen.getByRole("tab", { name: "Carpetas de trabajo" })).toHaveAttribute("aria-selected", "true");
    const antes = escrituras().length;
    await u.click(screen.getByRole("button", { name: "Declarar la moneda" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Declarar la moneda" })).toBeNull());
    expect(escrituras().slice(antes).map((l) => `${l.metodo} ${l.ruta} ${JSON.stringify(l.cuerpo)}`)).toEqual([
      'PUT /v1/carpeta/moneda {"moneda":"Bs"}',
    ]);
    expect(servidor.de("POST", "/v1/casos")).toHaveLength(1);
  });
});

// Menores de la ronda 3 de MOD-3b: el nombre vacio se dice en el navegador; la moneda pendiente es de SU carpeta (se borra
// al cambiar de carpeta y un reintento en curso que falla despues de cambiar no la vuelve a ofrecer en otra).
describe("menores de la ronda 3", () => {
  const PENDIENTE =
    "La carpeta «Nueva» se creó y ya trabaja con ella, pero no se pudo declarar su moneda: La carpeta de trabajo está ocupada: repita en unos segundos.";
  const OCUPADA = () => json({ detalle: "La carpeta de trabajo está ocupada: repita en unos segundos." }, 503);
  const puts = () => servidor.de("PUT", "/v1/carpeta/moneda");

  async function crearNueva(u: ReturnType<typeof userEvent.setup>) {
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "Nueva");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(await within(dialogo()).findByText(PENDIENTE)).toBeInTheDocument();
  }

  test("crear con el nombre vacío lo dice en el campo y no llama a la API", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.type(within(dialogo()).getByRole("textbox", { name: "Nombre de la carpeta" }), "   ");
    await u.selectOptions(within(dialogo()).getByRole("combobox", { name: "Moneda de trabajo" }), "Bs");
    await u.click(within(dialogo()).getByRole("button", { name: "Crear y abrir" }));
    expect(await within(dialogo()).findByText("Escriba un nombre para la carpeta de trabajo.")).toBeInTheDocument();
    expect(servidor.llamadas.filter((l) => l.metodo !== "GET" && !l.ruta.startsWith("/v1/sesion/"))).toEqual([]);
  });

  test("la moneda pendiente se borra al cambiar de carpeta", async () => {
    const u = userEvent.setup();
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) =>
      metodo === "PUT" && ruta === "/v1/carpeta/moneda" ? OCUPADA() : undefined,
    );
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await crearNueva(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Abrir s2" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta de trabajo «s2».")).toBeInTheDocument();
    await abrirCarpetas(u);
    expect(within(dialogo()).queryByText(PENDIENTE)).toBeNull();
    expect(within(dialogo()).queryByRole("button", { name: "Declarar la moneda" })).toBeNull();
    expect(puts()).toHaveLength(1);
  });

  test("mientras se declara la moneda la lista del diálogo no deja abrir otra carpeta", async () => {
    const u = userEvent.setup();
    let soltar: () => void = () => {};
    let primero = true;
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) => {
      if (metodo !== "PUT" || ruta !== "/v1/carpeta/moneda") return undefined;
      if (primero) {
        primero = false;
        return OCUPADA();
      }
      return new Promise<Response>((resolver) => {
        soltar = () => resolver(OCUPADA());
      });
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await crearNueva(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Declarar la moneda" }));
    await waitFor(() => expect(puts()).toHaveLength(2));
    expect(within(dialogo()).getByRole("button", { name: "Abrir s2" })).toBeDisabled();
    soltar();
    await waitFor(() => expect(within(dialogo()).getByRole("button", { name: "Abrir s2" })).toBeEnabled());
  });

  test("un reintento en curso que falla después de abrir otra carpeta no ofrece la moneda en la otra", async () => {
    const u = userEvent.setup();
    let soltar: () => void = () => {};
    let primero = true;
    servidor = servidorFalso(estadoInicial(), (metodo, ruta) => {
      if (metodo !== "PUT" || ruta !== "/v1/carpeta/moneda") return undefined;
      if (primero) {
        primero = false;
        return OCUPADA();
      }
      return new Promise<Response>((resolver) => {
        soltar = () => resolver(OCUPADA());
      });
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    // La lista del diálogo no deja abrir otra mientras se declara: la otra carpeta se abre por la aplicación (como lo haría
    // cualquier pantalla con `abrirCarpeta`).
    function HojaQueAbre() {
      const { abrirCarpeta } = useAplicacion();
      return (
        <>
          <h1>Hoja del proyecto</h1>
          <button type="button" onClick={() => void abrirCarpeta?.("s2.db")}>
            Abrir s2 desde la página
          </button>
        </>
      );
    }
    montarShell(sesionDe("ana"), "/hoja", ligeras({ hoja: HojaQueAbre }));
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await crearNueva(u);
    await u.click(within(dialogo()).getByRole("button", { name: "Declarar la moneda" }));
    await waitFor(() => expect(puts()).toHaveLength(2));
    // Con el reintento en curso se cierra el diálogo y se abre otra carpeta.
    await u.click(within(dialogo()).getByRole("button", { name: "Cerrar" }));
    await u.click(await screen.findByRole("button", { name: "Abrir s2 desde la página" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta de trabajo «s2».")).toBeInTheDocument();
    soltar();
    await new Promise((r) => setTimeout(r, 30));
    await abrirCarpetas(u);
    expect(within(dialogo()).queryByText(PENDIENTE)).toBeNull();
    expect(within(dialogo()).queryByRole("button", { name: "Declarar la moneda" })).toBeNull();
    expect(puts()).toHaveLength(2);
  });
});

describe("subir: lo que se rechaza en el navegador no queda elegido", () => {
  test("un archivo que no es .db vacía el que estaba elegido y «Subir» queda deshabilitado", async () => {
    const u = userEvent.setup({ applyAccept: false });
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Subir un archivo" }));
    const campo = () => dialogo().querySelector<HTMLInputElement>('input[type="file"]')!;
    await u.upload(campo(), new File(["x"], "s1.db"));
    expect(within(dialogo()).getByRole("button", { name: "Subir" })).toBeEnabled();
    await u.upload(campo(), new File(["x"], "libro.xlsx"));
    expect(within(dialogo()).getByText("Solo se aceptan archivos .db.")).toBeInTheDocument();
    expect(within(dialogo()).queryByText(/^s1\.db · /)).toBeNull();
    expect(within(dialogo()).getByRole("button", { name: "Subir" })).toBeDisabled();
  });

  test("un .db de más de 20 MiB se rechaza en el navegador con el texto de la API y no se sube", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await abrirCarpetas(u);
    await u.click(within(dialogo()).getByRole("tab", { name: "Subir un archivo" }));
    const grande = new File(["x"], "grande.db");
    Object.defineProperty(grande, "size", { value: 20 * 1024 * 1024 + 1 });
    await u.upload(dialogo().querySelector<HTMLInputElement>('input[type="file"]')!, grande);
    expect(await within(dialogo()).findByText("El archivo pasa de 20 MiB.")).toBeInTheDocument();
    expect(within(dialogo()).getByRole("button", { name: "Subir" })).toBeDisabled();
    expect(servidor.de("POST", "/v1/casos/subida")).toEqual([]);
  });
});

describe("GestionCarpetas sola (la usa Administración)", () => {
  test("F7: sin la demostración no trae su pestaña y dice por qué", async () => {
    render(<GestionCarpetas alAbrir={vi.fn()} conDemostracion={false} />);
    expect(await screen.findByRole("list", { name: "Carpetas de trabajo de la instalación" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Crear", "Subir un archivo"]);
    expect(screen.getByText("La carpeta de demostración la abre una cuenta que arma presupuestos.")).toBeInTheDocument();
  });

  test("abrir una carpeta de la lista avisa con su nombre", async () => {
    const u = userEvent.setup();
    const alAbrir = vi.fn();
    render(<GestionCarpetas alAbrir={alAbrir} conDemostracion />);
    await u.click(await screen.findByRole("button", { name: "Abrir s1" }));
    expect(alAbrir).toHaveBeenCalledWith("s1.db");
  });

  test("DialogoCarpetas cerrado no pinta nada", () => {
    const { container } = render(<DialogoCarpetas abierto={false} alCerrar={vi.fn()} alAbrir={vi.fn()} conDemostracion />);
    expect(container).toBeEmptyDOMElement();
  });
});
