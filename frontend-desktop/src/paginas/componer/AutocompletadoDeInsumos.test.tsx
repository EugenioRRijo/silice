import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { olvidarInsumosDelCatalogo } from "./cliente";
import { TablaInsumos } from "./TablaInsumos";
import { agregarFila, borrarFila, completarFila, editarCelda, tablasVacias } from "./tablas";
import type { Fila, Tablas, TipoTabla } from "./tablas";

// AC1 (pedido de Eugenio, 2026-10-21): la descripción de cada fila es un campo con sugerencias del catálogo. Montos y
// textos ficticios; la API es un `fetch` falso que responde como `GET /v1/consulta/{tabla}` y `GET /insumos`.

const MODALIDADES = ["JORNAL", "DESTAJO"];
const AVISO = "Descripción propia: no viene del catálogo.";

const CATALOGO = [
  { codigo: "MAT-1", descripcion: "Cemento gris ficticio", tipo: "material", unidad: "saco", precio_vigente: "18.00" },
  { codigo: "MAT-2", descripcion: "Cemento blanco ficticio", tipo: "material", unidad: null, precio_vigente: null },
  { codigo: "EQ-1", descripcion: "Mezcladora ficticia", tipo: "equipo", unidad: "h", precio_vigente: "2000" },
  { codigo: "MO-1", descripcion: "Albañil ficticio", tipo: "mano_obra", unidad: null, precio_vigente: "12.3400" },
];
const TIPOS_DE: Record<string, string[]> = { insumos: ["material", "equipo"], salarios_cct: ["mano_obra"] };

