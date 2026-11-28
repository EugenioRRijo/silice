import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import { AlertasDePrecio } from "./AlertasDePrecio";
import { ConclusionDelLibro } from "./ConclusionDelLibro";
import { alertasDePrueba, auditoriaDePrueba, auditoriaSinHallazgos, catalogoDePrueba } from "./datosDePrueba";
import { avisosDePrecio, cuentaDeHallazgos } from "./logicaDelLibro";
import { ProblemasDelLibro } from "./ProblemasDelLibro";
import { QueHacer } from "../../comun/QueHacer";

const catalogo = catalogoDePrueba();

describe("QueHacer", () => {
  const guia = catalogo.reglas["L4"];

  it("llega cerrado: no dice nada hasta que la persona lo pide", () => {
    render(<QueHacer guia={guia} />);
    const boton = screen.getByRole("button", { name: /Qué hacer/ });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(guia.que_hacer)).not.toBeInTheDocument();
    expect(screen.queryByText(guia.significa)).not.toBeInTheDocument();
  });

  it("al pulsarlo dice qué quiere decir y qué hacer, y al volver a pulsarlo se cierra", async () => {
    const usuario = userEvent.setup();
    render(<QueHacer guia={guia} />);
    const boton = screen.getByRole("button", { name: /Qué hacer/ });
    await usuario.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(guia.significa)).toBeInTheDocument();
    expect(screen.getByText(guia.que_hacer)).toBeInTheDocument();
    expect(boton).toHaveAttribute("aria-controls", screen.getByText(guia.que_hacer).closest("div")?.id);
    await usuario.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(guia.que_hacer)).not.toBeInTheDocument();
  });

  it("su nombre accesible dice de qué regla es, sin usar title", () => {
    render(<QueHacer guia={guia} />);
    const boton = screen.getByRole("button", { name: "Qué hacer con «Componente fuera del total»" });
    expect(boton).not.toHaveAttribute("title");
    expect(boton).toHaveAttribute("type", "button");
  });

  it("con Intro o Espacio también se abre", async () => {
    const usuario = userEvent.setup();
    render(<QueHacer guia={guia} />);
    const boton = screen.getByRole("button", { name: /Qué hacer/ });
    boton.focus();
    await usuario.keyboard("{Enter}");
    expect(boton).toHaveAttribute("aria-expanded", "true");
    await usuario.keyboard(" ");
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  it("una guía genérica lo dice, para no pasar por una guía propia", async () => {
    const usuario = userEvent.setup();
    render(<QueHacer guia={{ ...catalogo.generico, codigo: "ZZ9" }} />);
    await usuario.click(screen.getByRole("button", { name: /Qué hacer/ }));
    expect(screen.getByText("Guía general: esta regla todavía no tiene una guía propia.")).toBeInTheDocument();
  });
});

