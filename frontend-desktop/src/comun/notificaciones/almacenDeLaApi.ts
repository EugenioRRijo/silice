import { pedir } from "../../api/cliente";
import type { AlmacenDeNotificaciones } from "./ProveedorDeNotificaciones";
import type { GravedadDeNotificacion, Notificacion } from "./modelo";

// C11 (f7520d3b): el servidor guarda las notificaciones de cada persona 30 días. El proveedor piensa en la lista entera
// (cargar y guardar); la API recibe una nueva por POST y marca las leídas aparte. Este adaptador traduce entre los dos y
// recuerda qué ya mandó, para no repetir un POST ni volver a marcar una leída.

interface NotificacionDelServidor {
  id: number;
  gravedad: string;
  titulo: string;
  detalle: string;
  enlace: { texto: string; ruta: string } | null;
  creada: string;
  leida: boolean;
}

interface ListaDelServidor {
  notificaciones: NotificacionDelServidor[];
}

export type PedirNotificaciones = (
  ruta: string,
  opciones?: { metodo?: "GET" | "POST"; cuerpo?: object },
) => Promise<unknown>;

const GRAVEDADES: ReadonlySet<string> = new Set(["listo", "info", "advertencia", "error"]);
const PREFIJO = "api:";

// Una ruta interna de la aplicación: empieza por «/», sin «//» ni esquema (la API rechaza lo demás con 422).
function rutaInterna(ruta: string): boolean {
  return ruta.startsWith("/") && !ruta.startsWith("//") && !/^[a-z][a-z0-9+.-]*:/i.test(ruta);
}

function desdeElServidor(n: NotificacionDelServidor): Notificacion {
  const gravedad = (GRAVEDADES.has(n.gravedad) ? n.gravedad : "info") as GravedadDeNotificacion;
  return {
    id: `${PREFIJO}${n.id}`,
    gravedad,
    titulo: n.titulo,
    ...(n.detalle !== "" ? { detalle: n.detalle } : {}),
    ...(n.enlace !== null && n.enlace.ruta !== "" ? { enlace: { texto: n.enlace.texto, ruta: n.enlace.ruta } } : {}),
    creada: n.creada,
    leida: n.leida,
  };
}

function cuerpoNuevo(n: Notificacion): object {
  return {
    gravedad: n.gravedad,
    titulo: n.titulo,
    detalle: n.detalle ?? "",
    ...(n.enlace !== undefined && rutaInterna(n.enlace.ruta) ? { enlace: { texto: n.enlace.texto, ruta: n.enlace.ruta } } : {}),
  };
}

export function almacenDeLaApi(pedirApi: PedirNotificaciones = (ruta, opciones) => pedir(ruta, opciones)): AlmacenDeNotificaciones {
  // id del proveedor -> id del servidor, y los del servidor que ya están leídos allá.
  const enElServidor = new Map<string, number>();
  const leidasAlla = new Set<number>();
  const enviando = new Set<string>();

  return {
    async cargar() {
      const datos = (await pedirApi("/v1/notificaciones")) as ListaDelServidor;
      return datos.notificaciones.map((n) => {
        enElServidor.set(`${PREFIJO}${n.id}`, n.id);
        if (n.leida) leidasAlla.add(n.id);
        return desdeElServidor(n);
      });
    },
    async guardar(lista) {
      for (const n of lista) {
        if (enElServidor.has(n.id) || enviando.has(n.id)) continue;
        enviando.add(n.id);
        try {
          const creada = (await pedirApi("/v1/notificaciones", { metodo: "POST", cuerpo: cuerpoNuevo(n) })) as NotificacionDelServidor;
          enElServidor.set(n.id, creada.id);
        } finally {
          // Si el envío falla, el guardado siguiente vuelve a intentarlo.
          enviando.delete(n.id);
        }
      }
      const porMarcar = lista
        .filter((n) => n.leida)
        .map((n) => enElServidor.get(n.id))
        .filter((id): id is number => id !== undefined && !leidasAlla.has(id));
      if (porMarcar.length > 0) {
        await pedirApi("/v1/notificaciones/leidas", { metodo: "POST", cuerpo: { ids: porMarcar } });
        for (const id of porMarcar) leidasAlla.add(id);
      }
    },
  };
}
