import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { CampoConBusqueda } from "./CampoConBusqueda";
import type { GrupoDeResultados, OpcionDeBusqueda } from "./logicaBusqueda";

// Diseño de autocompletado (2026-10-21) §3.2 a §3.6 y §8.3; Tarea 10 del plan de montar un presupuesto. `buscar` es
// un doble: cuenta las peticiones, guarda su señal y responde cuando la prueba lo decide. Partidas ficticias.

type Buscar = (q: string, senal: AbortSignal, limite: number) => Promise<GrupoDeResultados<string>[]>;

interface Pendiente {
  q: string;
  senal: AbortSignal;
  limite: number;
  resolver: (grupos: GrupoDeResultados<string>[]) => void;
  rechazar: (error: unknown) => void;
}

const VACIO = {
  titulo: "¿No la encuentra?",
  pasos: "Pruebe con una palabra de la descripción (por ejemplo «tubo»).",
};
const ROTULO_PROPIO = (texto: string) => `Crear una partida nueva con el código «${texto}»`;

function opcion(codigo: string, descripcion: string): OpcionDeBusqueda<string> {
  return { clave: `partida:${codigo}`, principal: descripcion, secundaria: [codigo, "m", "obra civil", "con composición"], valor: codigo };
}

const TRES = [
  opcion("LB-01-EXC", "Excavación en tierra para zanja de tubería"),
  opcion("LB-02-TUB", "Suministro e instalación de tubería PVC"),
  opcion("LB-06-TUB", "Tubo de drenaje ficticio"),
];

function grupo(opciones: OpcionDeBusqueda<string>[], hayMas = false): GrupoDeResultados<string>[] {
  return [{ rotulo: "Partidas del catálogo", opciones, hayMas }];
}

function muchas(n: number): OpcionDeBusqueda<string>[] {
  return Array.from({ length: n }, (_, i) => opcion(`PRU-${String(i + 1).padStart(2, "0")}`, `Partida ficticia ${i + 1}`));
}

let pendientes: Pendiente[];
let buscar: ReturnType<typeof vi.fn<Buscar>>;

function buscarDiferido(): ReturnType<typeof vi.fn<Buscar>> {
  return vi.fn<Buscar>(
    (q, senal, limite) =>
      new Promise((resolver, rechazar) => {
        pendientes.push({ q, senal, limite, resolver, rechazar });
      }),
  );
}

interface Arnes {
  alElegir?: (o: OpcionDeBusqueda<string>) => void;
  alCambiarTexto?: (t: string) => void;
  alExpirar?: () => void;
  alUsar?: (t: string) => void;
  conPropio?: boolean;
  alEnviar?: () => void;
}

// La página controla el texto (§3.2): al elegir pone el código de la partida.
function Pagina({ alElegir, alCambiarTexto, alExpirar, alUsar, conPropio, alEnviar }: Arnes) {
  const [texto, setTexto] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        alEnviar?.();
      }}
    >
      <CampoConBusqueda<string>
        id="partida"
        etiqueta="Código de la partida"
        ayuda="Escriba una palabra de la descripción, por ejemplo «tubo»."
        texto={texto}
        alCambiarTexto={(t) => {
          setTexto(t);
          alCambiarTexto?.(t);
        }}
        buscar={buscar}
        alElegir={(o) => {
          setTexto(o.valor);
          alElegir?.(o);
        }}
        valorPropio={conPropio ? { rotulo: ROTULO_PROPIO, alUsar: (t) => alUsar?.(t) } : undefined}
        vacio={VACIO}
        alExpirar={alExpirar ?? (() => {})}
      />
      <button type="submit">Enviar</button>
    </form>
  );
}

const campo = () => screen.getByRole("combobox", { name: "Código de la partida" });
const lista = () => screen.queryByRole("listbox", { name: "Código de la partida" });
const regiones = () => Array.from(document.querySelectorAll('[role="status"], [aria-live]'));
const estado = () => screen.queryByRole("status");

