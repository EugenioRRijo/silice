import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { SeleccionMultipleConBusqueda } from "./SeleccionMultipleConBusqueda";
import type { GrupoDeResultados } from "./logicaBusqueda";

// AC3: seleccion multiple con busqueda en el servidor (patron combobox con etiquetas quitables). Se construye sobre
// CampoConBusqueda por composicion: aqui solo se prueba lo propio (las etiquetas, el teclado, los anuncios y lo que
// guarda); la lista, las flechas y la carrera de peticiones ya las prueba CampoConBusqueda.

const GRUPOS: GrupoDeResultados<string>[] = [
  {
    rotulo: "Insumos del catálogo",
    hayMas: false,
    opciones: [
      { clave: "i:1", principal: "Cemento ficticio", secundaria: ["MAT-1"], valor: "Cemento ficticio" },
      { clave: "i:2", principal: "Arena ficticia", secundaria: ["MAT-2"], valor: "Arena ficticia" },
      { clave: "i:3", principal: "Tubo ficticio, 4 pulgadas", secundaria: ["MAT-3"], valor: "Tubo ficticio, 4 pulgadas" },
    ],
  },
];

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  vi.stubGlobal("jest", { advanceTimersByTime: vi.advanceTimersByTime.bind(vi) });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function Prueba({
  inicial = [],
  alEnviar,
  alCambiar,
  rechazar,
}: {
  inicial?: string[];
  alEnviar?: () => void;
  alCambiar?: (elegidos: string[]) => void;
  rechazar?: (texto: string) => string | null;
}) {
  const [elegidos, setElegidos] = useState(inicial);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        alEnviar?.();
      }}
    >
      <SeleccionMultipleConBusqueda<string>
        id="insumos"
        etiqueta="Insumos"
        ayuda="Escriba y elija de la lista."
        elegidos={elegidos}
        alCambiar={(nuevos) => {
          setElegidos(nuevos);
          alCambiar?.(nuevos);
        }}
        buscar={() => Promise.resolve(GRUPOS)}
        textoDe={(opcion) => opcion.valor}
        rechazar={rechazar}
        vacio={{ titulo: "¿No lo encuentra?", pasos: "Pruebe con otra palabra." }}
        alExpirar={() => {}}
      />
      <button type="submit">Enviar</button>
    </form>
  );
}

const usuario = () => userEvent.setup({ delay: null, advanceTimers: vi.advanceTimersByTime.bind(vi) });
const campo = () => screen.getByRole("combobox", { name: "Insumos" });
const textosDeLasRegiones = () => screen.queryAllByRole("status").map((r) => r.textContent);

async function buscarYElegir(u: ReturnType<typeof usuario>, texto: string, flechas = 1) {
  await u.type(campo(), texto);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
  await u.keyboard("{ArrowDown}".repeat(flechas));
  await u.keyboard("{Enter}");
}