describe("ProblemasDelLibro", () => {
  function montar(a = auditoriaDePrueba(), c: typeof catalogo | null = catalogo) {
    return render(<ProblemasDelLibro auditoria={a} cuenta={cuentaDeHallazgos(a)} catalogo={c} />);
  }

  it("A6: una causa con seis casos se dice con su gravedad en palabra, su cuenta y su regla", () => {
    montar();
    const causas = screen.getByRole("list", { name: "Causas raíz" });
    const causa = within(causas).getByRole("listitem");
    expect(causa).toHaveTextContent("Error · 6 casos · Referencia desalineada (L1)");
    expect(causa).toHaveTextContent("PRESUPUESTO!F10 (partida 1) lee APU-01!E14 (valor 0) como rendimiento");
    expect(causa).toHaveTextContent("Encontrado 0 · esperado 120");
    expect(causa).toHaveTextContent("PRESUPUESTO!F10, PRESUPUESTO!F11, PRESUPUESTO!F12, PRESUPUESTO!F13 y 2 más");
  });

  it("A4 y A5: los hallazgos sueltos llevan celda, gravedad, regla e impacto, y su descripción", () => {
    montar();
    const sueltos = screen.getByRole("list", { name: "Hallazgos uno por uno" });
    const [l4, l5] = within(sueltos).getAllByRole("listitem");
    expect(l4).toHaveTextContent("APU-02!G36 · Error · Componente fuera del total (L4) · Impacto 1.265,00");
    expect(l4).toHaveTextContent("la fórmula APU-02!G36 =SUM(G32:G34) deja fuera transporte y disposición");
    expect(l5).toHaveTextContent("RESUMEN!B4 · Error · Referencia rota o externa (L5)");
    expect(l5).not.toHaveTextContent("Impacto");
  });

  it("cada hallazgo y cada causa tienen su «Qué hacer», cerrado", () => {
    montar();
    expect(screen.getAllByRole("button", { name: /^Qué hacer con/ })).toHaveLength(3);
    for (const b of screen.getAllByRole("button", { name: /^Qué hacer con/ })) {
      expect(b).toHaveAttribute("aria-expanded", "false");
    }
  });

  it("la gravedad se dice siempre con su palabra, además del ícono", () => {
    montar();
    const items = [
      ...within(screen.getByRole("list", { name: "Causas raíz" })).getAllByRole("listitem"),
      ...within(screen.getByRole("list", { name: "Hallazgos uno por uno" })).getAllByRole("listitem"),
    ];
    expect(items).toHaveLength(3);
    for (const item of items) {
      expect(item).toHaveTextContent(/Crítico|Error|Advertencia|Información/);
    }
    expect(document.querySelectorAll("[data-icono]").length).toBeGreaterThanOrEqual(3);
  });

  it("sin catálogo, el libro se ve igual y no hay botones «Qué hacer»", () => {
    montar(auditoriaDePrueba(), null);
    expect(screen.queryByRole("button", { name: /Qué hacer/ })).not.toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Hallazgos uno por uno" })).toBeInTheDocument();
  });

  it("un código sin guía propia recibe la genérica", async () => {
    const usuario = userEvent.setup();
    const a = auditoriaSinHallazgos();
    const base = auditoriaDePrueba();
    const conRara = { ...a, hallazgos: [{ ...base.hallazgos[0], codigo: "ZZ9" }] };
    montar(conRara);
    await usuario.click(screen.getByRole("button", { name: /Qué hacer/ }));
    expect(screen.getByText(/todavía no tiene una guía propia/)).toBeInTheDocument();
  });

  it("los avisos de regla no aplicable van aparte, plegados, y no son errores", () => {
    montar();
    const aviso = screen.getByText("Reglas que no aplicaron a este libro (1)").closest("details");
    expect(aviso).not.toBeNull();
    expect(aviso).not.toHaveAttribute("open");
    expect(within(aviso as HTMLElement).getByText(/no son errores/i)).toBeInTheDocument();
    expect(within(aviso as HTMLElement).getByText(/regla no aplicable: el libro no trae curva/)).toBeInTheDocument();
  });

  it("sin hallazgos lo dice y no pinta listas vacías", () => {
    montar(auditoriaSinHallazgos());
    expect(screen.getByText("Sílice revisó el libro y no halló nada que corregir.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("una causa de un solo caso se lee suelta, no como causa raíz", () => {
    const a = auditoriaDePrueba();
    montar({ ...a, causas: a.causas?.filter((c) => c.ocurrencias === 1) });
    expect(screen.queryByRole("list", { name: "Causas raíz" })).not.toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Hallazgos uno por uno" })).toBeInTheDocument();
  });
});

describe("AlertasDePrecio", () => {
  const avisos = avisosDePrecio(alertasDePrueba(), catalogo);

  it("A1 a A3: tipo, código del insumo y el mensaje del servidor, sin color de gravedad", () => {
    render(<AlertasDePrecio avisos={avisos} catalogo={catalogo} />);
    const [a1, a2, a3] = screen.getAllByRole("listitem");
    expect(a1).toHaveTextContent("Sin fuente · MT-04");
    expect(a1).toHaveTextContent("la FUENTE de MT-04 dice «POR COTIZAR»: el precio (INSUMOS!E12) no se puede rastrear");
    expect(a2).toHaveTextContent("Base de la empresa · MT-08");
    expect(a2).toHaveTextContent("el libro usa 18,00 USD; precio propio de la instalación 15,00 USD del 2026-10-15: +20,00 %, pasa del umbral de 5,00 %");
    expect(a3).toHaveTextContent("USD-Bs · MT-08");
    // La forma que manda fusion/alertas.py: montos a dos decimales y la tasa exacta, sin ceros finales («tasa 50», no «50,00»).
    expect(a3).toHaveTextContent(
      "900,00 Bs al 2026-10-01 (tasa 50) y 990,00 Bs al 2026-11-24 (tasa 55): +10,00 %, pasa del umbral de 5,00 %",
    );
    expect(document.querySelector("[style*='--halo-color']")).toBeNull();
    expect(document.querySelector("[data-icono]")).toBeNull();
  });

  it("dice que no son errores del libro", () => {
    render(<AlertasDePrecio avisos={avisos} catalogo={catalogo} />);
    expect(screen.getByText(/No son errores del libro/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alertas de precio (3)" })).toBeInTheDocument();
  });

  it("cada una tiene su «Qué hacer», cerrado", () => {
    render(<AlertasDePrecio avisos={avisos} catalogo={catalogo} />);
    expect(screen.getAllByRole("button", { name: /^Qué hacer con/ })).toHaveLength(3);
  });

  it("las que dicen lo mismo van en una sola línea con su cuenta", () => {
    const igual = "no contrastable: la instalación no tiene la tasa del BCV de 2026-11-24";
    const base = alertasDePrueba()[0];
    const alertas = ["MT-01", "MT-02", "MT-03", "MT-04", "MT-05", "MT-06"].map((codigo) => ({
      ...base,
      tipo: "USD-Bs",
      codigo,
      mensaje: igual,
    }));
    render(<AlertasDePrecio avisos={avisosDePrecio(alertas, catalogo)} catalogo={catalogo} />);
    const [unica] = screen.getAllByRole("listitem");
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(unica).toHaveTextContent("USD-Bs · 6 precios · MT-01, MT-02, MT-03, MT-04 y 2 más");
    expect(unica).toHaveTextContent(igual);
  });

  it("sin avisos no pinta nada", () => {
    const { container } = render(<AlertasDePrecio avisos={[]} catalogo={catalogo} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ConclusionDelLibro", () => {
  function montar(a = auditoriaDePrueba(), parcial: Partial<React.ComponentProps<typeof ConclusionDelLibro>> = {}) {
    const props: React.ComponentProps<typeof ConclusionDelLibro> = {
      auditoria: a,
      cuenta: cuentaDeHallazgos(a),
      archivo: new File(["x"], "Presupuesto cliente A.xlsx"),
      fecha: "2026-11-24",
      alOtro: vi.fn(),
      alVerLaHoja: vi.fn(),
      preparandoLaHoja: false,
      errorDeLaHoja: null,
      alExpirar: vi.fn(),
      ...parcial,
    };
    render(
      <MemoryRouter>
        <ConclusionDelLibro {...props} />
      </MemoryRouter>,
    );
    return props;
  }

  it("no cumple: lo dice con palabra y deja un solo principal, el informe", () => {
    montar();
    const seccion = screen.getByRole("region", { name: /Conclusión y entrega/ });
    expect(within(seccion).getByText("El libro no cumple")).toBeInTheDocument();
    expect(within(seccion).getByText(/Tiene 8 errores\./)).toBeInTheDocument();
    const principales = within(seccion)
      .getAllByRole("button")
      .filter((b) => b.classList.contains("cds--btn--primary"));
    expect(principales.map((b) => b.textContent)).toEqual(["Descargar el informe en PDF"]);
    expect(within(seccion).queryByRole("button", { name: "Auditar otro libro" })).not.toBeInTheDocument();
  });

  it("explica qué baja el informe", () => {
    montar();
    expect(screen.getByText(/Un informe de esta auditoría para entregar a quien hizo el libro/)).toBeInTheDocument();
  });

  it("«Ver la hoja marcada» es secundario y avisa mientras prepara", async () => {
    const usuario = userEvent.setup();
    const props = montar();
    const boton = screen.getByRole("button", { name: "Ver la hoja marcada" });
    expect(boton).toHaveClass("cds--btn--secondary");
    await usuario.click(boton);
    expect(props.alVerLaHoja).toHaveBeenCalledTimes(1);
  });

  it("preparando la hoja el botón dice que está trabajando y no se puede pulsar dos veces", () => {
    montar(auditoriaDePrueba(), { preparandoLaHoja: true });
    expect(screen.getByRole("button", { name: "Preparando la hoja…" })).toBeDisabled();
  });

  it("un error al preparar la hoja se dice con su detalle y deja el resultado a la vista", () => {
    montar(auditoriaDePrueba(), { errorDeLaHoja: new ErrorDeApi(422, "No se pudo leer la hoja.") });
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo leer la hoja.");
    expect(screen.getByRole("button", { name: "Ver la hoja marcada" })).toBeEnabled();
  });

  it("lleva al historial con un enlace", () => {
    montar();
    expect(screen.getByRole("link", { name: "Ver el historial" })).toHaveAttribute("href", "/auditoria/historial");
  });

  it("cumple y sin nada que corregir: el principal es auditar otro libro", async () => {
    const usuario = userEvent.setup();
    const props = montar(auditoriaSinHallazgos());
    expect(screen.getByText("El libro cumple")).toBeInTheDocument();
    expect(screen.getByText("Sílice no halló nada que corregir.")).toBeInTheDocument();
    const otro = screen.getByRole("button", { name: "Auditar otro libro" });
    expect(otro).toHaveClass("cds--btn--primary");
    await usuario.click(otro);
    expect(props.alOtro).toHaveBeenCalledTimes(1);
  });

  it("el aviso del historial se muestra tal como lo dice el servidor", () => {
    montar(auditoriaDePrueba({ aviso_historial: "No se pudo guardar la auditoría en el historial." }));
    expect(screen.getByText("No se pudo guardar la auditoría en el historial.")).toBeInTheDocument();
  });

  it("los totales del libro frente a Sílice salen de la franja, con su valor del servidor", () => {
    const a = auditoriaDePrueba({
      indicadores: [
        {
          clave: "TOTALGEN",
          titulo: "Total general",
          actual: "2418730.00",
          meta: "2376044.50",
          delta: "42685.50",
          delta_pct: "1.80",
          sentido: "exactitud",
        },
      ],
    });
    montar(a);
    expect(screen.getByRole("region", { name: "Indicadores del libro" })).toBeInTheDocument();
  });
});
