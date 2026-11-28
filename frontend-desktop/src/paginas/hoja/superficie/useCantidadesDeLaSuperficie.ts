import { useEffect, useMemo, useRef, useState } from "react";
import { pedir } from "../../../api/cliente";
import { rutaDeVista } from "../../../comun/borradorAbierto";
import { leerVistaPresupuesto } from "../analizadores";
import type { FilaPresupuesto, Resumen } from "../logica";
import {
  FRASES_DE_RECHAZO,
  cambiarCantidad,
  cuerpoDeCantidades,
  resembrarCantidades,
  rutaDeCantidades,
  sembrarCantidades,
  ubicarErrorDeCantidad,
} from "../logicaSecciones";
import type { EdicionDeCantidades } from "../logicaSecciones";
import { useEdicionDeSeccion } from "../useEdicionDeSeccion";
import type { EnvioDeSeccion, ErrorDeSeccion, Peticion } from "../useEdicionDeSeccion";
import type { PropiedadesDeCeldaDeCantidad } from "./CeldaDeCantidad";
import { rechazoDeLaCelda } from "./logicaDeCantidad";

// Conecta las celdas de cantidad de la grilla del Presupuesto con el motor de la edición (lote B1-5, ficha-b1 §4):
// `useEdicionDeSeccion` guarda lo escrito como texto, espera la pausa de 400 ms tras la última tecla y manda
// `PUT /v1/hoja/borradores/{id}/cantidades` con el `rev` que vio, una sola petición en vuelo (lo escrito entre tanto sale en
// otra). Un solo motor para toda la grilla: con uno por celda, dos envíos a la vez se pisarían el `rev` y darían 409.
// Lo que viaja es el texto escrito, tal cual, con coma decimal: lo interpreta el servidor (`aplicacion/cifras.py`) y la
// vista trae la cantidad en el mismo formato. Aquí no se convierte ni se calcula nada.

export interface OpcionesDeCantidades {
  // El id del borrador abierto.
  readonly borrador: string;
  // El `rev` con que está el borrador según la página (sube al aceptar una edición o al recargarlo).
  readonly rev: number;
  // Las filas de la vista del presupuesto, en el orden del servidor (de él sale «fila N» de un rechazo).
  readonly filas: readonly FilaPresupuesto[];
  readonly puedeEditar: boolean;
  // Lo que contestó el servidor al aceptar una edición: la página sube su `rev` y su resumen.
  readonly alAceptar: (resumen: Resumen) => void;
  // Pide volver a leer la vista del presupuesto y la revisión tras una edición.
  readonly alRelectura: () => void;
  // Vuelve a leer el borrador del servidor (su `rev` y su resumen), tras un 409 por `rev`.
  readonly alRecargarBorrador: () => Promise<void>;
  readonly alAusente: () => void;
  readonly alExpirar: () => void;
}

export interface CantidadesDeLaSuperficie {
  // Lo que recibe la celda de cantidad de esa fila: `<CeldaDeCantidad {...cantidades.celda(fila)} />`.
  readonly celda: (fila: Pick<FilaPresupuesto, "clave" | "partida" | "cantidad">) => PropiedadesDeCeldaDeCantidad;
  // El fallo de la última escritura: un 422 (`rechazo`) marca su celda y lo dice el aviso; un 409 (`conflicto`) pide
  // `recargar`. Se muestra con `AvisoDeEdicion`.
  readonly error: ErrorDeSeccion<number> | null;
  readonly envio: EnvioDeSeccion;
  // «Recargar el borrador» tras un 409: vuelve a leer el borrador y la vista, y siembra de nuevo lo que se ve.
  readonly recargar: () => Promise<void>;
  // Manda ya lo que espera la pausa y espera lo que va en vuelo; devuelve el `rev` con que quedó el borrador.
  readonly esperarEnvios: () => Promise<number>;
  // Escribe un texto en la cantidad de una partida desde fuera de la celda («Volver a la calculada» del inspector).
  readonly escribir: (clave: string, texto: string) => void;
  // Una acción que no puede adelantarse a lo escrito ni pisar su `rev` («Quitar» del inspector): primero sale lo escrito que
  // espera la pausa, se espera a lo que va en vuelo y entonces se manda `peticion(rev)` con el `rev` que dejó el servidor; lo
  // que se escriba mientras ella va espera y sale después. Devuelve el resumen que contestó, o null si no salió: porque el
  // servidor rechazó lo escrito antes (su aviso queda en `error`) o porque la propia acción falló (también en `error`).
  readonly accionarEnOrden: (peticion: (rev: number) => Peticion) => Promise<Resumen | null>;
}

export function useCantidadesDeLaSuperficie({
  borrador,
  rev,
  filas,
  puedeEditar,
  alAceptar,
  alRelectura,
  alRecargarBorrador,
  alAusente,
  alExpirar,
}: OpcionesDeCantidades): CantidadesDeLaSuperficie {
  const [inicial] = useState(() => sembrarCantidades([...filas]));
  const edicion = useEdicionDeSeccion<EdicionDeCantidades, number>({
    borrador,
    inicial,
    rev,
    peticion: (r, cantidades) => ({ ruta: rutaDeCantidades(borrador), metodo: "PUT", cuerpo: cuerpoDeCantidades(r, cantidades) }),
    ubicar: ubicarErrorDeCantidad,
    frase: FRASES_DE_RECHAZO.cantidades,
    leerFresca: async () =>
      sembrarCantidades((await pedir(rutaDeVista(borrador, "presupuesto"), { leer: leerVistaPresupuesto })).filas),
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const { error, envio, estado, cambiar, aceptado, esperarEnvios, accionarEnOrden, recargar, resembrar } = edicion;

  // Se agregó o se quitó un renglón (o llegó la vista): se vuelve a sembrar conservando lo escrito y no aceptado de las
  // demás filas. Volver a montar la grilla lo perdía.
  const claves = filas.map((f) => f.clave).join("\n");
  const sembradas = useRef(claves);
  useEffect(() => {
    if (sembradas.current === claves) return;
    sembradas.current = claves;
    resembrar((escrito, yaAceptado) => resembrarCantidades([...filas], escrito, yaAceptado));
  }, [claves, filas, resembrar]);

  // «fila N» de un rechazo es la posición del renglón en el presupuesto, desde 1.
  const posiciones = useMemo(() => new Map(filas.map((f, i) => [f.clave, i + 1])), [filas]);

  const escribir = (clave: string, texto: string) => cambiar((previo) => cambiarCantidad(previo, clave, texto));

  return {
    celda: (fila) => ({
      etiqueta: `Cantidad, ${fila.partida}`,
      valor: estado.textos[fila.clave] ?? fila.cantidad,
      soloLectura: !puedeEditar,
      rechazo: rechazoDeLaCelda(error, posiciones.get(fila.clave) ?? 0),
      alCambiar: (texto) => escribir(fila.clave, texto),
      alRestaurar: () =>
        cambiar((previo) => ({
          ...previo,
          textos: { ...previo.textos, [fila.clave]: aceptado().textos[fila.clave] ?? fila.cantidad },
        })),
      alConfirmar: () => {
        void esperarEnvios();
      },
    }),
    error,
    envio,
    recargar,
    esperarEnvios,
    escribir,
    accionarEnOrden,
  };
}