describe("SeleccionMultipleConBusqueda", () => {
  test("elegir una opcion la agrega como etiqueta con su boton «Quitar», limpia el campo y deja el foco en el", async () => {
    const alCambiar = vi.fn();
    render(<Prueba alCambiar={alCambiar} />);
    const u = usuario();
    await buscarYElegir(u, "cem");
    expect(alCambiar).toHaveBeenLastCalledWith(["Cemento ficticio"]);
    const lista = screen.getByRole("list", { name: "Elegidos: Insumos" });
    expect(within(lista).getAllByRole("listitem")).toHaveLength(1);
    expect(within(lista).getByText("Cemento ficticio")).toBeInTheDocument();
    expect(within(lista).getByRole("button", { name: "Quitar Cemento ficticio" })).toBeInTheDocument();
    expect(campo()).toHaveValue("");
    expect(campo()).toHaveFocus();
  });

  test("sin nada elegido no hay lista de etiquetas", () => {
    render(<Prueba />);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  test("se pueden elegir varias, en el orden en que se eligen", async () => {
    const alCambiar = vi.fn();
    render(<Prueba alCambiar={alCambiar} />);
    const u = usuario();
    await buscarYElegir(u, "cem");
    await buscarYElegir(u, "are", 2);
    expect(alCambiar).toHaveBeenLastCalledWith(["Cemento ficticio", "Arena ficticia"]);
    const botones = within(screen.getByRole("list", { name: "Elegidos: Insumos" })).getAllByRole("button");
    expect(botones.map((b) => b.getAttribute("aria-label"))).toEqual(["Quitar Cemento ficticio", "Quitar Arena ficticia"]);
  });

  test("elegir una ya elegida no la repite y lo dice", async () => {
    const alCambiar = vi.fn();
    render(<Prueba inicial={["Cemento ficticio"]} alCambiar={alCambiar} />);
    const u = usuario();
    await buscarYElegir(u, "cem");
    expect(alCambiar).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(textosDeLasRegiones()).toContain("Cemento ficticio ya estaba en la lista.");
  });

  test("el boton «Quitar» saca esa etiqueta, devuelve el foco al campo y lo anuncia en una region viva", async () => {
    const alCambiar = vi.fn();
    render(<Prueba inicial={["Cemento ficticio", "Arena ficticia"]} alCambiar={alCambiar} />);
    const u = usuario();
    await u.click(screen.getByRole("button", { name: "Quitar Cemento ficticio" }));
    expect(alCambiar).toHaveBeenLastCalledWith(["Arena ficticia"]);
    expect(campo()).toHaveFocus();
    const region = screen.getByText("Quitado: Cemento ficticio. 1 elegido.");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveAttribute("role", "status");
  });

  test("al agregar se anuncia cuantas hay", async () => {
    render(<Prueba />);
    const u = usuario();
    await buscarYElegir(u, "cem");
    await buscarYElegir(u, "are", 2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(textosDeLasRegiones()).toContain("Agregado: Arena ficticia. 2 elegidos.");
  });

  test("Retroceso con el campo vacio quita la ultima etiqueta; con texto escrito no quita nada", async () => {
    const alCambiar = vi.fn();
    render(<Prueba inicial={["Cemento ficticio", "Arena ficticia"]} alCambiar={alCambiar} />);
    const u = usuario();
    await u.click(campo());
    await u.type(campo(), "ab");
    await u.keyboard("{Backspace}{Backspace}"); // borra lo escrito: aun no quita etiquetas
    expect(alCambiar).not.toHaveBeenCalled();
    await u.keyboard("{Backspace}"); // con el campo ya vacio, quita la ultima
    expect(alCambiar).toHaveBeenLastCalledWith(["Cemento ficticio"]);
    expect(screen.queryByRole("button", { name: "Quitar Arena ficticia" })).not.toBeInTheDocument();
    expect(screen.getByText("Quitado: Arena ficticia. 1 elegido.")).toBeInTheDocument();
  });

  test("Enter con texto escrito y ninguna opcion activa no envia el formulario ni agrega el texto tal cual", async () => {
    const alEnviar = vi.fn();
    const alCambiar = vi.fn();
    render(<Prueba alEnviar={alEnviar} alCambiar={alCambiar} />);
    const u = usuario();
    await u.type(campo(), "cemento a medias");
    await u.keyboard("{Enter}");
    expect(alEnviar).not.toHaveBeenCalled();
    expect(alCambiar).not.toHaveBeenCalled();
  });

  test("Enter con el campo vacio envia el formulario como siempre", async () => {
    const alEnviar = vi.fn();
    render(<Prueba alEnviar={alEnviar} />);
    const u = usuario();
    await u.click(campo());
    await u.keyboard("{Enter}");
    expect(alEnviar).toHaveBeenCalledTimes(1);
  });

  test("lo escrito sin elegir se avisa bajo el campo: no se agrega solo", async () => {
    render(<Prueba />);
    const u = usuario();
    expect(screen.getByText("Escriba y elija de la lista.")).toBeInTheDocument();
    await u.type(campo(), "cemen");
    expect(screen.getByText("Falta elegir «cemen» de la lista: así no se agrega.")).toBeInTheDocument();
    expect(screen.queryByText("Escriba y elija de la lista.")).not.toBeInTheDocument();
  });

  test("no ofrece «usar tal cual»: solo se agrega lo que viene de la lista", async () => {
    render(<Prueba />);
    const u = usuario();
    await u.type(campo(), "cem");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    const opciones = screen.getAllByRole("option").map((o) => o.textContent ?? "");
    expect(opciones).toHaveLength(3);
    expect(opciones.some((t) => /tal cual/.test(t))).toBe(false);
  });

  test("`rechazar` impide agregar una opcion y dice por que, sin cambiar lo elegido", async () => {
    const alCambiar = vi.fn();
    render(<Prueba alCambiar={alCambiar} rechazar={(t) => (t.includes(",") ? `«${t}» lleva una coma.` : null)} />);
    const u = usuario();
    await buscarYElegir(u, "tub", 3);
    expect(alCambiar).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    // el motivo se ve bajo el campo (marcado como invalido) y ademas se anuncia
    expect(screen.getByText("«Tubo ficticio, 4 pulgadas» lleva una coma.")).toBeInTheDocument();
    expect(campo()).toHaveAttribute("aria-invalid", "true");
    expect(textosDeLasRegiones()).toContain("No se agregó: «Tubo ficticio, 4 pulgadas» lleva una coma.");
  });

  test("ninguna region viva queda vacia", async () => {
    render(<Prueba inicial={["Cemento ficticio"]} />);
    const u = usuario();
    const regiones = () => [...document.querySelectorAll("[aria-live], [role=status], [role=alert]")];
    expect(regiones()).toHaveLength(0);
    await u.click(screen.getByRole("button", { name: "Quitar Cemento ficticio" }));
    expect(regiones().length).toBeGreaterThan(0);
    for (const region of regiones()) expect((region.textContent ?? "").trim()).not.toBe("");
  });

  // Un lector de pantalla suele no leer una region viva que aparece ya con su primer mensaje: se monta con el foco, con el
  // conteo, y luego solo cambia su texto (como hace CampoConBusqueda).
  test("al enfocar el campo la región viva ya está, con el conteo, y el primer «Agregado» cambia su texto", async () => {
    render(<Prueba />);
    const u = usuario();
    await u.click(campo());
    const region = screen.getByText("Ninguno elegido.");
    expect(region).toHaveAttribute("role", "status");
    expect(region).toHaveAttribute("aria-live", "polite");
    await buscarYElegir(u, "cem");
    expect(region).toBeInTheDocument();
    expect(region.textContent).toBe("Agregado: Cemento ficticio. 1 elegido.");
  });

  test("con elegidos, al enfocar la región dice cuántos hay", async () => {
    render(<Prueba inicial={["Cemento ficticio", "Arena ficticia"]} />);
    const u = usuario();
    await u.click(campo());
    expect(screen.getByText("2 elegidos.")).toHaveAttribute("role", "status");
  });

  test("un mensaje repetido cambia el texto de la región para que se vuelva a leer", async () => {
    render(<Prueba inicial={["Cemento ficticio"]} />);
    const u = usuario();
    await buscarYElegir(u, "cem");
    const region = screen.getByText("Cemento ficticio ya estaba en la lista.");
    const primero = region.textContent;
    await buscarYElegir(u, "cem");
    expect(region.textContent).not.toBe(primero);
    expect(region.textContent?.trim()).toBe("Cemento ficticio ya estaba en la lista.");
    await buscarYElegir(u, "cem");
    expect(region.textContent).toBe(primero);
  });

  test("al salir del campo la región se desmonta", async () => {
    render(<Prueba />);
    const u = usuario();
    await u.click(campo());
    expect(screen.getByText("Ninguno elegido.")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Enviar" }));
    expect(screen.queryByText("Ninguno elegido.")).not.toBeInTheDocument();
  });

  test("la etiqueta del campo es su nombre accesible y la ayuda lo describe", () => {
    render(<Prueba />);
    expect(campo()).toHaveAccessibleDescription(/Escriba y elija de la lista\./);
  });
});
