import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ProveedorDeAnuncios } from "../Anunciador";
import { Dialogo } from "../Dialogo";
import { ProveedorDeNotificaciones, crearAlmacenEnMemoria, useNotificaciones } from "./ProveedorDeNotificaciones";
import type { AlmacenDeNotificaciones } from "./ProveedorDeNotificaciones";
import type { Notificacion } from "./modelo";

afterEach(() => {
  vi.useRealTimers();
});

function SondaDeContexto() {
  const { notificaciones, emergentes, sinLeer, notificar, cerrar, marcarTodasLeidas } = useNotificaciones();
  return (
    <div>
      <p data-testid="resumen">{`total:${notificaciones.length}|emergentes:${emergentes.length}|sinLeer:${sinLeer}`}</p>
      <button
        type="button"
        onClick={() =>
          notificar({
            id: "n-listo",
            gravedad: "listo",
            titulo: "Versión V2 guardada",
            detalle: "Vialidad Tramo 3",
          })
        }
      >
        Emitir confirmación
      </button>
      <button
        type="button"
        onClick={() =>
          notificar({
            id: "n-error",
            gravedad: "error",
            titulo: "2 errores abiertos en la auditoría",
            enlace: { texto: "Ver los problemas", ruta: "/auditoria" },
          })
        }
      >
        Emitir error
      </button>
      <button type="button" onClick={() => cerrar("n-listo")}>
        Cerrar confirmación
      </button>
      <button type="button" onClick={marcarTodasLeidas}>
        Leer todas
      </button>
      <ul>
        {emergentes.map((n) => (
          <li key={n.id}>{`emergente:${n.titulo}`}</li>
        ))}
      </ul>
    </div>
  );
}

