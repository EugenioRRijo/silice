import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { CampoTexto } from "./CampoTexto";

// VB-18: el TextInput de Carbon monta siempre un <span role="alert"> vacio (el contador de caracteres); con 4 a 8
// campos por pagina el lector de pantalla encuentra otras tantas regiones vivas sin contenido. El campo de Sílice las
// monta solo si hay contenido (contador activo).
describe("CampoTexto", () => {
  test("es un campo de texto con su etiqueta y no deja regiones role=alert vacías", () => {
    const { container } = render(<CampoTexto id="c1" labelText="Nombre" value="" onChange={() => {}} />);
    expect(screen.getByLabelText("Nombre")).toBeInTheDocument();
    expect(container.querySelectorAll('[role="alert"]')).toHaveLength(0);
    expect(container.querySelectorAll("[aria-live]")).toHaveLength(0);
  });

  test("un campo inválido sigue anunciando su mensaje", () => {
    render(<CampoTexto id="c2" labelText="Huella" value="x" onChange={() => {}} invalid invalidText="La huella no coincide." />);
    expect(screen.getByText("La huella no coincide.")).toBeInTheDocument();
  });

  test("con contador la región viva se conserva", () => {
    const { container } = render(
      <CampoTexto id="c3" labelText="Corto" value="abc" onChange={() => {}} enableCounter maxCount={10} />,
    );
    expect(container.querySelectorAll('[role="alert"]').length).toBeGreaterThan(0);
  });
});
