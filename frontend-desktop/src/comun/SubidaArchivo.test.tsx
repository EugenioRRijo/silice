import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { SubidaArchivo } from "./SubidaArchivo";

function campo(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

describe("SubidaArchivo", () => {
  test("muestra la etiqueta que le dice a la persona que soltar", () => {
    render(<SubidaArchivo etiqueta="Suelte aquí el libro .xlsx" extensiones={[".xlsx"]} alElegir={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Suelte aquí el libro .xlsx" })).toBeInTheDocument();
  });

  test("entrega el archivo elegido si tiene una extension permitida (sin importar mayusculas)", async () => {
    const usuario = userEvent.setup();
    const alElegir = vi.fn();
    render(<SubidaArchivo etiqueta="Suelte" extensiones={[".xlsx"]} alElegir={alElegir} />);
    const archivo = new File(["x"], "LIBRO.XLSX");
    await usuario.upload(campo(), archivo);
    expect(alElegir).toHaveBeenCalledWith(archivo);
  });

  test("un archivo de otra extension no se entrega y se explica", async () => {
    const usuario = userEvent.setup({ applyAccept: false });
    const alElegir = vi.fn();
    render(<SubidaArchivo etiqueta="Suelte" extensiones={[".xlsx"]} alElegir={alElegir} />);
    await usuario.upload(campo(), new File(["x"], "libro.pdf"));
    expect(alElegir).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Solo se aceptan archivos .xlsx.");
  });

  test("una lista de extensiones se dice completa en el mensaje", async () => {
    const usuario = userEvent.setup({ applyAccept: false });
    render(<SubidaArchivo etiqueta="Suelte" extensiones={[".csv", ".xlsx"]} alElegir={vi.fn()} />);
    await usuario.upload(campo(), new File(["x"], "a.txt"));
    expect(screen.getByRole("alert")).toHaveTextContent("Solo se aceptan archivos .csv o .xlsx.");
  });

  test("deshabilitada no acepta archivos", () => {
    render(<SubidaArchivo etiqueta="Suelte" extensiones={[".xlsx"]} alElegir={vi.fn()} deshabilitada />);
    expect(campo()).toBeDisabled();
  });
});
