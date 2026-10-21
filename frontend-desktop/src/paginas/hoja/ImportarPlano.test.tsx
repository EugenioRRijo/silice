import { cleanup, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  ALTURAS_OF001,
  AVISO_PENDIENTES,
  MENSAJE_DE_FUSION,
  detenida,
  importada,
  rechazada,
  respuestaDeFusion,
  sinPendientes,
} from "./datosDePlano";
import { ImportarPlano } from "./ImportarPlano";
import { olvidarImportaciones } from "./useImportacion";
import type { Resumen } from "./logica";

// Rebanada 3e-2 (frente): el flujo «Importar plano (DXF o IFC)» de la pestaña Espacio. El servidor se simula con las
// respuestas del contrato (docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md, P1 a P6). Los literales (textos, conteos 33/0/9/6,
// 48 líneas de informe, 6 alturas, 2 circuitos, 6+6+21 filas) salen de la clásica (ui/paginas/hoja.py:1238-1385) y de
// tests/unit/test_ui_hoja_planos.py, escritos a mano.
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const ID = "id-borrador-aaaaaaaaaaaa";
// Las rutas del plano de cualquier borrador: el id de cada prueba es propio (lo último que se leyó se recuerda por id).
const RUTA_DEL_PLANO = /^\/v1\/hoja\/borradores\/[^/]+\/plano(\/[a-z]+)?$/;
const REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo.";
const CASO_CAMBIO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.";
const SIN_BORRADOR =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";

