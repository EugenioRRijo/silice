import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Mock } from "vitest";
import { Grilla } from "../../../comun/Grilla";
import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { AvisoDeEdicion } from "../AvisoDeEdicion";
import { vistaPresupuesto } from "../datosDePrueba";
import type { FilaPresupuesto, Resumen, VistaPresupuesto } from "../logica";
import { FRASES_DE_RECHAZO } from "../logicaSecciones";
import { CeldaDeCantidad } from "./CeldaDeCantidad";
import { useCantidadesDeLaSuperficie } from "./useCantidadesDeLaSuperficie";
import type { CantidadesDeLaSuperficie } from "./useCantidadesDeLaSuperficie";

// Lote B1-5 (ficha-b1 §1.10, pruebas 5 y 6): las celdas de cantidad dentro de la grilla real, con el motor de la edición
// (`useEdicionDeSeccion`) y un servidor simulado con la forma del contrato de `PUT …/cantidades` (docs/bitacora/2026-10-19-
// hoja-3c2-contrato-rutas.md): `{rev, filas:[{clave, cantidad}]}` y respuesta `{rev, resumen}`. Datos ficticios.

const ID = "id-borrador-b1-5";
const URL_PUT = `/v1/hoja/borradores/${ID}/cantidades`;
const URL_QUITAR = `/v1/hoja/borradores/${ID}/partidas/quitar`;
const CLAVE_1 = "AF-LLAVE|esp_puntos:P1";
const CLAVE_2 = "AF-SALIDA|esp_puntos:P2";

const json = (cuerpo: unknown, estado = 200): Response =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

function resumen(rev: number): Resumen {
  return {
    rev,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
    cambios: 1,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
  };
}

interface Cuerpo {
  rev: number;
  filas: { clave: string; cantidad: string }[];
}

interface Espias {
  alRecargarBorrador: Mock<() => Promise<void>>;
  alRelectura: Mock<() => void>;
  alAceptar: Mock<(resumen: Resumen) => void>;
}

// La superficie en pequeño: una grilla con la columna Cantidad, el aviso de la sección y un control fuera de la grilla.
function Superficie({
  puedeEditar = true,
  espias,
  vista,
  exponer,
}: {
  puedeEditar?: boolean;
  espias: Espias;
  vista: VistaPresupuesto;
  // Entrega el motor a la prueba, para llamar a lo que la grilla no pinta (una acción que se encola con lo escrito).
  exponer?: (cantidades: CantidadesDeLaSuperficie) => void;
}) {
  const [rev, setRev] = useState(0);
  const cantidades = useCantidadesDeLaSuperficie({
    borrador: ID,
    rev,
    filas: vista.filas,
    puedeEditar,
    alAceptar: (r) => {
      espias.alAceptar(r);
      setRev(r.rev);
    },
    alRelectura: espias.alRelectura,
    alRecargarBorrador: async () => {
      await espias.alRecargarBorrador();
      setRev(7);
    },
    alAusente: vi.fn(),
    alExpirar: vi.fn(),
  });
  exponer?.(cantidades);
  const columnas: ColumnaDeGrilla<FilaPresupuesto>[] = [
    { clave: "partida", titulo: "Partida", valor: (f) => f.partida },
    { clave: "descripcion", titulo: "Descripción", valor: (f) => f.descripcion },
    {
      clave: "cantidad",
      titulo: "Cantidad",
      numerica: true,
      valor: (f) => f.cantidad,
      render: (f) => <CeldaDeCantidad {...cantidades.celda(f)} />,
    },
  ];
  return (
    <div>
      <button type="button">Afuera</button>
      <Grilla<FilaPresupuesto> etiqueta="Presupuesto" columnas={columnas} filas={vista.filas} idDeFila={(f) => f.clave} />
      {cantidades.error !== null && (
        <AvisoDeEdicion
          error={cantidades.error}
          id="aviso-de-cantidades"
          alRecargar={() => void cantidades.recargar()}
          alReabrir={vi.fn()}
        />
      )}
    </div>
  );
}