async function avanzar(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function responder(n: number, grupos: GrupoDeResultados<string>[]) {
  await act(async () => {
    pendientes[n].resolver(grupos);
  });
}

function usuario() {
  return userEvent.setup({ delay: null, advanceTimers: vi.advanceTimersByTime.bind(vi) });
}

// Escribe y espera la pausa; responde con `grupos`. Deja la lista abierta.
async function buscarYResponder(u: ReturnType<typeof usuario>, texto: string, grupos: GrupoDeResultados<string>[]) {
  await u.type(campo(), texto);
  await avanzar(300);
  await responder(pendientes.length - 1, grupos);
}

function activa(): HTMLElement | null {
  const id = campo().getAttribute("aria-activedescendant");
  return id ? document.getElementById(id) : null;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  // Testing Library solo reconoce temporizadores falsos si existe un `jest` global (como en componer/index.test.tsx).
  vi.stubGlobal("jest", { advanceTimersByTime: vi.advanceTimersByTime.bind(vi) });
  pendientes = [];
  buscar = buscarDiferido();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("CampoConBusqueda: cuándo busca (§3.3-1 a 3)", () => {
  test("con una letra no busca; con dos, una sola búsqueda 300 ms después, con límite 8", async () => {
    const u = usuario();
    render(<Pagina />);
    await u.type(campo(), "t");
    await avanzar(1000);
    expect(buscar).not.toHaveBeenCalled();
    await u.type(campo(), "u");
    await avanzar(299);
    expect(buscar).not.toHaveBeenCalled();
    await avanzar(1);
    expect(buscar).toHaveBeenCalledTimes(1);
    expect(buscar.mock.calls[0][0]).toBe("tu");
    expect(buscar.mock.calls[0][2]).toBe(8);
  });

  test("teclear seguido hace una sola búsqueda, con el último texto y sin espacios en los bordes", async () => {
    const u = usuario();
    render(<Pagina />);
    await u.type(campo(), " tubo ");
    await avanzar(300);
    expect(buscar).toHaveBeenCalledTimes(1);
    expect(buscar.mock.calls[0][0]).toBe("tubo");
  });

  test("la petición vieja se aborta, su respuesta tardía se descarta y nunca hay dos en vuelo", async () => {
    const u = usuario();
    render(<Pagina />);
    await u.type(campo(), "tu");
    await avanzar(300);
    expect(pendientes).toHaveLength(1);
    await u.type(campo(), "bo");
    expect(pendientes[0].senal.aborted).toBe(true);
    await avanzar(300);
    expect(pendientes).toHaveLength(2);
    expect(pendientes[1].q).toBe("tubo");
    expect(pendientes.filter((p) => !p.senal.aborted)).toHaveLength(1);
    await responder(1, grupo([TRES[2]]));
    await responder(0, grupo([opcion("VIEJA-01", "Respuesta vieja de «tu»")]));
    expect(screen.queryByText("Respuesta vieja de «tu»")).not.toBeInTheDocument();
    expect(within(lista()!).getAllByRole("option")).toHaveLength(1);
    expect(within(lista()!).getByRole("option")).toHaveTextContent("Tubo de drenaje ficticio");
  });

  test("si el padre cambia el texto (al elegir), no se vuelve a buscar", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.keyboard("{ArrowDown}{Enter}");
    expect(campo()).toHaveValue("LB-01-EXC");
    await avanzar(1000);
    expect(buscar).toHaveBeenCalledTimes(1);
  });

  test("el campo admite hasta 80 caracteres, como el servidor", () => {
    render(<Pagina />);
    expect(campo()).toHaveAttribute("maxLength", "80");
  });
});

describe("CampoConBusqueda: teclado (§3.3-7 a 9 y §3.6)", () => {
  test("↓ abre y activa la primera, ↓↓ la segunda; Enter la entrega sin enviar el formulario", async () => {
    const u = usuario();
    const alElegir = vi.fn();
    const alEnviar = vi.fn();
    render(<Pagina alElegir={alElegir} alEnviar={alEnviar} />);
    await buscarYResponder(u, "tub", grupo(TRES));
    expect(campo()).toHaveAttribute("aria-expanded", "true");
    expect(campo()).not.toHaveAttribute("aria-activedescendant");
    await u.keyboard("{ArrowDown}");
    expect(activa()).toHaveTextContent("Excavación en tierra");
    await u.keyboard("{ArrowDown}");
    expect(activa()).toHaveTextContent("Suministro e instalación");
    expect(activa()).toHaveAttribute("aria-selected", "true");
    expect(within(lista()!).getAllByRole("option").filter((o) => o.getAttribute("aria-selected") === "true")).toHaveLength(1);
    await u.keyboard("{Enter}");
    expect(alElegir).toHaveBeenCalledTimes(1);
    expect(alElegir.mock.calls[0][0].valor).toBe("LB-02-TUB");
    expect(alEnviar).not.toHaveBeenCalled();
    expect(campo()).toHaveAttribute("aria-expanded", "false");
    expect(lista()).not.toBeInTheDocument();
    expect(campo()).toHaveFocus();
  });

  test("Enter sin haber navegado no elige nada ni cambia el texto", async () => {
    const u = usuario();
    const alElegir = vi.fn();
    render(<Pagina alElegir={alElegir} />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.keyboard("{Enter}");
    expect(alElegir).not.toHaveBeenCalled();
    expect(campo()).toHaveValue("tub");
  });

  test("↓ desde la última vuelve al campo; ↑ desde el campo va a la última", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.keyboard("{ArrowUp}");
    expect(activa()).toHaveTextContent("Tubo de drenaje ficticio");
    await u.keyboard("{ArrowDown}");
    expect(campo()).not.toHaveAttribute("aria-activedescendant");
    expect(campo()).toHaveAttribute("aria-expanded", "true");
  });

  test("Esc cierra sin borrar lo escrito; Alt+↓ vuelve a abrir sin mover la opción activa", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.keyboard("{ArrowDown}{Escape}");
    expect(campo()).toHaveAttribute("aria-expanded", "false");
    expect(campo()).toHaveValue("tub");
    await u.keyboard("{Escape}"); // sin nada elegido, Esc con la lista cerrada no borra lo escrito
    expect(campo()).toHaveValue("tub");
    await u.keyboard("{Alt>}{ArrowDown}{/Alt}");
    expect(campo()).toHaveAttribute("aria-expanded", "true");
    expect(campo()).not.toHaveAttribute("aria-activedescendant");
    expect(buscar).toHaveBeenCalledTimes(1); // reabre lo que ya tenía, sin pedir de nuevo
  });

  test("con un valor elegido y la lista cerrada, Esc pide al padre limpiar", async () => {
    const u = usuario();
    const alCambiarTexto = vi.fn();
    render(<Pagina alCambiarTexto={alCambiarTexto} />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.keyboard("{ArrowDown}{Enter}");
    expect(campo()).toHaveValue("LB-01-EXC");
    alCambiarTexto.mockClear();
    await u.keyboard("{Escape}");
    expect(alCambiarTexto).toHaveBeenCalledWith("");
    expect(campo()).toHaveValue("");
  });

  test("Tab cierra la lista y no elige", async () => {
    const u = usuario();
    const alElegir = vi.fn();
    render(<Pagina alElegir={alElegir} />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.keyboard("{ArrowDown}");
    await u.tab();
    expect(alElegir).not.toHaveBeenCalled();
    expect(campo()).toHaveAttribute("aria-expanded", "false");
    expect(campo()).toHaveValue("tub");
  });

  test("un clic en una opción la elige y el foco sigue en el campo", async () => {
    const u = usuario();
    const alElegir = vi.fn();
    render(<Pagina alElegir={alElegir} />);
    await buscarYResponder(u, "tub", grupo(TRES));
    await u.click(within(lista()!).getAllByRole("option")[2]);
    expect(alElegir.mock.calls[0][0].valor).toBe("LB-06-TUB");
    expect(campo()).toHaveFocus();
  });

  test("el botón «Borrar» pide al padre limpiar", async () => {
    const u = usuario();
    const alCambiarTexto = vi.fn();
    render(<Pagina alCambiarTexto={alCambiarTexto} />);
    await u.type(campo(), "tu");
    alCambiarTexto.mockClear();
    await u.click(screen.getByRole("button", { name: "Borrar" }));
    expect(alCambiarTexto).toHaveBeenCalledWith("");
    expect(campo()).toHaveValue("");
  });
});

describe("CampoConBusqueda: ARIA (§3.6)", () => {
  test("combobox con lista, aria-controls a la lista que existe y grupo con su rótulo", async () => {
    const u = usuario();
    render(<Pagina />);
    expect(campo()).toHaveAttribute("aria-autocomplete", "list");
    expect(campo()).toHaveAttribute("aria-expanded", "false");
    await buscarYResponder(u, "tub", grupo(TRES));
    const id = campo().getAttribute("aria-controls");
    expect(id).toBeTruthy();
    expect(document.getElementById(id!)).toBe(lista());
    const grupoDeOpciones = within(lista()!).getByRole("group", { name: "Partidas del catálogo" });
    expect(within(grupoDeOpciones).getAllByRole("option")).toHaveLength(3);
    await u.keyboard("{ArrowDown}");
    expect(document.getElementById(campo().getAttribute("aria-activedescendant")!)).toHaveAttribute("role", "option");
  });

  test("el código va en Plex Mono y la línea de abajo dice código, unidad, tipo de obra y composición", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "tub", grupo(TRES));
    const primera = within(lista()!).getAllByRole("option")[0];
    expect(primera).toHaveTextContent("LB-01-EXC · m · obra civil · con composición");
    expect(within(primera).getByText("LB-01-EXC")).toHaveClass("silice-busqueda__codigo");
  });

  test("resalta en negrita lo que coincide, como texto", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "tubo", grupo([TRES[2]]));
    const negritas = within(lista()!).getAllByText("Tubo", { selector: "strong" });
    expect(negritas).toHaveLength(1);
  });
});