describe("Importar plano (3e-2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alAusente = vi.fn();
  const alAceptar = vi.fn<(r: Resumen) => void>();
  const alRecargar = vi.fn<() => Promise<void>>();
  const alReabrir = vi.fn();
  const alExpirar = vi.fn();
  const alOcuparse = vi.fn<(ocupada: boolean) => void>();
  // Lo que el servidor simulado contesta a cada ruta; cada prueba lo cambia.
  let alLeer: (cuerpo: FormData) => Response | Promise<Response>;
  let alUnidad: (cuerpo: { rev: number; unidades: string }) => Response | Promise<Response>;
  let alAlturas: (cuerpo: { rev: number; alturas: Record<string, string> }) => Response | Promise<Response>;
  let alCircuitos: (cuerpo: { rev: number; circuitos: Record<string, string[]> }) => Response | Promise<Response>;
  let alFusionar: (cuerpo: { rev: number }) => Response | Promise<Response>;
  let alDescartar: () => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    for (const f of [alAusente, alAceptar, alRecargar, alReabrir, alExpirar, alOcuparse]) f.mockReset();
    alRecargar.mockResolvedValue(undefined);
    alLeer = () => json(importada());
    alUnidad = () => json(importada());
    alAlturas = () => json(importada({ alturas_pendientes: [] }));
    alCircuitos = () => json(importada({ circuitos_supuestos: [] }));
    alFusionar = (c) => json(respuestaDeFusion(c.rev + 1));
    alDescartar = () => new Response(null, { status: 204 });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const camino = String(ruta);
      const metodo = init?.method ?? "GET";
      const cuerpo = init?.body;
      const m = RUTA_DEL_PLANO.exec(camino);
      if (m === null) throw new Error(`ruta no simulada: ${metodo} ${camino}`);
      const parte = m[1] ?? "";
      if (parte === "" && metodo === "POST") return alLeer(cuerpo as FormData);
      if (parte === "" && metodo === "DELETE") return alDescartar();
      if (parte === "/unidad") return alUnidad(JSON.parse(String(cuerpo)));
      if (parte === "/alturas") return alAlturas(JSON.parse(String(cuerpo)));
      if (parte === "/circuitos") return alCircuitos(JSON.parse(String(cuerpo)));
      if (parte === "/fusionar") return alFusionar(JSON.parse(String(cuerpo)));
      throw new Error(`ruta no simulada: ${metodo} ${camino}`);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  let contador = 0;
  // Cada prueba usa un borrador propio: lo último que se leyó de un borrador se recuerda por su id (ver la última prueba).
  let id = ID;
  function montar(rev = 3, extra: { ocupadoPorEdicion?: boolean; id?: string } = {}) {
    contador += 1;
    id = extra.id ?? `${ID.slice(0, 18)}${String(contador).padStart(6, "0")}`;
    const propiedades = (r: number, o?: boolean) => (
      <ImportarPlano
        id={id}
        rev={r}
        ocupadoPorEdicion={o ?? extra.ocupadoPorEdicion ?? false}
        alAusente={alAusente}
        alAceptar={alAceptar}
        alRecargar={alRecargar}
        alReabrir={alReabrir}
        alExpirar={alExpirar}
        alOcuparse={alOcuparse}
      />
    );
    const dibujo = render(propiedades(rev));
    return { ...dibujo, conRev: (r: number) => dibujo.rerender(propiedades(r)), propiedades };
  }

  const campoDeArchivo = () => document.querySelector('input[type="file"]') as HTMLInputElement;
  const llamadas = () => fetchFalso.mock.calls;

  async function abrir(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.click(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" }));
  }
  async function leer(usuario: ReturnType<typeof userEvent.setup>, nombre = "of001.dxf") {
    await abrir(usuario);
    await usuario.upload(campoDeArchivo(), new File(["0\nEOF"], nombre));
    await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
  }
  const encabezado = (nombre: string) => screen.findByRole("heading", { name: nombre });

  describe("3e-F1: elegir y leer el plano", () => {
    test("plegado al montar: el botón del bloque dice que está cerrado, sin pedir nada", () => {
      montar();
      const boton = screen.getByRole("button", { name: "Importar plano (DXF o IFC)" });
      expect(boton).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByRole("button", { name: "Leer plano" })).toBeNull();
      expect(llamadas()).toHaveLength(0);
    });

    test("el título del bloque es un h2 de la página", () => {
      montar();
      expect(screen.getByRole("heading", { level: 2, name: "Importar plano (DXF o IFC)" })).toBeInTheDocument();
    });

    test("abierto: dice qué formatos acepta (la ayuda de la clásica) y ofrece la zona de soltar y «Leer plano»", async () => {
      const usuario = userEvent.setup();
      montar();
      await abrir(usuario);
      expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toHaveAttribute("aria-expanded", "true");
      expect(
        screen.getByText(
          "Suba un plano en formato DXF o IFC. El plano crea filas en el borrador de esta hoja, con el archivo como origen de medida, y un informe de lo que importó, lo que no reconoció, lo que aproximó y lo que queda pendiente. Nada salta la hoja ni la auditoría: las filas entran para que las revise.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Suelte aquí el plano .dxf o .ifc, o haga clic para elegirlo" })).toBeInTheDocument();
      expect(campoDeArchivo()).toHaveAttribute("accept", ".dxf,.ifc");
      expect(screen.getByRole("button", { name: "Leer plano" })).toBeInTheDocument();
    });

    test("con otra extensión no sube nada y lo dice antes de subir", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      await abrir(usuario);
      await usuario.upload(campoDeArchivo(), new File(["x"], "libro.exe"));
      expect(screen.getByText("Solo se aceptan archivos .dxf o .ifc.")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      expect(llamadas()).toHaveLength(0);
      // no queda ningún archivo elegido: pulsar «Leer plano» recuerda elegir uno
      expect(screen.getByText("Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano.")).toBeInTheDocument();
    });

    test("sin archivo elegido, «Leer plano» dice el texto de la clásica y no manda nada", async () => {
      const usuario = userEvent.setup();
      montar();
      await abrir(usuario);
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      expect(screen.getByText("Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano.")).toBeInTheDocument();
      expect(llamadas()).toHaveLength(0);
    });

    test("el archivo elegido se nombra y «Leer plano» lo manda por multipart con el rev vigente", async () => {
      const usuario = userEvent.setup();
      montar(7);
      await abrir(usuario);
      await usuario.upload(campoDeArchivo(), new File(["0\nEOF"], "of001.DXF"));
      expect(screen.getByText("Archivo elegido: of001.DXF")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      await encabezado("Informe de la importación de of001.dxf");
      const [ruta, init] = llamadas()[0]!;
      expect(String(ruta)).toBe(`/v1/hoja/borradores/${id}/plano`);
      expect(init?.method).toBe("POST");
      const cuerpo = init?.body as FormData;
      expect(cuerpo).toBeInstanceOf(FormData);
      expect(cuerpo.get("rev")).toBe("7");
      expect((cuerpo.get("archivo") as File).name).toBe("of001.DXF");
    });

    test("el nombre del archivo es texto: nada de HTML, y un nombre largo no cuesta un segundo", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      await abrir(usuario);
      await usuario.upload(campoDeArchivo(), new File(["x"], "<img src=x onerror=alert(1)>.dxf"));
      expect(screen.getByText("Archivo elegido: <img src=x onerror=alert(1)>.dxf")).toBeInTheDocument();
      expect(document.querySelector("img")).toBeNull();
      // Carbon (la zona de soltar, src/comun) tarda tiempo cuadrático con el nombre: 20 000 caracteres ya cuestan 1,3 s; se declara en el informe.
      const largo = `${"a".repeat(3_000)}.dxf`;
      const inicio = performance.now();
      fireEvent.change(campoDeArchivo(), { target: { files: [new File(["x"], largo)] } });
      const dicho = await waitFor(() => {
        const p = [...document.querySelectorAll("p")].find((e) => (e.textContent ?? "").startsWith("Archivo elegido: aaa"));
        if (!p) throw new Error("falta");
        return p;
      });
      expect(dicho.textContent).toBe(`Archivo elegido: ${largo}`);
      expect(performance.now() - inicio).toBeLessThan(1000);
    });

    test("el 422 de la extensión del servidor se muestra tal cual y se puede subir otro", async () => {
      const usuario = userEvent.setup();
      const texto = "El archivo «plano.dxf» no es un plano que se pueda importar. Suba un plano en formato DXF o IFC.";
      alLeer = () => json({ detalle: texto }, 422);
      montar();
      await leer(usuario, "plano.dxf");
      expect(await screen.findByText(texto)).toBeInTheDocument();
      alLeer = () => json(importada());
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      await encabezado("Informe de la importación de of001.dxf");
      expect(screen.queryByText(texto)).toBeNull();
    });

    test("si falta el lector, se dice sin el comando (solo en la vista)", async () => {
      const usuario = userEvent.setup();
      alLeer = () =>
        json(
          {
            detalle:
              "Falta instalar el componente para leer planos DXF. Instale el extra «planos» con el comando «uv sync --extra planos» y vuelva a intentarlo.",
          },
          422,
        );
      montar();
      await leer(usuario);
      expect(
        await screen.findByText("Falta instalar el componente para leer planos DXF. Pídalo a quien instaló Sílice y vuelva a intentarlo."),
      ).toBeInTheDocument();
      expect(screen.queryByText(/uv sync/)).toBeNull();
    });

    test("mientras sube: el bloque está ocupado, lo dice y no admite una segunda petición", async () => {
      const usuario = userEvent.setup();
      let soltar: (r: Response) => void = () => undefined;
      alLeer = () => new Promise<Response>((resolver) => (soltar = resolver));
      montar();
      await leer(usuario);
      const cuerpo = document.getElementById(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" }).getAttribute("aria-controls")!)!;
      expect(cuerpo).toHaveAttribute("aria-busy", "true");
      // el anuncio no vive dentro de una región ocupada: algunos lectores retienen lo que se anuncia ahí
      const estado = screen.getByRole("status");
      expect(estado).toHaveTextContent("Leyendo el plano…");
      expect(estado.closest('[aria-busy="true"]')).toBeNull();
      expect(screen.getByRole("button", { name: "Leer plano" })).toBeDisabled();
      expect(llamadas()).toHaveLength(1);
      soltar(json(importada()));
      await encabezado("Informe de la importación de of001.dxf");
      expect(cuerpo).toHaveAttribute("aria-busy", "false");
    });
  });

  describe("3e-F2: los tres estados de la respuesta", () => {
    test("rechazada: el motivo con las palabras de la clásica, sin «Fusionar», y se puede descartar", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(rechazada());
      montar();
      await leer(usuario, "roto.dxf");
      expect(await screen.findByText("No se pudo importar «roto.dxf»: el archivo no es un dibujo DXF válido")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeNull();
      expect(screen.getByRole("button", { name: "Descartar la importación" })).toBeInTheDocument();
    });

    test("rechazada: se puede subir otro plano sin descartar", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(rechazada());
      montar();
      await leer(usuario, "roto.dxf");
      await screen.findByText(/No se pudo importar/);
      alLeer = () => json(importada());
      await usuario.upload(campoDeArchivo(), new File(["0\nEOF"], "of001.dxf"));
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      await encabezado("Informe de la importación de of001.dxf");
      expect(screen.queryByText(/No se pudo importar/)).toBeNull();
    });

    test("detenida: pide la unidad con las del servidor y reanuda con la elegida (P2)", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(detenida());
      montar(4);
      await leer(usuario, "sin_unidad.dxf");
      expect(await screen.findByText("El dibujo no declara su unidad. Elija la unidad en que está dibujado.")).toBeInTheDocument();
      const selector = screen.getByRole("combobox", { name: "Unidad del dibujo" });
      expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual(["m", "cm", "mm", "dm", "in", "ft"]);
      expect(screen.queryByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeNull();
      await usuario.selectOptions(selector, "cm");
      alUnidad = (c) => {
        expect(c).toEqual({ rev: 4, unidades: "cm" });
        return json(importada({ archivo: "sin_unidad.dxf" }));
      };
      await usuario.click(screen.getByRole("button", { name: "Continuar con esta unidad" }));
      await encabezado("Informe de la importación de sin_unidad.dxf");
      expect(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeInTheDocument();
    });

    test("detenida: sin tocar el selector se manda la primera unidad del servidor", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(detenida({ unidades: ["mm", "m"] }));
      montar();
      await leer(usuario);
      const visto = vi.fn((c: { unidades: string }) => c.unidades);
      alUnidad = (c) => {
        visto(c);
        return json(importada());
      };
      await usuario.click(await screen.findByRole("button", { name: "Continuar con esta unidad" }));
      await encabezado("Informe de la importación de of001.dxf");
      expect(visto).toHaveReturnedWith("mm");
    });

    test("importada: el encabezado, los cuatro conteos y las 48 líneas del informe", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Informe de la importación de of001.dxf");
      for (const [rotulo, n] of [
        ["Importado", "33"],
        ["No reconocido", "0"],
        ["Aproximado", "9"],
        ["Pendiente", "6"],
      ] as const) {
        const termino = screen.getByText(rotulo, { selector: "dt" });
        expect(termino.nextElementSibling).toHaveTextContent(n);
      }
      const tabla = screen.getByRole("table", { name: "Informe de la importación" });
      expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
        "Tipo",
        "En el plano",
        "Fila de la hoja",
        "Qué pasó",
      ]);
      expect(within(tabla).getAllByRole("row")).toHaveLength(1 + 48);
    });

    test("importada: seis alturas con su etiqueta, vacías, y el texto de ayuda", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      expect(
        screen.getByText(
          "El plano no trae la altura de estos ambientes. Escríbala en metros (por ejemplo 2,50); los que deje en blanco siguen pendientes.",
        ),
      ).toBeInTheDocument();
      for (const a of ALTURAS_OF001) {
        expect(screen.getByRole("textbox", { name: `Altura de ${a.id} (${a.nombre}), en metros` })).toHaveValue("");
      }
      expect(screen.getAllByRole("textbox", { name: /^Altura de / })).toHaveLength(6);
      expect(screen.getByRole("button", { name: "Cargar alturas" })).toBeInTheDocument();
    });

    test("importada: dos circuitos con sus cuatro campos precargados con lo supuesto", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Circuitos por declarar");
      expect(
        screen.getByText(
          "El plano no dice cuántos conductores tiene cada circuito ni cuántos puntos admite: se supusieron. Confírmelos o corríjalos; mientras sean supuestos, la auditoría lo advierte.",
        ),
      ).toBeInTheDocument();
      for (const c of ["C1", "C2"]) {
        for (const [campo, valor] of [
          ["Conductores de fase", "1"],
          ["Conductores de neutro", "1"],
          ["Conductores de tierra", "1"],
          ["Puntos máximos", "6"],
        ]) {
          expect(screen.getByRole("textbox", { name: `${campo} del circuito ${c}` })).toHaveValue(valor);
        }
      }
      expect(screen.getByRole("button", { name: "Declarar circuitos" })).toBeInTheDocument();
    });

    test("importada con pendientes: el aviso del servidor, y «Fusionar» y «Descartar»", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Informe de la importación de of001.dxf");
      expect(screen.getByText(AVISO_PENDIENTES)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "Descartar la importación" })).toBeEnabled();
    });

    test("importada sin pendientes: no hay alturas, circuitos ni aviso", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(sinPendientes());
      montar();
      await leer(usuario);
      await encabezado("Informe de la importación de of001.dxf");
      expect(screen.queryByRole("heading", { name: "Alturas pendientes" })).toBeNull();
      expect(screen.queryByRole("heading", { name: "Circuitos por declarar" })).toBeNull();
      expect(screen.queryByText(AVISO_PENDIENTES)).toBeNull();
      expect(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeInTheDocument();
    });

    test("leer otro plano reemplaza la importación anterior", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Informe de la importación de of001.dxf");
      alLeer = () => json(importada({ archivo: "piso2.dxf" }));
      await usuario.upload(campoDeArchivo(), new File(["0\nEOF"], "piso2.dxf"));
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      await encabezado("Informe de la importación de piso2.dxf");
      expect(screen.queryByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeNull();
    });
  });

  describe("alturas y circuitos (P3, P4)", () => {
    test("cargar alturas manda el TEXTO escrito, con coma, y el rev vigente; al quedar sin pendientes lo dice", async () => {
      const usuario = userEvent.setup();
      montar(9);
      await leer(usuario);
      await encabezado("Alturas pendientes");
      for (const a of ALTURAS_OF001) {
        await usuario.type(screen.getByRole("textbox", { name: `Altura de ${a.id} (${a.nombre}), en metros` }), "2,50");
      }
      const visto = vi.fn();
      alAlturas = (c) => {
        visto(c);
        return json(sinPendientes());
      };
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      await screen.findByText("Se cargaron 6 alturas. No quedan ambientes pendientes.");
      expect(visto).toHaveBeenCalledWith({
        rev: 9,
        alturas: { A1: "2,50", A2: "2,50", A3: "2,50", A4: "2,50", A5: "2,50", A6: "2,50" },
      });
      expect(screen.queryByRole("heading", { name: "Alturas pendientes" })).toBeNull();
      expect(screen.getByText("Pendiente", { selector: "dt" }).nextElementSibling).toHaveTextContent("0");
    });

    test("las que se dejan en blanco viajan en blanco y siguen pendientes", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      await usuario.type(screen.getByRole("textbox", { name: "Altura de A1 (Oficina 1), en metros" }), "2.5");
      const visto = vi.fn();
      alAlturas = (c) => {
        visto(c);
        return json(importada({ alturas_pendientes: ALTURAS_OF001.slice(1) }));
      };
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      await screen.findByText("Se cargó 1 altura. Quedan 5 ambientes pendientes.");
      expect(visto.mock.calls[0]![0].alturas).toEqual({ A1: "2.5", A2: "", A3: "", A4: "", A5: "", A6: "" });
      expect(screen.getAllByRole("textbox", { name: /^Altura de / })).toHaveLength(5);
    });

    test("una altura inválida: el texto del servidor tal cual, y lo escrito se conserva", async () => {
      const usuario = userEvent.setup();
      const texto =
        "Altura de «A2»: «abc» no es una altura valida. Escriba un numero de metros mayor que 0 y hasta 250, por ejemplo 2,50. No se cargó ninguna altura.";
      alAlturas = () => json({ detalle: texto }, 422);
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      await usuario.type(screen.getByRole("textbox", { name: "Altura de A1 (Oficina 1), en metros" }), "2,50");
      await usuario.type(screen.getByRole("textbox", { name: "Altura de A2 (Oficina 2), en metros" }), "abc");
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      expect(await screen.findByText(texto)).toBeInTheDocument();
      expect(screen.getByRole("textbox", { name: "Altura de A1 (Oficina 1), en metros" })).toHaveValue("2,50");
      expect(screen.getAllByRole("textbox", { name: /^Altura de / })).toHaveLength(6);
    });

    test("declarar circuitos manda los cuatro textos de cada uno, con lo corregido", async () => {
      const usuario = userEvent.setup();
      montar(2);
      await leer(usuario);
      await encabezado("Circuitos por declarar");
      const puntos = screen.getByRole("textbox", { name: "Puntos máximos del circuito C1" });
      await usuario.clear(puntos);
      await usuario.type(puntos, "8");
      const visto = vi.fn();
      alCircuitos = (c) => {
        visto(c);
        return json(importada({ circuitos_supuestos: [] }));
      };
      await usuario.click(screen.getByRole("button", { name: "Declarar circuitos" }));
      await screen.findByText("Se declararon 2 circuitos.");
      expect(visto).toHaveBeenCalledWith({
        rev: 2,
        circuitos: { C1: ["1", "1", "1", "8"], C2: ["1", "1", "1", "6"] },
      });
      expect(screen.queryByRole("heading", { name: "Circuitos por declarar" })).toBeNull();
    });

    test("un circuito inválido: el texto del servidor tal cual y los campos siguen", async () => {
      const usuario = userEvent.setup();
      const texto = "Circuito «C2»: puntos máximos «0» no es un entero mayor o igual que 1. No se declaró ningún circuito.";
      alCircuitos = () => json({ detalle: texto }, 422);
      montar();
      await leer(usuario);
      await encabezado("Circuitos por declarar");
      const puntos = screen.getByRole("textbox", { name: "Puntos máximos del circuito C2" });
      await usuario.clear(puntos);
      await usuario.type(puntos, "0");
      await usuario.click(screen.getByRole("button", { name: "Declarar circuitos" }));
      expect(await screen.findByText(texto)).toBeInTheDocument();
      expect(screen.getByRole("textbox", { name: "Puntos máximos del circuito C2" })).toHaveValue("0");
    });
  });

  describe("3e-F3: fusionar y descartar (P5, P6)", () => {
    test("fusionar manda el rev vigente, avisa a la página con el resumen nuevo y vuelve a leer el borrador", async () => {
      const usuario = userEvent.setup();
      montar(5);
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await screen.findByText(MENSAJE_DE_FUSION);
      const llamada = llamadas().find(([r]) => String(r).endsWith("/plano/fusionar"))!;
      expect(JSON.parse(String(llamada[1]?.body))).toEqual({ rev: 5 });
      expect(alAceptar).toHaveBeenCalledTimes(1);
      expect(alAceptar.mock.calls[0]![0].rev).toBe(6);
      expect(alAceptar.mock.calls[0]![0].total.texto).toBe("2703.86");
      expect(alRecargar).toHaveBeenCalledTimes(1);
    });

    test("tras fusionar queda el mensaje de éxito y el informe de la última fusión, sin la importación", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await screen.findByText(MENSAJE_DE_FUSION);
      await encabezado("Informe de la última fusión");
      // la importación se fue: ni su informe, ni alturas, ni botones
      expect(screen.queryByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Cargar alturas" })).toBeNull();
      // los conteos son los de la importación y no se duplican con las filas (6 + 6 + 21 = 33)
      expect(screen.getByText("Importado", { selector: "dt" }).nextElementSibling).toHaveTextContent("33");
      expect(screen.getByText("Pendiente", { selector: "dt" }).nextElementSibling).toHaveTextContent("6");
      expect(screen.getByText("Filas que entraron al borrador: Ambientes 6 · Fuentes 6 · Puntos 21.")).toBeInTheDocument();
      expect(
        screen.getByText("33 orígenes de medida del plano, aparte de las filas: cada fila importada cita el suyo."),
      ).toBeInTheDocument();
      expect(within(screen.getByRole("table", { name: "Informe de la fusión" })).getAllByRole("row")).toHaveLength(1 + 48);
    });

    test("leer otro plano quita el informe de la última fusión", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await encabezado("Informe de la última fusión");
      await usuario.upload(campoDeArchivo(), new File(["0\nEOF"], "otro.dxf"));
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      await encabezado("Informe de la importación de of001.dxf");
      expect(screen.queryByRole("heading", { name: "Informe de la última fusión" })).toBeNull();
    });

    test("una importación rechazada o detenida no se fusiona: el servidor lo dice y se muestra tal cual", async () => {
      const usuario = userEvent.setup();
      const texto = "No se puede fusionar «of001.dxf»: el archivo no se pudo leer";
      alFusionar = () => json({ detalle: texto }, 409);
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      expect(await screen.findByText(texto)).toBeInTheDocument();
      expect(alAceptar).not.toHaveBeenCalled();
      // la importación sigue a la vista y se puede reintentar
      expect(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" })).toBeEnabled();
    });

    test("el espacio inválido (422) se muestra tal cual y el borrador no cambia", async () => {
      const usuario = userEvent.setup();
      const texto = "El espacio resultante no es válido: el ambiente A1 no tiene largo.";
      alFusionar = () => json({ detalle: texto }, 422);
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      expect(await screen.findByText(texto)).toBeInTheDocument();
      expect(alAceptar).not.toHaveBeenCalled();
      expect(alRecargar).not.toHaveBeenCalled();
    });

    test("descartar manda el DELETE, quita la importación y lo dice", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Descartar la importación" }));
      await screen.findByText("Se descartó la importación.");
      expect(llamadas().filter(([, i]) => i?.method === "DELETE")).toHaveLength(1);
      expect(screen.queryByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeNull();
      expect(alAceptar).not.toHaveBeenCalled(); // no cambia el borrador
    });

    test("descartar una importación rechazada o detenida también manda el DELETE", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(detenida());
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Descartar la importación" }));
      await screen.findByText("Se descartó la importación.");
      expect(llamadas().filter(([, i]) => i?.method === "DELETE")).toHaveLength(1);
    });

    test("si descartar falla, la importación sigue y el error se muestra", async () => {
      const usuario = userEvent.setup();
      alDescartar = () => json({ detalle: "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa." }, 503);
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Descartar la importación" }));
      expect(await screen.findByText(/No se pudo leer o escribir el caso/)).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeInTheDocument();
    });
  });

  describe("errores de borrador, como en E1 a E11", () => {
    test("409 de rev: avisa, ofrece recargar y no manda más hasta recargar", async () => {
      const usuario = userEvent.setup();
      alAlturas = () => json({ detalle: REV_VIEJO }, 409);
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      expect(await screen.findByText(REV_VIEJO)).toBeInTheDocument();
      const antes = llamadas().length;
      await usuario.click(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" }));
      expect(llamadas()).toHaveLength(antes);
      await usuario.click(screen.getByRole("button", { name: "Recargar el borrador" }));
      expect(alRecargar).toHaveBeenCalledTimes(1);
      await waitFor(() => expect(screen.queryByText(REV_VIEJO)).toBeNull());
      alFusionar = (c) => json(respuestaDeFusion(c.rev + 1));
      await usuario.click(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await screen.findByText(MENSAJE_DE_FUSION);
    });

    test("409 de caso: «Abrir de nuevo» reabre el borrador", async () => {
      const usuario = userEvent.setup();
      alFusionar = () => json({ detalle: CASO_CAMBIO }, 409);
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      expect(await screen.findByText(CASO_CAMBIO)).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Abrir de nuevo" }));
      expect(alReabrir).toHaveBeenCalledTimes(1);
    });

    test("404: el borrador ya no está, se avisa a la página", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json({ detalle: SIN_BORRADOR }, 404);
      montar();
      await leer(usuario);
      await waitFor(() => expect(alAusente).toHaveBeenCalledTimes(1));
    });

    test("401: la sesión venció, se avisa a la aplicación", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json({ detalle: "Sesión vencida." }, 401);
      montar();
      await leer(usuario);
      await waitFor(() => expect(alExpirar).toHaveBeenCalledTimes(1));
    });

    test("409 «Vuelva a subir el plano»: se dice tal cual y la importación que ya no existe se quita", async () => {
      const usuario = userEvent.setup();
      const texto = "Vuelva a subir el plano: ya no está disponible.";
      alAlturas = () => json({ detalle: texto }, 409);
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      expect(await screen.findByText(texto)).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeNull();
      expect(screen.getByRole("button", { name: "Leer plano" })).toBeInTheDocument();
    });

    test("falla de red: el mensaje general, sin detalles internos", async () => {
      const usuario = userEvent.setup();
      alLeer = () => {
        throw new TypeError("Failed to fetch C:\\interno\\ruta");
      };
      montar();
      await leer(usuario);
      expect(await screen.findByText("No se pudo hablar con el programa de Sílice. Compruebe que esté encendido.")).toBeInTheDocument();
      expect(screen.queryByText(/interno/)).toBeNull();
    });
  });

  describe("una petición a la vez y el rev vigente", () => {
    test("mientras una petición vuela, los otros botones no mandan nada", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      let soltar: (r: Response) => void = () => undefined;
      alAlturas = () => new Promise<Response>((resolver) => (soltar = resolver));
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      const enVuelo = llamadas().length;
      for (const nombre of ["Cargar alturas", "Declarar circuitos", "Fusionar con el espacio del borrador", "Descartar la importación"]) {
        expect(screen.getByRole("button", { name: nombre })).toBeDisabled();
      }
      await usuario.click(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" }));
      expect(llamadas()).toHaveLength(enVuelo);
      soltar(json(importada()));
      await waitFor(() => expect(screen.getByRole("button", { name: "Cargar alturas" })).toBeEnabled());
    });

    test("cada petición lleva el rev que la página tiene en ese momento", async () => {
      const usuario = userEvent.setup();
      const { conRev } = montar(1);
      await leer(usuario);
      await encabezado("Alturas pendientes");
      conRev(4);
      await usuario.click(screen.getByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await screen.findByText(MENSAJE_DE_FUSION);
      const llamada = llamadas().find(([r]) => String(r).endsWith("/plano/fusionar"))!;
      expect(JSON.parse(String(llamada[1]?.body))).toEqual({ rev: 4 });
    });

    test("con una edición del espacio en curso no se fusiona ni se manda nada", async () => {
      const usuario = userEvent.setup();
      const { propiedades, rerender } = montar(1);
      await leer(usuario);
      await encabezado("Alturas pendientes");
      rerender(propiedades(1, true));
      for (const nombre of ["Cargar alturas", "Declarar circuitos", "Fusionar con el espacio del borrador", "Leer plano"]) {
        expect(screen.getByRole("button", { name: nombre })).toBeDisabled();
      }
    });
  });

  describe("estado de la importación", () => {
    test("montar y desmontar sin importación no manda ninguna petición (ni DELETE)", () => {
      const { unmount } = montar();
      unmount();
      expect(llamadas()).toHaveLength(0);
    });

    test("desmontar con una importación no la descarta: vive en el servidor y se recuerda al volver", async () => {
      const usuario = userEvent.setup();
      const { unmount } = montar(3);
      const mismo = id;
      await leer(usuario);
      await encabezado("Informe de la importación de of001.dxf");
      const antes = llamadas().length;
      unmount();
      expect(llamadas()).toHaveLength(antes);
      montar(3, { id: mismo });
      // vuelve abierto y con el informe, sin pedir nada
      await encabezado("Informe de la importación de of001.dxf");
      expect(llamadas()).toHaveLength(antes);
      expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toHaveAttribute("aria-expanded", "true");
    });

    test("otro borrador no hereda lo del anterior", async () => {
      const usuario = userEvent.setup();
      const { unmount } = montar();
      await leer(usuario);
      await encabezado("Informe de la importación de of001.dxf");
      unmount();
      montar();
      expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeNull();
    });

    test("tras fusionar se recuerda el informe de la fusión y no la importación", async () => {
      const usuario = userEvent.setup();
      const { unmount } = montar();
      const mismo = id;
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await encabezado("Informe de la última fusión");
      unmount();
      montar(3, { id: mismo });
      await encabezado("Informe de la última fusión");
      expect(screen.queryByRole("heading", { name: "Informe de la importación de of001.dxf" })).toBeNull();
    });
  });

  describe("accesibilidad", () => {
    test("no deja regiones role=alert vacías (VD-6)", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      const vacias = screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "").trim() === "");
      expect(vacias).toHaveLength(0);
    });

    test("cada campo tiene su etiqueta propia: nombres únicos", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Circuitos por declarar");
      const nombres = screen.getAllByRole("textbox").map((c) => c.getAttribute("aria-label") ?? (c as HTMLInputElement).labels?.[0]?.textContent ?? "");
      expect(nombres).toHaveLength(6 + 8);
      expect(new Set(nombres).size).toBe(nombres.length);
    });

    test("el aviso de lo pendiente es un estado, no una alerta", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      const aviso = screen.getByText(AVISO_PENDIENTES).closest("[role]");
      expect(aviso).toHaveAttribute("role", "status");
    });

    test("Enter en un campo de altura carga las alturas (formulario, teclado completo)", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      const visto = vi.fn();
      alAlturas = (c) => {
        visto(c);
        return json(importada({ alturas_pendientes: [] }));
      };
      await usuario.type(screen.getByRole("textbox", { name: "Altura de A1 (Oficina 1), en metros" }), "2,50{Enter}");
      await waitFor(() => expect(visto).toHaveBeenCalledTimes(1));
    });
  });

  // El foco no se queda en `body` cuando el botón que lo tenía desaparece (patrón de Cancelar/Olvidar de Administración):
  // jsdom sí lleva `document.activeElement`, lo que no ve es el anillo (eso se mide en navegador).
  describe("foco tras cada acción", () => {
    test("tras leer un plano importado, en el encabezado del informe", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      const h = await encabezado("Informe de la importación de of001.dxf");
      await waitFor(() => expect(h).toHaveFocus());
    });

    test("tras leer un plano rechazado, en el aviso del motivo", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(rechazada());
      montar();
      await leer(usuario, "roto.dxf");
      const aviso = (await screen.findByText(/No se pudo importar «roto.dxf»/)).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras leer un plano detenido, en el aviso que pide la unidad", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(detenida());
      montar();
      await leer(usuario);
      const aviso = (await screen.findByText(/no declara su unidad/)).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras un error de la lectura, en el aviso del error", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json({ detalle: "El archivo «a.dxf» no es un plano que se pueda importar. Suba un plano en formato DXF o IFC." }, 422);
      montar();
      await leer(usuario, "a.dxf");
      const aviso = (await screen.findByText(/no es un plano que se pueda importar/)).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras continuar con la unidad, en el encabezado del informe (el botón desapareció)", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json(detenida());
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Continuar con esta unidad" }));
      const h = await encabezado("Informe de la importación de of001.dxf");
      await waitFor(() => expect(h).toHaveFocus());
    });

    test("tras cargar las alturas, en el aviso de resultado (el botón puede desaparecer)", async () => {
      const usuario = userEvent.setup();
      alAlturas = () => json(sinPendientes());
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      const aviso = (await screen.findByText(/Se cargaron 0 alturas|No escribió ninguna altura/)).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras declarar los circuitos, en el aviso de resultado", async () => {
      const usuario = userEvent.setup();
      alCircuitos = () => json(importada({ circuitos_supuestos: [] }));
      montar();
      await leer(usuario);
      await encabezado("Circuitos por declarar");
      await usuario.click(screen.getByRole("button", { name: "Declarar circuitos" }));
      const aviso = (await screen.findByText("Se declararon 2 circuitos.")).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras fusionar, en el aviso de éxito", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      const aviso = (await screen.findByText(MENSAJE_DE_FUSION)).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras un error al fusionar, en el aviso del error", async () => {
      const usuario = userEvent.setup();
      alFusionar = () => json({ detalle: "No se puede fusionar «of001.dxf»: el archivo no se pudo leer" }, 409);
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      const aviso = (await screen.findByText(/No se puede fusionar/)).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("tras descartar, en el aviso de que se descartó", async () => {
      const usuario = userEvent.setup();
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Descartar la importación" }));
      const aviso = (await screen.findByText("Se descartó la importación.")).closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("abrir el bloque no mueve el foco del botón que lo abre", async () => {
      const usuario = userEvent.setup();
      montar();
      await abrir(usuario);
      expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toHaveFocus();
    });
  });
  describe("ronda 1 del árbitro", () => {
    test("tras recargar por un 409 de rev, el foco va al encabezado del informe (el botón desapareció)", async () => {
      const usuario = userEvent.setup();
      alAlturas = () => json({ detalle: REV_VIEJO }, 409);
      montar();
      await leer(usuario);
      await encabezado("Alturas pendientes");
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      await usuario.click(await screen.findByRole("button", { name: "Recargar el borrador" }));
      const h = await encabezado("Informe de la importación de of001.dxf");
      await waitFor(() => expect(h).toHaveFocus());
    });

    test("tras recargar sin importación a la vista, el foco va a «Leer plano»", async () => {
      const usuario = userEvent.setup();
      alLeer = () => json({ detalle: REV_VIEJO }, 409);
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Recargar el borrador" }));
      await waitFor(() => expect(screen.getByRole("button", { name: "Leer plano" })).toHaveFocus());
    });

    test("«Leer plano» sin archivo lleva el foco al aviso", async () => {
      const usuario = userEvent.setup();
      montar();
      await abrir(usuario);
      await usuario.click(screen.getByRole("button", { name: "Leer plano" }));
      const aviso = screen.getByText("Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano.").closest("[tabindex]");
      await waitFor(() => expect(aviso).toHaveFocus());
    });

    test("413 (plano demasiado grande) y 403 (sin permiso): el texto del servidor tal cual y el foco en el aviso", async () => {
      const usuario = userEvent.setup();
      for (const [estado, texto] of [
        [413, "El archivo es demasiado grande: el tope es de 20 MiB."],
        [403, "Su cuenta no tiene permiso para esta acción."],
      ] as const) {
        alLeer = () => json({ detalle: texto }, estado);
        const { unmount } = montar();
        await leer(usuario);
        const aviso = (await screen.findByText(texto)).closest("[tabindex]");
        await waitFor(() => expect(aviso).toHaveFocus());
        expect(alExpirar).not.toHaveBeenCalled();
        unmount();
      }
    });

    test("una sesión vencida (401) olvida lo recordado; también `olvidarImportaciones`", async () => {
      const usuario = userEvent.setup();
      const { unmount } = montar();
      const mismo = id;
      await leer(usuario);
      await encabezado("Alturas pendientes");
      alAlturas = () => json({ detalle: "Sesión vencida." }, 401);
      await usuario.click(screen.getByRole("button", { name: "Cargar alturas" }));
      await waitFor(() => expect(alExpirar).toHaveBeenCalledTimes(1));
      unmount();
      montar(3, { id: mismo });
      expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toHaveAttribute("aria-expanded", "false");
      // y por orden explícita
      const segundo = userEvent.setup();
      await leer(segundo);
      await encabezado("Informe de la importación de of001.dxf");
      olvidarImportaciones();
      screen.getByRole("button", { name: "Descartar la importación" }); // sigue a la vista mientras la página no se va
      cleanup();
      montar(3, { id: mismo });
      expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toHaveAttribute("aria-expanded", "false");
    });

    test("al fusionar avisa a la página que ocupa el espacio y no lo suelta hasta que la relectura termina", async () => {
      const usuario = userEvent.setup();
      let terminar: () => void = () => undefined;
      alRecargar.mockImplementation(() => new Promise<void>((resolver) => (terminar = resolver)));
      montar();
      await leer(usuario);
      await usuario.click(await screen.findByRole("button", { name: "Fusionar con el espacio del borrador" }));
      await screen.findByText(MENSAJE_DE_FUSION);
      expect(alOcuparse).toHaveBeenLastCalledWith(true);
      expect(screen.getByRole("button", { name: "Leer plano" })).toBeDisabled();
      terminar();
      await waitFor(() => expect(alOcuparse).toHaveBeenLastCalledWith(false));
      await waitFor(() => expect(screen.getByRole("button", { name: "Leer plano" })).toBeEnabled());
    });
  });
});
