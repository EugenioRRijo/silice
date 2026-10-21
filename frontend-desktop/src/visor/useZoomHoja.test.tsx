import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { aplicarTamanoLetra } from "../comun/preferenciaDeLetra";
import { crearHojaFalsa } from "./hojaFalsa";
import { CLAVE_ZOOM_HOJA } from "./zoomHoja";
import { useAtajosZoom, useZoomHoja } from "./useZoomHoja";

describe("useZoomHoja", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("style");
    delete document.documentElement.dataset.siliceLetra;
  });
  afterEach(() => vi.restoreAllMocks());

  test("empieza en 100 % y, con el visor listo, le pide razon 1", () => {
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    expect(result.current.zoom).toBe(100);
    expect(result.current.razon).toBe(1);
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(1);
  });

  test("sin visor no pide nada; al llegar el visor recibe la razon vigente", () => {
    const hoja = crearHojaFalsa();
    const { rerender } = renderHook(({ v }) => useZoomHoja(v), {
      initialProps: { v: null as ReturnType<typeof crearHojaFalsa> | null },
    });
    expect(hoja.fijarZoom).not.toHaveBeenCalled();
    rerender({ v: hoja });
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(1);
  });

  test("subir y bajar mueven de 10 en 10, respetan 50 y 300, y guardan solo al actuar", () => {
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    expect(localStorage.getItem(CLAVE_ZOOM_HOJA)).toBeNull();
    act(() => result.current.subir());
    expect(result.current.zoom).toBe(110);
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(1.1);
    expect(localStorage.getItem(CLAVE_ZOOM_HOJA)).toBe("110");
    for (let i = 0; i < 30; i++) act(() => result.current.subir());
    expect(result.current.zoom).toBe(300);
    for (let i = 0; i < 40; i++) act(() => result.current.bajar());
    expect(result.current.zoom).toBe(50);
    act(() => result.current.restablecer());
    expect(result.current.zoom).toBe(100);
    expect(localStorage.getItem(CLAVE_ZOOM_HOJA)).toBe("100");
  });

  test("lee el zoom guardado al montar", () => {
    localStorage.setItem(CLAVE_ZOOM_HOJA, "200");
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    expect(result.current.zoom).toBe(200);
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(2);
  });

  test("el zoom inicial ya sale con el factor de letra vigente al abrir", () => {
    aplicarTamanoLetra("grande");
    localStorage.setItem(CLAVE_ZOOM_HOJA, "200");
    const { result } = renderHook(() => useZoomHoja(null));
    expect(result.current.factor).toBe(1.25);
    expect(result.current.razon).toBe(2.5);
  });

  test("al cambiar el tamano de letra en vivo, la razon sigue al factor sin tocar el zoom propio", async () => {
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    await act(async () => {
      aplicarTamanoLetra("muy-grande");
    });
    expect(result.current.zoom).toBe(100);
    expect(result.current.factor).toBe(1.5);
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(1.5);
    await act(async () => {
      aplicarTamanoLetra("normal");
    });
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(1);
  });

  test("el producto pasa del tope de Univer: se recorta a 4 y se avisa", () => {
    aplicarTamanoLetra("muy-grande");
    localStorage.setItem(CLAVE_ZOOM_HOJA, "300");
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    expect(result.current.razon).toBe(4);
    expect(result.current.limitado).toBe(true);
    expect(hoja.fijarZoom).toHaveBeenLastCalledWith(4);
  });

  test("con Muy grande, de 270 % en adelante no se puede subir: el lienzo ya esta en su tope y no se veria nada", () => {
    aplicarTamanoLetra("muy-grande");
    localStorage.setItem(CLAVE_ZOOM_HOJA, "270");
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    expect(result.current.puedeSubir).toBe(false);
    act(() => result.current.subir());
    expect(result.current.zoom).toBe(270);
    act(() => result.current.bajar());
    expect(result.current.zoom).toBe(260);
    expect(result.current.puedeSubir).toBe(true);
  });

  test("al desmontarse desconecta el observador del tamano de letra", () => {
    const desconectar = vi.spyOn(MutationObserver.prototype, "disconnect");
    const hoja = crearHojaFalsa();
    const { unmount } = renderHook(() => useZoomHoja(hoja));
    const antes = desconectar.mock.calls.length;
    unmount();
    expect(desconectar.mock.calls.length).toBeGreaterThan(antes);
  });

  test("sin almacenamiento la hoja sigue funcionando", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("x");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("x");
    });
    const hoja = crearHojaFalsa();
    const { result } = renderHook(() => useZoomHoja(hoja));
    act(() => result.current.subir());
    expect(result.current.zoom).toBe(110);
  });
});

function Banco({ acciones }: { acciones: { subir: () => void; bajar: () => void; restablecer: () => void } }) {
  const [seccion, setSeccion] = useState<HTMLElement | null>(null);
  const [lienzo, setLienzo] = useState<HTMLDivElement | null>(null);
  useAtajosZoom(seccion, lienzo, acciones);
  return (
    <div>
      <button type="button">fuera</button>
      <section ref={setSeccion} aria-label="seccion">
        <button type="button">dentro</button>
        <div ref={setLienzo} data-testid="lienzo" tabIndex={0} />
      </section>
    </div>
  );
}

