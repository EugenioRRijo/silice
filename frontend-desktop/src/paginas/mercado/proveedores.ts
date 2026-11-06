// AC4 (pedido de Eugenio del 2026-10-21): el proveedor de una cotizacion se elige de los que ya se usaron en la carpeta o
// se escribe uno nuevo. `GET /v1/consulta/proveedores` los da sin repetir, como en su cotizacion mas reciente y con su
// fecha, el ultimo usado primero. Es una lista corta: se pide una vez por dialogo y se filtra en el navegador.
import { pedir } from "../../api/cliente";
import type { GrupoDeResultados } from "../../comun/logicaBusqueda";
import { filtrarPorPalabras } from "../../comun/normalizar";
import { fechaEsVe } from "../../indicadores/formatoEsVe";

export const RUTA_DE_PROVEEDORES = "/v1/consulta/proveedores";
const ROTULO = "Proveedores de cotizaciones anteriores";

export interface ProveedorUsado {
  proveedor: string;
  ultimo_uso: string; // AAAA-MM-DD: la fecha de su cotizacion mas reciente
}

interface ProveedoresRespuesta {
  proveedores: ProveedorUsado[];
}

// Los que tienen todas las palabras escritas, en cualquier orden y sin distinguir mayusculas ni tildes; en el orden del
// servidor (el ultimo usado primero).
export function filtrarProveedores(proveedores: readonly ProveedorUsado[], q: string): ProveedorUsado[] {
  return filtrarPorPalabras(proveedores, q, (p) => p.proveedor);
}

export function gruposDeProveedores(halladas: readonly ProveedorUsado[], limite: number): GrupoDeResultados<ProveedorUsado>[] {
  if (halladas.length === 0) return [];
  return [
    {
      rotulo: ROTULO,
      hayMas: halladas.length > limite,
      opciones: halladas.slice(0, limite).map((p) => ({
        clave: `proveedor:${p.proveedor}`,
        principal: p.proveedor,
        secundaria: [`Última cotización: ${fechaEsVe(p.ultimo_uso)}`],
        valor: p,
      })),
    },
  ];
}

// La funcion `buscar` de CampoConBusqueda: la lista se pide la primera vez; si falla, la siguiente busqueda la vuelve a
// pedir.
export function buscadorDeProveedores() {
  let cargada: Promise<ProveedorUsado[]> | null = null;
  return async (q: string, _senal: AbortSignal, limite: number): Promise<GrupoDeResultados<ProveedorUsado>[]> => {
    const pedido = (cargada ??= pedir<ProveedoresRespuesta | undefined>(RUTA_DE_PROVEEDORES).then((r) => r?.proveedores ?? []));
    try {
      return gruposDeProveedores(filtrarProveedores(await pedido, q), limite);
    } catch (error) {
      if (cargada === pedido) cargada = null;
      throw error;
    }
  };
}
