import { render, screen, within } from "@testing-library/react";
import { alertaConTexto } from "../../../test/ayudas";
import userEvent from "@testing-library/user-event";
import { useEffect, useRef, useState } from "react";
import { describe, expect, test, vi } from "vitest";
import type { HallazgoInformeRespuesta, InformeAuditoriaRespuesta } from "../../../api/tipos";
import { Grilla } from "../../../comun/Grilla";
import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { informeAuditoria, vistaPresupuesto } from "../datosDePrueba";
import type { FilaPresupuesto } from "../logica";
import { InspectorDeProblemas } from "./InspectorDeProblemas";
import type { PropiedadesDeInspectorDeProblemas } from "./InspectorDeProblemas";
import type { RevisionDeLaSuperficie } from "./logica";

// Lote B1-7 (ficha-b1 §1.10 prueba 8, §2 T3 y §4): inspector lateral no modal de Problemas.
// Muestra «3 problemas en 2 partidas», agrupados por regla, con severidad en palabra, sin hallazgos usando `sin_hallazgos`
// del servidor, sin abrir nada no pedido y avisando qué fila activar al elegir un problema.

function crearFila(clave: string, partida: string, descripcion: string): Pick<FilaPresupuesto, "clave" | "partida" | "descripcion"> {
  return { clave, partida, descripcion };
}

function crearHallazgo(
  parcial: Partial<HallazgoInformeRespuesta> & Pick<HallazgoInformeRespuesta, "numero" | "regla" | "severidad">,
): HallazgoInformeRespuesta {
  return {
    numero: parcial.numero,
    regla: parcial.regla,
    severidad: parcial.severidad,
    partida: parcial.partida ?? null,
    descripcion: parcial.descripcion ?? `Detalle del hallazgo ${String(parcial.numero)}`,
    impacto: parcial.impacto ?? null,
    observado: parcial.observado ?? null,
    esperado: parcial.esperado ?? null,
    origen: parcial.origen ?? [],
  };
}

function informeTresProblemasEnDosPartidas(): {
  informe: InformeAuditoriaRespuesta;
  filas: Pick<FilaPresupuesto, "clave" | "partida" | "descripcion">[];
} {
  const filas = [
    crearFila("CIM-01|manual", "CIM-01", "Excavación a mano"),
    crearFila("MUR-02|manual", "MUR-02", "Muro de bloques"),
    crearFila("FRI-01|manual", "FRI-01", "Friso de pared"),
  ];
  const informe: InformeAuditoriaRespuesta = {
    codigo_presupuesto: "OF-001-001",
    cumple: false,
    veredicto: "NO CUMPLE",
    total_hallazgos: 4,
    por_severidad: [
      { severidad: "CRITICO", total: 1 },
      { severidad: "ERROR", total: 1 },
      { severidad: "ADVERTENCIA", total: 1 },
      { severidad: "INFO", total: 1 },
    ],
    reglas_evaluadas: [
      { regla: "R01", nombre: "Rendimiento fuera de rango", hallazgos: 1 },
      { regla: "R02", nombre: "Insumos y precios", hallazgos: 2 },
      { regla: "R03", nombre: "Notas informativas", hallazgos: 1 },
    ],
    hallazgos: [
      crearHallazgo({
        numero: 1,
        regla: "R01",
        severidad: "CRITICO",
        partida: "CIM-01",
        descripcion: "El rendimiento supera el tope de 12.50 m2/día.",
      }),
      crearHallazgo({
        numero: 2,
        regla: "R02",
        severidad: "ERROR",
        partida: "CIM-01",
        descripcion: "Falta cotización del cemento.",
      }),
      crearHallazgo({
        numero: 3,
        regla: "R02",
        severidad: "ADVERTENCIA",
        partida: "MUR-02",
        descripcion: "Cotización con más de 90 días.",
      }),
      crearHallazgo({
        numero: 4,
        regla: "R03",
        severidad: "INFO",
        partida: "FRI-01",
        descripcion: "Nota informativa que no cuenta como problema.",
      }),
    ],
    sin_hallazgos: null,
  };
  return { informe, filas };
}

function montar(parcial: Partial<PropiedadesDeInspectorDeProblemas> = {}) {
  const { informe, filas } = informeTresProblemasEnDosPartidas();
  const alElegirFila = vi.fn();
  const alCerrar = vi.fn();
  const props: PropiedadesDeInspectorDeProblemas = {
    abierto: true,
    revision: { estado: "lista", informe },
    filas,
    alElegirFila,
    alCerrar,
    ...parcial,
  };
  return { ...render(<InspectorDeProblemas {...props} />), alElegirFila, alCerrar };
}

