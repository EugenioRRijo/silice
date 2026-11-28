// Máquina de estados pura de navegación espacial y edición de celdas de la grilla (lote B1-2a).
// Sigue la guía `spatial-navigation` de Google: una sola parada de tabulación (Tab no se consume),
// preservación del desplazamiento nativo en los bordes (consumir = false cuando no hay celda vecina)
// y descarte de modificadores, eventos ya prevenidos o teclas propias del campo en edición.

export interface PosicionDeCelda {
  readonly fila: number;
  readonly columna: number;
}

export type DireccionDeFlecha = "arriba" | "abajo" | "izquierda" | "derecha";

export type EstadoNavegarDeGrilla = {
  readonly modo: "navegar";
  readonly activa: PosicionDeCelda;
};

export type EstadoEditarDeGrilla = {
  readonly modo: "editar";
  readonly activa: PosicionDeCelda;
  readonly valorOriginal: string;
  readonly borrador: string;
};

export type EstadoDeGrilla = EstadoNavegarDeGrilla | EstadoEditarDeGrilla;

export type EventoDeGrilla =
  | {
      readonly tipo: "flecha";
      readonly direccion: DireccionDeFlecha;
      readonly filas: number;
      readonly columnas: number;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "inicio";
      readonly columnas: number;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "fin";
      readonly columnas: number;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "f2";
      readonly valorCelda: string | null;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "enter";
      readonly filas: number;
      readonly valorCelda?: string | null | undefined;
      readonly componiendo?: boolean | undefined;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "caracter";
      readonly caracter: string;
      readonly valorCelda?: string | null | undefined;
      readonly componiendo?: boolean | undefined;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "cambiar";
      readonly valor: string;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "escape";
      readonly componiendo?: boolean | undefined;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "tab";
      readonly conShift?: boolean | undefined;
      readonly componiendo?: boolean | undefined;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    }
  | {
      readonly tipo: "activar";
      readonly celda: PosicionDeCelda;
      readonly filas: number;
      readonly columnas: number;
      readonly conModificador?: boolean | undefined;
      readonly yaPrevenido?: boolean | undefined;
    };

export type EfectoDeEdicion =
  | {
      readonly tipo: "confirmar";
      readonly celda: PosicionDeCelda;
      readonly valor: string;
    }
  | {
      readonly tipo: "restaurar";
      readonly celda: PosicionDeCelda;
      readonly valor: string;
    };

export interface TransicionDeGrilla {
  readonly estado: EstadoDeGrilla;
  readonly activa: PosicionDeCelda;
  readonly consumir: boolean;
  readonly edicion: EfectoDeEdicion | null;
}

export interface EntradaDeTeclado {
  readonly key: string;
  readonly ctrlKey?: boolean | undefined;
  readonly altKey?: boolean | undefined;
  readonly metaKey?: boolean | undefined;
  readonly shiftKey?: boolean | undefined;
  readonly isComposing?: boolean | undefined;
  readonly defaultPrevented?: boolean | undefined;
}

export interface ContextoDeTecla {
  readonly filas: number;
  readonly columnas: number;
  readonly valorCelda: string | null;
}

export function estadoInicialDeGrilla(
  activa: PosicionDeCelda = { fila: 0, columna: 0 },
): EstadoDeGrilla {
  return {
    modo: "navegar",
    activa: { fila: activa.fila, columna: activa.columna },
  };
}

function sinCambio(estado: EstadoDeGrilla): TransicionDeGrilla {
  return {
    estado,
    activa: estado.activa,
    consumir: false,
    edicion: null,
  };
}

function navegarHacia(activa: PosicionDeCelda): TransicionDeGrilla {
  return {
    estado: { modo: "navegar", activa },
    activa,
    consumir: true,
    edicion: null,
  };
}

function iniciarEdicion(
  activa: PosicionDeCelda,
  valorOriginal: string,
  borrador: string,
): TransicionDeGrilla {
  return {
    estado: {
      modo: "editar",
      activa,
      valorOriginal,
      borrador,
    },
    activa,
    consumir: true,
    edicion: null,
  };
}

