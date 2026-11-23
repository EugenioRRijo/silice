import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, test } from "vitest";
import { DialogoSalida } from "../shell/DialogoSalida";
import { olvidarFormularios, useFormularioSucio } from "../shell/sucio";
import { EnlaceComoBoton } from "./EnlaceComoBoton";

function PantallaSucia() {
  useFormularioSucio("riesgo", true);
  return (
    <EnlaceComoBoton to="/hoja" kind="secondary">
      Ir al presupuesto
    </EnlaceComoBoton>
  );
}

describe("EnlaceComoBoton", () => {
  afterEach(() => {
    olvidarFormularios();
  });

  test("pinta un enlace con el aspecto de botón de Carbon y navega al pulsarlo", async () => {
    const usuario = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/tablero"]}>
        <Routes>
          <Route
            path="/tablero"
            element={
              <EnlaceComoBoton to="/control" kind="secondary">
                Abrir el control de obra
              </EnlaceComoBoton>
            }
          />
          <Route path="/control" element={<p>En control</p>} />
        </Routes>
      </MemoryRouter>,
    );
    const enlace = screen.getByRole("link", { name: "Abrir el control de obra" });
    expect(enlace).toHaveAttribute("href", "/control");
    expect(enlace).toHaveClass("cds--btn", "cds--btn--secondary");
    await usuario.click(enlace);
    expect(await screen.findByText("En control")).toBeInTheDocument();
  });

  test("usa kind primary por omisión", () => {
    render(
      <MemoryRouter>
        <EnlaceComoBoton to="/hoja">Ir al presupuesto</EnlaceComoBoton>
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Ir al presupuesto" })).toHaveClass("cds--btn", "cds--btn--primary");
  });

  test("si hay cambios sin guardar, pregunta antes de salir", async () => {
    const usuario = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/riesgo"]}>
        <DialogoSalida />
        <Routes>
          <Route path="/riesgo" element={<PantallaSucia />} />
          <Route path="/hoja" element={<p>En presupuesto</p>} />
        </Routes>
      </MemoryRouter>,
    );
    await usuario.click(screen.getByRole("link", { name: "Ir al presupuesto" }));
    expect(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).toBeInTheDocument();
    expect(screen.queryByText("En presupuesto")).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Salir y descartar" }));
    expect(await screen.findByText("En presupuesto")).toBeInTheDocument();
  });
});
