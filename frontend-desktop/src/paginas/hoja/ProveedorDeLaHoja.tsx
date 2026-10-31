import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import type { Resumen, VersionesRespuesta } from "./logica";
import type { OfertaDeRetomar } from "./logicaRetomar";
import type { AlCrearVersion } from "./OperacionesDePrecios";
import type { EstadoBorrador } from "./useBorrador";

// Rojo de la Tarea 3 del plan F4: solo la forma del contexto; el proveedor todavía no abre nada.
export type VersionesDeLaObra =
  | { estado: "cargando" }
  | { estado: "listo"; datos: VersionesRespuesta }
  | { estado: "error"; error: unknown };

export interface HojaDeLaObra {
  proyecto: string;
  nombreProyecto: string | null;
  versiones: VersionesDeLaObra;
  codigo: string | null | undefined;
  estado: EstadoBorrador;
  hayCambios: boolean;
  puedeEditar: boolean;
  ofrecidos: OfertaDeRetomar[];
  retomar: (o: OfertaDeRetomar) => void;
  descartarOfrecidos: () => Promise<void>;
  descartando: boolean;
  falloAlDescartar: unknown;
  existente: string | null;
  pedirVersion: (codigo: string) => void;
  refrescar: () => Promise<void>;
  aplicar: (r: Resumen) => void;
  reabrirNuevo: () => void;
  descartarCambios: () => Promise<void>;
  abrirGuardado: () => void;
  alCrearVersion: AlCrearVersion;
  exito: { proyecto: string; texto: string } | null;
  quitarExito: () => void;
  inerte: boolean;
}

export const ContextoDeLaHoja = createContext<HojaDeLaObra | null>(null);

export function useHojaDeLaObra(): HojaDeLaObra {
  const hoja = useContext(ContextoDeLaHoja);
  if (hoja === null) throw new Error("useHojaDeLaObra se usó fuera de ProveedorDeLaHoja.");
  return hoja;
}

export function ProveedorDeLaHoja({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