function confirmarEdicion(
  estado: EstadoEditarDeGrilla,
  nuevaActiva: PosicionDeCelda,
  consumir: boolean,
): TransicionDeGrilla {
  return {
    estado: { modo: "navegar", activa: nuevaActiva },
    activa: nuevaActiva,
    consumir,
    edicion: {
      tipo: "confirmar",
      celda: estado.activa,
      valor: estado.borrador,
    },
  };
}

function celdaEnRango(
  celda: PosicionDeCelda,
  filas: number,
  columnas: number,
): boolean {
  return (
    celda.fila >= 0 &&
    celda.fila < filas &&
    celda.columna >= 0 &&
    celda.columna < columnas
  );
}

function esCaracterImprimible(caracter: string): boolean {
  if (caracter.length !== 1) {
    return false;
  }
  const codigo = caracter.charCodeAt(0);
  return codigo >= 0x20 && (codigo < 0x7f || codigo > 0x9f);
}

function desplazarPorFlecha(
  activa: PosicionDeCelda,
  direccion: DireccionDeFlecha,
): PosicionDeCelda {
  switch (direccion) {
    case "arriba":
      return { fila: activa.fila - 1, columna: activa.columna };
    case "abajo":
      return { fila: activa.fila + 1, columna: activa.columna };
    case "izquierda":
      return { fila: activa.fila, columna: activa.columna - 1 };
    case "derecha":
      return { fila: activa.fila, columna: activa.columna + 1 };
  }
}

export function siguiente(
  estado: EstadoDeGrilla,
  evento: EventoDeGrilla,
): TransicionDeGrilla {
  if (evento.conModificador || evento.yaPrevenido) {
    return sinCambio(estado);
  }

  switch (evento.tipo) {
    case "flecha": {
      if (estado.modo === "editar") {
        return sinCambio(estado);
      }
      const destino = desplazarPorFlecha(estado.activa, evento.direccion);
      if (!celdaEnRango(destino, evento.filas, evento.columnas)) {
        return sinCambio(estado);
      }
      return navegarHacia(destino);
    }

    case "inicio": {
      if (
        estado.modo === "editar" ||
        evento.columnas <= 0 ||
        estado.activa.columna <= 0
      ) {
        return sinCambio(estado);
      }
      return navegarHacia({ fila: estado.activa.fila, columna: 0 });
    }

    case "fin": {
      const ultimaColumna = evento.columnas - 1;
      if (
        estado.modo === "editar" ||
        evento.columnas <= 0 ||
        estado.activa.columna >= ultimaColumna
      ) {
        return sinCambio(estado);
      }
      return navegarHacia({ fila: estado.activa.fila, columna: ultimaColumna });
    }

    case "f2": {
      if (estado.modo === "editar" || evento.valorCelda === null) {
        return sinCambio(estado);
      }
      return iniciarEdicion(estado.activa, evento.valorCelda, evento.valorCelda);
    }

    case "enter": {
      if (evento.componiendo) {
        return sinCambio(estado);
      }
      if (estado.modo === "navegar") {
        if (evento.valorCelda === null || evento.valorCelda === undefined) {
          return sinCambio(estado);
        }
        return iniciarEdicion(
          estado.activa,
          evento.valorCelda,
          evento.valorCelda,
        );
      }
      const siguienteFila =
        evento.filas > 0 && estado.activa.fila + 1 < evento.filas
          ? estado.activa.fila + 1
          : estado.activa.fila;
      const activa: PosicionDeCelda = {
        fila: siguienteFila,
        columna: estado.activa.columna,
      };
      return confirmarEdicion(estado, activa, true);
    }

    case "caracter": {
      if (evento.componiendo || !esCaracterImprimible(evento.caracter)) {
        return sinCambio(estado);
      }
      if (estado.modo === "navegar") {
        if (evento.valorCelda === null || evento.valorCelda === undefined) {
          return sinCambio(estado);
        }
        return iniciarEdicion(
          estado.activa,
          evento.valorCelda,
          evento.caracter,
        );
      }
      return {
        estado: {
          modo: "editar",
          activa: estado.activa,
          valorOriginal: estado.valorOriginal,
          borrador: estado.borrador + evento.caracter,
        },
        activa: estado.activa,
        consumir: false,
        edicion: null,
      };
    }

    case "cambiar": {
      if (estado.modo === "navegar") {
        return sinCambio(estado);
      }
      return {
        estado: {
          modo: "editar",
          activa: estado.activa,
          valorOriginal: estado.valorOriginal,
          borrador: evento.valor,
        },
        activa: estado.activa,
        consumir: false,
        edicion: null,
      };
    }

    case "escape": {
      if (evento.componiendo || estado.modo === "navegar") {
        return sinCambio(estado);
      }
      return {
        estado: { modo: "navegar", activa: estado.activa },
        activa: estado.activa,
        consumir: true,
        edicion: {
          tipo: "restaurar",
          celda: estado.activa,
          valor: estado.valorOriginal,
        },
      };
    }

    case "tab": {
      if (evento.componiendo || estado.modo === "navegar") {
        return sinCambio(estado);
      }
      return confirmarEdicion(estado, estado.activa, false);
    }

    case "activar": {
      if (!celdaEnRango(evento.celda, evento.filas, evento.columnas)) {
        return sinCambio(estado);
      }
      const mismaCelda =
        estado.activa.fila === evento.celda.fila &&
        estado.activa.columna === evento.celda.columna;
      if (mismaCelda) {
        return sinCambio(estado);
      }
      const activa: PosicionDeCelda = {
        fila: evento.celda.fila,
        columna: evento.celda.columna,
      };
      if (estado.modo === "editar") {
        return confirmarEdicion(estado, activa, false);
      }
      return {
        estado: { modo: "navegar", activa },
        activa,
        consumir: false,
        edicion: null,
      };
    }
  }
}

