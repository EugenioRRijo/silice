import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import type { HallazgoLibroRespuesta, HojaVisualRespuesta } from "../api/tipos";
import { ListaHallazgos } from "./ListaHallazgos";

const hallazgos: HallazgoLibroRespuesta[] = [
  {
    codigo: "L3",
    severidad: "CRITICO",
    descripcion: "El total no coincide con la suma de las partidas",
    celda: "PRESUPUESTO!F12",
    impacto: "238.407",
    accion: "Corregir la suma",
  },
  {
    codigo: "L5",
    severidad: "ERROR",
    descripcion: "Precio unitario distinto al de INSUMOS",
    celda: "APU-01!G48",
    impacto: "12.50",
    accion: "Igualar el precio",
  },
  {
    codigo: "L7",
    severidad: "ADVERTENCIA",
    descripcion: "El libro no declara la fecha de la portada",
    celda: "",
    impacto: null,
    accion: "Completar la portada",
  },
  {
    codigo: "L9",
    severidad: "INFO",
    descripcion: "Rendimiento fuera de rango",
    celda: "APU-01!Rendimiento",
    impacto: null,
    accion: "Revisar",
  },
];

function hoja(nombre: string, extra: Partial<HojaVisualRespuesta> = {}): HojaVisualRespuesta {
  return {
    nombre,
    visible: true,
    filas: 60,
    columnas: 10,
    anchos: {},
    altos: {},
    ocultas_filas: [],
    ocultas_columnas: [],
    combinadas: [],
    fijas: null,
    celdas: [],
    ...extra,
  };
}

function montar(extra: Partial<React.ComponentProps<typeof ListaHallazgos>> = {}) {
  const irACelda = vi.fn();
  const onElegir = vi.fn();
  const vista = render(
    <ListaHallazgos
      hallazgos={hallazgos}
      seleccionado={null}
      irACelda={irACelda}
      onElegir={onElegir}
      {...extra}
    />,
  );
  return { irACelda, onElegir, unmount: vista.unmount };
}

function fila(descripcion: string): HTMLElement {
  const celda = screen.getByText(descripcion);
  const f = celda.closest("tr");
  if (!f) throw new Error("sin fila");
  return f;
}

