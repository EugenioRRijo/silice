import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
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