describe("CampoConBusqueda: región de estado (§3.6, VB-18)", () => {
  test("sin foco no hay región; con foco dice el mínimo de letras; al salir se desmonta", async () => {
    const u = usuario();
    render(<Pagina />);
    expect(estado()).not.toBeInTheDocument();
    await u.click(campo());
    expect(estado()).toHaveTextContent("Escriba al menos 2 letras o un código");
    await u.tab();
    expect(estado()).not.toBeInTheDocument();
  });

  test("anuncia la cuenta 400 ms después de pintar la lista, una vez, y nunca queda vacía", async () => {
    const u = usuario();
    render(<Pagina />);
    await u.click(campo());
    await u.type(campo(), "tub");
    for (const r of regiones()) expect(r.textContent?.trim()).not.toBe("");
    await avanzar(300);
    await responder(0, grupo(TRES));
    expect(estado()).not.toHaveTextContent("3 resultados");
    await avanzar(400);
    expect(estado()).toHaveTextContent("3 resultados. Use las flechas para recorrerlos.");
    expect(regiones()).toHaveLength(1);
    // Moverse por la lista no vuelve a anunciar la cuenta (no se anuncia cada tecla).
    await u.keyboard("{ArrowDown}");
    await avanzar(1000);
    expect(estado()).toHaveTextContent("3 resultados. Use las flechas para recorrerlos.");
    for (const r of regiones()) expect(r.textContent?.trim()).not.toBe("");
  });

  test("uno y ninguno", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "tubo", grupo([TRES[2]]));
    await avanzar(400);
    expect(estado()).toHaveTextContent(/^1 resultado\.$/);
    await u.clear(campo());
    await u.type(campo(), "zz");
    await avanzar(300);
    await responder(1, grupo([]));
    await avanzar(400);
    expect(estado()).toHaveTextContent("Sin resultados para «zz».");
  });

  test("«Buscando…» solo si la respuesta tarda 700 ms", async () => {
    const u = usuario();
    render(<Pagina />);
    await u.type(campo(), "tub");
    await avanzar(300 + 699);
    expect(estado()).not.toHaveTextContent("Buscando…");
    await avanzar(1);
    expect(estado()).toHaveTextContent("Buscando…");
  });
});

