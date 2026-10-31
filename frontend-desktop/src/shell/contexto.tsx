import { createContext, useContext } from "react";
import type { CasoRespuesta, SesionRespuesta } from "../api/tipos";
import type { AlmacenDelVisor } from "../visor/almacen";
import type { CrearHojaVisor } from "../visor/hojaVisor";

// Lo que toda pagina necesita saber de la aplicacion. Vive en memoria (nada en localStorage, RT-9).
export interface Aplicacion {
  sesion: SesionRespuesta;
  // Codigo de la obra (el proyecto en la API): la de la ruta dentro de una obra; fuera, la elegida en la sesion; o null.
  proyecto: string | null;
  // Nombre de esa obra; null si no hay o aun no carga la lista.
  nombreProyecto?: string | null;
  // Carpeta de trabajo (el caso en la API, la base de datos) en uso, o null mientras carga o si la API no lo informa.
  caso: CasoRespuesta | null;
  // Las especialidades que la instalacion apago (`GET /v1/modulos`, plan vial Tarea 19): sus pantallas no se ofrecen ni se
  // abren. Sin esta lista (pruebas, o la API no la dio) no se oculta nada: la API sigue cortando.
  modulosApagados?: readonly string[];
  // Vuelve a leer lo apagado; Administracion › Especialidades lo llama al encender o apagar una.
  recargarModulos?: () => void;
  // Para volver a pedir la lista de proyectos (por ejemplo, despues de crear uno).
  recargarProyectos: () => void;
  // Plan de modulos, MOD-3b. Fija la obra (el proyecto en la API) y la recuerda para la cuenta (`PUT /v1/sesion/proyecto`).
  elegirObra?: (codigo: string | null) => void;
  // Abre el dialogo «Nueva obra» del marco (el de la barra lateral, que dice donde se creara).
  abrirNuevaObra?: () => void;
  // Abre otra carpeta de trabajo con la confirmacion y el aviso del armazon: true si la abrio, false si la persona se
  // quedo o la sesion vencio; si la API la rechaza, lanza el error. Con `preparar` (crear la carpeta), primero pregunta,
  // luego la crea y abre el nombre que `preparar` devuelve. La usa Administracion › Carpetas de trabajo. Con `abrirCon`,
  // la abre esa peticion en vez de `POST /v1/casos/actual` (la mesa, al abrir un envio por aprobar de otra carpeta, T19).
  abrirCarpeta?: (
    nombre: string,
    preparar?: () => Promise<string>,
    abrirCon?: (nombre: string) => Promise<CasoRespuesta>,
  ) => Promise<boolean>;
  // La moneda pendiente vive en el armazon (no en el formulario que crea): abrir la carpeta vuelve a montar la pagina
  // (Administracion › Carpetas de trabajo) y el aviso y su reintento no deben perderse con ella. Se olvida al cambiar de
  // carpeta. `declararMoneda` resuelve true si la declaro; si falla, la deja pendiente con su error.
  monedaPendiente?: MonedaPendiente | null;
  declararMoneda?: (carpeta: string, moneda: string) => Promise<boolean>;
  // Mientras se declara, la lista de carpetas no deja abrir otra (la moneda iria a parar a la que se abre).
  declarandoMoneda?: boolean;
  // El marco siempre da las anteriores; son opcionales para que las pruebas de cada pagina no tengan que inventarlas.
  // La API contesto 401: la sesion vencio.
  alExpirar: () => void;
  // «Libro de la empresa»: lo abierto vive por encima de la puerta de sesion (UC-26), asi que el almacen llega de
  // App. `ranuraCabecera` ya no la da el marco (V-24, T8): los controles del libro van en el cuerpo de la pagina; el
  // campo queda solo porque el visor y su prueba aun lo aceptan. `crearHojaVisor` solo cambia en pruebas.
  almacenDelLibro?: AlmacenDelVisor;
  ranuraCabecera?: HTMLElement | null;
  crearHojaVisor?: CrearHojaVisor;
}

// La moneda de una carpeta recien creada que no se pudo declarar (fallo `PUT /v1/carpeta/moneda`): se reintenta sola.
export interface MonedaPendiente {
  carpeta: string;
  moneda: string;
  error: unknown;
}

export const ContextoAplicacion = createContext<Aplicacion | null>(null);

export function useAplicacion(): Aplicacion {
  const valor = useContext(ContextoAplicacion);
  if (!valor) throw new Error("useAplicacion se usa dentro del marco.");
  return valor;
}
