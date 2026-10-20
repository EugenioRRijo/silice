// API simulada de /v1/produccion para las pruebas de la pagina (solo la importan los *.test.tsx).
// Los datos son inventados (ejemplos construidos); no hay nada real de una arenera.
import { vi } from "vitest";
import type { ExistenciaRespuesta, MaterialRespuesta, SospechosoRespuesta } from "./tipos";

export function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

export interface Llamada {
  metodo: string;
  ruta: string; // sin la consulta
  consulta: URLSearchParams;
  cuerpo: unknown; // JSON ya leido (o null)
  formulario: FormData | null;
}

export const MATERIALES: MaterialRespuesta[] = [
  { id: 1, codigo: "ARE-01", nombre: "Arena lavada", unidad_venta: "m3", densidad_t_m3: "1.6", existencia_minima: "50", activo: true },
  { id: 2, codigo: "PIE-01", nombre: "Piedra picada", unidad_venta: "t", densidad_t_m3: null, existencia_minima: "20.000", activo: true },
  { id: 3, codigo: "GRA-01", nombre: "Granzón", unidad_venta: "m3", densidad_t_m3: null, existencia_minima: "10", activo: true },
];

export const EXISTENCIAS: ExistenciaRespuesta[] = [
  { codigo: "ARE-01", nombre: "Arena lavada", unidad_venta: "m3", existencia: "120.5000", minima: "50", queda_poco: false, negativa: false },
  { codigo: "PIE-01", nombre: "Piedra picada", unidad_venta: "t", existencia: "15", minima: "20.000", queda_poco: true, negativa: false },
  { codigo: "GRA-01", nombre: "Granzón", unidad_venta: "m3", existencia: "-4.25", minima: "10", queda_poco: true, negativa: true },
];

export const SOSPECHOSOS: SospechosoRespuesta[] = [
  {
    id: 7,
    huella_archivo: "f".repeat(64),
    fila: 12,
    ticket: "T-0042",
    fecha_texto: "2026-10-15",
    placa: "A12BC3D",
    material_texto: "arena lavada",
    bruto_texto: "31500",
    tara_texto: "12000",
    neto_texto: "20500",
    motivo: "El neto no es bruto menos tara",
    estado: "pendiente",
  },
  {
    id: 8,
    huella_archivo: "f".repeat(64),
    fila: 15,
    ticket: "",
    fecha_texto: "15/13/2026",
    placa: "",
    material_texto: "cemento",
    bruto_texto: "28,300",
    tara_texto: "11000",
    neto_texto: "",
    motivo: "Material desconocido",
    estado: "pendiente",
  },
];

type Manejador = (llamada: Llamada) => Response | Promise<Response>;

// Un servidor en memoria. Por omision los GET devuelven `estado` y los POST contestan 201 con un cuerpo minimo; cada
// prueba cambia lo que necesita con `responder("POST /v1/produccion/movimientos", ...)`.
export function crearServidor() {
  const estado = {
    materiales: structuredClone(MATERIALES),
    existencias: structuredClone(EXISTENCIAS),
    sospechosos: structuredClone(SOSPECHOSOS),
  };
  const llamadas: Llamada[] = [];
  const manejadores = new Map<string, Manejador>();
  const fetchFalso = vi.fn<typeof fetch>();

  fetchFalso.mockImplementation(async (entrada, init) => {
    const url = new URL(String(entrada), "http://localhost");
    const metodo = init?.method ?? "GET";
    const cuerpoCrudo = init?.body;
    const formulario = cuerpoCrudo instanceof FormData ? cuerpoCrudo : null;
    const llamada: Llamada = {
      metodo,
      ruta: url.pathname,
      consulta: url.searchParams,
      cuerpo: typeof cuerpoCrudo === "string" ? (JSON.parse(cuerpoCrudo) as unknown) : null,
      formulario,
    };
    llamadas.push(llamada);
    const propio = manejadores.get(`${metodo} ${url.pathname}`);
    if (propio) return propio(llamada);
    if (metodo === "GET" && url.pathname === "/v1/produccion/materiales") return json(estado.materiales);
    if (metodo === "GET" && url.pathname === "/v1/produccion/existencias") return json(estado.existencias);
    if (metodo === "GET" && url.pathname === "/v1/produccion/pesajes-sospechosos") return json(estado.sospechosos);
    if (metodo === "POST") return json({}, 201);
    return json({ detalle: `Ruta no simulada: ${metodo} ${url.pathname}` }, 404);
  });

  return {
    estado,
    llamadas,
    fetchFalso,
    responder(clave: string, manejador: Manejador) {
      manejadores.set(clave, manejador);
    },
    // Las llamadas que coinciden, en orden.
    de(metodo: string, ruta: string): Llamada[] {
      return llamadas.filter((l) => l.metodo === metodo && l.ruta === ruta);
    },
  };
}

export type ServidorFalso = ReturnType<typeof crearServidor>;