export function eventoDesdeTecla(
  tecla: EntradaDeTeclado,
  contexto: ContextoDeTecla,
): EventoDeGrilla | null {
  if (tecla.defaultPrevented || tecla.ctrlKey || tecla.altKey || tecla.metaKey) {
    return null;
  }

  if (tecla.key === "Tab") {
    return {
      tipo: "tab",
      conShift: Boolean(tecla.shiftKey),
    };
  }

  if (esCaracterImprimible(tecla.key)) {
    return {
      tipo: "caracter",
      caracter: tecla.key,
      valorCelda: contexto.valorCelda,
      componiendo: Boolean(tecla.isComposing),
    };
  }

  if (tecla.shiftKey) {
    return null;
  }

  switch (tecla.key) {
    case "ArrowUp":
      return {
        tipo: "flecha",
        direccion: "arriba",
        filas: contexto.filas,
        columnas: contexto.columnas,
      };
    case "ArrowDown":
      return {
        tipo: "flecha",
        direccion: "abajo",
        filas: contexto.filas,
        columnas: contexto.columnas,
      };
    case "ArrowLeft":
      return {
        tipo: "flecha",
        direccion: "izquierda",
        filas: contexto.filas,
        columnas: contexto.columnas,
      };
    case "ArrowRight":
      return {
        tipo: "flecha",
        direccion: "derecha",
        filas: contexto.filas,
        columnas: contexto.columnas,
      };
    case "Home":
      return { tipo: "inicio", columnas: contexto.columnas };
    case "End":
      return { tipo: "fin", columnas: contexto.columnas };
    case "F2":
      return { tipo: "f2", valorCelda: contexto.valorCelda };
    case "Enter":
      return {
        tipo: "enter",
        filas: contexto.filas,
        valorCelda: contexto.valorCelda,
        componiendo: Boolean(tecla.isComposing),
      };
    case "Escape":
      return {
        tipo: "escape",
        componiendo: Boolean(tecla.isComposing),
      };
    default:
      return null;
  }
}
