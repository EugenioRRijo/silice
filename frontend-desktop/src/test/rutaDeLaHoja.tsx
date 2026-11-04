import { act, screen } from "@testing-library/react";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { MemoryRouter, useNavigate } from "react-router";
import type { NavigateFunction } from "react-router";

// Solo lo importan las pruebas (vive en `src/test/` desde el cierre de F4, menor 3 de la Tarea 6). Por qué existe (baja 9
// de la Tarea 6 del plan F4): sin el selector «Versión», la Hoja abre otra versión por `?version=<código>` en la ruta, que
// es lo que hace «Abrir» de Versiones. Las pruebas que montan la Hoja sola la envuelven en un enrutador de memoria
// (`conEnrutador`) y piden la versión con `pedirVersionPorLaRuta`; la versión abierta la leen en el estado del borrador
// (`versionAbierta`), que es donde la ve la persona.

let navegar: NavigateFunction | null = null;

function Navegador() {
  const n = useNavigate();
  useEffect(() => {
    navegar = n;
    return () => {
      navegar = null;
    };
  }, [n]);
  return null;
}

export function conEnrutador(nodo: ReactNode): ReactNode {
  return (
    <MemoryRouter>
      <Navegador />
      {nodo}
    </MemoryRouter>
  );
}

export function pedirVersionPorLaRuta(codigo: string): void {
  const n = navegar;
  if (n === null) throw new Error("pedirVersionPorLaRuta necesita la Hoja montada con conEnrutador.");
  act(() => {
    void n(`?${new URLSearchParams({ version: codigo }).toString()}`);
  });
}

// «Versión 002 · Sin cambios sin guardar» → "002"; el borrador en blanco, o sin borrador, → null.
export function versionAbierta(): string | null {
  const estado = screen.queryByRole("region", { name: "Estado del borrador", hidden: true });
  const linea = estado?.querySelector("p")?.textContent ?? "";
  return /^Versión (\S+) ·/.exec(linea)?.[1] ?? null;
}