describe("ProveedorDeNotificaciones", () => {
  test("notifica, anuncia en polite salvo error que va urgente, cierra emergente conservando historial y marca leídas", () => {
    const guardados: (readonly Notificacion[])[] = [];
    const base = crearAlmacenEnMemoria();
    const almacen: AlmacenDeNotificaciones = {
      cargar: () => base.cargar(),
      guardar: (lista) => {
        guardados.push(lista);
        base.guardar(lista);
      },
    };

    const { container } = render(
      <ProveedorDeAnuncios>
        <ProveedorDeNotificaciones almacen={almacen}>
          <SondaDeContexto />
        </ProveedorDeNotificaciones>
      </ProveedorDeAnuncios>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Emitir confirmación" }));
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:1|emergentes:1|sinLeer:1");
    expect(screen.getByRole("status")).toHaveTextContent("Listo: Versión V2 guardada. Vialidad Tramo 3");
    expect(container.querySelector('[aria-live="assertive"]')).toHaveTextContent("");

    fireEvent.click(screen.getByRole("button", { name: "Emitir error" }));
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:2|emergentes:2|sinLeer:2");
    expect(container.querySelector('[aria-live="assertive"]')).toHaveTextContent(
      "Error: 2 errores abiertos en la auditoría. Acción disponible.",
    );

    fireEvent.click(screen.getByRole("button", { name: "Cerrar confirmación" }));
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:2|emergentes:1|sinLeer:2");
    expect(screen.queryByText("emergente:Versión V2 guardada")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Leer todas" }));
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:2|emergentes:1|sinLeer:0");
    expect(guardados.length).toBeGreaterThanOrEqual(3);
    expect(guardados.at(-1)?.every((n) => n.leida)).toBe(true);
  });

  test("descarta las notificaciones de más de 30 días al cargar desde un almacén asíncrono", async () => {
    const ahora = new Date("2026-11-26T14:00:00.000Z");
    const inicial: Notificacion[] = [
      {
        id: "vigente",
        gravedad: "info",
        titulo: "Auditoría reciente",
        creada: "2026-11-20T10:00:00.000Z",
        leida: false,
      },
      {
        id: "vencida",
        gravedad: "advertencia",
        titulo: "Aviso de hace 40 días",
        creada: "2026-10-15T10:00:00.000Z",
        leida: false,
      },
    ];
    const guardar = vi.fn();
    const almacen: AlmacenDeNotificaciones = {
      cargar: async () => inicial,
      guardar,
    };

    render(
      <ProveedorDeNotificaciones almacen={almacen} ahora={() => ahora}>
        <SondaDeContexto />
      </ProveedorDeNotificaciones>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("resumen")).toHaveTextContent("total:1|emergentes:0|sinLeer:1");
    });
    expect(guardar).toHaveBeenCalledWith([expect.objectContaining({ id: "vigente" })]);
  });

  test("no muestra emergentes ni anuncia mientras hay un diálogo modal abierto y los saca al cerrarlo", async () => {
    function EscenaConDialogo() {
      const [abierto, setAbierto] = useState(true);
      return (
        <div>
          <button type="button" onClick={() => setAbierto(false)}>
            Cerrar diálogo
          </button>
          <SondaDeContexto />
          <Dialogo abierto={abierto} titulo="Confirmar entrega" alCerrar={() => setAbierto(false)}>
            <p>Revise antes de entregar.</p>
          </Dialogo>
        </div>
      );
    }

    render(
      <ProveedorDeAnuncios>
        <ProveedorDeNotificaciones>
          <EscenaConDialogo />
        </ProveedorDeNotificaciones>
      </ProveedorDeAnuncios>,
    );

    expect(screen.getByRole("dialog", { name: "Confirmar entrega" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Emitir confirmación", hidden: true }));
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:1|emergentes:0|sinLeer:1");
    expect(screen.queryByText("emergente:Versión V2 guardada")).toBeNull();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Cerrar diálogo", hidden: true }));
    });

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:1|emergentes:1|sinLeer:1");
    expect(screen.getByText("emergente:Versión V2 guardada")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Listo: Versión V2 guardada. Vialidad Tramo 3");
  });

  // T4 (mutante PR3): emitir de nuevo la misma notificación (mismo id) la reemplaza, no la duplica ni en la lista ni en pantalla.
  test("emitir dos veces la misma notificación deja una sola, en el historial y entre las emergentes", () => {
    render(
      <ProveedorDeAnuncios>
        <ProveedorDeNotificaciones>
          <SondaDeContexto />
        </ProveedorDeNotificaciones>
      </ProveedorDeAnuncios>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Emitir confirmación" }));
    fireEvent.click(screen.getByRole("button", { name: "Emitir confirmación" }));
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:1|emergentes:1|sinLeer:1");
    expect(screen.getAllByText("emergente:Versión V2 guardada")).toHaveLength(1);
  });

  // T4 (mutante PR6): una notificación que se cierra a mano mientras espera a que cierre el diálogo ya no sale después.
  test("lo que se cierra mientras el diálogo sigue abierto no reaparece al cerrarlo", async () => {
    function EscenaConDialogo() {
      const [abierto, setAbierto] = useState(true);
      return (
        <div>
          <button type="button" onClick={() => setAbierto(false)}>
            Cerrar diálogo
          </button>
          <SondaDeContexto />
          <Dialogo abierto={abierto} titulo="Confirmar entrega" alCerrar={() => setAbierto(false)}>
            <p>Revise antes de entregar.</p>
          </Dialogo>
        </div>
      );
    }
    render(
      <ProveedorDeAnuncios>
        <ProveedorDeNotificaciones>
          <EscenaConDialogo />
        </ProveedorDeNotificaciones>
      </ProveedorDeAnuncios>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Emitir confirmación", hidden: true }));
    fireEvent.click(screen.getByRole("button", { name: "Cerrar confirmación", hidden: true }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Cerrar diálogo", hidden: true }));
    });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByTestId("resumen")).toHaveTextContent("total:1|emergentes:0|sinLeer:1");
    expect(screen.queryByText("emergente:Versión V2 guardada")).toBeNull();
  });

  // T4 (mutante PR7): si llega la carga del servidor y ya había algo nuevo, la lista unida se guarda aunque nada haya vencido.
  test("al llegar la carga asíncrona con notificaciones ya emitidas guarda la lista unida", async () => {
    const ahora = new Date("2026-11-26T14:00:00.000Z");
    let entregar!: (lista: Notificacion[]) => void;
    const guardar = vi.fn();
    const almacen: AlmacenDeNotificaciones = {
      cargar: () =>
        new Promise<Notificacion[]>((resolver) => {
          entregar = resolver;
        }),
      guardar,
    };
    render(
      <ProveedorDeAnuncios>
        <ProveedorDeNotificaciones almacen={almacen} ahora={() => ahora}>
          <SondaDeContexto />
        </ProveedorDeNotificaciones>
      </ProveedorDeAnuncios>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Emitir confirmación" }));
    await act(async () => {
      entregar([{ id: "previa", gravedad: "info", titulo: "De antes", creada: "2026-11-25T10:00:00.000Z", leida: false }]);
    });
    await waitFor(() => expect(screen.getByTestId("resumen")).toHaveTextContent("total:2|emergentes:1|sinLeer:2"));
    const ultima = guardar.mock.calls.at(-1)![0] as Notificacion[];
    expect(ultima.map((n) => n.id).sort()).toEqual(["n-listo", "previa"]);
  });
});
