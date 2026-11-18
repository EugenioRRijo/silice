import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { pedir } from "../../api/cliente";
import { esperarEnvios } from "./envioPendiente";
import type { RespuestaDeEdicion, Resumen } from "./logica";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";

vi.mock("../../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Una respuesta que el servidor todavía no dio: la prueba decide cuándo llega.
function enEspera() {
  let contestar: (valor: RespuestaDeEdicion) => void = () => undefined;
  const promesa = new Promise<RespuestaDeEdicion>((resolver) => {
    contestar = resolver;
  });
  return { promesa, contestar };
}

// Un resumen ficticio: el motor solo lee `rev` y se lo pasa a la página tal cual.
function resumen(rev: number): Resumen {
  return { rev } as Resumen;
}

const BORRADOR = "borrador-ficticio-a5";

// Deja correr las promesas ya resueltas (con relojes falsos no hay `setTimeout` real que esperar).
async function vaciarMicrotareas() {
  for (let vuelta = 0; vuelta < 20; vuelta++) await Promise.resolve();
}

function montar() {
  return renderHook(() =>
    useEdicionDeSeccion<string, null>({
      borrador: BORRADOR,
      inicial: "1",
      rev: 4,
      peticion: (rev, estado) => ({ ruta: `/v1/hoja/borradores/${BORRADOR}/cantidades`, metodo: "PUT", cuerpo: { rev, estado } }),
      ubicar: () => null,
      frase: "",
      leerFresca: () => Promise.resolve("1"),
      alAceptar: () => undefined,
      alRelectura: () => undefined,
      alRecargarBorrador: () => Promise.resolve(),
      alAusente: () => undefined,
      alExpirar: () => undefined,
    }),
  );
}

afterEach(() => {
  pedirFalso.mockReset();
  vi.useRealTimers();
});

describe("useEdicionDeSeccion: lo escrito durante una acción, con la pestaña ya cerrada (anexo A.5, H13)", () => {
  test("el reenvío que sale al terminar la acción queda anotado: esperarEnvios espera también su PUT", async () => {
    vi.useFakeTimers();
    const accion = enEspera();
    const reenvio = enEspera();
    pedirFalso.mockReturnValueOnce(accion.promesa).mockReturnValueOnce(reenvio.promesa);
    const { result, unmount } = montar();

    // Una acción en vuelo («Usar este insumo», por ejemplo), y la persona escribe mientras tanto.
    let respuestaDeLaAccion: Promise<Resumen | null> = Promise.resolve(null);
    act(() => {
      respuestaDeLaAccion = result.current.accionarEnOrden((rev) => ({
        ruta: `/v1/hoja/borradores/${BORRADOR}/apu/X/insumo`,
        metodo: "POST",
        cuerpo: { rev },
      }));
    });
    act(() => result.current.cambiar(() => "2"));
    expect(pedirFalso).toHaveBeenCalledTimes(1);

    // Se va de la pestaña: lo escrito no puede salir aún (hay una en vuelo) y espera a la acción.
    unmount();
    let esperado = false;
    const espera = esperarEnvios(BORRADOR).then((resumenes) => {
      esperado = true;
      return resumenes;
    });

    // Contesta la acción: al cerrarse, sale lo escrito con el `rev` que ella dejó.
    await act(async () => {
      accion.contestar({ rev: 5, resumen: resumen(5) });
      await respuestaDeLaAccion;
    });
    expect(pedirFalso).toHaveBeenCalledTimes(2);
    expect(pedirFalso.mock.calls[1]).toEqual([
      `/v1/hoja/borradores/${BORRADOR}/cantidades`,
      { metodo: "PUT", cuerpo: { rev: 5, estado: "2" } },
    ]);
    // Quien descarta el borrador al irse no puede adelantarse a ese PUT.
    await act(vaciarMicrotareas);
    expect(esperado).toBe(false);

    await act(async () => {
      reenvio.contestar({ rev: 6, resumen: resumen(6) });
      await espera;
    });
    expect(esperado).toBe(true);
    expect(await espera).toEqual([resumen(5), resumen(6)]);
  });
});