describe("CampoConBusqueda: «no lo encuentro» y valor propio (§3.5)", () => {
  test("sin resultados dice qué escribió y qué hacer, y conserva lo escrito", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "zz", grupo([]));
    expect(screen.getByText("No encontramos «zz».")).toBeInTheDocument();
    expect(screen.getByText(/¿No la encuentra\? Pruebe con una palabra de la descripción/)).toBeInTheDocument();
    expect(campo()).toHaveValue("zz");
  });

  test("«Crear una partida nueva con el código «X»» va al final, después de los resultados, y usa lo escrito", async () => {
    const u = usuario();
    const alUsar = vi.fn();
    const alElegir = vi.fn();
    render(<Pagina conPropio alUsar={alUsar} alElegir={alElegir} />);
    await buscarYResponder(u, "LB-07", grupo(TRES));
    const opciones = within(lista()!).getAllByRole("option");
    expect(opciones).toHaveLength(4);
    expect(opciones[3]).toHaveTextContent("Crear una partida nueva con el código «LB-07»");
    await u.keyboard("{ArrowUp}{Enter}");
    expect(alUsar).toHaveBeenCalledWith("LB-07");
    expect(alElegir).not.toHaveBeenCalled();
    expect(campo()).toHaveAttribute("aria-expanded", "false");
  });

  test("sin resultados, el valor propio sigue ofrecido", async () => {
    const u = usuario();
    render(<Pagina conPropio />);
    await buscarYResponder(u, "LB-07", grupo([]));
    expect(within(lista()!).getByRole("option")).toHaveTextContent("Crear una partida nueva con el código «LB-07»");
  });

  test("sin valorPropio no hay esa opción", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "LB-07", grupo(TRES));
    expect(screen.queryByText(/Crear una partida nueva/)).not.toBeInTheDocument();
  });
});

