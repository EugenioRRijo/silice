import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { Evaluacion } from "./cliente";
import { PanelDesglose } from "./PanelDesglose";

const BASE: Evaluacion = {
  estado: "valido",
  aviso: null,
  desglose: {
    materiales: "20.00",
    equipos: "1.50",
    mano_obra: "3.25",
    costo_directo: "24.75",
    con_administracion: "29.70",
    precio_unitario: "29.70",
  },
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};

describe("PanelDesglose", () => {
  test("sin respuesta todavía, dice que no hay desglose", () => {
    render(<PanelDesglose evaluacion={null} cargando={false} error={null} />);
    expect(screen.getByRole("heading", { name: "Desglose en vivo" })).toBeInTheDocument();
    expect(screen.getByText(/Aún no hay desglose/)).toBeInTheDocument();
  });

  test("vacío e incompleto muestran el aviso de la API como información", () => {
    render(<PanelDesglose evaluacion={{ ...BASE, estado: "vacio", desglose: null, aviso: "Comience por la cabecera." }} cargando={false} error={null} />);
    expect(screen.getByText("Comience por la cabecera.")).toBeInTheDocument();
    expect(screen.queryByText("Precio unitario")).not.toBeInTheDocument();
  });

  test("válido: seis montos exactos, tal como los manda la API", () => {
    render(<PanelDesglose evaluacion={BASE} cargando={false} error={null} />);
    for (const [rotulo, monto] of [
      ["Materiales", "20.00"],
      ["Equipos", "1.50"],
      ["Mano de obra", "3.25"],
      ["Costo directo", "24.75"],
      ["Con administración", "29.70"],
    ] as const) {
      const fila = screen.getByText(rotulo).closest("tr")!;
      expect(fila).toHaveTextContent(monto);
    }
    const pu = screen.getByText("Precio unitario").closest("tr")!;
    expect(pu).toHaveTextContent("29.70");
    expect(pu.querySelector(".silice-cifra")).not.toBeNull();
  });

  test("las advertencias se pintan como avisos y no bloquean el desglose", () => {
    render(
      <PanelDesglose
        evaluacion={{
          ...BASE,
          requiere_justificacion: true,
          advertencias: [
            { tipo: "rendimiento", texto: "El rendimiento se aparta de lo observado." },
            { tipo: "precio_atipico", texto: "Precio atípico ficticio." },
          ],
        }}
        cargando={false}
        error={null}
      />,
    );
    expect(screen.getByText("El rendimiento se aparta de lo observado.")).toBeInTheDocument();
    expect(screen.getByText("Precio atípico ficticio.")).toBeInTheDocument();
    expect(screen.getByText("Precio unitario")).toBeInTheDocument();
  });

  test("el contraste con la estimación por reglas muestra técnica, registros y PU estimado", () => {
    render(
      <PanelDesglose
        evaluacion={{
          ...BASE,
          contraste: { tecnica: "regla ficticia", registros: 4, pu_estimado: "28.00", dentro_de_rango: true },
        }}
        cargando={false}
        error={null}
      />,
    );
    expect(screen.getByRole("heading", { name: /Contraste con la estimación por reglas/ })).toBeInTheDocument();
    expect(screen.getByText(/regla ficticia/)).toBeInTheDocument();
    expect(screen.getByText(/28\.00/)).toBeInTheDocument();
    expect(screen.getByText(/dentro del rango/i)).toBeInTheDocument();
  });

  test("un error de la API se muestra con su detalle", () => {
    render(<PanelDesglose evaluacion={null} cargando={false} error="Falla ficticia del desglose." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Falla ficticia del desglose.");
  });

  test("mientras recalcula lo marca y conserva el último desglose", () => {
    render(<PanelDesglose evaluacion={BASE} cargando error={null} />);
    expect(screen.getByText("Recalculando…")).toBeInTheDocument();
    expect(screen.getByText("Precio unitario")).toBeInTheDocument();
  });
});