describe("las celdas de cantidad en la grilla del Presupuesto", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let espias: Espias;
  let alPoner: (cuerpo: Cuerpo) => Response | Promise<Response>;
  let alQuitar: (cuerpo: { rev: number; clave: string }) => Response | Promise<Response>;
  let vistaDelServidor: VistaPresupuesto;
  let u: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    espias = { alRecargarBorrador: vi.fn(async () => {}), alRelectura: vi.fn(), alAceptar: vi.fn() };
    vistaDelServidor = vistaPresupuesto();
    alPoner = (cuerpo) => json({ rev: cuerpo.rev + 1, resumen: resumen(cuerpo.rev + 1) });
    alQuitar = (cuerpo) => json({ rev: cuerpo.rev + 1, resumen: resumen(cuerpo.rev + 1) });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url === URL_QUITAR && init?.method === "POST") return alQuitar(JSON.parse(String(init.body)) as { rev: number; clave: string });
      if (url === URL_PUT && init?.method === "PUT") return alPoner(JSON.parse(String(init.body)) as Cuerpo);
      if (url.endsWith("/vistas/presupuesto")) return json(vistaDelServidor);
      return new Response(null, { status: 204 });
    });
    // Solo se simulan los temporizadores de la pausa; las promesas siguen reales. El reloj simulado avanza con el real
    // (`shouldAdvanceTime`) porque Testing Library y user-event esperan con setTimeout(0) y sin eso se cuelgan.
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    u = userEvent.setup({ delay: null });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const montar = (puedeEditar = true, exponer?: (cantidades: CantidadesDeLaSuperficie) => void) =>
    render(<Superficie puedeEditar={puedeEditar} espias={espias} vista={vistaPresupuesto()} exponer={exponer} />);
  const quitadas = (): Array<{ rev: number; clave: string }> =>
    fetchFalso.mock.calls
      .filter(([ruta, init]) => String(ruta) === URL_QUITAR && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as { rev: number; clave: string });
  const escrituras = (): Cuerpo[] =>
    fetchFalso.mock.calls
      .filter(([ruta, init]) => String(ruta) === URL_PUT && init?.method === "PUT")
      .map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const lecturasDeLaVista = () => fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/presupuesto")).length;
  const celdaDe = (partida: string) => {
    const fila = screen.getByRole("rowheader", { name: partida }).closest("tr")!;
    return fila.querySelectorAll<HTMLElement>("[data-celda]")[2]!;
  };
  const campoDe = (partida: string) => screen.getByRole("textbox", { name: `Cantidad, ${partida}` });
  // Con setTimeout simulado `waitFor` se cuelga: se espera dando turnos a las promesas.
  const turnos = async (n = 20) => {
    for (let i = 0; i < n; i++) {
      await act(async () => {
        await new Promise<void>((resolver) => setImmediate(resolver));
      });
    }
  };
  const pausa = (ms: number) =>
    act(async () => {
      vi.advanceTimersByTime(ms);
    });
  // Abre la celda de la partida, borra lo que tenía y escribe `texto`.
  async function escribirEn(partida: string, texto: string) {
    celdaDe(partida).focus();
    await u.keyboard(`{F2}{Backspace}${texto}`);
  }

  describe("el teclado de la grilla (prueba 6)", () => {
    test("una sola parada de Tab: las celdas de cantidad en reposo no suman campos ni tabindex", () => {
      montar();
      expect(document.querySelectorAll('[data-celda][tabindex="0"]')).toHaveLength(1);
      expect(screen.queryAllByRole("textbox")).toHaveLength(0);
      expect(document.querySelectorAll("tbody input, tbody button")).toHaveLength(0);
    });

    test("las flechas llevan a la celda de cantidad, F2 la edita y Esc restaura lo último que aceptó el servidor", async () => {
      montar();
      screen.getByRole("rowheader", { name: "AF-LLAVE" }).focus();
      await u.keyboard("{ArrowRight}{ArrowRight}");
      expect(celdaDe("AF-LLAVE")).toHaveFocus();
      await u.keyboard("{F2}{Backspace}99");
      expect(campoDe("AF-LLAVE")).toHaveValue("99");
      await u.keyboard("{Escape}");
      expect(screen.queryAllByRole("textbox")).toHaveLength(0);
      expect(celdaDe("AF-LLAVE")).toHaveTextContent("3");
      expect(celdaDe("AF-LLAVE")).toHaveFocus();
    });

    test("dentro del campo las flechas no mueven la celda activa de la grilla", async () => {
      montar();
      await escribirEn("AF-LLAVE", "12,5");
      await u.keyboard("{ArrowLeft}{ArrowDown}{ArrowUp}{Home}{End}");
      expect(campoDe("AF-LLAVE")).toHaveFocus();
      expect(document.querySelectorAll('[data-celda][tabindex="0"]')).toHaveLength(1);
    });
  });

  describe("escribir y esperar la pausa", () => {
    test("escribir «12,5» y esperar la pausa manda un PUT con su rev, solo de esa fila, con el texto tal cual", async () => {
      montar();
      await escribirEn("AF-LLAVE", "12,5");
      await pausa(300);
      expect(escrituras()).toHaveLength(0);
      await pausa(150);
      await turnos();
      expect(escrituras()).toEqual([{ rev: 0, filas: [{ clave: CLAVE_1, cantidad: "12,5" }] }]);
      expect(espias.alAceptar).toHaveBeenCalledWith(resumen(1));
      expect(espias.alRelectura).toHaveBeenCalled();
    });

    test("tras aceptar, la edición siguiente manda el rev nuevo y las filas ya tocadas viajan con lo último escrito", async () => {
      montar();
      await escribirEn("AF-LLAVE", "12,5");
      await pausa(400);
      await turnos();
      await escribirEn("AF-SALIDA", "6");
      await pausa(400);
      await turnos();
      expect(escrituras()).toHaveLength(2);
      expect(escrituras()[1]).toEqual({
        rev: 1,
        filas: [
          { clave: CLAVE_1, cantidad: "12,5" },
          { clave: CLAVE_2, cantidad: "6" },
        ],
      });
    });

    test("la cifra con punto de miles se manda como se escribió: la lee el servidor", async () => {
      montar();
      await escribirEn("AF-LLAVE", "1.234,56");
      await pausa(400);
      await turnos();
      expect(escrituras()[0]!.filas).toEqual([{ clave: CLAVE_1, cantidad: "1.234,56" }]);
    });

    test("Enter confirma sin esperar la pausa y baja a la cantidad de la fila de abajo", async () => {
      montar();
      await escribirEn("AF-LLAVE", "12,5");
      await u.keyboard("{Enter}");
      await turnos();
      expect(escrituras()).toEqual([{ rev: 0, filas: [{ clave: CLAVE_1, cantidad: "12,5" }] }]);
      expect(celdaDe("AF-SALIDA")).toHaveFocus();
    });

    test("salir del campo con un clic en otro lugar confirma sin esperar la pausa", async () => {
      montar();
      await escribirEn("AF-LLAVE", "12,5");
      expect(escrituras()).toHaveLength(0);
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      expect(escrituras()).toEqual([{ rev: 0, filas: [{ clave: CLAVE_1, cantidad: "12,5" }] }]);
    });

    test("Esc antes de la pausa no deja escrito lo que se descartó", async () => {
      montar();
      await escribirEn("AF-LLAVE", "99");
      await u.keyboard("{Escape}");
      await pausa(400);
      await turnos();
      expect(escrituras().flatMap((c) => c.filas.map((f) => f.cantidad)).filter((c) => c !== "3")).toEqual([]);
      expect(celdaDe("AF-LLAVE")).toHaveTextContent("3");
    });
  });

  describe("errores del servidor (prueba 5)", () => {
    const DETALLE =
      "presupuesto, fila 1 (AF-LLAVE): la cantidad no puede ser negativa; escriba cero o una cantidad positiva";

    test("un 422 deja lo escrito, marca solo esa celda con texto y el aviso dice el mensaje completo", async () => {
      alPoner = () => json({ detalle: DETALLE }, 422);
      montar();
      await escribirEn("AF-LLAVE", "-1");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      // Lo escrito sigue ahí y la celda queda marcada, aunque la persona ya salió de ella.
      expect(campoDe("AF-LLAVE")).toHaveValue("-1");
      expect(campoDe("AF-LLAVE")).toHaveAttribute("aria-invalid", "true");
      expect(screen.getByText("La cantidad no puede ser negativa; escriba cero o una cantidad positiva.")).toBeVisible();
      // La otra fila no se marca ni se abre.
      expect(screen.queryByRole("textbox", { name: "Cantidad, AF-SALIDA" })).toBeNull();
      // El aviso de la sección dice el texto del servidor y la frase de la clásica.
      expect(screen.getByRole("alert")).toHaveTextContent(`${DETALLE}. ${FRASES_DE_RECHAZO.cantidades}`);
    });

    test("un 422 de otra fila no marca la celda de esta", async () => {
      alPoner = () => json({ detalle: DETALLE.replace("fila 1 (AF-LLAVE)", "fila 2 (AF-SALIDA)") }, 422);
      montar();
      await escribirEn("AF-SALIDA", "-1");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      expect(campoDe("AF-SALIDA")).toHaveAttribute("aria-invalid", "true");
      expect(screen.queryByRole("textbox", { name: "Cantidad, AF-LLAVE" })).toBeNull();
    });

    test("corregir el texto limpia la marca y, al aceptarse, el aviso desaparece", async () => {
      alPoner = (cuerpo) =>
        cuerpo.filas[0]!.cantidad === "-1" ? json({ detalle: DETALLE }, 422) : json({ rev: cuerpo.rev + 1, resumen: resumen(cuerpo.rev + 1) });
      montar();
      await escribirEn("AF-LLAVE", "-1");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      expect(campoDe("AF-LLAVE")).toHaveAttribute("aria-invalid", "true");
      // Vuelve a la celda marcada y la corrige.
      await u.click(campoDe("AF-LLAVE"));
      await u.keyboard("{Backspace}{Backspace}4");
      expect(campoDe("AF-LLAVE")).toHaveAttribute("aria-invalid", "false");
      await u.keyboard("{Enter}");
      await turnos();
      expect(screen.queryByRole("alert")).toBeNull();
      expect(celdaDe("AF-LLAVE")).toHaveTextContent("4");
    });

    test("Esc en una celda rechazada la devuelve a lo último que aceptó el servidor", async () => {
      alPoner = (cuerpo) =>
        cuerpo.filas[0]!.cantidad === "-1" ? json({ detalle: DETALLE }, 422) : json({ rev: cuerpo.rev + 1, resumen: resumen(cuerpo.rev + 1) });
      montar();
      await escribirEn("AF-LLAVE", "-1");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      await u.click(campoDe("AF-LLAVE"));
      await u.keyboard("{Escape}");
      await pausa(400);
      await turnos();
      expect(celdaDe("AF-LLAVE")).toHaveTextContent("3");
      expect(screen.queryByRole("alert")).toBeNull();
    });

    test("un 409 por rev viejo pide volver a leer: no marca ninguna celda, no manda más y «Recargar el borrador» siembra lo del servidor", async () => {
      alPoner = () => json({ detalle: "El borrador cambió en otra ventana: vuelva a cargarlo." }, 409);
      montar();
      await escribirEn("AF-LLAVE", "12,5");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      expect(screen.getByRole("alert")).toHaveTextContent("El borrador cambió en otra ventana");
      // Ninguna celda queda marcada como inválida por un conflicto: el aviso es de la sección.
      expect(document.querySelectorAll('[aria-invalid="true"]')).toHaveLength(0);
      // Bloqueada hasta recargar: una edición más no manda nada.
      await escribirEn("AF-SALIDA", "6");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      expect(escrituras()).toHaveLength(1);
      // Recargar vuelve a leer el borrador y la vista, y siembra lo que el servidor tiene.
      vistaDelServidor = vistaPresupuesto({
        filas: vistaPresupuesto().filas.map((f, i) => (i === 0 ? { ...f, cantidad: "8" } : f)),
      });
      const lecturasAntes = lecturasDeLaVista();
      await u.click(screen.getByRole("button", { name: "Recargar el borrador" }));
      await turnos();
      expect(espias.alRecargarBorrador).toHaveBeenCalledTimes(1);
      expect(lecturasDeLaVista()).toBe(lecturasAntes + 1);
      expect(screen.queryByRole("alert")).toBeNull();
      expect(celdaDe("AF-LLAVE")).toHaveTextContent("8");
      // Y se vuelve a poder escribir, con el rev que dejó la recarga.
      await escribirEn("AF-LLAVE", "9");
      await u.click(screen.getByRole("button", { name: "Afuera" }));
      await turnos();
      expect(escrituras().at(-1)).toEqual({ rev: 7, filas: [{ clave: CLAVE_1, cantidad: "9" }] });
    });
  });

  describe("sin permiso de edición (prueba 9)", () => {
    test("las cantidades son texto: no hay campos ni se abren con el teclado", async () => {
      alPoner = () => json({ detalle: "no debía llamarse" }, 500);
      montar(false);
      celdaDe("AF-LLAVE").focus();
      await u.keyboard("{F2}7");
      expect(screen.queryAllByRole("textbox")).toHaveLength(0);
      expect(celdaDe("AF-LLAVE")).toHaveTextContent("3");
      await pausa(400);
      await turnos();
      expect(escrituras()).toHaveLength(0);
    });
  });

  // Defecto B1-6: «Quitar» del inspector tiene que entrar en la misma cola que las cantidades (como la vista por pestañas).
  describe("una acción en orden con las cantidades (el «Quitar» del inspector)", () => {
    const DETALLE = "presupuesto, fila 1 (AF-LLAVE): la cantidad no puede ser negativa; escriba cero o una cantidad positiva";
    let motor: CantidadesDeLaSuperficie;
    const exponer = (c: CantidadesDeLaSuperficie) => {
      motor = c;
    };
    const quitar = (clave: string) =>
      motor.accionarEnOrden((rev) => ({ ruta: URL_QUITAR, metodo: "POST", cuerpo: { rev, clave }, frase: "" }));

    test("sin nada pendiente sale de inmediato con el rev vigente y su respuesta pasa a la página", async () => {
      montar(true, exponer);
      let resultado: Resumen | null = null;
      await act(async () => {
        resultado = await quitar(CLAVE_2);
      });
      expect(quitadas()).toEqual([{ rev: 0, clave: CLAVE_2 }]);
      expect(escrituras()).toEqual([]);
      expect(resultado).toEqual(resumen(1));
      expect(espias.alAceptar).toHaveBeenCalledWith(resumen(1));
    });

    test("lo escrito que espera la pausa sale primero y la acción lleva el rev que contestó el servidor", async () => {
      montar(true, exponer);
      await escribirEn("AF-LLAVE", "12,5");
      let resultado: Resumen | null = null;
      await act(async () => {
        resultado = await quitar(CLAVE_2);
      });
      expect(escrituras()).toEqual([{ rev: 0, filas: [{ clave: CLAVE_1, cantidad: "12,5" }] }]);
      expect(quitadas()).toEqual([{ rev: 1, clave: CLAVE_2 }]);
      expect(resultado).toEqual(resumen(2));
    });

    test("si el servidor rechaza lo escrito (422), la acción no sale, devuelve null y el aviso y lo escrito quedan", async () => {
      alPoner = () => json({ detalle: DETALLE }, 422);
      montar(true, exponer);
      await escribirEn("AF-LLAVE", "-1");
      let resultado: Resumen | null | undefined;
      await act(async () => {
        resultado = await quitar(CLAVE_2);
      });
      await turnos();
      expect(escrituras()).toEqual([{ rev: 0, filas: [{ clave: CLAVE_1, cantidad: "-1" }] }]);
      expect(resultado).toBeNull();
      expect(quitadas()).toEqual([]);
      expect(screen.getByRole("alert")).toHaveTextContent(DETALLE);
      expect(campoDe("AF-LLAVE")).toHaveValue("-1");
      expect(campoDe("AF-LLAVE")).toHaveAttribute("aria-invalid", "true");
    });

    test("mientras la acción va en vuelo, una cantidad nueva espera y sale después con el rev que dejó la acción", async () => {
      let soltar: (r: Response) => void = () => {};
      alQuitar = () => new Promise<Response>((resolver) => (soltar = resolver));
      montar(true, exponer);
      let resultado: Promise<Resumen | null> = Promise.resolve(null);
      await act(async () => {
        resultado = quitar(CLAVE_2);
      });
      await turnos();
      expect(quitadas()).toEqual([{ rev: 0, clave: CLAVE_2 }]);
      // Lo escrito entre tanto no puede salir con el rev viejo: la pausa se cumple y el PUT sigue esperando.
      await act(async () => {
        motor.escribir(CLAVE_1, "4");
      });
      await pausa(450);
      await turnos();
      expect(escrituras()).toEqual([]);
      await act(async () => {
        soltar(json({ rev: 1, resumen: resumen(1) }));
        await resultado;
      });
      await turnos();
      expect(escrituras()).toEqual([{ rev: 1, filas: [{ clave: CLAVE_1, cantidad: "4" }] }]);
      expect(quitadas()).toHaveLength(1);
    });
  });

  test("una fila que llega con la vista siembra su texto sin perder lo escrito y aún no aceptado de las demás", async () => {
    const { rerender } = montar();
    await escribirEn("AF-LLAVE", "12,5"); // espera la pausa: el servidor todavía no lo aceptó
    const nueva: FilaPresupuesto = { ...vistaPresupuesto().filas[0]!, clave: "NUEVA|1", partida: "NUEVA", cantidad: "2" };
    rerender(<Superficie espias={espias} vista={vistaPresupuesto({ filas: [...vistaPresupuesto().filas, nueva] })} />);
    await turnos();
    expect(celdaDe("NUEVA")).toHaveTextContent("2");
    expect(campoDe("AF-LLAVE")).toHaveValue("12,5");
  });
});
