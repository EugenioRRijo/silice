import { render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { LimiteDeError } from "./LimiteDeError";

// Ronda 2 de la Tarea 3 del plan F4 (menor 4 del árbitro): el marco ya no le cambia la `key` al límite de fuera de la
// sección mientras se navega dentro de una obra (la cabecera y el proveedor de la Hoja no se vuelven a montar). Con
// `reinicio`, un error se olvida al navegar sin volver a montar lo que no falló.

const AVISO = "No se pudo abrir la pantalla";

let montajes = 0;
function Hijo({ falla }: { falla: boolean }) {
  if (falla) throw new Error("fallo de prueba");
  return <Contador />;
}
function Contador() {
  useEffect(() => {
    montajes += 1;
  }, []);
  return <p>contenido</p>;
}

beforeEach(() => {
  montajes = 0;
  vi.spyOn(console, "error").mockImplementation(() => undefined);
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("LimiteDeError con reinicio", () => {
  test("un error se olvida cuando cambia el reinicio", () => {
    const { rerender } = render(
      <LimiteDeError reinicio="/obra/empresa/7/presupuesto">
        <Hijo falla />
      </LimiteDeError>,
    );
    expect(screen.getByText(AVISO)).toBeInTheDocument();
    rerender(
      <LimiteDeError reinicio="/obra/empresa/7/versiones">
        <Hijo falla={false} />
      </LimiteDeError>,
    );
    expect({ aviso: screen.queryByText(AVISO) !== null, contenido: screen.queryByText("contenido") !== null }).toEqual({
      aviso: false,
      contenido: true,
    });
  });

  test("con el mismo reinicio el error se queda", () => {
    const { rerender } = render(
      <LimiteDeError reinicio="/a">
        <Hijo falla />
      </LimiteDeError>,
    );
    rerender(
      <LimiteDeError reinicio="/a">
        <Hijo falla={false} />
      </LimiteDeError>,
    );
    expect(screen.getByText(AVISO)).toBeInTheDocument();
  });

  test("sin error, cambiar el reinicio no vuelve a montar lo de dentro", () => {
    const { rerender } = render(
      <LimiteDeError reinicio="/a">
        <Hijo falla={false} />
      </LimiteDeError>,
    );
    rerender(
      <LimiteDeError reinicio="/b">
        <Hijo falla={false} />
      </LimiteDeError>,
    );
    expect(montajes).toBe(1);
  });
});
