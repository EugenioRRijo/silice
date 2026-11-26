import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf, pedir } from "../api/cliente";
import { invalidarRecursos, useRecurso, vaciarRecursosParaPruebas } from "./recurso";

interface Diferido<T> {
  promesa: Promise<T>;
  resolver: (valor: T) => void;
  rechazar: (error: unknown) => void;
}

function diferido<T>(): Diferido<T> {
  let resolver!: (valor: T) => void;
  let rechazar!: (error: unknown) => void;
  const promesa = new Promise<T>((alResolver, alRechazar) => {
    resolver = alResolver;
    rechazar = alRechazar;
  });
  return { promesa, resolver, rechazar };
}

// Deja pasar las promesas pendientes y los renders que provocan.
async function asentar(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

beforeEach(() => vaciarRecursosParaPruebas());
afterEach(() => vaciarRecursosParaPruebas());

describe("useRecurso", () => {
  test("dice cargando y después listo con los datos", async () => {
    const d = diferido<string>();
    const cargar = vi.fn(() => d.promesa);
    const { result } = renderHook(() => useRecurso("a", cargar));
    expect(result.current.carga).toEqual({ estado: "cargando" });
    d.resolver("uno");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "uno" });
    expect(cargar).toHaveBeenCalledTimes(1);
  });

  test("con clave null no pide nada y queda cargando", async () => {
    const cargar = vi.fn(() => Promise.resolve("x"));
    const { result } = renderHook(() => useRecurso<string>(null, cargar));
    await asentar();
    expect(cargar).not.toHaveBeenCalled();
    expect(result.current.carga).toEqual({ estado: "cargando" });
  });

  test("al cambiar la clave nunca muestra los datos de la anterior", async () => {
    const da = diferido<string>();
    const db = diferido<string>();
    const cargar = vi.fn((clave: string) => (clave === "a" ? da.promesa : db.promesa));
    const { result, rerender } = renderHook(({ clave }) => useRecurso(clave, () => cargar(clave)), { initialProps: { clave: "a" } });
    da.resolver("datos de a");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "datos de a" });

    rerender({ clave: "b" });
    expect(result.current.carga).toEqual({ estado: "cargando" });
    db.resolver("datos de b");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "datos de b" });
  });

  test("dos componentes con la misma clave hacen una sola llamada y ambos reciben el dato", async () => {
    const d = diferido<string>();
    const cargar = vi.fn(() => d.promesa);
    const primero = renderHook(() => useRecurso("a", cargar));
    const segundo = renderHook(() => useRecurso("a", cargar));
    expect(cargar).toHaveBeenCalledTimes(1);
    d.resolver("compartido");
    await asentar();
    expect(primero.result.current.carga).toEqual({ estado: "listo", datos: "compartido" });
    expect(segundo.result.current.carga).toEqual({ estado: "listo", datos: "compartido" });
  });

  test("con la clave ya en caché entrega de inmediato y no vuelve a pedir", async () => {
    const cargar = vi.fn(() => Promise.resolve("guardado"));
    const primero = renderHook(() => useRecurso("a", cargar));
    await asentar();
    expect(primero.result.current.carga.estado).toBe("listo");
    primero.unmount();

    const segundo = renderHook(() => useRecurso("a", cargar));
    expect(segundo.result.current.carga).toEqual({ estado: "listo", datos: "guardado" });
    await asentar();
    expect(cargar).toHaveBeenCalledTimes(1);
  });

  test("invalidarRecursos borra las claves del prefijo y los montados vuelven a pedir; las demás quedan", async () => {
    let n = 0;
    const cargarA = vi.fn(() => Promise.resolve(`a${++n}`));
    const cargarB = vi.fn(() => Promise.resolve("b"));
    const a = renderHook(() => useRecurso("obra:1:tramos", cargarA));
    const b = renderHook(() => useRecurso("otra:1", cargarB));
    await asentar();
    expect(a.result.current.carga).toEqual({ estado: "listo", datos: "a1" });

    act(() => invalidarRecursos("obra:"));
    await asentar();
    expect(cargarA).toHaveBeenCalledTimes(2);
    expect(a.result.current.carga).toEqual({ estado: "listo", datos: "a2" });
    expect(cargarB).toHaveBeenCalledTimes(1);
    expect(b.result.current.carga).toEqual({ estado: "listo", datos: "b" });
  });

  test("invalidarRecursos de una clave sin montar la borra de la caché", async () => {
    const cargar = vi.fn(() => Promise.resolve("v"));
    const primero = renderHook(() => useRecurso("obra:1", cargar));
    await asentar();
    primero.unmount();
    act(() => invalidarRecursos("obra:"));
    renderHook(() => useRecurso("obra:1", cargar));
    await asentar();
    expect(cargar).toHaveBeenCalledTimes(2);
  });

  test("desmontar aborta la señal", async () => {
    let senal!: AbortSignal;
    const cargar = vi.fn((s: AbortSignal) => {
      senal = s;
      return new Promise<string>(() => undefined);
    });
    const { unmount } = renderHook(() => useRecurso("a", cargar));
    expect(senal.aborted).toBe(false);
    unmount();
    expect(senal.aborted).toBe(true);
  });

  test("cambiar la clave aborta la petición de la anterior", () => {
    const senales: Record<string, AbortSignal> = {};
    const { rerender } = renderHook(
      ({ clave }) =>
        useRecurso(clave, (s) => {
          senales[clave] = s;
          return new Promise<string>(() => undefined);
        }),
      { initialProps: { clave: "a" } },
    );
    rerender({ clave: "b" });
    expect(senales.a.aborted).toBe(true);
    expect(senales.b.aborted).toBe(false);
  });

  test("desmontar no aborta si otro componente sigue esperando la misma clave", async () => {
    const d = diferido<string>();
    let senal!: AbortSignal;
    const cargar = vi.fn((s: AbortSignal) => {
      senal = s;
      return d.promesa;
    });
    const primero = renderHook(() => useRecurso("a", cargar));
    const segundo = renderHook(() => useRecurso("a", cargar));
    primero.unmount();
    expect(senal.aborted).toBe(false);
    d.resolver("sigue");
    await asentar();
    expect(segundo.result.current.carga).toEqual({ estado: "listo", datos: "sigue" });
    segundo.unmount();
  });

  test("al irse el último interesado sí aborta", () => {
    let senal!: AbortSignal;
    const cargar = vi.fn((s: AbortSignal) => {
      senal = s;
      return new Promise<string>(() => undefined);
    });
    const primero = renderHook(() => useRecurso("a", cargar));
    const segundo = renderHook(() => useRecurso("a", cargar));
    primero.unmount();
    segundo.unmount();
    expect(senal.aborted).toBe(true);
  });

  test("un error queda en el estado del componente pero no en la caché: al volver a montar se reintenta", async () => {
    const falla = new Error("falló");
    const cargar = vi.fn().mockRejectedValueOnce(falla).mockResolvedValueOnce("bien");
    const primero = renderHook(() => useRecurso("a", cargar));
    await asentar();
    expect(primero.result.current.carga).toEqual({ estado: "error", error: falla });
    primero.unmount();

    const segundo = renderHook(() => useRecurso("a", cargar));
    expect(segundo.result.current.carga).toEqual({ estado: "cargando" });
    await asentar();
    expect(cargar).toHaveBeenCalledTimes(2);
    expect(segundo.result.current.carga).toEqual({ estado: "listo", datos: "bien" });
  });

  test("al cambiar la clave tras un error no arrastra el error de la anterior", async () => {
    const db = diferido<string>();
    const { result, rerender } = renderHook(({ clave }) => useRecurso(clave, () => (clave === "a" ? Promise.reject(new Error("falló")) : db.promesa)), {
      initialProps: { clave: "a" },
    });
    await asentar();
    expect(result.current.carga.estado).toBe("error");
    rerender({ clave: "b" });
    expect(result.current.carga).toEqual({ estado: "cargando" });
    db.resolver("b");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "b" });
  });

  test("el error llega a todos los componentes que compartían la petición", async () => {
    const d = diferido<string>();
    const cargar = vi.fn(() => d.promesa);
    const primero = renderHook(() => useRecurso("a", cargar));
    const segundo = renderHook(() => useRecurso("a", cargar));
    const falla = new Error("falló");
    d.rechazar(falla);
    await asentar();
    expect(cargar).toHaveBeenCalledTimes(1);
    expect(primero.result.current.carga).toEqual({ estado: "error", error: falla });
    expect(segundo.result.current.carga).toEqual({ estado: "error", error: falla });
  });

  test("recargar vuelve a pedir y muestra cargando hasta que llegue el dato nuevo", async () => {
    let n = 0;
    const cargar = vi.fn(() => Promise.resolve(`v${++n}`));
    const { result } = renderHook(() => useRecurso("a", cargar));
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "v1" });

    act(() => result.current.recargar());
    await asentar();
    expect(cargar).toHaveBeenCalledTimes(2);
    expect(result.current.carga).toEqual({ estado: "listo", datos: "v2" });
  });

  test("recargar después de un error sale del error y pide otra vez", async () => {
    const cargar = vi.fn().mockRejectedValueOnce(new Error("falló")).mockResolvedValueOnce("bien");
    const { result } = renderHook(() => useRecurso("a", cargar));
    await asentar();
    expect(result.current.carga.estado).toBe("error");
    act(() => result.current.recargar());
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "bien" });
  });

  test("reemplazar pone los datos sin pedir de nuevo y los ve quien comparte la clave", async () => {
    const cargar = vi.fn(() => Promise.resolve("viejo"));
    const primero = renderHook(() => useRecurso("a", cargar));
    const segundo = renderHook(() => useRecurso("a", cargar));
    await asentar();
    act(() => primero.result.current.reemplazar("nuevo"));
    expect(primero.result.current.carga).toEqual({ estado: "listo", datos: "nuevo" });
    expect(segundo.result.current.carga).toEqual({ estado: "listo", datos: "nuevo" });
    expect(cargar).toHaveBeenCalledTimes(1);
  });
});

