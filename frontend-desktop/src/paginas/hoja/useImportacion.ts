import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { esBorradorAusente } from "./logica";
import type { Resumen } from "./logica";
import {
  AVISO_SIN_ARCHIVO,
  cuerpoDeAlturas,
  cuerpoDeCircuitos,
  cuerpoDeUnidad,
  esImportacionPerdida,
  formularioDeLectura,
  rutaDeAlturas,
  rutaDeCircuitos,
  rutaDeFusion,
  rutaDePlano,
  rutaDeUnidad,
  textoDeAlturasCargadas,
  textoDeCircuitosDeclarados,
  textoDeLector,
} from "./logicaPlano";
import type {
  FilaDeInforme,
  ImportacionRespuesta,
  RespuestaDeFusion,
  ResumenDeFusionRespuesta,
  ValoresDeCircuito,
} from "./logicaPlano";
import { claseDeConflicto } from "./logicaSecciones";

// Lo que quedó de la última fusión: se muestra como «Informe de la última fusión» (ui/paginas/hoja.py:1479-1485).
export interface FusionGuardada {
  mensaje: string;
  fusion: ResumenDeFusionRespuesta;
  informe: FilaDeInforme[];
}

export interface DatosDelPlano {
  importacion: ImportacionRespuesta | null;
  fusion: FusionGuardada | null;
  // Sube al leer un plano (o al reanudar con su unidad): los formularios de alturas y circuitos arrancan de cero.
  lectura: number;
}

export interface ErrorDePlano {
  // «conflicto»: el `rev` es viejo (409), se recarga; «perdido»: el caso cambió o el borrador ya se guardó (409), se abre de
  // nuevo; «otro»: cualquier otro fallo, con el texto del servidor tal cual.
  tipo: "conflicto" | "perdido" | "otro";
  titulo: string;
  mensaje: string;
}

const VACIO: DatosDelPlano = { importacion: null, fusion: null, lectura: 0 };

// La importación vive en el servidor (aparte del borrador, por borrador): aquí solo se recuerda lo último que contestó, por id de
// borrador, para que cambiar de pestaña y volver no la pierda de vista. No se pide nada al volver. Tope de borradores recordados.
const TOPE_DE_RECUERDOS = 20;
const recuerdos = new Map<string, DatosDelPlano>();

function recordar(id: string, datos: DatosDelPlano): void {
  recuerdos.delete(id);
  if (datos.importacion !== null || datos.fusion !== null) recuerdos.set(id, datos);
  while (recuerdos.size > TOPE_DE_RECUERDOS) recuerdos.delete(recuerdos.keys().next().value!);
}

// La sesión terminó o venció: nada de lo recordado debe quedar en memoria (lo llama también el marco al salir).
export function olvidarImportaciones(): void {
  recuerdos.clear();
}

interface Opciones {
  id: string;
  // El `rev` del borrador según la página; cada petición manda el vigente.
  rev: number;
  alAusente: () => void;
  // El servidor aceptó una fusión: su resumen (rev, total, cambios...) es ahora el del borrador.
  alAceptar: (resumen: Resumen) => void;
  // Vuelve a leer el borrador y las tablas del espacio (tras un 409 de `rev` y tras fusionar, que cambia el borrador).
  alRecargar: () => Promise<void>;
  alExpirar: () => void;
  // Avisa a la página que el flujo ocupa el espacio (desde que se pulsa «Fusionar» hasta que se vuelve a leer): mientras tanto
  // las tablas del espacio no se editan. Una edición que saliera con el `rev` nuevo y las filas de antes borraría lo fusionado.
  alOcuparse?: (ocupada: boolean) => void;
}