describe("useAtajosZoom", () => {
  function montar() {
    const acciones = { subir: vi.fn(), bajar: vi.fn(), restablecer: vi.fn() };
    render(<Banco acciones={acciones} />);
    return acciones;
  }

  test("Ctrl + + / = acerca, Ctrl + - aleja, Ctrl + 0 restablece, con el foco dentro de la hoja; el navegador no hace zoom", () => {
    const a = montar();
    const dentro = screen.getByRole("button", { name: "dentro" });
    dentro.focus();
    for (const [key, accion] of [
      ["+", "subir"],
      ["=", "subir"],
      ["-", "bajar"],
      ["0", "restablecer"],
    ] as const) {
      const evento = new KeyboardEvent("keydown", { key, ctrlKey: true, bubbles: true, cancelable: true });
      dentro.dispatchEvent(evento);
      expect(evento.defaultPrevented, key).toBe(true);
      expect(a[accion], key).toHaveBeenCalled();
    }
    expect(a.subir).toHaveBeenCalledTimes(2);
  });

  test("con el foco fuera de la hoja no hace nada y deja pasar el zoom del navegador", () => {
    const a = montar();
    const fuera = screen.getByRole("button", { name: "fuera" });
    fuera.focus();
    const evento = new KeyboardEvent("keydown", { key: "+", ctrlKey: true, bubbles: true, cancelable: true });
    fuera.dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(false);
    expect(a.subir).not.toHaveBeenCalled();
  });

  test("sin Ctrl (o con Alt) las teclas no hacen nada", () => {
    const a = montar();
    const dentro = screen.getByRole("button", { name: "dentro" });
    fireEvent.keyDown(dentro, { key: "+" });
    fireEvent.keyDown(dentro, { key: "-", ctrlKey: true, altKey: true });
    expect(a.subir).not.toHaveBeenCalled();
    expect(a.bajar).not.toHaveBeenCalled();
  });

  test("Ctrl + rueda sobre el lienzo acerca o aleja y no deja que el navegador ni Univer la usen", () => {
    const a = montar();
    const lienzo = screen.getByTestId("lienzo");
    const arriba = new WheelEvent("wheel", { deltaY: -100, ctrlKey: true, bubbles: true, cancelable: true });
    lienzo.dispatchEvent(arriba);
    expect(arriba.defaultPrevented).toBe(true);
    expect(a.subir).toHaveBeenCalledTimes(1);
    const abajo = new WheelEvent("wheel", { deltaY: 100, ctrlKey: true, bubbles: true, cancelable: true });
    lienzo.dispatchEvent(abajo);
    expect(a.bajar).toHaveBeenCalledTimes(1);
  });

  test("una muesca en lineas (Firefox, deltaMode 1) tambien da un paso", () => {
    const a = montar();
    screen.getByTestId("lienzo").dispatchEvent(new WheelEvent("wheel", { deltaY: -3, deltaMode: 1, ctrlKey: true, bubbles: true, cancelable: true }));
    expect(a.subir).toHaveBeenCalledTimes(1);
  });

  test("al desmontarse quita los dos oyentes (teclado en la seccion y rueda en el lienzo, en captura)", () => {
    const { unmount } = render(<Banco acciones={{ subir: vi.fn(), bajar: vi.fn(), restablecer: vi.fn() }} />);
    const seccion = screen.getByRole("region", { name: "seccion" });
    const lienzo = screen.getByTestId("lienzo");
    const quitarSeccion = vi.spyOn(seccion, "removeEventListener");
    const quitarLienzo = vi.spyOn(lienzo, "removeEventListener");
    unmount();
    expect(quitarSeccion).toHaveBeenCalledWith("keydown", expect.any(Function));
    expect(quitarLienzo).toHaveBeenCalledWith("wheel", expect.any(Function), { capture: true });
  });

  test("tras desmontar, ni la tecla ni la rueda llaman a las acciones", () => {
    const acciones = { subir: vi.fn(), bajar: vi.fn(), restablecer: vi.fn() };
    const { unmount } = render(<Banco acciones={acciones} />);
    const seccion = screen.getByRole("region", { name: "seccion" });
    const lienzo = screen.getByTestId("lienzo");
    unmount();
    seccion.dispatchEvent(new KeyboardEvent("keydown", { key: "+", ctrlKey: true, bubbles: true, cancelable: true }));
    lienzo.dispatchEvent(new WheelEvent("wheel", { deltaY: -100, ctrlKey: true, bubbles: true, cancelable: true }));
    expect(acciones.subir).not.toHaveBeenCalled();
  });

  test("la rueda sin Ctrl sigue siendo desplazamiento: no se toca", () => {
    const a = montar();
    const evento = new WheelEvent("wheel", { deltaY: -100, bubbles: true, cancelable: true });
    screen.getByTestId("lienzo").dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(false);
    expect(a.subir).not.toHaveBeenCalled();
  });
});
