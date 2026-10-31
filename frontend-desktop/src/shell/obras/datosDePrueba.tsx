// Servidor de mentira para las pruebas del marco, las carpetas de trabajo y «Nueva obra» (plan de modulos, MOD-3b, y
// rediseño del marco). Responde como la API (`api/rutas/casos.py`, `proyectos.py`, `carpeta.py`, `sesion.py`, `hoja.py`) con datos
// ficticios y anota cada llamada. Solo lo importan las pruebas.
import { render } from "@testing-library/react";
import type { ComponentType } from "react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import type { CasoRespuesta, ProyectoRespuesta, SesionRespuesta } from "../../api/tipos";
import { PAGINAS } from "../rutas";
import type { PaginaDef } from "../rutas";
import { Marco } from "../../marco/Marco";

export function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

export const caso = (nombre: string): CasoRespuesta => ({ nombre, ruta_relativa: `casos/${nombre}` });

export const CASA_DEMO: ProyectoRespuesta = {
  codigo: "7",
  nombre: "Casa Demo",
  version_vigente: 1,
  actualizado: "2026-10-20",
  cliente: "Contratista Demo, C.A.",
  ubicacion: "Maracay",
};
export const TORRE_B: ProyectoRespuesta = {
  codigo: "8",
  nombre: "Torre B",
  version_vigente: null,
  actualizado: null,
  cliente: "Constructora Ficticia, S.A.",
  ubicacion: "Valencia",
};

// Acciones por rol, escritas a mano desde PERMISOS de seguridad/permisos.py. `tests/unit/test_front_acciones_por_rol.py`
// vigila que sigan siendo las de la matriz.
export const ACCIONES = {
  ana: [
    "editar_hoja",
    "convertir_y_reajustar",
    "control_de_obra",
    "decidir_recuperacion",
    "entregar_paquete",
    "operar_arenera",
    "registrar_costos_produccion",
    "leer_proyecto",
    "ver_riesgo",
    "aprobar_version",
    "cambiar_caso",
  ],
  rita: ["leer_proyecto", "ver_riesgo", "revisar_paquete", "aprobar_version"],
  admin: [
    "operar_arenera",
    "registrar_costos_produccion",
    "publicar_costo_propio",
    "ver_riesgo",
    "cambiar_caso",
    "administrar_cuentas",
    "administrar_empresa",
    "administrar_precios",
    "administrar_red_y_api",
    "activar_modulos",  # plan vial, Tarea 19: solo el administrador
    "cambiar_carpeta_de_datos",
  ],
} as const;

export type Rol = keyof typeof ACCIONES;

export function sesionDe(rol: Rol, parcial: Partial<SesionRespuesta> = {}): SesionRespuesta {
  const nombres: Record<Rol, string> = { ana: "Ana Pérez", rita: "Rita Gómez", admin: "Admin Ficticio" };
  const roles: Record<Rol, string> = { ana: "arma", rita: "revisa", admin: "administrador" };
  return {
    login: rol,
    nombre: nombres[rol],
    roles: [roles[rol]],
    csrf: "tok",
    debe_cambiar_clave: false,
    acciones: [...ACCIONES[rol]],
    modo_entrega: false,
    eleccion: { caso: null, proyecto: null, aviso: null },
    preferencias: { modulo: null, sidebar_fijado: false },
    ...parcial,
  };
}

export interface Llamada {
  metodo: string;
  ruta: string;
  cuerpo: unknown;
}

export interface EstadoDelServidor {
  actual: CasoRespuesta;
  casos: CasoRespuesta[];
  empresa: CasoRespuesta | null;
  proyectos: ProyectoRespuesta[];
  // La moneda de trabajo de la carpeta abierta (`GET /v1/carpeta`).
  moneda: string | null;
  borradores: { id: string; proyecto: string; version: string | null; cambios: number; rev: number; tocado: string }[];
}

export type Respondedor = (metodo: string, ruta: string, cuerpo: unknown) => Response | Promise<Response> | undefined;

