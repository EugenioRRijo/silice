"""Un índice del BCV expresado en USD (RF-214; ola 2, línea 4, 2026-11-13).

Para el reajuste de un contrato en USD: un índice de precios en bolívares aplicado a montos en
dólares cuenta dos veces la devaluación (S1-R11). Aquí se deriva, de un índice mensual en Bs ya
importado (UC-17), su serie en USD, que se guarda como una importación más (con su huella, su
fuente y su informe) y que la cláusula de reajuste cita como cualquier otra serie: el núcleo no
cambia y el estudio guardado se recalcula igual (RNF-14).

**La regla** (simulada en la bitácora `2026-11-13-ola2-pdf-e-indices.md` §2): el valor en USD de
un mes es el índice en Bs de ese mes ÷ el promedio de la tasa del BCV de cada día del mes, donde
la tasa de cada día es la aplicable de S1-R1 (la de mayor fecha valor ≤ ese día) y no vale con más
de 7 días naturales (S1-R2). Un mes con un día sin tasa aplicable no se expresa y se dice por qué.
Divisiones con 28 dígitos y ROUND_HALF_EVEN, como `core.budget.reajuste`.

Sin red (RNF-14). `ver` no escribe; `guardar` confirma o deshace todo.
"""

from __future__ import annotations

import calendar
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from sqlalchemy import select

from aplicacion.cifras import texto_de_cifra
from core import models
from core.catalog.indices import (
    DIAS_MAXIMOS_SIN_TASA,
    LADO_POR_DEFECTO,
    SERIES_DE_TASA,
    UNIDAD_INDICE_BS,
    DefinicionSerie,
    Observacion,
    definicion_tasa,
    registrar_importacion,
)

UNIDAD_INDICE_USD = "indice_usd"
LADOS = ("venta", "compra")
#: El código de la serie nueva: el de origen con «-USD» (tasa de venta, S1-R1) o «-USD-COMPRA».
SUFIJOS = {"venta": "-USD", "compra": "-USD-COMPRA"}
LARGO_DEL_CODIGO = 40  # `serie_indice.codigo` es String(40)


class SerieInexistente(LookupError):  # noqa: N818 (como TasaNoDisponible del núcleo)
    """No hay una serie con ese código."""


class HuellaCambiada(ValueError):  # noqa: N818
    """Los valores que se guardarían no son los que se revisaron."""


@dataclass(frozen=True, slots=True)
class MesEnUsd:
    mes: date
    indice_bs: Decimal
    tasa_promedio: Decimal
    dias: int
    valor: Decimal
    provisional: bool


@dataclass(frozen=True, slots=True)
class MesOmitido:
    mes: date
    motivo: str


@dataclass(frozen=True, slots=True)
class VistaEnUsd:
    origen: str
    lado: str
    serie_nueva: str
    nombre: str
    meses: list[MesEnUsd]
    omitidos: list[MesOmitido]
    huella: str
    ya_guardada: bool


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def _dias(mes: date) -> list[date]:
    ultimo = calendar.monthrange(mes.year, mes.month)[1]
    return [date(mes.year, mes.month, d) for d in range(1, ultimo + 1)]


def _tramos(dias: Sequence[date]) -> str:
    """«del 09/02/2027 al 14/02/2027» por cada tramo de días seguidos; «el 09/02/2027» si es uno."""
    tramos: list[list[date]] = []
    for dia in dias:
        if tramos and dia - tramos[-1][-1] == timedelta(days=1):
            tramos[-1].append(dia)
        else:
            tramos.append([dia])
    return ", ".join(
        f"el {t[0]:%d/%m/%Y}" if len(t) == 1 else f"del {t[0]:%d/%m/%Y} al {t[-1]:%d/%m/%Y}"
        for t in tramos
    )


