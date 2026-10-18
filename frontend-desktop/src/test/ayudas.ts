import { screen, waitFor } from "@testing-library/react";

// Carbon pone un span vacio con role="alert" en cada campo de texto; la alerta de verdad es la que trae texto.
export async function alertaConTexto(): Promise<HTMLElement> {
  return waitFor(() => {
    const alerta = screen.getAllByRole("alert").find((a) => (a.textContent ?? "").trim() !== "");
    if (!alerta) throw new Error("Todavia no hay una alerta con texto");
    return alerta;
  });
}