// El estado de partida: la carpeta de la empresa «silice.db» abierta, otra carpeta «s2.db» y dos obras.
export function estadoInicial(): EstadoDelServidor {
  const silice = caso("silice.db");
  return {
    actual: silice,
    casos: [silice, caso("s1.db"), caso("s2.db")],
    empresa: silice,
    proyectos: [CASA_DEMO, TORRE_B],
    moneda: "Bs",
    borradores: [],
  };
}

function cuerpoDe(init: RequestInit | undefined): unknown {
  const cuerpo = init?.body;
  if (cuerpo === undefined || cuerpo === null) return null;
  if (cuerpo instanceof FormData) return cuerpo;
  try {
    return JSON.parse(String(cuerpo));
  } catch {
    return String(cuerpo);
  }
}

// El nombre final que daria `sanear_nombre` (lo no permitido pasa a «_») con la extension .db.
function saneado(nombre: string): string {
  const limpio = nombre.trim().replace(/[^A-Za-z0-9 ._-]/g, "_");
  return limpio.toLowerCase().endsWith(".db") ? limpio : `${limpio}.db`;
}

// Un `fetch` falso con el estado mutable y la lista de llamadas. `antes` responde primero (para errores a medida).
export function servidorFalso(estado: EstadoDelServidor = estadoInicial(), antes?: Respondedor) {
  const llamadas: Llamada[] = [];
  const fetchFalso = async (entrada: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const ruta = String(entrada);
    const metodo = init?.method ?? "GET";
    const cuerpo = cuerpoDe(init);
    llamadas.push({ metodo, ruta, cuerpo });
    const propia = await antes?.(metodo, ruta, cuerpo);
    if (propia) return propia;
    const datos = (cuerpo ?? {}) as Record<string, unknown>;
    if (ruta === "/v1/casos" && metodo === "GET") {
      return json({
        actual: estado.actual,
        casos: estado.casos,
        empresa: estado.empresa,
        es_demostracion: estado.actual.nombre === "demostracion.db",
      });
    }
    if (ruta === "/v1/casos/actual" && metodo === "POST") {
      const elegido = estado.casos.find((c) => c.nombre === datos["nombre"]);
      if (!elegido) return json({ detalle: "Esa carpeta de trabajo no está en la lista: elija una de la lista." }, 404);
      estado.actual = elegido;
      return json(elegido);
    }
    if (ruta === "/v1/casos/actual" && metodo === "DELETE") {
      if (!estado.empresa) return json({ detalle: "No hay carpeta de la empresa." }, 503);
      estado.actual = estado.empresa;
      return json(estado.empresa);
    }
    if (ruta === "/v1/casos" && metodo === "POST") {
      const final = saneado(String(datos["nombre"] ?? ""));
      if (estado.casos.some((c) => c.nombre.toLowerCase() === final.toLowerCase())) {
        return json({ detalle: `Ya existe la carpeta de trabajo ${final}: ábrala de la lista o elija otro nombre.` }, 409);
      }
      estado.casos = [...estado.casos, caso(final)];
      return json(caso(final), 201);
    }
    if (ruta === "/v1/casos/demostracion" && metodo === "POST") {
      const ya = estado.casos.some((c) => c.nombre === "demostracion.db");
      if (!ya) estado.casos = [...estado.casos, caso("demostracion.db")];
      return json(caso("demostracion.db"), ya ? 200 : 201);
    }
    if (ruta === "/v1/proyectos" && metodo === "GET") return json(estado.proyectos);
    if (ruta === "/v1/proyectos" && metodo === "POST") {
      const nombre = String(datos["nombre"] ?? "").trim();
      if (!nombre) return json({ detalle: "Escriba un nombre para la obra: no puede quedar vacío." }, 422);
      const nueva: ProyectoRespuesta = {
        codigo: String(9 + estado.proyectos.length),
        nombre,
        version_vigente: null,
        actualizado: null,
        cliente: String(datos["cliente"] ?? ""),
        ubicacion: String(datos["ubicacion"] ?? ""),
      };
      estado.proyectos = [...estado.proyectos, nueva];
      return json(nueva, 201);
    }
    if (ruta === "/v1/carpeta" && metodo === "GET") {
      return json({ moneda: estado.moneda, declarada: estado.moneda !== null, lista: null, aviso: null });
    }
    if (ruta === "/v1/carpeta/moneda" && metodo === "PUT") {
      estado.moneda = String(datos["moneda"]);
      return json({ moneda: estado.moneda, declarada: true, lista: null, aviso: null });
    }
    if (ruta === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: estado.borradores });
    // Lo que pide el marco: las obras de la barra lateral (las de la carpeta abierta) y el tema neutro.
    if (ruta === "/v1/obras/todas" && metodo === "GET") {
      const deLaEmpresa = estado.empresa !== null && estado.actual.nombre === estado.empresa.nombre;
      const carpeta = deLaEmpresa ? null : estado.actual.nombre;
      return json({
        carpeta_actual: carpeta,
        carpeta_actual_titulo: carpeta === null ? "Carpeta de la empresa" : carpeta.replace(/\.db$/, ""),
        obras: estado.proyectos.map((p) => ({
          carpeta,
          carpeta_titulo: carpeta === null ? "Carpeta de la empresa" : carpeta.replace(/\.db$/, ""),
          obra_id: Number(p.codigo),
          obra: p.nombre,
          version_codigo: p.version_vigente === null ? null : String(p.version_vigente).padStart(3, "0"),
        })),
      });
    }
    // La bandeja de Pendientes (rediseño F3): sin pendientes, salvo que la prueba responda otra cosa en `antes`.
    if (ruta === "/v1/obras/pendientes/todas" && metodo === "GET") return json({ pendientes: [], carpetas_omitidas: 0 });
    if (ruta === "/v1/tema" && metodo === "GET") {
      return json({ acento: null, marco: null, lateral: null, tiene_logo: false, avisos: [] });
    }
    if ((ruta === "/v1/sesion/proyecto" || ruta === "/v1/sesion/preferencias") && metodo === "PUT") {
      return new Response(null, { status: 204 });
    }
    return json({ detalle: "No encontrado." }, 404);
  };
  const de = (metodo: string, ruta: string) => llamadas.filter((l) => l.metodo === metodo && l.ruta === ruta);
  return { fetchFalso, llamadas, de, estado };
}