describe("ListaHallazgos", () => {
  // axe «scrollable-region-focusable» (recorrido de medición 2026-11-28, T2): sin hallazgos, el cuerpo se desplaza y no
  // tiene nada enfocable; con el teclado no se podía leer. La región se nombra y entra en el orden de Tab.
  test("el cuerpo desplazable es una región con nombre que se alcanza con Tab, también sin hallazgos", () => {
    montar({ hallazgos: [] });
    const region = screen.getByRole("region", { name: "Lista de hallazgos" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(within(region).getByText("La auditoría terminó y el libro no tiene hallazgos.")).toBeInTheDocument();
  });

  test("lista todos los hallazgos con el nombre de su severidad en texto", () => {
    montar();
    expect(within(fila("El total no coincide con la suma de las partidas")).getByText("Crítico")).toBeInTheDocument();
    expect(within(fila("Precio unitario distinto al de INSUMOS")).getByText("Error")).toBeInTheDocument();
    expect(within(fila("El libro no declara la fecha de la portada")).getByText("Advertencia")).toBeInTheDocument();
    expect(within(fila("Rendimiento fuera de rango")).getByText("Información")).toBeInTheDocument();
  });

  test("la celda va en Plex Mono y el impacto sale en es-VE (coma decimal), no con el punto de la API (M4)", () => {
    montar();
    const f = fila("El total no coincide con la suma de las partidas");
    const celda = within(f).getByText("PRESUPUESTO!F12");
    expect(celda).toHaveClass("silice-codigo");
    expect(within(f).queryByText("238.407")).toBeNull();
    const impacto = within(f).getByText("238,407");
    expect(impacto).toHaveClass("silice-cifra");
  });

  test("la primera linea de cada fila es celda, severidad, codigo e impacto, en ese orden (M5)", () => {
    montar();
    const linea = fila("El total no coincide con la suma de las partidas").querySelector(".hallazgo__encabezado");
    expect(linea?.textContent?.replace(/\s+/g, " ").trim()).toBe("PRESUPUESTO!F12 · Crítico · L3 · Impacto 238,407");
    const sinImpacto = fila("Precio unitario distinto al de INSUMOS").querySelector(".hallazgo__encabezado");
    expect(sinImpacto?.textContent).toContain("APU-01!G48 · Error · L5 · Impacto 12,50");
  });

  test("sin celda la primera linea lo dice, y sin impacto no deja un hueco (M4, M5)", () => {
    montar();
    const linea = fila("El libro no declara la fecha de la portada").querySelector(".hallazgo__encabezado");
    expect(linea?.textContent?.replace(/\s+/g, " ").trim()).toBe("Sin celda · Advertencia · L7");
  });

  test("no hay columna Impacto: el impacto vive en la primera linea (M4)", () => {
    montar();
    expect(screen.queryByRole("columnheader", { name: "Impacto" })).toBeNull();
    expect(screen.queryByText("sin impacto")).toBeNull();
  });

  test("la descripcion se recorta a 3 lineas y solo la fila elegida la muestra completa (M5)", () => {
    montar({ seleccionado: 1 });
    const elegida = fila("Precio unitario distinto al de INSUMOS");
    const otra = fila("El total no coincide con la suma de las partidas");
    expect(elegida).toHaveClass("lista-hallazgos__fila--elegida");
    expect(otra).not.toHaveClass("lista-hallazgos__fila--elegida");
    expect(within(otra).getByText("El total no coincide con la suma de las partidas")).toHaveClass("hallazgo__descripcion");
  });

  test("solo una fila entra en el orden de Tab y las flechas mueven el foco entre filas (m3)", async () => {
    const usuario = userEvent.setup();
    montar();
    const filas = [...document.querySelectorAll<HTMLElement>("tr[data-indice]")];
    expect(filas.filter((f) => f.tabIndex === 0)).toHaveLength(1);
    expect(filas[0].tabIndex).toBe(0);
    filas[0].focus();
    await usuario.keyboard("{ArrowDown}");
    expect(filas[1]).toHaveFocus();
    expect(filas[1].tabIndex).toBe(0);
    expect(filas[0].tabIndex).toBe(-1);
    await usuario.keyboard("{End}");
    expect(filas[filas.length - 1]).toHaveFocus();
    await usuario.keyboard("{Home}");
    expect(filas[0]).toHaveFocus();
    await usuario.keyboard("{ArrowUp}");
    expect(filas[0]).toHaveFocus();
  });

  test("con una fila elegida, esa es la parada de Tab (m3)", () => {
    montar({ seleccionado: 1 });
    expect(fila("Precio unitario distinto al de INSUMOS").tabIndex).toBe(0);
    expect(fila("El total no coincide con la suma de las partidas").tabIndex).toBe(-1);
  });

  test("la fila elegida dice de que fila de la hoja habla el hallazgo, aunque la hoja no deje ver esa columna (M1)", () => {
    const contextoDe = vi.fn((c: { hoja: string; fila0: number }) => `Fila ${c.fila0 + 1}: Friso liso (ficticio)`);
    montar({ seleccionado: 1, contextoDeCelda: contextoDe });
    const elegida = fila("Precio unitario distinto al de INSUMOS");
    expect(within(elegida).getByText("Fila 48: Friso liso (ficticio)")).toHaveClass("hallazgo__contexto");
    expect(within(fila("El total no coincide con la suma de las partidas")).queryByText(/Friso liso/)).toBeNull();
  });

  test("sin texto de contexto no se pinta la linea", () => {
    montar({ seleccionado: 1, contextoDeCelda: () => null });
    expect(document.querySelector(".hallazgo__contexto")).toBeNull();
  });

  test("la fila elegida muestra la acción que manda el servidor; las demás y una acción vacía no la pintan", () => {
    const { unmount } = montar({ seleccionado: 1 });
    const elegida = fila("Precio unitario distinto al de INSUMOS");
    expect(within(elegida).getByText("Acción: Igualar el precio")).toHaveClass("hallazgo__accion");
    expect(within(fila("El total no coincide con la suma de las partidas")).queryByText(/^Acción:/)).toBeNull();
    unmount();
    montar({ hallazgos: [{ ...hallazgos[0], accion: "" }], seleccionado: 0 });
    expect(document.querySelector(".hallazgo__accion")).toBeNull();
  });

  test("muestra el nombre de la regla junto al código cuando el servidor lo manda, y solo el código si viene vacío", () => {
    montar({
      hallazgos: [
        { ...hallazgos[0], codigo: "L4", nombre_regla: "Componente fuera del total" },
        { ...hallazgos[1], codigo: "L5", nombre_regla: "" },
      ],
    });
    const conNombre = fila("El total no coincide con la suma de las partidas");
    expect(conNombre.querySelector(".hallazgo__encabezado")?.textContent?.replace(/\s+/g, " ").trim()).toBe(
      "PRESUPUESTO!F12 · Crítico · Componente fuera del total (L4) · Impacto 238,407",
    );
    expect(within(conNombre).getByText("L4")).toHaveClass("silice-codigo");
    const sinNombre = fila("Precio unitario distinto al de INSUMOS");
    expect(sinNombre.querySelector(".hallazgo__encabezado")?.textContent?.replace(/\s+/g, " ").trim()).toBe(
      "APU-01!G48 · Error · L5 · Impacto 12,50",
    );
  });

  test("los filtros por severidad llevan icono ademas del texto y el numero (el color nunca va solo)", () => {
    montar();
    const boton = screen.getByRole("button", { name: "Crítico 1" });
    expect(boton.querySelector("svg")).not.toBeNull();
  });

  test("filtrar por Critico deja solo los criticos", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.click(screen.getByRole("button", { name: /^Crítico/ }));
    expect(screen.getByText("El total no coincide con la suma de las partidas")).toBeInTheDocument();
    expect(screen.queryByText("Precio unitario distinto al de INSUMOS")).not.toBeInTheDocument();
    expect(screen.queryByText("Rendimiento fuera de rango")).not.toBeInTheDocument();
  });

  test("quitar el filtro devuelve todos", async () => {
    const usuario = userEvent.setup();
    montar();
    const boton = screen.getByRole("button", { name: /^Crítico/ });
    await usuario.click(boton);
    await usuario.click(boton);
    expect(screen.getByText("Precio unitario distinto al de INSUMOS")).toBeInTheDocument();
  });

  test("los botones del filtro dicen cuantos hay de cada severidad", () => {
    montar();
    expect(screen.getByRole("button", { name: "Crítico 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Advertencia 1" })).toBeInTheDocument();
  });

  test("los hallazgos sin celda ubicable van en el grupo Sin celda en el libro", () => {
    montar();
    const grupo = screen.getByRole("region", { name: /Sin celda en el libro/ });
    expect(within(grupo).getByText("El libro no declara la fecha de la portada")).toBeInTheDocument();
    expect(within(grupo).getByText("Rendimiento fuera de rango")).toBeInTheDocument();
    expect(within(grupo).queryByText("Precio unitario distinto al de INSUMOS")).not.toBeInTheDocument();
    // La referencia que no es A1 se muestra tal cual, para que el auditor sepa donde buscar.
    expect(within(grupo).getByText("APU-01!Rendimiento")).toBeInTheDocument();
  });

  test("sin hallazgos sin celda no aparece el grupo", () => {
    montar({ hallazgos: hallazgos.slice(0, 2) });
    expect(screen.queryByRole("region", { name: /Sin celda en el libro/ })).not.toBeInTheDocument();
  });

  test("clic en un hallazgo llama a irACelda con la hoja y la celda en base 0", async () => {
    const usuario = userEvent.setup();
    const { irACelda, onElegir } = montar();
    await usuario.click(fila("El total no coincide con la suma de las partidas"));
    expect(onElegir).toHaveBeenCalledWith(0);
    expect(irACelda).toHaveBeenCalledWith({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 }, 0);
  });

  test("clic en un hallazgo sin celda lo elige pero no mueve la hoja", async () => {
    const usuario = userEvent.setup();
    const { irACelda, onElegir } = montar();
    await usuario.click(fila("El libro no declara la fecha de la portada"));
    expect(onElegir).toHaveBeenCalledWith(2);
    expect(irACelda).not.toHaveBeenCalled();
  });

  test("con el teclado, Enter sobre una fila hace lo mismo que el clic", async () => {
    const usuario = userEvent.setup();
    const { irACelda } = montar();
    fila("Precio unitario distinto al de INSUMOS").focus();
    await usuario.keyboard("{Enter}");
    expect(irACelda).toHaveBeenCalledWith({ hoja: "APU-01", fila0: 47, columna0: 6 }, 1);
  });

  test("la fila elegida se marca con aria-current", () => {
    montar({ seleccionado: 1 });
    expect(fila("Precio unitario distinto al de INSUMOS")).toHaveAttribute("aria-current", "true");
    expect(fila("El total no coincide con la suma de las partidas")).not.toHaveAttribute("aria-current");
  });

  test("enfocar mueve el foco del teclado a la fila pedida", () => {
    montar({ seleccionado: 1, enfocar: { indice: 1, n: 1 } });
    expect(fila("Precio unitario distinto al de INSUMOS")).toHaveFocus();
  });

  describe("hallazgos en hojas, filas o columnas ocultas", () => {
    const ocultoEnFila: HallazgoLibroRespuesta = {
      codigo: "L2",
      severidad: "ERROR",
      descripcion: "Partida con cantidad cero",
      celda: "PRESUPUESTO!F19",
      impacto: "5.00",
      accion: "Revisar",
    };
    const hojas = [hoja("PRESUPUESTO", { ocultas_filas: [19] }), hoja("APU-01")];

    test("van a su propio grupo, con lo que esta oculto, y no a Sin celda en el libro", () => {
      montar({ hallazgos: [...hallazgos.slice(0, 1), ocultoEnFila], hojas });
      const grupo = screen.getByRole("region", { name: /En hoja, fila o columna oculta/ });
      expect(within(grupo).getByText("Partida con cantidad cero")).toBeInTheDocument();
      expect(within(grupo).getByText("fila 19 oculta")).toBeInTheDocument();
      expect(screen.queryByRole("region", { name: /Sin celda en el libro/ })).not.toBeInTheDocument();
    });

    test("al hacer clic avisa en la lista por que no se ve, y no mueve la hoja", async () => {
      const usuario = userEvent.setup();
      const { irACelda, onElegir } = montar({ hallazgos: [ocultoEnFila], hojas });
      await usuario.click(fila("Partida con cantidad cero"));
      expect(onElegir).toHaveBeenCalledWith(0);
      expect(irACelda).not.toHaveBeenCalled();
      expect(screen.getByRole("status")).toHaveTextContent(/fila 19 oculta/);
    });

    test("un hallazgo sin celda tambien avisa que no se puede ubicar", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.click(fila("El libro no declara la fecha de la portada"));
      expect(screen.getByRole("status")).toHaveTextContent(/no tiene una celda/i);
    });

    test("el aviso se va al elegir un hallazgo con celda", async () => {
      const usuario = userEvent.setup();
      montar({ hallazgos: [ocultoEnFila, hallazgos[0]], hojas: [...hojas, hoja("PRESUPUESTO", { ocultas_filas: [19] })] });
      await usuario.click(fila("Partida con cantidad cero"));
      await usuario.click(fila("El total no coincide con la suma de las partidas"));
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });
  });

  test("el filtro se recuerda hacia afuera (alFiltrar) y se puede restaurar (filtroInicial)", async () => {
    const usuario = userEvent.setup();
    const alFiltrar = vi.fn();
    const { rerender } = render(
      <ListaHallazgos hallazgos={hallazgos} seleccionado={null} irACelda={vi.fn()} onElegir={vi.fn()} alFiltrar={alFiltrar} />,
    );
    await usuario.click(screen.getByRole("button", { name: /^Crítico/ }));
    expect(alFiltrar).toHaveBeenLastCalledWith(["CRITICO"]);
    rerender(<div />);
    render(
      <ListaHallazgos hallazgos={hallazgos} seleccionado={null} irACelda={vi.fn()} onElegir={vi.fn()} filtroInicial={["ERROR"]} />,
    );
    expect(screen.queryByText("El total no coincide con la suma de las partidas")).not.toBeInTheDocument();
    expect(screen.getByText("Precio unitario distinto al de INSUMOS")).toBeInTheDocument();
  });

  test("sin hallazgos dice que el libro no tiene ninguno", () => {
    montar({ hallazgos: [] });
    expect(screen.getByText(/no tiene hallazgos/i)).toBeInTheDocument();
  });

  test("cuando hay precios atípicos muestra la etiqueta y la nota en la cabecera; sin ellos no la muestra", () => {
    const { unmount } = montar();
    expect(screen.queryByText(/En morado: precios muy distintos al histórico/)).toBeNull();
    unmount();
    montar({
      hallazgos: [
        {
          codigo: "ATIPICO",
          severidad: "ADVERTENCIA",
          descripcion: "Precio fuera de rango histórico",
          celda: "PRESUPUESTO!F12",
          impacto: null,
          accion: "Revisar",
        },
      ],
    });
    expect(screen.getByText("Precio atípico (revisar)")).toBeInTheDocument();
    expect(screen.getByText("En morado: precios muy distintos al histórico; revise si tienen justificación")).toBeInTheDocument();
  });

  test("un no aplicable no cuenta en el total ni en las tablas y va a Reglas que no aplicaron", () => {
    const mixto: HallazgoLibroRespuesta[] = [
      hallazgos[0],
      {
        codigo: "R7",
        nombre_regla: "Plan de trabajo",
        severidad: "INFO",
        descripcion: "Regla no aplicable: el libro no declara cronograma",
        celda: "",
        impacto: null,
        accion: "",
      },
      hallazgos[1],
    ];
    montar({ hallazgos: mixto, noAplicables: [1] });
    expect(screen.getByRole("heading", { level: 2, name: "Hallazgos (2)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crítico 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Error 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Información 0" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /Sin celda en el libro/ })).toBeNull();

    const region = screen.getByRole("region", { name: "Reglas que no aplicaron a este libro (1)" });
    expect(within(region).getByText(/No son errores/)).toBeInTheDocument();
    expect(within(region).getByText(/Plan de trabajo/)).toBeInTheDocument();
    expect(within(region).getByText("R7")).toHaveClass("silice-codigo");
    expect(within(region).getByText("Regla no aplicable: el libro no declara cronograma")).toBeInTheDocument();
    expect(within(region).queryByRole("button")).toBeNull();
    expect(region.querySelector("tr")).toBeNull();
  });

  test("una causa con traza dice el valor encontrado frente al esperado, en es-VE", () => {
    const causas = [
      {
        codigo: "F1",
        nombre_regla: "P.U. distinto del recálculo",
        severidad: "ERROR",
        descripcion: "partida 1: PRESUPUESTO guarda un P.U. de 999,99",
        ocurrencias: 1,
        indices: [0],
        celdas: ["PRESUPUESTO!P5"],
        observado: "999.99",
        esperado: "14.486725",
      },
    ];
    montar({ causas });
    const apartado = screen.getByRole("region", { name: /Por causa raíz/ });
    expect(within(apartado).getByText(/Encontrado 999,99/)).toBeInTheDocument();
    expect(within(apartado).getByText(/esperado 14,486725/)).toBeInTheDocument();
  });

  test("con causas muestra Por causa raíz, el resumen, casos y al pulsar elige su primera celda", async () => {
    const usuario = userEvent.setup();
    const conCausas: HallazgoLibroRespuesta[] = [
      { ...hallazgos[1], celda: "APU-01!G48", descripcion: "Cemento distinto al tabulador; partida 1" },
      { ...hallazgos[1], celda: "APU-02!G48", descripcion: "Cemento distinto al tabulador; partida 2" },
      { ...hallazgos[1], celda: "APU-03!G48", descripcion: "Cemento distinto al tabulador; partida 3" },
      hallazgos[0],
    ];
    const causas = [
      {
        codigo: "L5",
        nombre_regla: "Precio distinto al de INSUMOS",
        severidad: "ERROR",
        descripcion: "Cemento distinto al tabulador; partida 1",
        ocurrencias: 3,
        indices: [0, 1, 2],
      },
      {
        codigo: "L3",
        nombre_regla: "Total de presupuesto",
        severidad: "CRITICO",
        descripcion: "El total no coincide con la suma de las partidas",
        ocurrencias: 1,
        indices: [3],
      },
    ];
    const { irACelda, onElegir } = montar({ hallazgos: conCausas, causas });
    const region = screen.getByRole("region", { name: "Por causa raíz (2)" });
    expect(within(region).getByText(/Los 4 hallazgos vienen de 2 causas/)).toBeInTheDocument();
    expect(within(region).getByText("3 casos")).toBeInTheDocument();
    expect(within(region).getByText("1 caso")).toBeInTheDocument();
    expect(within(region).getByText("Cemento distinto al tabulador")).toBeInTheDocument();
    expect(within(region).queryByText(/partida 1/)).toBeNull();
    expect(within(region).getByText("L5")).toHaveClass("silice-codigo");
    expect(screen.getByRole("heading", { level: 3, name: "Uno por uno (4)" })).toBeInTheDocument();

    await usuario.click(within(region).getByRole("button", { name: /Precio distinto al de INSUMOS/ }));
    expect(onElegir).toHaveBeenCalledWith(0);
    expect(irACelda).toHaveBeenCalledWith({ hoja: "APU-01", fila0: 47, columna0: 6 }, 0);
  });

  test("el filtro por severidad oculta las causas de otra severidad", async () => {
    const usuario = userEvent.setup();
    const conCausas: HallazgoLibroRespuesta[] = [hallazgos[1], hallazgos[0]];
    const causas = [
      {
        codigo: "L5",
        nombre_regla: "Precio distinto al de INSUMOS",
        severidad: "ERROR",
        descripcion: "Precio unitario distinto al de INSUMOS",
        ocurrencias: 1,
        indices: [0],
      },
      {
        codigo: "L3",
        nombre_regla: "Total de presupuesto",
        severidad: "CRITICO",
        descripcion: "El total no coincide con la suma de las partidas",
        ocurrencias: 1,
        indices: [1],
      },
    ];
    montar({ hallazgos: conCausas, causas });
    // La causa crítica también empieza por «Crítico»: el clic va a la etiqueta del filtro.
    const filtro = screen.getByRole("group", { name: "Filtrar por severidad" });
    await usuario.click(within(filtro).getByRole("button", { name: /^Crítico/ }));
    const region = screen.getByRole("region", { name: "Por causa raíz (1)" });
    expect(within(region).getByText(/Total de presupuesto/)).toBeInTheDocument();
    expect(within(region).queryByText(/Precio distinto al de INSUMOS/)).toBeNull();
  });

  test("sin la prop causas no hay apartado Por causa raíz", () => {
    montar();
    expect(screen.queryByRole("heading", { name: /Por causa raíz/ })).toBeNull();
    expect(screen.queryByRole("heading", { name: /Uno por uno/ })).toBeNull();
  });

  test("si todos los hallazgos son no aplicables sale el mensaje vacío y Reglas que no aplicaron", () => {
    const soloNoAplicable: HallazgoLibroRespuesta[] = [
      {
        codigo: "R2",
        nombre_regla: "Curva de inversión",
        severidad: "INFO",
        descripcion: "Regla no aplicable: sin curva de inversión",
        celda: "",
        impacto: null,
        accion: "",
      },
    ];
    montar({ hallazgos: soloNoAplicable, noAplicables: [0] });
    expect(screen.getByRole("heading", { level: 2, name: "Hallazgos (0)" })).toBeInTheDocument();
    expect(screen.getByText(/La auditoría terminó y el libro no tiene hallazgos\./)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Reglas que no aplicaron a este libro (1)" })).toBeInTheDocument();
  });
});