let llamadas: string[];
let catalogoFalla: boolean;
let estadoDeConsulta: number;

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  llamadas = [];
  catalogoFalla = false;
  estadoDeConsulta = 200;
  olvidarInsumosDelCatalogo();
  vi.stubGlobal(
    "fetch",
    vi.fn((ruta: string) => {
      llamadas.push(ruta);
      const consulta = /^\/v1\/consulta\/(\w+)\?(.*)$/.exec(ruta);
      if (consulta) {
        if (estadoDeConsulta !== 200) return Promise.resolve(json({ detalle: "Sin sesión." }, estadoDeConsulta));
        const q = (new URLSearchParams(consulta[2]).get("q") ?? "").toLowerCase();
        const halladas = CATALOGO.filter(
          (i) => TIPOS_DE[consulta[1]]?.includes(i.tipo) && i.descripcion.toLowerCase().includes(q),
        );
        return Promise.resolve(
          json({
            tabla: consulta[1],
            hay_mas: false,
            resultados: halladas.map((i) => ({
              valor: i.codigo,
              etiqueta: `${i.descripcion} (${i.codigo}${i.unidad ? `, ${i.unidad}` : ""})`,
              fuente: `Catálogo de la carpeta de trabajo: ${i.tipo.replace("_", " ")}`,
            })),
          }),
        );
      }
      if (ruta === "/insumos") return Promise.resolve(catalogoFalla ? json({ detalle: "Caído." }, 503) : json(CATALOGO));
      return Promise.resolve(json({ detalle: "No hay." }, 404));
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

interface PropsArnes {
  tipo: TipoTabla;
  filas: Fila[];
  alEscape?: () => void;
  alExpirar?: () => void;
}

function Arnes({ tipo, filas, alEscape, alExpirar = () => {} }: PropsArnes) {
  const [tablas, setTablas] = useState<Tablas>({ ...tablasVacias(), [tipo]: filas });
  return (
    <div onKeyDown={(e) => e.key === "Escape" && alEscape?.()}>
      <TablaInsumos
        tipo={tipo}
        filas={tablas[tipo]}
        modalidades={MODALIDADES}
        alCambiar={(i, clave, valor) => setTablas((t) => editarCelda(t, tipo, i, clave, valor))}
        alCompletar={(i, valores) => setTablas((t) => completarFila(t, tipo, i, valores))}
        alAgregar={() => setTablas((t) => agregarFila(t, tipo))}
        alBorrar={(i) => setTablas((t) => borrarFila(t, tipo, i))}
        alExpirar={alExpirar}
      />
    </div>
  );
}

const MATERIAL = { descripcion: "", unidad: "", cantidad: "3", precio: "" };
const EQUIPO = { descripcion: "", cantidad: "1", precio: "", depreciacion: "0,5" };
const OBRERO = { descripcion: "", cantidad: "2", sueldo: "", modalidad: "JORNAL" };
const descripcion = (n = 1) => screen.getByRole("combobox", { name: `Descripción, fila ${n}` });

describe("TablaInsumos: autocompletado de la descripción", () => {
  test("cada descripción es un combobox con su nombre «Descripción, fila N»; las demás columnas siguen siendo texto", () => {
    render(<Arnes tipo="materiales" filas={[MATERIAL, { ...MATERIAL }]} />);
    expect(descripcion(1)).toBeInTheDocument();
    expect(descripcion(2)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Unidad, fila 1" })).toBeInTheDocument();
    expect(screen.getAllByRole("combobox")).toHaveLength(2);
  });

  test("materiales: pide «insumos»; al elegir llena descripción, unidad y precio (con coma) y respeta el consumo", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    const opcion = await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?q=cemento+g"))).toBe(true);
    await u.click(opcion);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Unidad, fila 1" })).toHaveValue("saco"));
    expect(descripcion()).toHaveValue("Cemento gris ficticio");
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("18,00");
    expect(screen.getByRole("textbox", { name: "Consumo por unidad, fila 1" })).toHaveValue("3");
  });

  test("equipos: usa la misma tabla «insumos»; llena descripción y precio y no toca cantidad ni depreciación", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="equipos" filas={[EQUIPO]} />);
    await u.type(descripcion(), "mezcla");
    await u.click(await screen.findByRole("option", { name: /Mezcladora ficticia/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("2.000"));
    expect(descripcion()).toHaveValue("Mezcladora ficticia");
    expect(screen.getByRole("textbox", { name: "Cantidad, fila 1" })).toHaveValue("1");
    expect(screen.getByRole("textbox", { name: "Depreciación, fila 1" })).toHaveValue("0,5");
    expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?"))).toBe(true);
  });

  test("mano de obra: usa «salarios_cct», el jornal va al sueldo y la modalidad no cambia", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="mano_obra" filas={[OBRERO]} />);
    await u.type(descripcion(), "alba");
    await u.click(await screen.findByRole("option", { name: /Albañil ficticio/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Sueldo, fila 1" })).toHaveValue("12,3400"));
    expect(descripcion()).toHaveValue("Albañil ficticio");
    expect(screen.getByRole("combobox", { name: "Modalidad, fila 1" })).toHaveValue("JORNAL");
    expect(llamadas.some((l) => l.startsWith("/v1/consulta/salarios_cct?"))).toBe(true);
  });

  test("un insumo sin unidad ni precio en el catálogo no borra ni inventa lo que ya hay", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[{ ...MATERIAL, unidad: "kg", precio: "7,5" }]} />);
    await u.type(descripcion(), "cemento b");
    await u.click(await screen.findByRole("option", { name: /Cemento blanco ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(screen.getByRole("textbox", { name: "Unidad, fila 1" })).toHaveValue("kg");
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("7,5");
  });

  test("si el catálogo completo no carga, elegir igual deja la descripción y nada más", async () => {
    catalogoFalla = true;
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("");
  });

  test("se puede usar una descripción propia: la lista lo ofrece con su aviso y queda dicho que no viene del catálogo", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "Piedra de río ficticia");
    const propio = await screen.findByRole("option", {
      name: /Usar «Piedra de río ficticia» tal cual.*no viene del catálogo/,
    });
    await u.click(propio);
    expect(descripcion()).toHaveValue("Piedra de río ficticia");
    expect(screen.getByText(AVISO)).toBeInTheDocument();
    expect(descripcion()).toHaveAccessibleDescription(expect.stringContaining("no viene del catálogo"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  test("lo escrito y no elegido también queda marcado como propio; elegir del catálogo quita el aviso", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "Cemento gris");
    await u.tab();
    expect(screen.getByText(AVISO)).toBeInTheDocument();
    await u.click(descripcion());
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test("una fila precargada o de la referencia no se marca como propia", () => {
    render(<Arnes tipo="materiales" filas={[{ ...MATERIAL, descripcion: "Arena ficticia" }]} />);
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test("teclado: Tab con la lista abierta la cierra, sigue a la columna siguiente y no elige; Enter elige la activa", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento b");
    await screen.findByRole("option", { name: /Cemento blanco ficticio/ });
    await u.tab();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Unidad, fila 1" })).toHaveFocus();
    expect(descripcion()).toHaveValue("cemento b");

    await u.click(descripcion());
    await u.keyboard("{Enter}"); // sin opción activa: no elige nada
    expect(descripcion()).toHaveValue("cemento b");
    await screen.findByRole("option", { name: /Cemento blanco ficticio/ });
    await u.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
  });

  test("Esc con la lista abierta solo la cierra: el Esc no llega al panel que contiene la tabla", async () => {
    const u = userEvent.setup();
    const alEscape = vi.fn();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} alEscape={alEscape} />);
    await u.type(descripcion(), "cemento g");
    await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(alEscape).not.toHaveBeenCalled();
    expect(descripcion()).toHaveValue("cemento g");
  });

  test("Esc con la lista cerrada no borra la descripción ya elegida", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    await u.keyboard("{Escape}");
    expect(descripcion()).toHaveValue("Cemento gris ficticio");
    expect(screen.getByRole("textbox", { name: "Unidad, fila 1" })).toHaveValue("saco");
  });

  test("una sesión vencida durante la búsqueda avisa con alExpirar", async () => {
    estadoDeConsulta = 401;
    const u = userEvent.setup();
    const alExpirar = vi.fn();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} alExpirar={alExpirar} />);
    await u.type(descripcion(), "cemento");
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("borrar una fila quita el aviso de propia de la que se va y no se lo pasa a la siguiente", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL, { ...MATERIAL, descripcion: "Arena ficticia" }]} />);
    await u.type(descripcion(1), "Piedra propia");
    await u.tab();
    expect(screen.getAllByText(AVISO)).toHaveLength(1);
    await u.click(screen.getByRole("button", { name: "Borrar fila 1 de Materiales" }));
    expect(descripcion(1)).toHaveValue("Arena ficticia");
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test("una descripción de más de 80 letras se puede escribir (el catálogo las tiene) y la búsqueda manda solo las primeras 80", async () => {
    const u = userEvent.setup();
    const larga = "Tubería de concreto reforzado ficticia para drenaje de aguas de lluvia, ".repeat(2).trim();
    expect(larga.length).toBeGreaterThan(80);
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.click(descripcion());
    await u.paste(larga);
    expect(descripcion()).toHaveValue(larga);
    await waitFor(() => expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?"))).toBe(true));
    const q = new URLSearchParams(llamadas.find((l) => l.startsWith("/v1/consulta/insumos?"))!.split("?")[1]).get("q")!;
    expect(q.length).toBeLessThanOrEqual(80);
    expect(larga.startsWith(q)).toBe(true);
  });
});