describe("CampoConBusqueda: «Ver más resultados» (§3.3-5)", () => {
  test("al final del grupo, se alcanza con ↓, repite con límite 20 sin elegir y deja activa la primera nueva", async () => {
    const u = usuario();
    const alElegir = vi.fn();
    render(<Pagina alElegir={alElegir} />);
    await buscarYResponder(u, "ficticia", grupo(muchas(8), true));
    for (let i = 0; i < 9; i++) await u.keyboard("{ArrowDown}");
    expect(activa()).toHaveTextContent("Ver más resultados");
    expect(activa()).toHaveAttribute("role", "option");
    await u.keyboard("{Enter}");
    expect(alElegir).not.toHaveBeenCalled();
    expect(buscar).toHaveBeenCalledTimes(2);
    expect(buscar.mock.calls[1][0]).toBe("ficticia");
    expect(buscar.mock.calls[1][2]).toBe(20);
    await responder(1, grupo(muchas(12)));
    expect(campo()).toHaveFocus();
    expect(within(lista()!).getAllByRole("option")).toHaveLength(12);
    expect(activa()).toHaveTextContent("Partida ficticia 9");
    await avanzar(400);
    expect(estado()).toHaveTextContent("Se muestran 12 resultados");
  });

  test("con 20 y más por ver, no ofrece otra vez «Ver más» y pide escribir más letras", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(u, "ficticia", grupo(muchas(8), true));
    for (let i = 0; i < 9; i++) await u.keyboard("{ArrowDown}");
    await u.keyboard("{Enter}");
    await responder(1, grupo(muchas(20), true));
    expect(screen.queryByText("Ver más resultados")).not.toBeInTheDocument();
    expect(screen.getByText("Hay más resultados: escriba más letras para acotar.")).toBeInTheDocument();
  });
});

describe("CampoConBusqueda: errores (§3.3-10)", () => {
  test("401 avisa a la página una sola vez y no muestra nada en la lista", async () => {
    const u = usuario();
    const alExpirar = vi.fn();
    render(<Pagina alExpirar={alExpirar} />);
    await u.type(campo(), "tub");
    await avanzar(300);
    await act(async () => pendientes[0].rechazar(new ErrorDeApi(401, "La sesión venció.")));
    expect(alExpirar).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/La sesión venció/)).not.toBeInTheDocument();
  });

  test.each([
    [403, "Su cuenta no tiene permiso para esta acción.", "Su cuenta no puede usar esta búsqueda. Su cuenta no tiene permiso para esta acción."],
    [422, "La búsqueda no es válida: tubXYZ", "La búsqueda no es válida: escriba otra cosa."],
    [503, "No se pudo leer el catálogo de la carpeta de trabajo.", "No se pudo leer el catálogo de la carpeta de trabajo."],
    [0, "No se pudo hablar con el programa de Sílice.", "No se pudo hablar con el programa de Sílice."],
  ])("%i muestra su mensaje y el campo sigue editable", async (codigo, detalle, mensaje) => {
    const u = usuario();
    render(<Pagina conPropio />);
    await u.type(campo(), "tubXYZ");
    await avanzar(300);
    await act(async () => pendientes[0].rechazar(new ErrorDeApi(codigo, detalle)));
    expect(screen.getByText(mensaje)).toBeInTheDocument();
    // El 422 no repite lo escrito: el detalle del servidor no se muestra, solo el mensaje fijo.
    if (codigo === 422) expect(screen.queryByText(detalle)).not.toBeInTheDocument();
    // Un error de búsqueda no impide seguir: lo escrito se puede usar tal cual.
    expect(within(lista()!).getByRole("option")).toHaveTextContent("Crear una partida nueva con el código «tubXYZ»");
    await avanzar(400);
    expect(estado()).toHaveTextContent(`No se pudo buscar: ${mensaje}`);
    await u.type(campo(), "1");
    expect(campo()).toHaveValue("tubXYZ1");
  });

  test("un aborto no es un error que mostrar", async () => {
    const u = usuario();
    render(<Pagina />);
    await u.type(campo(), "tub");
    await avanzar(300);
    await act(async () => pendientes[0].rechazar(new DOMException("aborted", "AbortError")));
    expect(screen.queryByText(/No se pudo/)).not.toBeInTheDocument();
  });
});