describe("InspectorDeProblemas (lote B1-7)", () => {
  test("cerrado no renderiza nada ni abre popovers que la persona no pidió", () => {
    const { container } = montar({ abierto: false });
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(container.querySelectorAll("[popover], [role='dialog']")).toHaveLength(0);
  });

  test("muestra «3 problemas en 2 partidas», agrupados por regla, con severidad en palabra y excluyendo INFO", () => {
    const { container } = montar();

    const panel = screen.getByRole("complementary", { name: "Problemas" });
    const titulo = within(panel).getByRole("heading", { level: 2, name: "Problemas" });
    expect(titulo).toHaveFocus();
    expect(within(panel).getByRole("button", { name: "Cerrar" })).toBeInTheDocument();

    expect(within(panel).getByText("3 problemas en 2 partidas")).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { level: 3, name: "Rendimiento fuera de rango" })).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { level: 3, name: "Insumos y precios" })).toBeInTheDocument();
    expect(within(panel).queryByRole("heading", { level: 3, name: "Notas informativas" })).toBeNull();

    expect(within(panel).getByText("Crítico")).toBeInTheDocument();
    expect(within(panel).getByText("Error")).toBeInTheDocument();
    expect(within(panel).getByText("Advertencia")).toBeInTheDocument();
    expect(within(panel).getByText("El rendimiento supera el tope de 12,50 m2/día.")).toBeInTheDocument();
    expect(within(panel).queryByText("Nota informativa que no cuenta como problema.")).toBeNull();

    expect(container.querySelectorAll("[title]")).toHaveLength(0);
  });

  test("elegir un problema llama a alElegirFila con la clave de la fila que lo causa", async () => {
    const u = userEvent.setup();
    const { alElegirFila } = montar();

    await u.click(screen.getByRole("button", { name: /^Ir a la partida CIM-01.*Rendimiento fuera de rango/ }));
    expect(alElegirFila).toHaveBeenCalledTimes(1);
    expect(alElegirFila).toHaveBeenLastCalledWith("CIM-01|manual");

    await u.click(screen.getByRole("button", { name: /^Ir a la partida MUR-02/ }));
    expect(alElegirFila).toHaveBeenCalledTimes(2);
    expect(alElegirFila).toHaveBeenLastCalledWith("MUR-02|manual");
  });

  test("prueba 8 de §1.10: al elegir un problema en conjunto con la grilla, activa y lleva el foco a la fila que lo causa", async () => {
    const u = userEvent.setup();
    const { informe, filas } = informeTresProblemasEnDosPartidas();
    const columnas: ColumnaDeGrilla<(typeof filas)[number]>[] = [
      { clave: "partida", titulo: "Partida", valor: (f) => f.partida },
      { clave: "descripcion", titulo: "Descripción", valor: (f) => f.descripcion },
    ];

    function SuperficieDePrueba() {
      const [abierto, setAbierto] = useState(false);
      const [filaElegida, setFilaElegida] = useState<string | null>(null);
      const contenedorGrilla = useRef<HTMLDivElement>(null);

      useEffect(() => {
        if (filaElegida === null) return;
        const filaDom = contenedorGrilla.current?.querySelector<HTMLElement>(
          `tr[aria-selected="true"] [data-celda]`,
        );
        filaDom?.focus();
      }, [filaElegida]);

      return (
        <div>
          <button type="button" onClick={() => setAbierto(true)}>
            Problemas (3)
          </button>
          <div ref={contenedorGrilla}>
            <Grilla
              etiqueta="Presupuesto"
              columnas={columnas}
              filas={filas}
              idDeFila={(f) => f.clave}
              filaElegida={filaElegida}
            />
          </div>
          <InspectorDeProblemas
            abierto={abierto}
            revision={{ estado: "lista", informe }}
            filas={filas}
            alElegirFila={(clave) => setFilaElegida(clave)}
            alCerrar={() => setAbierto(false)}
          />
        </div>
      );
    }

    render(<SuperficieDePrueba />);
    const botonProblemas = screen.getByRole("button", { name: "Problemas (3)" });
    await u.click(botonProblemas);

    expect(screen.getByRole("heading", { level: 2, name: "Problemas" })).toHaveFocus();
    await u.click(screen.getByRole("button", { name: /^Ir a la partida MUR-02/ }));

    const grilla = screen.getByRole("grid", { name: "Presupuesto" });
    const filaMur = within(grilla).getByText("MUR-02").closest("tr");
    expect(filaMur).toHaveAttribute("aria-selected", "true");
    expect(within(grilla).getByRole("rowheader", { name: "MUR-02" })).toHaveFocus();

    await u.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(screen.queryByRole("complementary", { name: "Problemas" })).toBeNull();
    expect(botonProblemas).toHaveFocus();
  });

  test("con datosDePrueba mantiene el hallazgo sin fila solo en la lista y muestra el texto Markdown como texto plano", () => {
    const informe = informeAuditoria();
    const filas = vistaPresupuesto().filas;
    montar({ revision: { estado: "lista", informe }, filas });

    expect(screen.getByText("2 problemas en 1 partida")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Origen de la medida" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Conexión de cada punto" })).toBeInTheDocument();
    expect(screen.getByText("Fuente F1: falta el origen ![x](http://ejemplo.invalid/a.png)")).toBeInTheDocument();
    expect(screen.getByText("En el presupuesto")).toBeInTheDocument();
    expect(document.querySelectorAll("img, a")).toHaveLength(0);

    const botonesIr = screen.getAllByRole("button", { name: /^Ir a la partida/ });
    expect(botonesIr).toHaveLength(1);
    expect(botonesIr[0]).toHaveAccessibleName(/^Ir a la partida AF-LLAVE/);
  });

  test("sin hallazgos muestra el texto sin_hallazgos del servidor", () => {
    const informe = informeAuditoria({
      cumple: true,
      veredicto: "CUMPLE",
      total_hallazgos: 0,
      por_severidad: [],
      hallazgos: [],
      sin_hallazgos: "Sílice revisó 18 reglas y no halló problemas.",
    });
    montar({ revision: { estado: "lista", informe }, filas: vistaPresupuesto().filas });

    expect(screen.getByText("Sin problemas")).toBeInTheDocument();
    expect(screen.getByText("Sílice revisó 18 reglas y no halló problemas.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ir a la partida/ })).toBeNull();
  });

  test("si solo hay hallazgos INFO y sin_hallazgos es null, informa que no halló problemas usando reglas_evaluadas", () => {
    const informe = informeAuditoria({
      hallazgos: [crearHallazgo({ numero: 1, regla: "R3", severidad: "INFO", partida: null })],
      sin_hallazgos: null,
    });
    montar({ revision: { estado: "lista", informe }, filas: vistaPresupuesto().filas });

    expect(screen.getByText("Sin problemas")).toBeInTheDocument();
    expect(screen.getByText("Sílice revisó 2 reglas y no halló problemas.")).toBeInTheDocument();
  });

  test("muestra singular en «1 problema en 1 partida» y «1 problema en el presupuesto»", () => {
    const { filas } = informeTresProblemasEnDosPartidas();
    const unProblemaEnFila = informeAuditoria({
      reglas_evaluadas: [{ regla: "R01", nombre: "Rendimiento fuera de rango", hallazgos: 1 }],
      hallazgos: [crearHallazgo({ numero: 1, regla: "R01", severidad: "ERROR", partida: "CIM-01" })],
    });
    const { rerender } = montar({ revision: { estado: "lista", informe: unProblemaEnFila }, filas });
    expect(screen.getByText("1 problema en 1 partida")).toBeInTheDocument();

    const unProblemaGlobal = informeAuditoria({
      reglas_evaluadas: [{ regla: "R08", nombre: "Parámetros generales", hallazgos: 1 }],
      hallazgos: [crearHallazgo({ numero: 1, regla: "R08", severidad: "ADVERTENCIA", partida: null })],
    });
    rerender(
      <InspectorDeProblemas
        abierto
        revision={{ estado: "lista", informe: unProblemaGlobal }}
        filas={filas}
        alElegirFila={vi.fn()}
        alCerrar={vi.fn()}
      />,
    );
    expect(screen.getByText("1 problema en el presupuesto")).toBeInTheDocument();
  });

  test("estado cargando no usa región viva y estado error permite reintentar la revisión", async () => {
    const u = userEvent.setup();
    const alReintentar = vi.fn();
    const cargando: RevisionDeLaSuperficie = { estado: "cargando" };
    const { container, rerender } = montar({ revision: cargando });

    expect(screen.getByText("Revisando el presupuesto…")).toBeInTheDocument();
    const regionesVivas = container.querySelectorAll('[role="status"], [role="alert"], [aria-live]');
    expect(regionesVivas).toHaveLength(0);

    rerender(
      <InspectorDeProblemas
        abierto
        revision={{ estado: "error" }}
        filas={[]}
        alElegirFila={vi.fn()}
        alCerrar={vi.fn()}
        error={new Error("Tiempo de espera agotado.")}
        alReintentar={alReintentar}
      />,
    );

    // Carbon pone además un role="alert" vacío: la alerta de verdad es la que trae texto.
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("No se pudo revisar el presupuesto");
    // Un Error común no muestra su mensaje interno (mensajeDeError): solo el detalle de un ErrorDeApi llega a la persona.
    expect(alerta).toHaveTextContent("Ocurrió un error inesperado. Inténtelo de nuevo.");
    expect(alerta).not.toHaveTextContent("Tiempo de espera agotado.");
    await u.click(screen.getByRole("button", { name: "Reintentar la revisión" }));
    expect(alReintentar).toHaveBeenCalledTimes(1);
  });
});
