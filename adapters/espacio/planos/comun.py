"""Lo que comparten los dos lectores de planos (DXF e IFC): el acumulador de filas e informe, la
asignacion de ambiente y fuente, la superficie de un punto y los numeros en `Decimal`.

Un adaptador no importa a otro (NORMAS.md §2): esto es del paquete `planos` de
`adapters/espacio` y no toma nada de `adapters/civil`. Constantes con fuente o
`SUPUESTO_DECLARADO`; ninguna inventada.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.modelo import (
    TOLERANCIA,
    Ambiente,
    Circuito,
    Fuente,
    Punto,
    Recorrido,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida
from adapters.espacio.planos.informe import (
    EstadoImportacion,
    ItemInforme,
    ResultadoImportacion,
    TipoItem,
)

#: Limite de tamano de un archivo de plano (spec §6.6, RNF-12): 20 MB.
LIMITE_BYTES = 20 * 1024 * 1024

#: Decimales con que se guardan las medidas importadas: 0,1 mm, un orden menos que la tolerancia.
CUANTO = Decimal("0.0001")

#: Supuestos de un circuito que el plano no declara (los mismos de OF-001, memoria `of001.md`).
CONDUCTORES_POR_DEFECTO = Constante(
    "SF5-1",
    "Conductores de un circuito importado (fase, neutro, tierra)",
    "1-1-1",
    SUPUESTO_DECLARADO,
)
PUNTOS_MAXIMOS_POR_DEFECTO = Constante(
    "SF5-2", "Puntos maximos de un circuito importado", Decimal(6), SUPUESTO_DECLARADO
)
CALIBRE_PENDIENTE = "pendiente"

#: Tipos de fuente que sirven a cada tipo de punto (la electricidad usa circuito y tablero).
FUENTES_DE = {
    TipoPunto.AGUA_FRIA: frozenset({TipoFuente.ACOMETIDA_AGUA, TipoFuente.MONTANTE_AGUA}),
    TipoPunto.DRENAJE: frozenset({TipoFuente.COLECTOR_DRENAJE}),
    TipoPunto.DATOS: frozenset({TipoFuente.RACK}),
}


def numero(texto: str | None) -> Decimal | None:
    """`'2,5'` o `'2.5'` -> `Decimal('2.5')`; None si no es un numero finito."""
    if texto is None:
        return None
    try:
        valor = Decimal(texto.strip().replace(",", "."))
    except InvalidOperation:
        return None
    return valor if valor.is_finite() else None


def decimal(valor: float, factor: Decimal = Decimal(1)) -> Decimal:
    """Un `float` de un archivo de plano en metros: `repr` (sin ruido binario) por el factor."""
    return (Decimal(repr(float(valor))) * factor).quantize(CUANTO)


def superficie_de(tipo: TipoPunto, z: Decimal) -> SuperficiePunto:
    """Superficie de un punto cuando el plano no la dice: la iluminacion va en el techo; lo demas,
    en el piso si su cota es 0 y si no, en la pared. No depende de la altura del ambiente, que
    puede estar pendiente."""
    if tipo is TipoPunto.ILUMINACION:
        return SuperficiePunto.TECHO
    return SuperficiePunto.PISO if z <= TOLERANCIA else SuperficiePunto.PARED


def contiene_en_planta(a: Ambiente, x: Decimal, y: Decimal) -> bool:
    t = TOLERANCIA
    return a.x0 - t <= x <= a.x0 + a.largo + t and a.y0 - t <= y <= a.y0 + a.ancho + t


def fuente_para(punto: Punto, fuentes: Iterable[Fuente]) -> tuple[Fuente | None, bool]:
    """La fuente de un punto: la compatible de su mismo ambiente; si no hay o hay varias, la mas
    cercana (empate: id menor). `(fuente, por_cercania)`; `(None, False)` si ninguna sirve."""
    validas = FUENTES_DE.get(punto.tipo)
    if not validas:
        return None, False
    compatibles = sorted((f for f in fuentes if f.tipo in validas), key=lambda f: f.id)
    if not compatibles:
        return None, False
    del_ambiente = [f for f in compatibles if f.ambiente_id == punto.ambiente_id]
    if len(del_ambiente) == 1:
        return del_ambiente[0], False
    candidatas = del_ambiente or compatibles
    return min(candidatas, key=lambda f: (f.posicion.distancia(punto.posicion), f.id)), True


def digitos_finales(id_: str) -> int | None:
    m = re.search(r"(\d+)$", id_)
    return int(m.group(1)) if m else None


def _por_id(filas: dict) -> tuple:
    """Las filas ordenadas por `id`: mismo plano, mismo resultado (determinismo)."""
    return tuple(filas[k] for k in sorted(filas))


class Acumulador:
    """Junta las filas y el informe de una importacion y arma el `ResultadoImportacion`."""

    def __init__(self, formato: str, archivo: str) -> None:
        self.formato = formato
        self.archivo = archivo
        self.origenes: dict[str, OrigenMedida] = {}
        self.ambientes: dict[str, Ambiente] = {}
        self.fuentes: dict[str, Fuente] = {}
        self.puntos: dict[str, Punto] = {}
        self.circuitos: dict[str, Circuito] = {}
        self.recorridos: dict[str, Recorrido] = {}
        self.informe: list[ItemInforme] = []

    def item(
        self, tipo: TipoItem, tabla: str, mensaje: str, referencia: str = "", fila: str = ""
    ) -> None:
        self.informe.append(ItemInforme(tipo, tabla, referencia, fila, mensaje))

    def importado(self, tabla: str, referencia: str, fila: str, que: str) -> None:
        self.item(TipoItem.IMPORTADO, tabla, f"{que} {fila}: importado", referencia, fila)

    def resultado(
        self,
        estado: EstadoImportacion = EstadoImportacion.IMPORTADA,
        mensaje: str = "",
        pide_unidad: bool = False,
    ) -> ResultadoImportacion:
        return ResultadoImportacion(
            formato=self.formato,
            archivo=self.archivo,
            estado=estado,
            mensaje=mensaje,
            pide_unidad=pide_unidad,
            origenes=_por_id(self.origenes),
            ambientes=_por_id(self.ambientes),
            fuentes=_por_id(self.fuentes),
            circuitos=_por_id(self.circuitos),
            puntos=_por_id(self.puntos),
            recorridos=_por_id(self.recorridos),
            informe=tuple(self.informe),
        )


def sin_filas(
    formato: str,
    archivo: str,
    estado: EstadoImportacion,
    mensaje: str,
    pide_unidad: bool = False,
) -> ResultadoImportacion:
    """Resultado sin filas (archivo rechazado o importacion detenida)."""
    return Acumulador(formato, archivo).resultado(estado, mensaje, pide_unidad)


def en_una_linea(texto: object, largo: int = 120) -> str:
    """Texto de error de una biblioteca, en una linea y acotado (RNF-12: nunca una traza)."""
    plano = " ".join(str(texto).split())
    return plano if len(plano) <= largo else plano[: largo - 3] + "..."