describe("CampoConBusqueda: texto de la API como texto (§3.4)", () => {
  test("una descripción con marcas se ve literal y no crea elementos", async () => {
    const u = usuario();
    render(<Pagina />);
    await buscarYResponder(
      u,
      "ma",
      grupo([opcion("MAL-01", "<img src=x onerror=alert(1)>"), opcion("MAL-02", "&lt;b&gt;negrita&lt;/b&gt;")]),
    );
    expect(document.querySelector("img")).toBeNull();
    const opciones = within(lista()!).getAllByRole("option");
    expect(opciones[0]).toHaveTextContent("<img src=x onerror=alert(1)>");
    expect(opciones[1]).toHaveTextContent("&lt;b&gt;negrita&lt;/b&gt;");
  });

  test("el código del componente no convierte montos ni inyecta HTML", () => {
    const nodo = (
      globalThis as unknown as {
        process: { cwd(): string; getBuiltinModule(n: "node:fs"): { readFileSync(r: string, c: string): string } };
      }
    ).process;
    const fs = nodo.getBuiltinModule("node:fs");
    for (const archivo of ["src/comun/CampoConBusqueda.tsx", "src/comun/logicaBusqueda.ts"]) {
      const codigo = fs.readFileSync(`${nodo.cwd()}/${archivo}`, "utf-8");
      for (const prohibido of ["Number(", "parseFloat(", "toFixed(", "dangerouslySetInnerHTML", "innerHTML"]) {
        expect(codigo.includes(prohibido), `${archivo}: ${prohibido}`).toBe(false);
      }
    }
  });
});

describe("CampoConBusqueda: en una celda (§3.7)", () => {
  test("con enCelda la lista se pinta en document.body con position fixed bajo el campo", async () => {
    const u = usuario();
    function EnCelda() {
      const [texto, setTexto] = useState("");
      return (
        <div data-testid="celda" style={{ overflow: "hidden" }}>
          <CampoConBusqueda<string>
            id="celda"
            etiqueta="Descripción, fila 1"
            texto={texto}
            alCambiarTexto={setTexto}
            buscar={buscar}
            alElegir={(o) => setTexto(o.valor)}
            vacio={VACIO}
            alExpirar={() => {}}
            enCelda
          />
        </div>
      );
    }
    render(<EnCelda />);
    const entrada = screen.getByRole("combobox", { name: "Descripción, fila 1" });
    entrada.getBoundingClientRect = () => ({ top: 100, bottom: 132, left: 40, right: 240, width: 200, height: 32, x: 40, y: 100, toJSON: () => ({}) });
    await u.type(entrada, "tub");
    await avanzar(300);
    await responder(0, grupo(TRES));
    const listaEnCelda = screen.getByRole("listbox", { name: "Descripción, fila 1" });
    expect(screen.getByTestId("celda")).not.toContainElement(listaEnCelda);
    const panel = listaEnCelda.closest(".silice-busqueda__panel") as HTMLElement;
    expect(panel.parentElement).toBe(document.body);
    expect(panel.style.position).toBe("fixed");
    expect(panel.style.top).toBe("132px");
    expect(panel.style.left).toBe("40px");
    fireEvent.keyDown(entrada, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