// El estado del flujo «Importar plano» (P1 a P6): guarda la última respuesta, manda una petición a la vez con el `rev`
// vigente y deja el error del servidor para mostrarlo tal cual. No calcula nada: las cuentas y los textos vienen del servidor.
export function useImportacion(opciones: Opciones) {
  const [datos, setDatos] = useState<DatosDelPlano>(() => recuerdos.get(opciones.id) ?? VACIO);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [error, setError] = useState<ErrorDePlano | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [detenido, setDetenido] = useState(false);
  // Sube cada vez que una acción termina: la pantalla lleva el foco al resultado.
  const [foco, setFoco] = useState(0);

  const actuales = useRef(opciones);
  const vigentes = useRef(datos);
  const motor = useRef({ enVuelo: false, detenido: false });
  useEffect(() => {
    actuales.current = opciones;
  });

  const aplicar = useCallback((nuevos: DatosDelPlano) => {
    vigentes.current = nuevos;
    recordar(actuales.current.id, nuevos);
    setDatos(nuevos);
  }, []);

  const tratar = useCallback(
    (e: unknown, titulo: string) => {
      const o = actuales.current;
      if (e instanceof ErrorDeApi && e.estado === 401) {
        olvidarImportaciones();
        o.alExpirar();
      } else if (esBorradorAusente(e)) {
        recordar(o.id, VACIO);
        o.alAusente();
      } else if (e instanceof ErrorDeApi && e.estado === 409) {
        const clase = claseDeConflicto(e.detalle);
        if (clase === "otro") {
          setError({ tipo: "otro", titulo, mensaje: e.detalle });
          if (esImportacionPerdida(e.detalle)) aplicar({ ...vigentes.current, importacion: null });
        } else {
          motor.current.detenido = true; // hasta recargar (o abrir de nuevo) no se manda más
          setDetenido(true);
          setError({ tipo: clase === "rev" ? "conflicto" : "perdido", titulo, mensaje: e.detalle });
        }
      } else {
        setError({ tipo: "otro", titulo, mensaje: textoDeLector(mensajeDeError(e)) });
      }
    },
    [aplicar],
  );

  // Una petición a la vez: con otra en vuelo (o detenido por un conflicto) no se manda nada.
  const ejecutar = useCallback(
    async <T>(
      titulo: string,
      ocupadoCon: string,
      llamar: (rev: number) => Promise<T>,
      alExito: (respuesta: T) => void | Promise<void>,
      bloqueaElEspacio = false,
    ) => {
      const m = motor.current;
      if (m.enVuelo || m.detenido) return;
      m.enVuelo = true;
      setOcupado(ocupadoCon);
      setError(null);
      setAviso(null);
      if (bloqueaElEspacio) actuales.current.alOcuparse?.(true);
      try {
        await alExito(await llamar(actuales.current.rev));
      } catch (e) {
        tratar(e, titulo);
      } finally {
        m.enVuelo = false;
        if (bloqueaElEspacio) actuales.current.alOcuparse?.(false);
        setOcupado(null);
        setFoco((n) => n + 1);
      }
    },
    [tratar],
  );

  const leer = useCallback(
    (archivo: File) =>
      ejecutar(
        "No se pudo leer el plano",
        "Leyendo el plano…",
        (rev) => pedir<ImportacionRespuesta>(rutaDePlano(actuales.current.id), { metodo: "POST", cuerpo: formularioDeLectura(rev, archivo) }),
        (importacion) => aplicar({ importacion, fusion: null, lectura: vigentes.current.lectura + 1 }),
      ),
    [ejecutar, aplicar],
  );

  const faltaArchivo = useCallback(() => {
    setAviso(null);
    setError({ tipo: "otro", titulo: "No se pudo leer el plano", mensaje: AVISO_SIN_ARCHIVO });
    setFoco((n) => n + 1);
  }, []);

  const reanudar = useCallback(
    (unidad: string) =>
      ejecutar(
        "No se continuó con esa unidad",
        "Leyendo el plano con esa unidad…",
        (rev) => pedir<ImportacionRespuesta>(rutaDeUnidad(actuales.current.id), { metodo: "POST", cuerpo: cuerpoDeUnidad(rev, unidad) }),
        (importacion) => aplicar({ ...vigentes.current, importacion, lectura: vigentes.current.lectura + 1 }),
      ),
    [ejecutar, aplicar],
  );

  const cargarAlturas = useCallback(
    (textos: Record<string, string>) => {
      const pendientes = vigentes.current.importacion?.alturas_pendientes ?? [];
      return ejecutar(
        "No se cargaron las alturas",
        "Cargando las alturas…",
        (rev) => pedir<ImportacionRespuesta>(rutaDeAlturas(actuales.current.id), { metodo: "POST", cuerpo: cuerpoDeAlturas(rev, pendientes, textos) }),
        (importacion) => {
          aplicar({ ...vigentes.current, importacion });
          setAviso(textoDeAlturasCargadas(pendientes.map((p) => textos[p.id] ?? ""), importacion.alturas_pendientes.length));
        },
      );
    },
    [ejecutar, aplicar],
  );

  const declarar = useCallback(
    (valores: Record<string, ValoresDeCircuito>) => {
      const supuestos = vigentes.current.importacion?.circuitos_supuestos ?? [];
      return ejecutar(
        "No se declararon los circuitos",
        "Declarando los circuitos…",
        (rev) => pedir<ImportacionRespuesta>(rutaDeCircuitos(actuales.current.id), { metodo: "POST", cuerpo: cuerpoDeCircuitos(rev, supuestos, valores) }),
        (importacion) => {
          aplicar({ ...vigentes.current, importacion });
          setAviso(textoDeCircuitosDeclarados(supuestos.length));
        },
      );
    },
    [ejecutar, aplicar],
  );

  const fusionar = useCallback(
    () =>
      ejecutar(
        "No se pudo fusionar",
        "Fusionando con el espacio del borrador…",
        (rev) => pedir<RespuestaDeFusion>(rutaDeFusion(actuales.current.id), { metodo: "POST", cuerpo: { rev } }),
        async (r) => {
          aplicar({
            importacion: null,
            fusion: { mensaje: r.mensaje, fusion: r.fusion, informe: r.informe },
            lectura: vigentes.current.lectura,
          });
          // La fusión cambió el borrador: la página toma su resumen y el espacio vuelve a leer sus tablas.
          actuales.current.alAceptar(r.resumen);
          // Hasta que la relectura termina el flujo sigue ocupado y el espacio sin editar.
          await actuales.current.alRecargar().catch(() => undefined);
        },
        true,
      ),
    [ejecutar, aplicar],
  );

  const descartar = useCallback(
    () =>
      ejecutar(
        "No se pudo descartar la importación",
        "Descartando la importación…",
        () => pedir(rutaDePlano(actuales.current.id), { metodo: "DELETE" }),
        () => {
          aplicar({ importacion: null, fusion: null, lectura: vigentes.current.lectura });
          setAviso("Se descartó la importación.");
        },
      ),
    [ejecutar, aplicar],
  );

  // Tras un 409 por `rev`: se vuelve a leer el borrador y se sigue donde estaba.
  const recargar = useCallback(async () => {
    try {
      await actuales.current.alRecargar();
    } finally {
      motor.current.detenido = false;
      setDetenido(false);
      setError(null);
      setFoco((n) => n + 1); // el botón «Recargar el borrador» desaparece: el foco va al resultado vigente
    }
  }, []);

  return { datos, ocupado, error, aviso, detenido, foco, leer, faltaArchivo, reanudar, cargarAlturas, declarar, fusionar, descartar, recargar };
}