def expresar_en_usd(
    indices: Mapping[date, tuple[Decimal, bool]],
    tasas: Sequence[tuple[date, Decimal, bool]],
) -> tuple[list[MesEnUsd], list[MesOmitido]]:
    """Los meses de `indices` (primer día del mes → valor en Bs, provisional) en USD con `tasas`
    (fecha valor, Bs por USD, provisional; una por fecha), y los que no se pueden con su motivo.
    Función pura: la regla del docstring del módulo."""
    ordenadas = sorted(tasas)
    meses, omitidos = [], []
    for mes in sorted(indices):
        valor_bs, provisional = indices[mes]
        aplicables, faltan, i, vigente = [], [], 0, None
        for dia in _dias(mes):
            while i < len(ordenadas) and ordenadas[i][0] <= dia:
                vigente = ordenadas[i]
                i += 1
            if vigente is None or (dia - vigente[0]).days > DIAS_MAXIMOS_SIN_TASA:
                faltan.append(dia)
            else:
                aplicables.append(vigente)
        if faltan:
            omitidos.append(
                MesOmitido(
                    mes,
                    f"{mes:%m/%Y}: {_tramos(faltan)} no hay tasa del BCV de los "
                    f"{DIAS_MAXIMOS_SIN_TASA} días anteriores (S1-R2)",
                )
            )
            continue
        with _contexto():
            promedio = sum((t[1] for t in aplicables), Decimal(0)) / len(aplicables)
            valor = valor_bs / promedio
        meses.append(
            MesEnUsd(
                mes,
                valor_bs,
                promedio,
                len(aplicables),
                valor,
                provisional or any(t[2] for t in aplicables),
            )
        )
    return meses, omitidos


# --- en la base ----------------------------------------------------------------------------------


def origenes(sesion) -> list[models.SerieIndice]:
    """Las series que se pueden expresar en USD: los índices mensuales en Bs, por código."""
    return list(
        sesion.scalars(
            select(models.SerieIndice)
            .where(
                models.SerieIndice.unidad == UNIDAD_INDICE_BS,
                models.SerieIndice.periodicidad == "mensual",
            )
            .order_by(models.SerieIndice.codigo)
        )
    )


def _serie(sesion, codigo: str) -> models.SerieIndice:
    serie = sesion.scalars(
        select(models.SerieIndice).where(models.SerieIndice.codigo == codigo)
    ).one_or_none()
    if serie is None:
        raise SerieInexistente(f"No hay una serie «{codigo}» importada.")
    return serie


def _vigentes(sesion, serie_id: int) -> list[tuple[date, Decimal, bool, int]]:
    """Un valor por fecha: el de la importación más reciente (como `valor_en` sin cita)."""
    filas = sesion.scalars(
        select(models.ValorIndice)
        .where(models.ValorIndice.serie_id == serie_id)
        .order_by(models.ValorIndice.fecha, models.ValorIndice.importacion_id)
    )
    por_fecha = {f.fecha: (f.fecha, f.valor, f.provisional, f.importacion_id) for f in filas}
    return [por_fecha[f] for f in sorted(por_fecha)]


def _huella(serie_nueva: str, origen: str, lado: str, meses: Sequence[MesEnUsd]) -> str:
    texto = "\n".join(
        [f"{serie_nueva}|{origen}|{lado}"]
        + [f"{m.mes.isoformat()}|{m.valor}|{int(m.provisional)}" for m in meses]
    )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _preparar(sesion, codigo: str, lado: str):
    if lado not in LADOS:
        definicion_tasa(lado)  # el ValueError del núcleo: «se espera compra o venta»
    origen = _serie(sesion, codigo)
    if origen.unidad != UNIDAD_INDICE_BS or origen.periodicidad != "mensual":
        raise ValueError(
            f"La serie «{codigo}» no es un índice mensual en bolívares: solo esos se expresan "
            "en USD."
        )
    serie_nueva = f"{codigo}{SUFIJOS[lado]}"
    if len(serie_nueva) > LARGO_DEL_CODIGO:
        raise ValueError(
            f"El código «{codigo}» es muy largo para su serie en USD ({serie_nueva}): el código "
            f"de una serie tiene hasta {LARGO_DEL_CODIGO} caracteres."
        )
    tasa = sesion.scalars(
        select(models.SerieIndice).where(models.SerieIndice.codigo == SERIES_DE_TASA[lado])
    ).one_or_none()
    if tasa is None:
        raise ValueError(
            f"No hay tasa {lado} del BCV importada: impórtela en «Índices del BCV» antes de "
            "expresar un índice en USD."
        )
    indices = _vigentes(sesion, origen.id)
    tasas = _vigentes(sesion, tasa.id)
    meses, omitidos = expresar_en_usd(
        {f: (v, p) for f, v, p, _ in indices}, [(f, v, p) for f, v, p, _ in tasas]
    )
    return origen, tasa, indices, tasas, serie_nueva, meses, omitidos


