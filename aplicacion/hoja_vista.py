"""La base de las vistas de la hoja del proyecto en la interfaz nueva (T10, 3b-1; diseno §4.2).

Lo que la API arma a partir del borrador vivo sin repetir logica de la hoja: `elaborar(borrador)`
es la UNICA via de la interfaz nueva a `aplicacion.hoja.elaborar_borrador` y agrega R17 (la
conexion de cada punto) ligada al espacio que se elabora, sin guardarla en el borrador (como
`_elaborar` de la pagina clasica, P:286-296); `calculo(vivo)` lo hace una vez por `rev`;
`resumen` y `base` son los contratos `Resumen` y `BaseAbierta`. Las cifras viajan como `Monto`
`{texto, exacto}`: `texto` a dos decimales, como la clasica, y `exacto` sin notacion cientifica;
la interfaz no calcula ni redondea. Sin FastAPI ni Streamlit.

Las 3b-2 y 3b-3 anaden aqui las vistas de cada pestana.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from adapters.espacio.conexion import con_conexion
from aplicacion import hoja
from aplicacion.hoja_borradores import BorradorVivo
from core.contracts import Severidad
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal


@dataclass(frozen=True, slots=True)
class Monto:
    """Una cifra: `texto` a dos decimales (como la clasica) y `exacto` sin redondear."""

    texto: str
    exacto: str


@dataclass(frozen=True, slots=True)
class HallazgosDeSeveridad:
    severidad: str
    total: int


@dataclass(frozen=True, slots=True)
class BaseAbierta:
    """Que se abrio: el proyecto, la version (o `None`: proyecto sin versiones) y como esta."""

    proyecto: str
    version: str | None
    vigente: str | None
    lista: str | None
    espacio_de: str | None
    solo_lectura: bool
    moneda: str


@dataclass(frozen=True, slots=True)
class ResumenHoja:
    """`Resumen` del contrato (§4.2): lo que muestra la barra de estado del borrador."""

    rev: int
    moneda: str
    total: Monto
    cambios: int
    pendientes_catalogo: int
    hallazgos: tuple[HallazgosDeSeveridad, ...]
    hay_plan: bool
    version_mas_nueva: str | None
    guardado_como: str | None


def monto(valor: Decimal) -> Monto:
    """`texto` como la clasica (dos decimales) y `exacto`; con precision de sobra para que una
    cifra de muchos digitos no falle al redondear (el contexto por omision tiene 28)."""
    with localcontext() as contexto:
        contexto.prec = max(60, len(valor.as_tuple().digits) + 10)
        return Monto(formatear_decimal(valor, DECIMALES_PRESENTACION), format(valor, "f"))


def version_por_omision(filas: Sequence[hoja.FilaVersion]) -> str | None:
    """La version que se preselecciona (P:417-421): entre las no descartadas (si todas lo estan,
    entre todas), la vigente; si ninguna lo es, la ultima. `None` sin versiones."""
    codigos = [f.codigo for f in filas if not f.descartada] or [f.codigo for f in filas]
    if not codigos:
        return None
    return next((f.codigo for f in filas if f.vigente and f.codigo in codigos), codigos[-1])


def mensaje_instantanea(creadas: int) -> str | None:
    """El aviso de que abrir congelo la instantanea de las composiciones (UC-15e; P:346-351)."""
    if not creadas:
        return None
    return (
        "Se creó y registró la instantánea de las composiciones de esta versión "
        f"({creadas} partidas): sus APU ya no cambian si cambia el catálogo."
    )


def elaborar(borrador: hoja.Borrador) -> hoja.ResultadoHoja:
    """Elabora el borrador con R17 del espacio vigente; la reemplaza si ya traia una vieja y no
    toca el borrador (las reglas extra no cuentan como cambios)."""
    ligado = replace(borrador, reglas_extra=con_conexion(borrador.reglas_extra, borrador.espacio))
    return hoja.elaborar_borrador(ligado)


def _base_de_comparacion(vivo: BorradorVivo) -> hoja.Borrador:
    if vivo.abierta is not None:
        return vivo.abierta.borrador
    return hoja.Borrador(fecha=vivo.borrador.fecha, moneda=vivo.borrador.moneda)


def calculo(vivo: BorradorVivo) -> tuple[hoja.ResultadoHoja, list]:
    """El resultado y los cambios del borrador vivo; se calculan una vez por `rev`."""
    with vivo.cerrojo:
        if vivo.calculo is None or vivo.calculo[0] != vivo.rev:
            resultado = elaborar(vivo.borrador)
            cambios = hoja.cambios_entre(_base_de_comparacion(vivo), vivo.borrador)
            vivo.calculo = (vivo.rev, resultado, cambios)
        return vivo.calculo[1], vivo.calculo[2]


def resumen(vivo: BorradorVivo, version_mas_nueva: str | None = None) -> ResumenHoja:
    resultado, cambios = calculo(vivo)
    presupuesto = resultado.elaboracion.presupuesto
    por_severidad: dict[int, int] = {}
    for hallazgo in resultado.elaboracion.informe.hallazgos:
        por_severidad[int(hallazgo.severidad)] = por_severidad.get(int(hallazgo.severidad), 0) + 1
    hallazgos = tuple(
        HallazgosDeSeveridad(Severidad(n).name, por_severidad[n])
        for n in sorted(por_severidad, reverse=True)
    )
    return ResumenHoja(
        rev=vivo.rev,
        moneda=presupuesto.moneda,
        total=monto(presupuesto.total),
        cambios=len(cambios),
        pendientes_catalogo=len(resultado.elaboracion.pendientes),
        hallazgos=hallazgos,
        hay_plan=vivo.borrador.plan is not None,
        version_mas_nueva=version_mas_nueva,
        guardado_como=vivo.guardado_como,
    )


def base(vivo: BorradorVivo, vigente: str | None) -> BaseAbierta:
    abierta = vivo.abierta
    return BaseAbierta(
        proyecto=vivo.proyecto,
        version=vivo.version,
        vigente=vigente,
        lista=None if abierta is None else abierta.lista,
        espacio_de=None if abierta is None else abierta.espacio_de,
        solo_lectura=False if abierta is None else abierta.solo_lectura,
        moneda=vivo.borrador.moneda,
    )