// Un `cargar` como el de `fetch`: rechaza con AbortError cuando se aborta su señal.
function cargarComoFetch<T>(): { cargar: (senal: AbortSignal) => Promise<T>; pedidos: Diferido<T>[]; senales: AbortSignal[] } {
  const pedidos: Diferido<T>[] = [];
  const senales: AbortSignal[] = [];
  const cargar = (senal: AbortSignal): Promise<T> => {
    const d = diferido<T>();
    pedidos.push(d);
    senales.push(senal);
    senal.addEventListener("abort", () => d.rechazar(new DOMException("Aborted", "AbortError")));
    return d.promesa;
  };
  return { cargar, pedidos, senales };
}

describe("useRecurso con un cargar que rechaza al abortarse", () => {
  test("R1: una respuesta tardía tras invalidar no pisa el dato nuevo", async () => {
    const pedidos: Diferido<string>[] = [];
    const cargar = vi.fn(() => {
      const d = diferido<string>();
      pedidos.push(d);
      return d.promesa; // ignora la señal, como un cargar que no la pasa a fetch
    });
    const { result } = renderHook(() => useRecurso("a", cargar));
    act(() => invalidarRecursos("a"));
    expect(pedidos).toHaveLength(2);
    pedidos[1].resolver("nuevo");
    await asentar();
    pedidos[0].resolver("viejo");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "nuevo" });
  });

  test("R5: abortar una petición no se muestra como error", async () => {
    const { cargar, pedidos } = cargarComoFetch<string>();
    const { result } = renderHook(() => useRecurso("a", cargar));
    act(() => invalidarRecursos("a"));
    await asentar();
    expect(result.current.carga).toEqual({ estado: "cargando" });
    pedidos[1].resolver("bien");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "bien" });
  });

  test("R15: desmontar a mitad de la petición y volver a montar pide otra vez y llega a listo", async () => {
    const { cargar, pedidos, senales } = cargarComoFetch<string>();
    const primero = renderHook(() => useRecurso("a", cargar));
    primero.unmount();
    expect(senales[0].aborted).toBe(true);
    const segundo = renderHook(() => useRecurso("a", cargar));
    expect(pedidos).toHaveLength(2);
    pedidos[1].resolver("ok");
    await asentar();
    expect(segundo.result.current.carga).toEqual({ estado: "listo", datos: "ok" });
  });

  test("R7: invalidar aborta la señal de la petición en vuelo", () => {
    const { cargar, senales } = cargarComoFetch<string>();
    renderHook(() => useRecurso("a", cargar));
    expect(senales[0].aborted).toBe(false);
    // Se mira dentro del `act`, antes de que React vuelva a renderizar: el efecto del componente también aborta al soltar,
    // y aquí se prueba que `invalidarRecursos` aborta por sí mismo.
    let abortada = false;
    act(() => {
      invalidarRecursos("a");
      abortada = senales[0].aborted;
    });
    expect(abortada).toBe(true);
  });

  test("R6: recargar desde error pasa por cargando", async () => {
    const { cargar, pedidos } = cargarComoFetch<string>();
    const { result } = renderHook(() => useRecurso("a", cargar));
    pedidos[0].rechazar(new Error("falló"));
    await asentar();
    expect(result.current.carga.estado).toBe("error");
    act(() => result.current.recargar());
    expect(result.current.carga).toEqual({ estado: "cargando" });
    pedidos[1].resolver("bien");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "bien" });
  });
});