def _nombre(origen: models.SerieIndice, lado: str) -> str:
    return f"{origen.nombre} en USD (tasa {lado} promedio del mes)"[:200]


def _ya_guardada(sesion, serie_nueva: str, huella: str) -> bool:
    return (
        sesion.scalar(
            select(models.ImportacionIndice.id)
            .join(models.SerieIndice)
            .where(
                models.SerieIndice.codigo == serie_nueva, models.ImportacionIndice.huella == huella
            )
        )
        is not None
    )


def ver(sesion, codigo: str, *, lado: str = LADO_POR_DEFECTO) -> VistaEnUsd:
    """Lo que se guardaría: la serie nueva, sus meses, los que no se pueden y la huella. No
    escribe nada."""
    origen, _, _, _, serie_nueva, meses, omitidos = _preparar(sesion, codigo, lado)
    huella = _huella(serie_nueva, codigo, lado, meses)
    return VistaEnUsd(
        codigo,
        lado,
        serie_nueva,
        _nombre(origen, lado),
        meses,
        omitidos,
        huella,
        _ya_guardada(sesion, serie_nueva, huella),
    )


def _cifra(valor: Decimal) -> str:
    return texto_de_cifra(valor.normalize())


def _informe(codigo, tasa_codigo, indices, tasas, meses, omitidos) -> str:
    citadas = sorted({i for *_, i in indices})
    de_tasas = sorted({i for *_, i in tasas})
    lineas = [
        f"Importaciones citadas: {codigo} {', '.join(map(str, citadas))}; "
        f"{tasa_codigo} {', '.join(map(str, de_tasas))}.",
        *(
            f"{m.mes:%m/%Y}: {_cifra(m.indice_bs)} ÷ {_cifra(m.tasa_promedio)} = {_cifra(m.valor)}"
            f" (promedio de {m.dias} días{', provisional' if m.provisional else ''})"
            for m in meses
        ),
        *(f"sin expresar {o.motivo}" for o in omitidos),
    ]
    return "\n".join(lineas)


def guardar(
    sesion,
    codigo: str,
    *,
    huella: str,
    responsable: str,
    ahora: datetime,
    lado: str = LADO_POR_DEFECTO,
) -> str:
    """Guarda la serie en USD como una importación (todo o nada) si sus valores son los que se
    revisaron (`huella`); la misma huella dos veces no escribe nada. Devuelve el mensaje."""
    try:
        origen, tasa, indices, tasas, serie_nueva, meses, omitidos = _preparar(sesion, codigo, lado)
        if _huella(serie_nueva, codigo, lado, meses) != huella:
            raise HuellaCambiada(
                "Los índices o las tasas cambiaron desde que lo revisó: revíselo de nuevo."
            )
        if not meses:
            raise ValueError(
                f"Ningún mes de «{codigo}» tiene tasa del BCV para todos sus días: importe las "
                "tasas que faltan y vuelva a intentarlo."
            )
        hecho = registrar_importacion(
            sesion,
            DefinicionSerie(
                serie_nueva,
                _nombre(origen, lado),
                f"{origen.organismo} y BCV; derivada en Sílice"[:120],
                UNIDAD_INDICE_USD,
                "mensual",
                f"{codigo} ÷ {tasa.codigo}, promedio del mes"[:200],
            ),
            [Observacion(m.mes, m.valor, m.provisional) for m in meses],
            archivo=f"{codigo} en USD (derivada en Sílice)"[:255],
            huella=huella,
            fuente=(
                f"Derivada en Sílice: {codigo} ÷ el promedio del mes de {tasa.codigo}, cada día "
                "con su tasa aplicable (S1-R1 y S1-R2)"
            ),
            fecha_descarga=ahora.date(),
            responsable=responsable,
            filas_leidas=len(meses) + len(omitidos),
            filas_rechazadas=len(omitidos),
            informe=_informe(codigo, tasa.codigo, indices, tasas, meses, omitidos),
            ahora=ahora,
        )
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    if hecho is None:
        return f"{serie_nueva}: ya estaba guardada con estos mismos valores; no se escribió nada."
    meses_texto = "1 mes" if len(meses) == 1 else f"{texto_de_cifra(Decimal(len(meses)))} meses"
    return f"{serie_nueva}: guardada con {meses_texto} en USD."
