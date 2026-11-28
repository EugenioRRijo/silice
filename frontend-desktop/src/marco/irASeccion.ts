// SOLO PARA PRUEBAS: llega a una sección de la obra como lo haría una persona con la barra del lugar (BarraDeObra, lote C4), que
// ya no es una fila de nueve secciones. Resumen es el nombre de la obra (la Portada); Presupuesto, la herramienta Presupuestar;
// Archivos y planos y Mercado, opciones de esa herramienta (si la herramienta abierta es otra, se pasa antes por Presupuestar);
// Versiones, el menú «Versión». Devuelve cuando el clic se hizo; quien llama espera la ruta o la pantalla que le importe.
// La cabecera se vuelve a buscar en cada paso: pasar de o a una sección con Hoja la monta otra vez.
import { screen, waitFor, within } from "@testing-library/react";
import type userEvent from "@testing-library/user-event";

export type SeccionDeLaObra = "Resumen" | "Presupuesto" | "Archivos y planos" | "Mercado" | "Versiones";

const OPCION_DE_PRESUPUESTAR: Readonly<Record<"Archivos y planos" | "Mercado", string>> = {
  "Archivos y planos": "Plano o cómputo",
  Mercado: "Precios de mercado",
};

const cabecera = () => screen.findByRole("region", { name: "Obra abierta" });

export async function irASeccion(u: ReturnType<typeof userEvent.setup>, seccion: SeccionDeLaObra): Promise<void> {
  if (seccion === "Resumen") {
    await u.click(within(await cabecera()).getByRole("link", { name: /Portada de la obra/ }));
    return;
  }
  if (seccion === "Presupuesto") {
    await u.click(await within(await cabecera()).findByRole("link", { name: "Presupuestar" }));
    return;
  }
  if (seccion === "Versiones") {
    await u.click(await within(await cabecera()).findByRole("button", { name: "Versión" }));
    await u.click(await screen.findByRole("menuitem", { name: "Versiones" }));
    return;
  }
  const opcion = OPCION_DE_PRESUPUESTAR[seccion];
  if (within(await cabecera()).queryByRole("link", { name: opcion }) === null) {
    await u.click(await within(await cabecera()).findByRole("link", { name: "Presupuestar" }));
    await waitFor(() => {
      if (within(screen.getByRole("region", { name: "Obra abierta" })).queryByRole("link", { name: opcion }) === null) throw new Error(`falta «${opcion}»`);
    });
  }
  await u.click(within(await cabecera()).getByRole("link", { name: opcion }));
}
