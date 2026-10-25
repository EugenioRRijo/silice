import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import type { CasosRespuesta, ProyectoRespuesta } from "../api/tipos";
import { PanelCarpetaProyecto, nombreDeCarpeta } from "./PanelCarpetaProyecto";

const CASO = (nombre: string) => ({ nombre, ruta_relativa: `data/${nombre}` }) as CasosRespuesta["actual"];
const casos = (nombre: string): CasosRespuesta => ({ actual: CASO(nombre), casos: [CASO(nombre), CASO("otra.db")] });
const PROYECTOS: ProyectoRespuesta[] = [
  { codigo: "P-01", nombre: "Torre B", version_vigente: 1, actualizado: null },
  { codigo: "P-02", nombre: "Galpón", version_vigente: null, actualizado: null },
];

function pintar(extra: Partial<Parameters<typeof PanelCarpetaProyecto>[0]> = {}) {
  const props = {
    casos: casos("demo.db"),
    proyectos: PROYECTOS,
    elegido: "P-01" as string | null,
    puedeCambiar: true,
    ocupado: false,
    alElegirCaso: vi.fn(),
    alElegirProyecto: vi.fn(),
    ...extra,
  };
  render(<PanelCarpetaProyecto {...props} />);
  return props;
}

describe("nombreDeCarpeta", () => {
  test("quita el .db final y solo ese", () => {
    expect(nombreDeCarpeta("demo.db")).toBe("demo");
    expect(nombreDeCarpeta("obra.v2.db")).toBe("obra.v2");
    expect(nombreDeCarpeta("x")).toBe("x");
  });
});

describe("PanelCarpetaProyecto", () => {
  test("el botón muestra la carpeta y el proyecto, con su nombre accesible", () => {
    pintar();
    const boton = screen.getByRole("button", { name: "Carpeta de trabajo: demo. Proyecto: Torre B. Cambiar" });
    expect(boton).toHaveTextContent("demo · Torre B");
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  test("sin la lista de carpetas el botón dice «Sin carpeta»", () => {
    pintar({ casos: null });
    expect(screen.getByRole("button", { name: /Cambiar$/ })).toHaveTextContent("Sin carpeta · Torre B");
  });

  test("dos instancias no repiten el id del panel", () => {
    pintar();
    render(
      <PanelCarpetaProyecto
        casos={casos("demo.db")}
        proyectos={PROYECTOS}
        elegido={null}
        puedeCambiar
        ocupado={false}
        alElegirCaso={() => {}}
        alElegirProyecto={() => {}}
      />,
    );
    const ids = screen.getAllByRole("button", { name: /Cambiar$/ }).map((b) => b.getAttribute("aria-controls"));
    expect(new Set(ids).size).toBe(2);
  });

  test("sin proyecto elegido dice «Sin proyecto»", () => {
    pintar({ elegido: null });
    expect(screen.getByRole("button", { name: /Cambiar$/ })).toHaveTextContent("demo · Sin proyecto");
  });

  test("el clic abre el panel con los dos selectores rotulados; Esc lo cierra y devuelve el foco", async () => {
    const u = userEvent.setup();
    pintar();
    const boton = screen.getByRole("button", { name: /Cambiar$/ });
    await u.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("combobox", { name: "Carpeta de trabajo" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toBeInTheDocument();
    expect(screen.getByText("Carpeta y proyecto")).toBeInTheDocument();
    await u.keyboard("{Escape}");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("combobox", { name: "Proyecto" })).not.toBeInTheDocument();
    expect(boton).toHaveFocus();
  });

  test("elegir en los selectores avisa a quien llama", async () => {
    const u = userEvent.setup();
    const props = pintar();
    await u.click(screen.getByRole("button", { name: /Cambiar$/ }));
    await u.selectOptions(screen.getByRole("combobox", { name: "Proyecto" }), "P-02");
    expect(props.alElegirProyecto).toHaveBeenCalledWith("P-02");
    await u.selectOptions(screen.getByRole("combobox", { name: "Carpeta de trabajo" }), "otra.db");
    expect(props.alElegirCaso).toHaveBeenCalledWith("otra.db");
  });

  test("un clic fuera cierra el panel", async () => {
    const u = userEvent.setup();
    pintar();
    const boton = screen.getByRole("button", { name: /Cambiar$/ });
    await u.click(boton);
    await u.click(document.body);
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  // Foco de revision 1: el nombre largo se recorta por CSS y el completo queda en el nombre accesible.
  test("una carpeta de 80 caracteres se recorta con la clase del texto y el nombre accesible la trae completa", () => {
    const larga = `${"a".repeat(77)}.db`;
    pintar({ casos: casos(larga) });
    const completo = "a".repeat(77);
    const boton = screen.getByRole("button", { name: new RegExp(`Carpeta de trabajo: ${completo}\\.`) });
    expect(boton.querySelector(".silice-contexto__texto")).not.toBeNull();
    expect(boton.querySelector(".silice-contexto__texto")).toHaveTextContent(completo);
  });

  test("ninguna cadena visible lleva la palabra «caso»", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(screen.getByRole("button", { name: /Cambiar$/ }));
    expect(screen.queryByText(/\bcaso\b/i)).toBeNull();
    expect(screen.queryByLabelText(/\bcaso\b/i)).toBeNull();
  });

  test("deja un hueco para contenido adicional al final del panel", async () => {
    const u = userEvent.setup();
    pintar({ children: <p>Extra</p> });
    await u.click(screen.getByRole("button", { name: /Cambiar$/ }));
    expect(within(screen.getByRole("region", { name: "Carpeta y proyecto" })).getByText("Extra")).toBeInTheDocument();
  });
});