describe("useRecurso: el error mostrado es el de la petición vigente", () => {
  test("el fallo tardío de la clave que se dejó no pisa el error de la clave actual", async () => {
    const da = diferido<string>();
    const db = diferido<string>();
    const cargar = (clave: string) => (clave === "a" ? da.promesa : db.promesa);
    const a = renderHook(({ clave }) => useRecurso(clave, () => cargar(clave)), { initialProps: { clave: "a" } });
    renderHook(() => useRecurso("a", () => cargar("a"))); // B sigue esperando "a": la petición compartida no se aborta
    a.rerender({ clave: "b" });
    const falloB = new Error("falló b");
    db.rechazar(falloB);
    await asentar();
    expect(a.result.current.carga).toEqual({ estado: "error", error: falloB });
    da.rechazar(new Error("falló a"));
    await asentar();
    expect(a.result.current.carga).toEqual({ estado: "error", error: falloB });
  });

  test("al volver a una clave que falló muestra cargando mientras pide de nuevo", async () => {
    const pedidos: Diferido<string>[] = [];
    const cargar = vi.fn((clave: string) => {
      if (clave === "b") return Promise.resolve("b");
      const d = diferido<string>();
      pedidos.push(d);
      return d.promesa;
    });
    const { result, rerender } = renderHook(({ clave }) => useRecurso(clave, () => cargar(clave)), { initialProps: { clave: "a" } });
    pedidos[0].rechazar(new Error("falló"));
    await asentar();
    expect(result.current.carga.estado).toBe("error");
    rerender({ clave: "b" });
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "b" });
    rerender({ clave: "a" });
    expect(pedidos).toHaveLength(2);
    expect(result.current.carga).toEqual({ estado: "cargando" });
    pedidos[1].resolver("a2");
    await asentar();
    expect(result.current.carga).toEqual({ estado: "listo", datos: "a2" });
  });

  test("después de invalidarRecursos, una clave que había fallado muestra cargando mientras pide de nuevo", async () => {
    const { cargar, pedidos } = cargarComoFetch<string>();
    const { result } = renderHook(() => useRecurso("a", cargar));
    pedidos[0].rechazar(new Error("falló"));
    await asentar();
    expect(result.current.carga.estado).toBe("error");
    act(() => invalidarRecursos("a"));
    expect(pedidos).toHaveLength(2);
    expect(result.current.carga).toEqual({ estado: "cargando" });
  });
});

describe("useRecurso y la sesión", () => {
  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
  });

  test("al perder la sesión (401 con sesión abierta) la caché se vacía: una clave lista vuelve a pedirse", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detalle: "Sesión vencida." }), { status: 401, headers: { "Content-Type": "application/json" } })));
    const cargar = vi.fn().mockResolvedValueOnce("de la cuenta anterior").mockResolvedValueOnce("de la cuenta nueva");
    fijarCsrf("tok");
    const primero = renderHook(() => useRecurso("obra:1", cargar));
    await asentar();
    expect(primero.result.current.carga).toEqual({ estado: "listo", datos: "de la cuenta anterior" });

    await act(async () => {
      await pedir("/v1/algo").catch(() => undefined);
    });
    await asentar();
    expect(cargar).toHaveBeenCalledTimes(2);
    expect(primero.result.current.carga).toEqual({ estado: "listo", datos: "de la cuenta nueva" });
    primero.unmount();
  });
});
