import { afterEach, describe, expect, it, vi } from "vitest";
import { crearVigilante, type CanalDeObra } from "./otraPestana";
import { busDePestanas } from "../test/pestanasFalsas";

describe("vigilancia de pestañas", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("avisa a la pestaña que tenia otra obra", () => {
    const bus = busDePestanas();
    const norte = crearVigilante(bus.canal());
    const sur = crearVigilante(bus.canal());
    const aviso = vi.fn();
    sur.escucharOtraPestana(aviso);
    sur.anunciarObra("Sur", 3);

    norte.anunciarObra("Norte", 1);

    expect(aviso).toHaveBeenCalledTimes(1);
    expect(aviso).toHaveBeenCalledWith({ carpeta: "Norte", obraId: 1 });
  });

  it("anunciar la misma obra no avisa", () => {
    const bus = busDePestanas();
    const una = crearVigilante(bus.canal());
    const otra = crearVigilante(bus.canal());
    const aviso = vi.fn();
    otra.escucharOtraPestana(aviso);
    otra.anunciarObra("Sur", 3);

    una.anunciarObra("Sur", 3);

    expect(aviso).not.toHaveBeenCalled();
  });

  it("la carpeta de la empresa (null) y otra con el mismo numero de obra son obras distintas", () => {
    const bus = busDePestanas();
    const una = crearVigilante(bus.canal());
    const otra = crearVigilante(bus.canal());
    const aviso = vi.fn();
    otra.escucharOtraPestana(aviso);
    otra.anunciarObra(null, 1);

    una.anunciarObra("Norte.db", 1);

    expect(aviso).toHaveBeenCalledWith({ carpeta: "Norte.db", obraId: 1 });
  });

  it("una pestaña sin obra anunciada no recibe avisos; tampoco quien dejo de escuchar", () => {
    const bus = busDePestanas();
    const una = crearVigilante(bus.canal());
    const sinObra = crearVigilante(bus.canal());
    const conObra = crearVigilante(bus.canal());
    const aviso1 = vi.fn();
    const aviso2 = vi.fn();
    sinObra.escucharOtraPestana(aviso1);
    const dejar = conObra.escucharOtraPestana(aviso2);
    conObra.anunciarObra("Sur", 3);
    dejar();

    una.anunciarObra("Norte", 1);

    expect(aviso1).not.toHaveBeenCalled();
    expect(aviso2).not.toHaveBeenCalled();
  });

  it("descarta mensajes con otra forma", () => {
    const bus = busDePestanas();
    const canalSuelto: CanalDeObra = bus.canal();
    const mia = crearVigilante(bus.canal());
    const aviso = vi.fn();
    mia.escucharOtraPestana(aviso);
    mia.anunciarObra("Sur", 3);

    canalSuelto.postMessage("hola");
    canalSuelto.postMessage({ carpeta: 4, obraId: "x" });

    expect(aviso).not.toHaveBeenCalled();
  });

  it("sin canal no hace nada", () => {
    const sola = crearVigilante(null);
    const aviso = vi.fn();
    const dejar = sola.escucharOtraPestana(aviso);
    expect(() => sola.anunciarObra("Sur", 3)).not.toThrow();
    expect(() => dejar()).not.toThrow();
    expect(aviso).not.toHaveBeenCalled();
  });

  it("sin BroadcastChannel en el navegador, anunciar y escuchar no hacen nada", async () => {
    vi.stubGlobal("BroadcastChannel", undefined);
    const { anunciarObra, escucharOtraPestana } = await import("./otraPestana");
    const dejar = escucharOtraPestana(vi.fn());
    expect(() => anunciarObra("Sur", 3)).not.toThrow();
    expect(() => dejar()).not.toThrow();
  });

  it("con BroadcastChannel usa el canal «silice-obra»", async () => {
    const nombres: string[] = [];
    class CanalDelNavegador {
      onmessage: ((evento: MessageEvent) => void) | null = null;
      constructor(nombre: string) {
        nombres.push(nombre);
      }
      postMessage() {}
      close() {}
    }
    vi.stubGlobal("BroadcastChannel", CanalDelNavegador);
    const { anunciarObra } = await import("./otraPestana");
    anunciarObra("Sur", 3);
    expect(nombres).toEqual(["silice-obra"]);
  });
});