// Las pantallas del registro con un h1 con su titulo (sin bajar las paginas reales), salvo las que la prueba cambie.
export function ligeras(propias: Record<string, ComponentType> = {}): PaginaDef[] {
  return PAGINAS.map((p) => {
    const Propia = propias[p.id];
    const Ligera = Propia ?? (() => <h1>{p.titulo}</h1>);
    return { ...p, cargar: async () => ({ default: Ligera }) };
  });
}

// Rediseño F3, Tarea 2: `#/pendientes` monta la bandeja y la mesa solo vive en el Resumen de una obra, que la fija en la
// sesión. Sus pruebas la miran sin obra elegida, como era la entrada: la montan en `#/mesa`, una pantalla más del
// registro (no es sección de la obra ni entrada de Empresa, así que el marco la monta donde está, sin redirigir). El
// Resumen de las obras que la prueba abre (`obras`) también es la mesa.
export const RUTA_DE_LA_MESA = "/mesa";
export function conLaMesa(mesa: ComponentType, propias: Record<string, ComponentType> = {}): PaginaDef[] {
  const paginas = ligeras({ obras: mesa, ...propias });
  const resumen = paginas.find((p) => p.id === "obras");
  if (!resumen) throw new Error("El registro no tiene la mesa.");
  return [...paginas, { ...resumen, id: RUTA_DE_LA_MESA.slice(1) }];
}

// El marco completo en `ruta`, con el registro de pantallas ligeras.
export function montarMarco(sesion: SesionRespuesta, ruta: string, paginas: readonly PaginaDef[] = ligeras()) {
  const alSalir = vi.fn();
  const alExpirar = vi.fn();
  const vista = render(
    <MemoryRouter initialEntries={[ruta]}>
      <Marco sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
    </MemoryRouter>,
  );
  return { ...vista, alSalir, alExpirar };
}
